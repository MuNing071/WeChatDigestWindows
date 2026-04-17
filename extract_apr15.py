# -*- coding: utf-8 -*-
"""
Extract messages from the ACTIVE decrypted DB for a specific group on April 15.
Supports zstd decompression and proper formatting.
"""
import sqlite3, os, sys, io, datetime, re, hashlib, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try zstd
try:
    import zstandard as zstd
    HAS_ZSTD = True
    dctx = zstd.ZstdDecompressor()
except:
    HAS_ZSTD = False
    dctx = None

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message_active'
target_date = '2026-04-15'
base = datetime.datetime.strptime(target_date, '%Y-%m-%d')
ts_start = int(base.timestamp())
ts_end = int((base + datetime.timedelta(days=1)).timestamp())

def format_msg(row):
    """Format a single message row into readable text"""
    ts_val, content, ct_val, lt_val = row[0], row[1], row[2] or 0, row[3] or 0
    
    if ts_val == 0 or not content:
        return None
        
    dt_str = datetime.datetime.fromtimestamp(ts_val).strftime('%H:%M')
    real_type = lt_val & 0xFFFFFFFF
    
    # Decompress
    try:
        if ct_val == 4 and dctx and isinstance(content, bytes):
            text = dctx.decompress(content).decode('utf-8', errors='replace')
        elif isinstance(content, bytes):
            text = content.decode('utf-8', errors='replace')
        else:
            text = str(content)
    except:
        return None
    
    # Parse by type
    if real_type == 1:  # Text
        parts = text.split('\n', 1) if '\n' in text else text.split(':\n', 1)
        if len(parts) == 2:
            sender = parts[0].strip()
            msg = parts[1].strip()
        else:
            sender = '?'
            msg = text.strip()
        return f'[{dt_str}] {sender}: {msg}'
    
    elif real_type == 34:  # Voice
        m = re.search(r'fromusername="(.*?)"', text)
        sender = m.group(1) if m else '?'
        lm = re.search(r'voicelength="(\d+)"', text)
        sec = int(lm.group(1)) / 1000 if lm else 0
        return f'[{dt_str}] {sender}: [语音 {sec:.0f}s]'
    
    elif real_type == 49:  # Link/article
        tm = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', text, re.DOTALL)
        if not tm:
            tm = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
        um = re.search(r'<url><!\[CDATA\[(.*?)\]\]></url>', text, re.DOTALL)
        title = tm.group(1).strip() if tm else ''
        url = um.group(1).strip().replace('&amp;', '&') if um else ''
        sm = re.search(r'<fromusername>(.*?)</fromusername>', text)
        sender = sm.group(1) if sm else '?'
        if title:
            return f'[{dt_str}] {sender}: [{title}]' + (f'({url})' if url.startswith('http') else '')
        return None
    
    elif real_type == 10000:  # System/revoke etc.
        return f'[{dt_str}] [系统消息] {text[:60]}'
    
    else:
        # Try to extract any readable content
        clean = text.replace('\x00', '').strip()[:100]
        if len(clean) > 5:
            return f'[{dt_str}] [type={real_type}] {clean}'
        return None


def extract_group_messages(group_username, db_path=None):
    """Extract messages for a group username on target date"""
    if db_path is None:
        db_path = os.path.join(db_dir, 'message_0.db')
    
    expected_table = f'Msg_{hashlib.md5(group_username.encode()).hexdigest()}'
    
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT create_time, message_content, WCDB_CT_message_content, local_type
        FROM "{}"
        WHERE create_time >= ? AND create_time < ?
        ORDER BY create_time
    """.format(expected_table), (ts_start, ts_end)).fetchall()
    conn.close()
    
    output = []
    for r in rows:
        line = format_msg(r)
        if line:
            output.append(line)
    
    return output


# Extract from TOP 5 most active groups on April 15
top_groups = [
    ('49710605556@chatroom', '#1 最活跃 1242条'),
    ('24098585320@chatroom', '#2 459条'),
    ('4917695187@chatroom', '#3 118条'),
    ('53133055615@chatroom', '#4 103条 skill.md群'),
    ('18102033871@chatroom', '#5 82条'),
]

db_path = os.path.join(db_dir, 'message_0.db')

for uname, desc in top_groups:
    msgs = extract_group_messages(uname, db_path)
    print(f'\n{"="*60}')
    print(f'GROUP: {uname} ({desc}) -> {len(msgs)} readable messages')
    print(f'{"="*60}')
    
    # Show first 10 and last 3 messages for context
    for m in msgs[:10]:
        print(m)
    if len(msgs) > 13:
        print(f'  ... ({len(msgs)-13} more messages) ...')
    for m in msgs[-3:]:
        print(m)

# Also save full extraction of #1 group (most likely "ai实践")
top_msgs = extract_group_messages('49710605556@chatroom', db_path)
out_file = r'e:\微信群聊总结\output\2026-04-15_topgroup_raw.txt'
os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    f.write(f'# 群: 49710605556@chatroom\n# 日期: 2026-04-15\n# 消息数: {len(top_msgs)}\n\n')
    f.write('\n'.join(top_msgs))
print(f'\nSaved {len(top_msgs)} messages to {out_file}')
