# -*- coding: utf-8 -*-
import sqlite3, os, datetime, hashlib, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
target_date = '2026-04-15'
base = datetime.datetime.strptime(target_date, '%Y-%m-%d')
ts_start = int(base.timestamp())
ts_end = int((base + datetime.timedelta(days=1)).timestamp())

# Step 1: Verify April 15 data exists
msg_dbs = sorted([f for f in os.listdir(db_dir) if re.match(r'message_\d+\.db$', f)])
print(f'Scanning {len(msg_dbs)} DBs for {target_date} messages...\n')

groups_0415 = []
for db_file in msg_dbs:
    db_path = os.path.join(db_dir, db_file)
    conn = sqlite3.connect(db_path)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
    for t in tables:
        try:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}" WHERE create_time >= ? AND create_time < ?', (ts_start, ts_end)).fetchone()[0]
            if cnt > 0:
                groups_0415.append((t, cnt))
        except:
            pass
    conn.close()

print(f'=== Groups with messages on {target_date}: {len(groups_0415)} ===')
for tbl, cnt in sorted(groups_0415, key=lambda x: -x[1])[:30]:
    print(f'  {cnt:4d} msgs -> {tbl}')

# Step 2: Build MD5->username mapping from session.db
conn_s = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
rows = conn_s.execute("SELECT username, summary, last_timestamp FROM SessionTable WHERE username LIKE '%@chatroom' ORDER BY last_timestamp DESC").fetchall()
md5_to_user = {}
for r in rows:
    h = hashlib.md5(r[0].encode()).hexdigest()
    md5_to_user[h] = (r[0], (r[1] or '')[:80])

# Map table names to group usernames
print(f'\n=== Groups with session info ===')
for tbl, cnt in sorted(groups_0415, key=lambda x: -x[1]):
    msg_hash = tbl.replace('Msg_', '')
    if msg_hash in md5_to_user:
        uname, summary = md5_to_user[msg_hash]
        print(f'[{cnt:4d} msgs] {uname}')
        print(f'           last_msg: {summary}')

conn_s.close()

# Step 3: Search for "ai 实践" in ALL session data
print(f'\n=== Searching for "实践" or "AI" across all sessions ===')
conn_s2 = sqlite3.connect(r'e:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\session\session.db')
try:
    tables_s = [r[0] for r in conn_s2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f'Active session.db tables: {tables_s}')
    
    for stbl in ['SessionTable', 'Name2Id']:
        try:
            cols = [d[0] for d in conn_s2.execute(f'SELECT * FROM {stbl} LIMIT 1').description]
            print(f'{stbl} columns: {cols}')
            
            # Try all text-like columns for search
            for col in cols:
                try:
                    rows_found = conn_s2.execute(f'SELECT * FROM {stbl} WHERE [{col}] LIKE "%AI%" OR [{col}] LIKE "%实践%" LIMIT 10').fetchall()
                    if rows_found:
                        print(f'  Found in {col}:')
                        for rf in rows_found[:5]:
                            d = dict(zip(cols, rf))
                            print(f'    {d}')
                except:
                    pass
        except Exception as e:
            print(f'{stbl} error: {e}')
except Exception as e:
    print(f'Active session.db error: {e}')
finally:
    conn_s2.close()

# Also check contact.db from active dir
contact_path = r'e:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\contact\contact.db'
if os.path.exists(contact_path):
    print(f'\n=== Active contact.db search ===')
    cc = sqlite3.connect(contact_path)
    ctbls = [r[0] for r in cc.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    # Check chat_room with full ext_buffer dump for group names
    for ct in ['chat_room', 'chat_room_info_detail']:
        if ct in ctbls:
            cols_c = [d[0] for d in cc.execute(f'SELECT * FROM {ct} LIMIT 1').description]
            total = cc.execute(f'SELECT COUNT(*) FROM {ct}').fetchone()[0]
            print(f'{ct}: {total} rows, cols={cols_c}')
            
            # Search all columns for AI/实践
            for col in cols_c:
                try:
                    found = cc.execute(f'SELECT * FROM {ct} WHERE [{col}] LIKE "%实践%" OR [{col}] LIKE "%ai实践%" OR [{col}] LIKE "%AI实践%" LIMIT 5').fetchall()
                    if found:
                        print(f'  Matches in {col}:')
                        for f in found:
                            print(f'    {dict(zip(cols_c, f))}')
                except:
                    pass
    
    cc.close()
