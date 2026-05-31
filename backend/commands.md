# To run migrations and upgrade head in alembic I use:
1. docker compose -f docker-compose.dev.yaml exec --workdir // app alembic revision --autogenerate -m "wtevr"
2. docker compose -f docker-compose.dev.yaml exec --workdir // app alembic upgrade head

## Also:
docker compose -f docker-compose.dev.yaml exec --workdir // app alembic current   (Shows current DB revision)
docker compose -f docker-compose.dev.yaml exec --workdir // app alembic history   (Shows all migrations)

## To run Docker:
Simply use - docker-compose up --build

---

## Safe migrations (when you have important data)

### Before any migration
1. **Check current revision**
   ```bash
   docker compose -f docker-compose.dev.yaml exec --workdir // app alembic current
   ```
2. **Back up the database** (recommended before every migration)
   - **Supabase dashboard:** Project → Database → Backups (or create a manual backup / snapshot if on a paid plan).
   - **From your machine** (requires `pg_dump` installed; use the direct connection string from Supabase, not the pooler URL):
     ```bash
     pg_dump "postgresql://USER:PASSWORD@HOST:5432/postgres" -F c -f backup-$(date +%Y%m%d).dump
     ```
   - Keep the dump somewhere safe before running `alembic upgrade`.

### Adding indexes is safe
- **Index-only migrations do not change row data.** They only build a lookup structure on existing columns.
- Reads may briefly slow during index creation on large tables; writes are usually unaffected.
- The `ix_thoughts_user_id_id` migration is index-only: safe to run on a live DB with data.

### Apply a specific migration
```bash
docker compose -f docker-compose.dev.yaml exec --workdir // app alembic upgrade head
```

### If something goes wrong — rollback
1. **Rollback one migration** (e.g. drop the new index only):
   ```bash
   docker compose -f docker-compose.dev.yaml exec --workdir // app alembic downgrade -1
   ```
2. **Rollback to a known good revision**:
   ```bash
   docker compose -f docker-compose.dev.yaml exec --workdir // app alembic downgrade b9f2e1d44c10
   ```
3. **Restore from backup** (only if data was affected — not needed for index-only migrations):
   ```bash
   pg_restore -d "postgresql://USER:PASSWORD@HOST:5432/postgres" --clean --if-exists backup-YYYYMMDD.dump
   ```
   Or use Supabase dashboard restore if available on your plan.

### After migrating
```bash
docker compose -f docker-compose.dev.yaml exec --workdir // app alembic current
```
Confirm revision is `c4d8e2f91a03` (or latest head) before relying on the app.
