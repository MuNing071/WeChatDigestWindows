# -*- coding: utf-8 -*-
"""
Extract ALL readable messages from target group on April 15,
then call Doubao (Volcano Engine) LLM API for summarization.
"""
import sqlite3, os, sys, io, datetime, re, hashlib, json, urllib.request, urllib.error
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Zstd setup
try:
    import zstandard as zstd
    dctx = zstd.ZstdDecompressor()
except:
    dctx = None

db_path = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message_active\message_0.db'
target_group = '49710605556@chatroom'  # ai实践群
target_date = '2026-04-15'

base = datetime.datetime.strptime(target_date, '%Y-%m-%d')
ts_start = int(base.timestamp())
ts_end = int((base + datetime.timedelta(days=1)).timestamp())

expected_table = f'Msg_{hashlib.md5(target_group.encode()).hexdigest()}'

def decompress(content, ct_val):
    if ct_val == 4 and dctx and isinstance(content, bytes):
        return dctx.decompress(content).decode('utf-8', errors='replace')
    elif isinstance(content, bytes):
        return content.decode('utf-8', errors='replace')
    return str(content)

def extract_all():
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT create_time, message_content, WCDB_CT_message_content, local_type
        FROM "{}"
        WHERE create_time >= ? AND create_time < ?
        ORDER BY create_time
    """.format(expected_table), (ts_start, ts_end)).fetchall()
    conn.close()

    messages = []
    for ts_val, content, ct_val, lt_val in rows:
        if not content or ts_val == 0:
            continue
        
        dt_str = datetime.datetime.fromtimestamp(ts_val).strftime('%H:%M')
        real_type = lt_val & 0xFFFFFFFF
        
        try:
            text = decompress(content, ct_val)
        except:
            continue
        
        if real_type == 1:
            parts = text.split('\n', 1) if '\n' in text else text.split(':\n', 1)
            sender = parts[0].strip() if len(parts) == 2 else '?'
            msg_body = parts[1].strip() if len(parts) == 2 else text.strip()
            if msg_body and len(msg_body) > 1:
                messages.append(f'[{dt_str}] {sender}: {msg_body}')
        
        elif real_type == 49:
            tm = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', text, re.DOTALL)
            if not tm:
                tm = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
            if tm:
                title = tm.group(1).strip()
                sm = re.search(r'<fromusername>(.*?)</fromusername>', text)
                sender = sm.group(1) if sm else '?'
                messages.append(f'[{dt_str}] {sender}: [{title}]')
    
    return messages

print(f'Extracting {target_group} on {target_date}...')
msgs = extract_all()
print(f'Extracted {len(msgs)} readable messages')

# Save raw chat log
out_dir = r'e:\微信群聊总结\output'
os.makedirs(out_dir, exist_ok=True)

raw_path = os.path.join(out_dir, f'{target_date}-ai_practice-chat.md')
with open(raw_path, 'w', encoding='utf-8') as f:
    f.write(f'# AI实践群聊天记录\n')
    f.write(f'> 日期: {target_date}\n')
    f.write(f'> 消息数: {len(msgs)}\n\n')
    f.write('---\n\n')
    f.write('\n'.join(msgs))
print(f'Saved raw chat to: {raw_path}')

# === Call Doubao (Volcano Engine) API ===
print('\nCalling Doubao API for summary...')

# Volcano Engine (火山引擎) API Key - correct format is UUID only
API_KEY = 'your-doubao-api-key-uuid'
MODEL = 'doubao-seed-2-0-lite-260215'
ENDPOINT = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'

# Build chat content (truncate if too long - keep most recent messages first or sample evenly)
MAX_MSGS_FOR_LLM = 500  # Limit context window
if len(msgs) > MAX_MSGS_FOR_LLM:
    # Keep first 50 + last 450 + evenly spaced middle
    sampled = msgs[:50]
    step = max(1, (len(msgs) - 100) // 400)
    for i in range(50, len(msgs)-50, step):
        sampled.append(msgs[i])
    sampled.extend(msgs[-50:])
    chat_content = '\n'.join(sampled)
else:
    chat_content = '\n'.join(msgs)

prompt = f"""你是一个微信群聊分析专家。请对以下微信群聊记录进行结构化分析和总结。

## 群聊基本信息
- 群名称: AI实践群
- 日期: {target_date}
- 总消息数: {len(msgs)} 条（当前展示前{min(len(chat_content.split(chr(10))), len(msgs))}条）

## 要求
请按以下格式输出 Markdown 报告：

### 1. 概述
用2-3句话概括当天讨论的核心主题和活跃度。

### 2. 主要话题
列出3-5个主要讨论话题，每个话题附上关键观点和参与人。

### 3. 关键信息
提取当天讨论中有价值的信息点（工具推荐、技术方案、链接资源、决策结论等）。

### 4. 活跃成员
列出最活跃的5位成员及其贡献方向。

### 5. 待跟进事项
如果有需要后续行动或待解决的问题，请列出。

---

## 聊天记录

{chat_content}
"""

payload = json.dumps({
    'model': MODEL,
    'messages': [
        {'role': 'system', 'content': '你是微信群聊分析专家，擅长从大量聊天记录中提炼有价值的信息。输出要求：中文、结构化Markdown、简洁精准。'},
        {'role': 'user', 'content': prompt}
    ],
    'max_tokens': 4000,
    'temperature': 0.3
}).encode('utf-8')

req = urllib.request.Request(
    ENDPOINT,
    data=payload,
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    },
    method='POST'
)

try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    
    summary_text = result['choices'][0]['message']['content']
    
    # Save summary
    summary_path = os.path.join(out_dir, f'{target_date}-ai_practice-summary.md')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f'# AI实践群日报\n\n')
        f.write(f'> **日期**: {target_date}\n')
        f.write(f'> **总消息数**: {len(msgs)} 条\n')
        f.write(f'> **分析模型**: {MODEL}\n')
        f.write(f'> **生成时间**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n')
        f.write('---\n\n')
        f.write(summary_text)
    
    print(f'\nSummary saved to: {summary_path}')
    print(f'\n=== SUMMARY PREVIEW ===\n')
    print(summary_text[:2000])
    if len(summary_text) > 2000:
        print(f'\n... ({len(summary_text) - 2000} more chars)')
        
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print(f'API Error {e.code}: {body}')
except Exception as e:
    print(f'Error: {e}')
