# Migration Strategy (Phase 2)

**Recommendation:** Use a real migration tool (Alembic, Flyway, Liquibase).  
For early bootstraps and local dev, `psql` + `postgres_schema.sql` is fine.

---

## 1) Baseline bootstrap

### Option A — psql (fastest for day 0)
Run:
```sql
\i postgres_schema.sql
```

Then optionally:
```sql
\i example_flow.sql
```

### Option B — migrations (recommended for team/prod)
Create an initial “baseline” migration that contains the DDL from `postgres_schema.sql`.

---

## 2) Rules of safe schema evolution (do this every time)

1) **Additive first**
- Add new columns as nullable
- Add new tables without touching old ones

2) **Backfill**
- Populate new columns with a deterministic backfill job

3) **Tighten constraints last**
- Add NOT NULL / UNIQUE only after backfill is complete
- Add foreign keys after you confirm referential integrity

4) **Index carefully**
- Create indexes concurrently in production (where supported) to reduce lock risk
- Add UNIQUE constraints after dedupe logic is stable

---

## 3) Versioning without schema churn

Use these fields to version algorithms without changing the DB:
- `features_daily.feature_set_version`
- `scores_daily.model_version`
- `signals.model_version`

This keeps your DB stable while the scoring logic evolves.

---

## 4) Phase 5 extension migration

If your database was created **before** `ticker_aliases` / `review_queue` existed:
- apply `migrations/phase5_add_review_queue_and_ticker_aliases.sql`

If you bootstrap using the current `postgres_schema.sql`, you can skip this migration (tables already exist).

