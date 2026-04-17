import sqlite3, os

decrypted_db = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message\message_0.db'
conn = sqlite3.connect(decrypted_db)

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
lines = [f'Total tables: {len(tables)}']
for t in sorted(tables):
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM [{t[0]}]').fetchone()[0]
        lines.append(f'  {t[0]}: {cnt}')
    except Exception as e:
        lines.append(f'  {t[0]}: ERROR - {e}')

msg_tables = [t[0] for t in tables if t[0].startswith('Msg_')]
lines.append(f'\nMsg_* group chat tables ({len(msg_tables)}):')
for t in msg_tables[:15]:
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        lines.append(f'  {t}: {cnt} msgs')
    except:
        pass

# Check Session table
try:
    cols = [d[0] for d in conn.execute('SELECT * FROM Session LIMIT 1').description]
    rows = conn.execute('SELECT username, nickname, type FROM Session LIMIT 10').fetchall()
    lines.append(f'\nSession columns: {cols[:6]}')
    for r in rows:
        lines.append(f'  username={r[0]} nick={r[1]} type={r[2]}')
except Exception as e:
    lines.append(f'\nSession error: {e}')

conn.close()

out_path = r'e:\微信群聊总结\db-structure.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'Results saved to {out_path}, {len(lines)} lines')
