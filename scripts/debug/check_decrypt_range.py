# -*- coding: utf-8 -*-
import sqlite3, os, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message'
msg_dbs = sorted([f for f in os.listdir(db_dir) if f.startswith('message_') and f.endswith('.db')])

print('=== Decrypted message_0.db time range ===')
db0 = os.path.join(db_dir, 'message_0.db')
conn = sqlite3.connect(db0)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
for t in tables[:10]:
    try:
        r_min = conn.execute(f'SELECT MIN(create_time) FROM "{t}"').fetchone()[0]
        r_max = conn.execute(f'SELECT MAX(create_time) FROM "{t}"').fetchone()[0]
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if r_min and r_max:
            dmin = datetime.datetime.fromtimestamp(r_min).strftime('%Y-%m-%d %H:%M')
            dmax = datetime.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d %H:%M')
            print(f'  {t[:50]}: {dmin} ~ {dmax} ({cnt} msgs)')
    except Exception as e:
        print(f'  {t}: error {e}')
conn.close()

# Also check file modification times
print('\n=== Decrypted file modification times ===')
for f in msg_dbs:
    fp = os.path.join(db_dir, f)
    st = os.stat(fp)
    mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    sz_mb = round(st.st_size / (1024*1024), 1)
    print(f'  {f}: modified={mt}, size={sz_mb}MB')

# Check source (encrypted) active dir
print('\n=== Source active message_0.db ===')
src0 = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message\message_0.db'
if os.path.exists(src0):
    st2 = os.stat(src0)
    mt2 = datetime.datetime.fromtimestamp(st2.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    # Read first bytes to confirm it's encrypted
    with open(src0, 'rb') as f:
        header = f.read(16)
    print(f'  modified={mt2}, size={round(st2.st_size/(1024*1024),1)}MB, header={header.hex()}')

# Compare sizes: source vs decrypted
print('\n=== Size comparison ===')
src_dir = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message'
for f in ['message_0.db', 'biz_message_0.db', 'message_resource.db']:
    src_f = os.path.join(src_dir, f)
    dec_f = os.path.join(db_dir, f)
    src_sz = os.path.getsize(src_f) if os.path.exists(src_f) else 0
    dec_sz = os.path.getsize(dec_f) if os.path.exists(dec_f) else 0
    print(f'  {f}: source={src_sz//(1024*1024)}MB vs decrypted={dec_sz//(1024*1024)}MB')
