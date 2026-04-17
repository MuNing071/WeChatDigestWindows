import sqlite3
conn = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\message\message_0.db')
# Get one of the bigger tables
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' ORDER BY name").fetchall()]
print(f'Total Msg tables: {len(tables)}')

# Pick the table with most rows (likely an active group)
for t in sorted(tables)[:3]:
    cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
    cols = [d[0] for d in conn.execute(f'SELECT * FROM [{t}] LIMIT 1').description]
    print(f'\n{t}: {cnt} rows')
    print(f'  Columns ({len(cols)}): {cols}')
    # Sample 1 row
    row = conn.execute(f'SELECT * FROM [{t}] LIMIT 1').fetchone()
    if row:
        for i, c in enumerate(cols):
            v = str(row[i])[:60] if row[i] else '(null)'
            if v != '(null)':
                print(f'  [{i}] {c} = {v}')
conn.close()
