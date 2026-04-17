# -*- coding: utf-8 -*-
import sqlite3, os, sys, io, datetime, hashlib, hmac
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try opening the DECRYPTED db with WAL mode to see all tables properly
# Also try to understand why April 15 data is missing
decrypted_path = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message\message_0.db'

conn = sqlite3.connect(decrypted_path)

# Check journal mode
mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
print(f'Journal mode: {mode}')

# List ALL tables  
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f'Total tables: {len(tables)}')
for t in sorted([x[0] for x in tables]):
    cnt = 0
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
    except:
        pass
    print(f'  {t}: {cnt} rows')

# Now check the LARGEST group by message count - these are likely active ones
print('\n=== Top 20 groups by message count ===')
msg_tables = [t[0] for t in tables if t[0].startswith('Msg_')]
group_stats = []
for t in msg_tables[:50]:  # check first 50 tables
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        r_max = conn.execute(f'SELECT MAX(create_time) FROM [{t}]').fetchone()[0]
        r_min = conn.execute(f'SELECT MIN(create_time) FROM [{t}]').fetchone()[0]
        if r_max:
            dmax = datetime.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d %H:%M')
            dmin = datetime.datetime.fromtimestamp(r_min).strftime('%Y-%m-%d %H:%M') if r_min else '?'
            group_stats.append((cnt, t, dmin, dmax))
    except Exception as e:
        pass

group_stats.sort(key=lambda x: -x[0])
for cnt, t, dmin, dmax in group_stats[:20]:
    print(f'  {cnt:5d} msgs | {dmin} ~ {dmax} | {t[:50]}')

conn.close()
