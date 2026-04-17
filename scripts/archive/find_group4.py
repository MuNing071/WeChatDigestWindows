# -*- coding: utf-8 -*-
import sqlite3, hashlib, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
target_date = '2026-04-15'
import datetime
base = datetime.datetime.strptime(target_date, '%Y-%m-%d')
ts_start = int(base.timestamp())
ts_end = int((base + datetime.timedelta(days=1)).timestamp())

msg_dbs = sorted([f for f in os.listdir(db_dir) if re.match(r'message_\d+\.db$', f)])

print(f'Scanning {len(msg_dbs)} DBs for messages on {target_date}...\n')

groups_with_msgs = {}  # username -> count

for db_file in msg_dbs:
    db_path = os.path.join(db_dir, db_file)
    conn = sqlite3.connect(db_path)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
    
    for t in tables:
        # Get username from MD5 hash (reverse lookup)
        # We can't reverse MD5, but let's just count messages per table
        try:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}" WHERE create_time >= ? AND create_time < ?', (ts_start, ts_end)).fetchone()[0]
            if cnt > 0:
                groups_with_msgs[t] = cnt
        except:
            pass
    
    conn.close()

print(f'Groups with messages on {target_date}: {len(groups_with_msgs)}')
for tbl, cnt in sorted(groups_with_msgs.items(), key=lambda x: -x[1])[:30]:
    print(f'  {tbl}: {cnt} msgs')

# Now try to match table names to usernames from SessionTable
conn_s = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
sessions = conn_s.execute('SELECT username, summary FROM SessionTable WHERE username LIKE "%@chatroom"').fetchall()

# Build md5(username) -> session mapping
session_map = {}
for s in sessions:
    h = hashlib.md5(s[0].encode()).hexdigest()
    session_map[h] = s[0]

# Map table names to sessions
print('\n--- Active groups on 2026-04-15 (with session info) ---')
for tbl, cnt in sorted(groups_with_msgs.items(), key=lambda x: -x[1]):
    msg_hash = tbl.replace('Msg_', '')  # This is MD5 of username
    if msg_hash in session_map:
        uname = session_map[msg_hash]
        summary = ''
        for s in sessions:
            if s[0] == uname:
                summary = (s[1] or '')[:80]
                break
        print(f'  [{cnt:4d} msgs] {uname}')
        print(f'           last_msg: {summary}')
    else:
        print(f'  [{cnt:4d} msgs] {tbl} (no session match)')

conn_s.close()
