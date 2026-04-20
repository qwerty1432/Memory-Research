# Memory `phase` column (SQLite)

Existing SQLite databases created before this feature need the `phase` column on `memories`.

The application runs this automatically on startup via `init_db()` (see `app/database.py`).

To apply manually on a server:

```sql
ALTER TABLE memories ADD COLUMN phase INTEGER;
```

`phase` is nullable: `1`–`3` for memories created during the guided study, `NULL` for older rows or manual creates without phase.
