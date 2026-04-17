import sqlite3

conn = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
rows = conn.execute("SELECT username, summary, last_timestamp FROM SessionTable WHERE username LIKE '%@chatroom' ORDER BY last_timestamp DESC").fetchall()
print(f'Total groups: {len(rows)}')
for r in rows:
    summary = str(r[1])[:50] if r[1] else ''
    print(f'  {r[0]} | {summary} | ts={r[2]}')

conn2 = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db')
contacts = conn2.execute("SELECT username, nickname FROM contact WHERE nickname IS NOT NULL AND nickname != '' LIMIT 50").fetchall()
print(f'\nContacts with nicknames ({len(contacts)}):')
for c in contacts:
    print(f'  {c[0]} -> {c[1]}')

# Check chat_room for group names
rooms = conn2.execute("SELECT * FROM chat_room LIMIT 10").fetchall()
if rooms:
    rc = [d[0] for d in conn2.execute("SELECT * FROM chat_room LIMIT 1").description]
    print(f'\nchat_room columns: {rc}')
    for r in rooms:
        print(f'  {dict(zip(rc, r))}')

conn.close()
conn2.close()
