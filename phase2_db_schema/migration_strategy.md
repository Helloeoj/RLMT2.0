# Migration Strategy

Recommended: Alembic (Python) or any migration tool (Flyway/Liquibase/etc.)

## Alembic approach (typical)
1) Create a SQLAlchemy model layer OR run raw SQL migrations.
2) Generate a baseline revision:
   - `alembic revision -m "init schema"`
3) Put the DDL from `postgres_schema.sql` into the upgrade() (execute as text),
   or translate into SQLAlchemy tables.

## Safety rules
- Prefer additive migrations (add columns nullable, backfill, then enforce NOT NULL)
- Add UNIQUE constraints after dedupe logic is stable
- Use `model_version` / `feature_set_version` strings to version algorithms without schema churn
