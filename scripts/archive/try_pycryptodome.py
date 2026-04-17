# -*- coding: utf-8 -*-
"""
Try to decrypt the active message_0.db directly using pycryptodome,
then open with SQLite to see all data including WAL-merged content.
"""
import os, sys, io, hashlib, hmac, struct
from Crypto.Cipher import AES
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_key_hex = '49f459a35b3046b39007edcc6c35be772ae49b44a3294c04b0749ad96d311994'
db_key = bytes.fromhex(db_key_hex)

src_db = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message\message_0.db'
out_db = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message_active\message_0.db'

os.makedirs(os.path.dirname(out_db), exist_ok=True)

# Read source DB
with open(src_db, 'rb') as f:
    data = f.read()

print(f'Source size: {len(data)} bytes')
print(f'Header: {data[:16].hex()}')

salt = data[:16]
print(f'Salt: {salt.hex()}')

# SQLCipher 4 derivation
derived_key = hashlib.pbkdf2_hmac('sha512', db_key, salt, 256000, dklen=32)
print(f'Derived key: {derived_key.hex()[:32]}...')

mac_salt = bytes([b ^ 0x3A for b in salt])
mac_key = hashlib.pbkdf2_hmac('sha512', db_key, mac_salt, 2, dklen=32)

# For each page, decrypt
page_size = 4096  # default
if len(data) >= 100:
    # Check page size from header (offset 16-17 for big-endian page size)
    ps_raw = struct.unpack('>H', data[16:18])[0]
    if ps_raw == 1:
        page_size = 65536
    elif ps_raw >= 512:
        page_size = ps_raw

print(f'Page size: {page_size}')

total_pages = len(data) // page_size
print(f'Total pages: {total_pages}')

decrypted_pages = bytearray()

for i in range(total_pages):
    offset = i * page_size
    page = data[offset:offset+page_size]
    
    if i == 0:
        # Page 1 has special layout: salt(16) + reserved(80) + rest
        if len(page) <= 96:
            decrypted_pages.extend(page)
            continue
        
        iv = page[96:112]
        ciphertext = page[112:-64] if len(page) > 176 else page[112:]
        stored_mac = page[-64:] if len(page) > 112 + 64 else b''
        
        if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
            decrypted_pages.extend(page)
            continue
        
        cipher = AES.new(derived_key, AES.MODE_CBC, iv=iv)
        decrypted = cipher.decrypt(ciphertext)
        
        # Verify MAC if present
        if stored_mac:
            hmac_data = page[16:-64]  # everything after salt but before mac
            computed_mac = hmac.new(mac_key, hmac_data, hashlib.sha512).digest()
            mac_match = computed_mac == stored_mac
            if not mac_match:
                print(f'  Page 0: MAC MISMATCH!')
        
        result = bytearray()
        result.extend(page[:96])  # header
        result.extend(decrypted)
        if stored_mac:
            result.extend(stored_mac)
        
        # Pad to page_size
        while len(result) < page_size:
            result.append(0)
        decrypted_pages.extend(bytes(result[:page_size]))
    else:
        # Normal pages: salt(16)? No, pages > 1 don't have salt
        # Actually in SQLCipher 4, non-first pages:
        # No salt, just IV(16) + ciphertext + HMAC(64)
        if len(page) < 80:
            decrypted_pages.extend(page)
            continue
        
        iv = page[:16]
        ciphertext = page[16:-64]
        stored_mac = page[-64:]
        
        if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
            decrypted_pages.extend(page)
            continue
        
        cipher = AES.new(derived_key, AES.MODE_CBC, iv=iv)
        decrypted = cipher.decrypt(ciphertext)
        
        result = bytearray()
        result.extend(decrypted)
        result.extend(stored_mac)
        while len(result) < page_size:
            result.append(0)
        decrypted_pages.extend(bytes(result[:page_size]))

with open(out_db, 'wb') as f:
    f.write(bytes(decrypted_pages))

print(f'\nDecrypted output: {out_db}')
print(f'Output size: {len(decrypted_pages)} bytes')

# Try to open with SQLite
import sqlite3
try:
    conn = sqlite3.connect(out_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f'\nTables: {len(tables)}')
    msg_tables = [t[0] for t in tables if t[0].startswith('Msg_')]
    print(f'Msg tables: {len(msg_tables)}')
    
    # Show top groups with latest dates
    import datetime as dt
    stats = []
    for t in msg_tables[:30]:
        try:
            cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
            r_max = conn.execute(f'SELECT MAX(create_time) FROM [{t}]').fetchone()[0]
            if r_max:
                dmax = dt.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d %H:%M')
                stats.append((cnt, t[:50], dmax))
        except:
            pass
    
    stats.sort(key=lambda x: -x[0])
    print('\nTop 15 groups:')
    for c, t, d in stats[:15]:
        print(f'  {c:5d} msgs | latest={d} | {t}')
    
    # Check April 15
    ts_s = int(dt.datetime(2026,4,15).timestamp())
    ts_e = int(dt.datetime(2026,4,16).timestamp())
    apr_count = 0
    for t in msg_tables:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM [{t}] WHERE create_time>=? AND create_time<?', (ts_s, ts_e)).fetchone()[0]
            apr_count += c
        except:
            pass
    print(f'\nApril 15 messages: {apr_count}')
    
    conn.close()
except Exception as e:
    print(f'SQLite error: {e}')
