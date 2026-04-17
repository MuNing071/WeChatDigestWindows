import sqlite3, os

base = r'e:\微信群聊总结\wetrace-bin\wetrace\data'
lines = []

# 1. SessionTable - sessions
conn = sqlite3.connect(os.path.join(base, 'session/session.db'))
cols = [d[0] for d in conn.execute('SELECT * FROM SessionTable LIMIT 1').description]
lines.append(f'SessionTable columns: {cols}')
rows = conn.execute('SELECT * FROM SessionTable LIMIT 30').fetchall()
lines.append(f'SessionTable: {len(rows)} total, showing first 30')
for r in rows:
    # Show readable fields
    vals = []
    for i, c in enumerate(cols):
        v = str(r[i])[:40] if r[i] else ''
        if v:
            vals.append(f'{c}={v}')
    lines.append(f'  {" | ".join(vals)}')

# 2. chat_room - group members
conn2 = sqlite3.connect(os.path.join(base, 'contact/contact.db'))
chatroom_count = conn2.execute('SELECT COUNT(*) FROM chat_room').fetchone()[0]
lines.append(f'\nchat_room: {chatroom_count} rooms')
rooms = conn2.execute('SELECT * FROM chat_room LIMIT 10').fetchall()
rcols = [d[0] for d in conn2.execute('SELECT * FROM chat_room LIMIT 1').description]
for r in rooms:
    lines.append(f'  {str(dict(zip(rcols, r)))}')

# 3. Contact info
contact_cols = [d[0] for d in conn2.execute('SELECT * FROM contact LIMIT 1').description]
lines.append(f'\nContact columns: {contact_cols}')
contacts = conn2.execute('SELECT username, nickname, type, verifyFlag FROM contact WHERE type IN (2,3) OR username LIKE "%@chatroom" LIMIT 20').fetchall()
for c in contacts:
    lines.append(f'  user={c[0]} | nick={c[1]} | type={c[2]}')

conn.close()
conn2.close()

with open(r'e:\微信群聊总结\db-sessions.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'Done - {len(lines)} lines')
