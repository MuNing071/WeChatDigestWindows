# Inspect Helpers

This folder keeps local inspection scripts only.

Do not commit generated inspection output here. Database schema dumps, table counts,
or session snapshots can reveal private local runtime details even when message
content is not included.

Suggested local workflow:

```powershell
python scripts/inspect/inspect_db.py > scripts/inspect/db-structure.local.txt
python scripts/inspect/inspect_sessions.py > scripts/inspect/db-sessions.local.txt
```

Files ending in `.local.txt` should stay untracked.
