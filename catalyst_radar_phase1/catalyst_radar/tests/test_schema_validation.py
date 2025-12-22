import unittest
from datetime import datetime, timezone

from catalyst_radar.core.models import Event, EventType, SourceType, Confidence
from catalyst_radar.core.schema_validation import validate_event


class TestSchemaValidation(unittest.TestCase):
    def test_validate_minimal_event(self):
        now = datetime.now(timezone.utc)
        ev = Event(
            event_id="e1",
            event_type=EventType.OTHER_PUBLIC_CATALYST,
            title="t",
            summary="s",
            event_timestamp_utc=now,
            discovered_timestamp_utc=now,
            source_type=SourceType.OTHER_PUBLIC,
            source_name="n",
            source_url="https://example.com",
            source_hash="h",
            entities=["Issuer"],
            tickers=[],
            theme_tags=[],
            confidence=Confidence.LOW,
            confidence_rationale="TBD",
            credibility_score=0,
            freshness_score=0,
            materiality_score=0,
            overall_score=0,
        )
        validate_event(ev)


if __name__ == "__main__":
    unittest.main()
