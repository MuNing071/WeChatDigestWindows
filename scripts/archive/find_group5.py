# -*- coding: utf-8 -*-
import sqlite3, os, sys, io, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'

# Check time range of messages in each DB
msg_dbs = sorted([f for f in os.listdir(db_dir) if f.startswith('message_') and f.endswith('.db')])

print('=== Message time range per DB ===')
for db_file in msg_dbs:
    db_path = os.path.join(db_dir, db_file)
    conn = sqlite3.connect(db_path)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
        all_ts = []
        for t in tables[:3]:  # check first 3 tables
            try:
                r_min = conn.execute(f'SELECT MIN(create_time) FROM "{t}"').fetchone()[0]
                r_max = conn.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
                cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                if r_min and r_max:
                    dt_min = datetime.datetime.fromtimestamp(r_min).strftime('%Y-%m-%d')
                    dt_max = datetime.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d')
                    all_ts.append((dt_min, dt_max, cnt))
            except:
                pass
        
        if all_ts:
            print(f'{db_file}: range={all_ts[0][0]} ~ {all_ts[0][1]} (table {tables[0][:30]}... {all_ts[0][2]} msgs)')
    except Exception as e:
        print(f'{db_file}: error {e}')
    conn.close()

# Also: dump ALL session table entries to file so we can find the right group
conn_s = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
rows = conn_s.execute('SELECT username, summary, last_timestamp FROM SessionTable ORDER BY last_timestamp DESC').fetchall()

with open(r'e:\all_groups_full.txt', 'w', encoding='utf-8') as f:
    for i, r in enumerate(rows):
        summary_clean = (r[1] or '').replace('\n', ' ')[:100]
        ts_str = ''
        if r[2]:
            ts_str = datetime.datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M')
        f.write(f'{i+1:3d}. {r[0]} | {ts_str} | {summary_clean}\n')

print(f'\nDumped {len(rows)} groups to e:\\all_groups_full.txt')

# Check contact table for any nickname/remark containing 实践
conn_c = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db')
try:
    # Check chatroom_member for group membership info
    cols_c = [d[0] for d in conn_c.execute('SELECT * FROM chatroom_member LIMIT 1').description]
    print(f'\nchatroom_member columns: {cols_c}')
    total_members = conn_c.execute('SELECT COUNT(*) FROM chatroom_member').fetchone()[0]
    print(f'Total chatroom_member rows: {total_members}')
except Exception as e:
    print(f'chatroom_member: {e}')

# Try searching in ext_buffer of chat_room for group names (protobuf encoded)
print('\nSearching chat_room ext_buffer for text patterns...')
cr_rows = conn_c.execute("SELECT username, length(ext_buffer) FROM chat_room WHERE ext_buffer IS NOT NULL AND length(ext_buffer) > 20").fetchall()
for cr in cr_rows[:10]:
    raw = cr[1]
    # Look for UTF-8 strings in the blob
    try:
        text_parts = []
        i = 0
        buf = conn_c.execute("SELECT ext_buffer FROM chat_room WHERE username=?", (cr[0],)).fetchone()[0]
        while i < len(buf):
            if buf[i:i+3] >= b'\xe4\xb8' and buf[i:i+3] <= b'\xef\xbf':
                # Start of CJK char sequence
                end = i + 3
                while end < len(buf) and 0x80 <= buf[end] <= 0xbf:
                    end += 1
                try:
                    ch = buf[i:end].decode('utf-8')
                    if ch.isprintable():
                        text_parts.append(ch)
                except:
                    pass
            i += 1
        if text_parts:
            joined = ''.join(text_parts)
            if len(joined) > 3:
                print(f'  {cr[0]}: {joined[:80]}')
    except:
        pass

conn_s.close()
conn_c.close()
