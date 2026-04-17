# -*- coding: utf-8 -*-
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Check chat_room table for group names
conn = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')

# Try to find chat_room or similar table with group display names
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print('Tables:', [t[0] for t in tables])

# Look for group name in different tables
for tbl_name in ['chat_room', 'chatroom', 'rcontact', 'Contact', 'contact', 'ChatRoom', 'SessionInfo']:
    try:
        cols = [d[0] for d in conn.execute(f'SELECT * FROM {tbl_name} LIMIT 1').description]
        count = conn.execute(f'SELECT COUNT(*) FROM {tbl_name}').fetchone()[0]
        print(f'\n{tbl_name}: {count} rows, cols={cols[:10]}')
        
        # Search for "实践" or "AI"
        for col in cols:
            if 'name' in col.lower() or 'nick' in col.lower() or 'display' in col.lower():
                try:
                    rows = conn.execute(f'SELECT * FROM {tbl_name} WHERE {col} LIKE "%实践%" OR {col} LIKE "%AI%" LIMIT 20').fetchall()
                    if rows:
                        print(f'  Found in {col}:')
                        for r in rows[:10]:
                            d = dict(zip(cols, r))
                            print(f'    {d}')
                except:
                    pass
    except Exception as e:
        pass

conn.close()

# Also check contact.db for group nicknames
conn2 = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db')
tables2 = [t[0] for t in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f'\n\ncontact.db tables: {tables2}')

for tbl in tables2:
    try:
        cols = [d[0] for d in conn2.execute(f'SELECT * FROM {tbl} LIMIT 1').description]
        # Find columns that might have names
        name_cols = [c for c in cols if any(k in c.lower() for k in ['name', 'nick', 'alias', 'remark'])]
        if name_cols:
            for nc in name_cols:
                try:
                    rows = conn2.execute(f'SELECT * FROM {tbl} WHERE {nc} LIKE "%实践%" OR {nc} LIKE "%AI%" LIMIT 20').fetchall()
                    if rows:
                        print(f'{tbl}.{nc} matches:')
                        for r in rows[:10]:
                            print(f'  {dict(zip(cols, r))}')
                except:
                    pass
    except:
        pass

conn2.close()
