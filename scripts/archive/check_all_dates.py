# -*- coding: utf-8 -*-
import sqlite3, os, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Check ALL decrypted DBs for their latest message time
db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
msg_dbs = sorted([f for f in os.listdir(db_dir) if f.startswith('message_') and f.endswith('.db')])

print('=== Decrypted DB: latest msg time per file ===')
global_max_ts = 0
for db_file in msg_dbs:
    dbp = os.path.join(db_dir, db_file)
    c2 = sqlite3.connect(dbp)
    try:
        r_max = c2.execute("SELECT MAX(create_time) FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchone()
        # Just get max create_time from any Msg table
        tbls = [r[0] for r in c2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
        file_max_ts = 0
        for t in tbls:
            try:
                m = c2.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
                if m and m > file_max_ts:
                    file_max_ts = m
            except:
                pass
        if file_max_ts > 0:
            dt_str = datetime.datetime.fromtimestamp(file_max_ts).strftime('%Y-%m-%d %H:%M')
            print(f'{db_file}: latest={dt_str}')
            if file_max_ts > global_max_ts:
                global_max_ts = file_max_ts
    except Exception as e:
        print(f'{db_file}: error {e}')
    c2.close()

print(f'\nGlobal latest message: {datetime.datetime.fromtimestamp(global_max_ts).strftime("%Y-%m-%d %H:%M") if global_max_ts else "NONE"}')

# Now compare with SOURCE encrypted DB modification times
src_dir = r'E:\Documents\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message'
if os.path.exists(src_dir):
    print(f'\n=== Source encrypted DB files ===')
    src_files = sorted([f for f in os.listdir(src_dir) if f.startswith('message_') and f.endswith('.db')])
    for f in src_files:
        fp = os.path.join(src_dir, f)
        stat = os.stat(fp)
        mt = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        sz = stat.st_size // 1024
        print(f'  {f}: modified={mt}, size={sz}KB')
else:
    print(f'\nSource dir not found: {src_dir}')

# Also check session.db last_msg times
session_path = r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db'
if os.path.exists(session_path):
    cs = sqlite3.connect(session_path)
    rows = cs.execute('SELECT username, summary, MAX(last_timestamp) FROM SessionTable GROUP BY username ORDER BY last_timestamp DESC LIMIT 10').fetchall()
    print(f'\n=== Most recent sessions (from session.db) ===')
    for r in rows:
        dt = datetime.datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M') if r[2] else '?'
        s = (r[1] or '')[:60].replace('\n',' ')
        print(f'  {dt} | {r[0]} | {s}')
    cs.close()
