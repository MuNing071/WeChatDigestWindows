# -*- coding: utf-8 -*-
import sqlite3, os, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
ts_0415_start = int(datetime.datetime(2026,4,15).timestamp())
ts_0415_end = int(datetime.datetime(2026,4,16).timestamp())

# Check EVERY table in EVERY db for April 15 data
msg_dbs = sorted([f for f in os.listdir(db_dir) if f.startswith('message_') and f.endswith('.db')])

total_msgs_0415 = 0
groups_found = []
latest_overall = 0

print('=== Comprehensive scan for April 15 + latest dates ===')
for db_file in msg_dbs:
    db_path = os.path.join(db_dir, db_file)
    conn = sqlite3.connect(db_path)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
        for t in tables:
            try:
                # Check latest time
                r_max = conn.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
                if r_max and r_max > latest_overall:
                    latest_overall = r_max
                
                # Check April 15 count
                cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}" WHERE create_time >= ? AND create_time < ?', (ts_0415_start, ts_0415_end)).fetchone()[0]
                if cnt > 0:
                    total_msgs_0415 += cnt
                    groups_found.append((db_file, t, cnt))
            except:
                pass
    finally:
        conn.close()

print(f'Global latest timestamp: {datetime.datetime.fromtimestamp(latest_overall).strftime("%Y-%m-%d %H:%M") if latest_overall else "NONE"}')
print(f'April 15 total messages: {total_msgs_0415} in {len(groups_found)} groups')

# Also check: what's the absolute latest message date across all?
print(f'\n=== Latest messages per DB ===')
for db_file in msg_dbs:
    db_path = os.path.join(db_dir, db_file)
    conn = sqlite3.connect(db_path)
    try:
        # Get max across all Msg tables
        result = conn.execute("""
            SELECT MAX(t.max_ts) FROM (
                SELECT MAX(create_time) as max_ts FROM sqlite_master 
                WHERE type='table' AND name LIKE 'Msg_%'
            )
        """).fetchone()
        # Alternative approach
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
        db_max = 0
        best_tbl = ''
        for t in tables[:30]:
            try:
                m = conn.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
                if m and m > db_max:
                    db_max = m
                    best_tbl = t
            except:
                pass
        if db_max > 0:
            dt_str = datetime.datetime.fromtimestamp(db_max).strftime('%Y-%m-%d %H:%M')
            print(f'  {db_file}: latest={dt_str} ({best_tbl[:40]}...)')
    finally:
        conn.close()

# Now check if source has WAL with uncommitted data
src_dir = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message'
print(f'\n=== Source dir WAL/SHM status ===')
for ext in ['*.wal', '*.shm']:
    files = os.listdir(src_dir)
    wal_files = [f for f in files if f.endswith(ext.replace('*', ''))]
    for wf in wal_files:
        fp = os.path.join(src_dir, wf)
        st = os.stat(fp)
        sz_kb = round(st.st_size / 1024, 1)
        mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f'  {wf}: size={sz_kb}KB, modified={mt}')
