from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
from typing import Any, Dict, Optional, Tuple


ISO_DT_KEYS = ("retrieved_at_utc", "published_at_utc", "event_timestamp_utc", "discovered_at_utc")


@dataclasses.dataclass
class NormalizationResult:
    status: str  # "ok" | "quarantine" | "reject"
    reason: str
    event: Optional[Dict[str, Any]] = None


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_dt(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Accept "Z" suffix
        s = s.replace("Z", "+00:00")
        try:
            t = dt.datetime.fromisoformat(s)
            return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
        except Exception:
            return None
    return None


def _is_https_url(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://")


def _try_parse_json(text: Optional[str]) -> Optional[Any]:
    if not text:
        return None
    s = text.strip()
    if not s:
        return None
    if not (s.startswith("{") or s.startswith("[")):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _sha256_text(s: str) -> bytes:
    return _sha256_bytes(s.encode("utf-8", errors="replace"))


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _scores_placeholder(discovered_at: dt.datetime) -> Tuple[int, int, int, int, str]:
    """
    Deterministic placeholder scoring until Phase 7.
    Returns: credibility, freshness, materiality, overall, confidence_enum(LOW/MEDIUM/HIGH)
    """
    credibility = 60
    materiality = 50

    age_days = 9999
    now = _now_utc()
    if discovered_at:
        age = now - discovered_at
        age_days = max(0, int(age.total_seconds() // 86400))

    if age_days <= 1:
        freshness = 90
    elif age_days <= 7:
        freshness = 75
    elif age_days <= 30:
        freshness = 55
    else:
        freshness = 35

    overall = int(round(0.4 * credibility + 0.3 * freshness + 0.3 * materiality))
    overall = max(0, min(100, overall))

    # Confidence placeholder: if it's very fresh, bump.
    if freshness >= 75:
        conf = "HIGH"
    elif freshness >= 50:
        conf = "MEDIUM"
    else:
        conf = "LOW"

    return credibility, freshness, materiality, overall, conf


def _base_event(raw: Dict[str, Any]) -> Tuple[Optional[dt.datetime], Optional[dt.datetime], Dict[str, Any]]:
    discovered_at = _parse_dt(raw.get("retrieved_at_utc")) or _parse_dt(raw.get("discovered_at_utc")) or _now_utc()
    event_time = _parse_dt(raw.get("published_at_utc")) or _parse_dt(raw.get("event_timestamp_utc")) or discovered_at

    source_url = raw.get("source_url") or ""
    source_name = raw.get("source_name") or raw.get("source_type") or "UNKNOWN"
    source_type = raw.get("source_type") or "OTHER_PUBLIC"

    return discovered_at, event_time, {
        "raw_document_id": raw.get("raw_document_id"),
        "title": _norm_ws(raw.get("title") or "Untitled"),
        "summary": _norm_ws(raw.get("summary") or raw.get("text_content") or "No summary available."),
        "discovered_at_utc": discovered_at,
        "event_timestamp_utc": event_time,
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "corroborating_sources": None,
        "theme_tags": [],
        "ambiguity_notes": None,
        "details_json": {},
    }


def _compute_source_hash(raw: Dict[str, Any], fallback_seed: str) -> bytes:
    """
    Prefer raw.content_sha256 if provided, else hash a deterministic seed.
    Accepts content_sha256 as bytes, hex string, or base64-ish string (best effort).
    """
    val = raw.get("content_sha256") or raw.get("source_hash")
    if isinstance(val, (bytes, bytearray)) and len(val) == 32:
        return bytes(val)
    if isinstance(val, str):
        s = val.strip().lower()
        # hex?
        if re.fullmatch(r"[0-9a-f]{64}", s):
            return bytes.fromhex(s)
    return _sha256_text(fallback_seed)


def _compute_event_fingerprint(identity_parts: Tuple[str, ...]) -> bytes:
    return _sha256_text("|".join([p or "" for p in identity_parts]))


def normalize_raw_document(raw: Dict[str, Any]) -> NormalizationResult:
    """
    Convert a raw_documents-like dict into an events table-like dict.
    """
    discovered_at, event_time, base = _base_event(raw)

    # Basic required checks
    if not _is_https_url(base["source_url"]):
        return NormalizationResult("reject", "source_url must be https", None)

    if not isinstance(base["title"], str) or not base["title"].strip():
        return NormalizationResult("reject", "missing title", None)

    if not isinstance(base["summary"], str) or not base["summary"].strip():
        return NormalizationResult("quarantine", "missing summary; needs enrichment", None)

    # Timestamp sanity: allow up to 24h in future
    now = _now_utc()
    if base["event_timestamp_utc"] and base["event_timestamp_utc"] > (now + dt.timedelta(hours=24)):
        return NormalizationResult("quarantine", "event_timestamp_utc too far in future", None)

    # Determine payload
    payload = raw.get("payload_json")
    if payload is None:
        payload = _try_parse_json(raw.get("text_content"))
    if payload is None:
        payload = {}

    src_name = (raw.get("source_name") or "").lower()
    src_type = (raw.get("source_type") or "").lower()

    # Route to mapper
    if "politic" in src_name or "senate" in src_name or "house" in src_name or "disclosure" in src_type:
        return _map_politician(raw, base, payload)
    if "usaspending" in src_name or "usaspending" in src_type:
        return _map_usaspending(raw, base, payload)
    if "dod" in src_name or "defense" in src_name or "d o d" in src_name or "dod" in src_type:
        return _map_dod_award(raw, base, payload)
    if "sec" in src_name or "edgar" in src_name or "sec" in src_type:
        return _map_sec(raw, base, payload)

    return NormalizationResult("quarantine", "unknown source routing; add mapper", None)


def _finalize(raw: Dict[str, Any], base: Dict[str, Any], event_type: str, identity: Tuple[str, ...]) -> Dict[str, Any]:
    discovered_at = base["discovered_at_utc"]
    credibility, freshness, materiality, overall, conf = _scores_placeholder(discovered_at)

    fallback_seed = f"{event_type}|{base['source_name']}|{base['source_url']}|{base['title']}|{base['event_timestamp_utc'].isoformat()}"
    source_hash = _compute_source_hash(raw, fallback_seed)
    event_fingerprint = _compute_event_fingerprint(identity)

    base["event_type"] = event_type
    base["confidence"] = conf
    base["credibility_score"] = credibility
    base["freshness_score"] = freshness
    base["materiality_score"] = materiality
    base["overall_score"] = overall
    base["source_hash"] = source_hash
    base["event_fingerprint"] = event_fingerprint

    return base


def _map_politician(raw: Dict[str, Any], base: Dict[str, Any], payload: Any) -> NormalizationResult:
    # Best-effort field extraction
    rp = _norm_ws(_get(payload, "reporting_person", "representative", "senator", "name"))
    office = _norm_ws(_get(payload, "office", "chamber", "state"))
    filing_date = _norm_ws(_get(payload, "filing_date", "filed", "date_filed"))
    tx_date = _norm_ws(_get(payload, "transaction_date_or_range", "transaction_date", "tx_date", "date"))
    tx_type = _norm_ws(_get(payload, "transaction_type", "type"))
    amt_band = _norm_ws(_get(payload, "amount_band", "amount", "amount_range"))
    asset = _norm_ws(_get(payload, "asset_description", "asset", "description", "security"))
    ticker = _norm_ws(_get(payload, "ticker", "symbol"))

    if not rp or not asset or not tx_type:
        return NormalizationResult("quarantine", "politician disclosure missing key fields (name/asset/type)", None)

    base["title"] = base["title"] if base["title"] != "Untitled" else f"{rp} disclosure: {tx_type} {asset}"
    base["summary"] = base["summary"] if base["summary"] != "No summary available." else f"{rp} filed a disclosure indicating a {tx_type} involving {asset} ({amt_band})."

    base["theme_tags"] = ["POLITICIAN", "DISCLOSURE"]
    base["details_json"] = {
        "type_specific": {
            "reporting_person": rp,
            "office": office,
            "filing_date": filing_date,
            "transaction_date_or_range": tx_date,
            "transaction_type": tx_type,
            "amount_band": amt_band,
            "asset_description": asset,
            "ticker_hint": ticker,
        },
        "entities": [
            {"name": rp, "entity_type": "PERSON", "role": "REPORTING_PERSON"},
        ],
        "raw_payload": payload,
    }

    identity = ("POLITICIAN_DISCLOSURE", rp.lower(), tx_date.lower(), tx_type.lower(), asset.lower(), amt_band.lower())
    event = _finalize(raw, base, "POLITICIAN_DISCLOSURE", identity)
    return NormalizationResult("ok", "mapped politician disclosure", event)


def _map_usaspending(raw: Dict[str, Any], base: Dict[str, Any], payload: Any) -> NormalizationResult:
    award_id = _norm_ws(_get(payload, "generated_unique_award_id", "award_id", "id"))
    piid = _norm_ws(_get(payload, "piid", "contract_number"))
    agency = _norm_ws(_get(payload, "awarding_agency", "agency"))
    recipient = _norm_ws(_get(payload, "recipient", "recipient_name", "awardee"))
    obligation = _get(payload, "obligation", "obligated_amount")
    ceiling = _get(payload, "base_and_all_options_value", "ceiling_amount")

    if not (award_id or piid) or not agency or not recipient:
        return NormalizationResult("quarantine", "USASpending missing key fields (award/agency/recipient)", None)

    base["title"] = base["title"] if base["title"] != "Untitled" else f"Federal award: {recipient} ({agency})"
    base["summary"] = base["summary"] if base["summary"] != "No summary available." else f"USASpending record: {recipient} awarded by {agency}."

    base["theme_tags"] = ["FEDERAL_AWARD"]
    base["details_json"] = {
        "type_specific": {
            "award_id": award_id,
            "contract_number": piid,
            "agency": agency,
            "recipient": recipient,
            "obligated_amount": obligation,
            "ceiling_amount": ceiling,
        },
        "entities": [
            {"name": agency, "entity_type": "AGENCY", "role": "AWARDING_AGENCY"},
            {"name": recipient, "entity_type": "COMPANY", "role": "RECIPIENT"},
        ],
        "raw_payload": payload,
    }

    stable = award_id or piid
    identity = ("FED_AWARD", "USASPENDING", stable.lower(), agency.lower(), recipient.lower())
    event = _finalize(raw, base, "FED_AWARD", identity)
    return NormalizationResult("ok", "mapped usaspending award", event)


def _map_dod_award(raw: Dict[str, Any], base: Dict[str, Any], payload: Any) -> NormalizationResult:
    contract = _norm_ws(_get(payload, "contract_number", "piid", "award_id", "id"))
    recipient = _norm_ws(_get(payload, "recipient", "awardee", "company"))
    agency = _norm_ws(_get(payload, "agency", "awarding_agency")) or "DoD"
    amount = _get(payload, "obligated_amount", "amount")

    # DoD press releases often have only text; fallback to title parsing.
    if not recipient and isinstance(base.get("title"), str):
        recipient = base["title"]

    if not contract and not recipient:
        return NormalizationResult("quarantine", "DoD award missing contract/recipient", None)

    base["title"] = base["title"] if base["title"] != "Untitled" else f"DoD award: {recipient}"
    base["summary"] = base["summary"] if base["summary"] != "No summary available." else f"Defense contract announcement for {recipient}."

    base["theme_tags"] = ["FEDERAL_AWARD", "DEFENSE"]
    base["details_json"] = {
        "type_specific": {"contract_number": contract, "recipient": recipient, "agency": agency, "obligated_amount": amount},
        "entities": [
            {"name": agency, "entity_type": "AGENCY", "role": "AWARDING_AGENCY"},
            {"name": recipient, "entity_type": "COMPANY", "role": "RECIPIENT"},
        ],
        "raw_payload": payload,
    }

    stable = contract or base["source_url"]
    identity = ("FED_AWARD", "DOD", stable.lower(), agency.lower(), (recipient or "").lower())
    event = _finalize(raw, base, "FED_AWARD", identity)
    return NormalizationResult("ok", "mapped dod award", event)


def _map_sec(raw: Dict[str, Any], base: Dict[str, Any], payload: Any) -> NormalizationResult:
    form = _norm_ws(_get(payload, "filing_form", "form", "form_type"))
    filer = _norm_ws(_get(payload, "filer_name", "filer", "company_name", "issuer"))
    accession = _norm_ws(_get(payload, "accession_number", "accession", "accessionNo"))
    filing_date = _norm_ws(_get(payload, "filing_date", "filed_at", "date"))

    # SEC records can be incomplete early; quarantine if missing critical identifiers
    if not accession and not base["source_url"]:
        return NormalizationResult("quarantine", "SEC filing missing accession/source_url", None)

    base["theme_tags"] = ["SEC_FILING"]
    base["details_json"] = {
        "type_specific": {
            "filing_form": form,
            "filer_name": filer,
            "accession_number": accession,
            "filing_date": filing_date,
        },
        "entities": [{"name": filer, "entity_type": "COMPANY", "role": "FILER"}] if filer else [],
        "raw_payload": payload,
    }

    base["title"] = base["title"] if base["title"] != "Untitled" else f"SEC filing {form} - {filer}".strip(" -")
    base["summary"] = base["summary"] if base["summary"] != "No summary available." else f"SEC EDGAR filing {form} by {filer}."

    stable = accession or base["source_url"]
    identity = ("OTHER_PUBLIC_CATALYST", "SEC", stable.lower(), (form or "").lower(), (filer or "").lower())
    event = _finalize(raw, base, "OTHER_PUBLIC_CATALYST", identity)
    return NormalizationResult("ok", "mapped sec filing", event)


def _get(obj: Any, *keys: str) -> Any:
    """
    Best-effort retrieval from dict payloads.
    """
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
    return None
