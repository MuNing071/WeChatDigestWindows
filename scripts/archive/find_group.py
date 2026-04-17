# -*- coding: utf-8 -*-
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
rows = conn.execute("SELECT username, summary, last_timestamp FROM SessionTable WHERE username LIKE '%@chatroom' ORDER BY last_timestamp DESC").fetchall()

print(f'Total groups: {len(rows)}')
print(f'--- Searching for "实践" or "ai" in group names ---')

for r in rows:
    summary = r[1] or ''
    # Search for keywords
    if '实践' in summary or 'AI' in summary.upper() or 'ai' in summary.lower():
        print(f'  FOUND: {r[0]} | summary={summary} | ts={r[2]}')

# Also show all groups with their summary decoded properly  
print(f'\n--- All groups (first 50) ---')
for i, r in enumerate(rows[:50]):
    summary = (r[1] or '')[:60]
    print(f'  [{i+1}] {r[0]} | {summary}')

conn.close()
