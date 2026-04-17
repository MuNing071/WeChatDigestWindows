# -*- coding: utf-8 -*-
import sqlite3, os, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message\message_0.db'
conn = sqlite3.connect(db_path)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
print(f'Total Msg tables: {len(tables)}')

# Check time range of first few tables
for t in tables[:5]:
    r_min = conn.execute(f'SELECT MIN(create_time) FROM "{t}"').fetchone()[0]
    r_max = conn.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
    cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    if r_min and r_max:
        dt_min = datetime.datetime.fromtimestamp(r_min).strftime('%Y-%m-%d')
        dt_max = datetime.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d')
        print(f'  {t[:40]}... range={dt_min} ~ {dt_max} ({cnt} msgs)')

# Check for April 15 messages across all DBs
ts_0415_start = int(datetime.datetime(2026,4,15).timestamp())
ts_0415_end = int(datetime.datetime(2026,4,16).timestamp())

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
msg_dbs = sorted([f for f in os.listdir(db_dir) if f.startswith('message_') and f.endswith('.db')])

total_0415 = 0
groups_0415 = []

for db_file in msg_dbs:
    dbp = os.path.join(db_dir, db_file)
    c2 = sqlite3.connect(dbp)
    tbls2 = [r[0] for r in c2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
    for t in tbls2:
        try:
            cnt = c2.execute(f'SELECT COUNT(*) FROM "{t}" WHERE create_time >= ? AND create_time < ?', (ts_0415_start, ts_0415_end)).fetchone()[0]
            if cnt > 0:
                total_0415 += cnt
                groups_0415.append((db_file, t, cnt))
        except:
            pass
    c2.close()

print(f'\n=== 2026-04-15 messages: {total_0415} total in {len(groups_0415)} groups ===')
for dbf, t, c in sorted(groups_0415, key=lambda x:-x[2])[:20]:
    print(f'  {c:4d} msgs | {dbf}/{t[:50]}')

conn.close()
