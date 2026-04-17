# -*- coding: utf-8 -*-
import sqlite3, os, sys, io, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Step 1: Build MD5->username mapping from session.db (use the decrypted one from wetrace)
# The old session.db has the mapping even if data is older
conn_s = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
rows = conn_s.execute("SELECT username FROM SessionTable WHERE username LIKE '%@chatroom'").fetchall()
md5_to_user = {}
for r in rows:
    h = hashlib.md5(r[0].encode()).hexdigest()
    md5_to_user[h] = r[0]
conn_s.close()

# Step 2: Show April 15 groups with their likely usernames
db_path = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message_active\message_0.db'
conn = sqlite3.connect(db_path)
ts_s = int(datetime.datetime(2026,4,15).timestamp())
ts_e = int(datetime.datetime(2026,4,16).timestamp())

print('=== April 15 groups with username lookup ===')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
apr_groups = []
for t in tables:
    try:
        c = conn.execute(f'SELECT COUNT(*) FROM [{t}] WHERE create_time>=? AND create_time<?', (ts_s, ts_e)).fetchone()[0]
        if c > 0:
            msg_hash = t.replace('Msg_', '')
            uname = md5_to_user.get(msg_hash, 'UNKNOWN')
            
            # Get a sample message to see content clues
            sample = conn.execute(f'SELECT message_content FROM [{t}] WHERE create_time>=? AND create_time<? LIMIT 1', (ts_s, ts_e)).fetchone()
            sample_text = ''
            if sample and sample[0]:
                try:
                    if isinstance(sample[0], bytes):
                        sample_text = sample[0][:100].decode('utf-8', errors='replace').replace('\n',' ')
                    else:
                        sample_text = str(sample[0])[:100].replace('\n',' ')
                except:
                    sample_text = '(binary)'
            
            apr_groups.append((c, uname, t, sample_text))
    except:
        pass

apr_groups.sort(key=lambda x: -x[0])
for cnt, uname, tbl, sample in apr_groups:
    print(f'[{cnt:4d} msgs] {uname}')
    print(f'           sample: {sample[:80]}')

# Also search for groups whose names might contain AI/实践 in contact/chat_room
print('\n=== Searching for group names ===')
# Check the active dir's chat_room via ext_buffer text extraction
contact_db = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\contact\contact.db'
# This is still encrypted, so use the one from wetrace decrypt
contact_dec = r'e:\微信群聊总结\wetrace-bin\wetrace\data\contact\contact.db'

if os.path.exists(contact_dec):
    cc = sqlite3.connect(contact_dec)
    # Try to read chat_room ext_buffer as raw bytes looking for UTF-8 strings
    rows_cr = cc.execute("SELECT username, ext_buffer FROM chat_room").fetchall()
    
    # Search all ext_buffers for "实践" or "ai" or "AI"
    for uname, buf in rows_cr:
        if not buf or len(buf) < 20:
            continue
        # Extract readable strings from binary buffer
        try:
            text = buf.decode('utf-8', errors='ignore')
            # Look for CJK characters forming names
            import re
            cjk_matches = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]{2,}', text)
            if any('实践' in m or 'AI' in m.upper() for m in cjk_matches):
                print(f'  MATCH: {uname} -> contains: {[m for m in cjk_matches if len(m)>2]}')
        except:
            pass
    
    cc.close()
else:
    print(f'Decrypted contact DB not found at {contact_dec}')

# Dump ALL unique group usernames for manual inspection  
print('\n=== All active group usernames (with Apr 15 msgs) ===')
seen_users = set()
for cnt, uname, _, _ in apr_groups:
    if uname not in seen_users:
        seen_users.add(uname)

# Cross-reference with session summaries
conn_s2 = sqlite3.connect(r'e:\微信群聊总结\wetrace-bin\wetrace\data\session\session.db')
for uname in sorted(seen_users):
    row = conn_s2.execute("SELECT summary, last_timestamp FROM SessionTable WHERE username=?", (uname,)).fetchone()
    summary = (row[0] or '')[:80].replace('\n',' ') if row else ''
    ts = datetime.datetime.fromtimestamp(row[1]).strftime('%m-%d %H:%M') if row and row[1] else ''
    print(f'  {uname} | {ts} | {summary}')
conn_s2.close()

conn.close()
