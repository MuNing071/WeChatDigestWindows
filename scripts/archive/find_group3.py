# -*- coding: utf-8 -*-
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db')

# Search in chat_room table for group names
cols = [d[0] for d in conn.execute('SELECT * FROM chat_room LIMIT 1').description]
print(f'chat_room columns: {cols}')
print(f'chat_room count: {conn.execute("SELECT COUNT(*) FROM chat_room").fetchone()[0]}')

# Get all groups with their display names / room names
rows = conn.execute('SELECT * FROM chat_room ORDER BY rowid LIMIT 50').fetchall()
print('\n--- All chat_room entries (first 50) ---')
for r in rows:
    d = dict(zip(cols, r))
    # Print readable fields
    name = d.get('room_name') or d.get('roomName') or d.get('display_name') or d.get('displayName') or ''
    uname = d.get('username') or d.get('userName') or ''
    print(f'  {uname} | name={name}')

# Now specifically search for 实践 or AI in all text fields  
print('\n--- Searching for "实践" ---')
for col in cols:
    try:
        rows = conn.execute(f'SELECT * FROM chat_room WHERE [{col}] LIKE "%实践%" LIMIT 10').fetchall()
        if rows:
            for r in rows:
                d = dict(zip(cols, r))
                print(f'  Found in {col}: username={d.get("username","")} value={d.get(col,"")}')
    except:
        pass

print('\n--- Searching for "AI" in group names ---')
for col in ['room_name', 'roomName', 'display_name', 'displayName', 'nick_name']:
    if col in cols:
        try:
            rows = conn.execute(f'SELECT * FROM chat_room WHERE [{col}] LIKE "%AI%" OR [{col}] LIKE "%ai%" LIMIT 20').fetchall()
            if rows:
                for r in rows:
                    d = dict(zip(cols, r))
                    print(f'  Found: {d.get("username","")} -> {d.get(col,"")}')
        except:
            pass

conn.close()

# Also check chat_room_info_detail
conn2 = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db')
try:
    cols2 = [d[0] for d in conn2.execute('SELECT * FROM chat_room_info_detail LIMIT 1').description]
    print(f'\nchat_room_info_detail columns: {cols2[:15]}')
    # Look for group name field
    for c in cols2:
        if any(k in c.lower() for k in ['name', 'title', 'display']):
            try:
                rows = conn2.execute(f'SELECT * FROM chat_room_info_detail WHERE [{c}] LIKE "%实践%" OR [{c}] LIKE "%AI%" LIMIT 10').fetchall()
                if rows:
                    print(f'  Matches in {c}:')
                    for r in rows:
                        d = dict(zip(cols2, r))
                        print(f'    {d}')
            except:
                pass
except Exception as e:
    print(f'chat_room_info_detail error: {e}')

conn2.close()
