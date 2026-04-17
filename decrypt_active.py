# -*- coding: utf-8 -*-
"""
Use wechat-digest's crypto module to decrypt the ACTIVE WeChat DB (including WAL).
This should give us data up to today.
"""
import sys, os, hashlib, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\微信群聊总结\wechat-digest')

from Crypto.Cipher import AES
import struct

# Constants from wechat-digest/crypto/decrypt.py
PAGE_SZ = 4096
SALT_SZ = 16
RESERVE_SZ = 80
SQLITE_HDR = b'SQLite format 3\x00'
WAL_HEADER_SZ = 32
WAL_FRAME_HEADER_SZ = 24


def derive_key(raw_key_bytes, salt):
    """SQLCipher 4 PBKDF2-HMAC-SHA512 derivation"""
    return hashlib.pbkdf2_hmac('sha512', raw_key_bytes, salt, 256000, dklen=32)


def decrypt_page(enc_key, page_data, pgno):
    iv = page_data[PAGE_SZ - RESERVE_SZ: PAGE_SZ - RESERVE_SZ + 16]
    if pgno == 1:
        encrypted = page_data[SALT_SZ: PAGE_SZ - RESERVE_SZ]
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted)
        return bytes(bytearray(SQLITE_HDR + decrypted + b'\x00' * RESERVE_SZ))
    else:
        encrypted = page_data[:PAGE_SZ - RESERVE_SZ]
        cipher = AES.new(enc_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted)
        return decrypted + b'\x00' * RESERVE_SZ


def full_decrypt(db_path, out_path, enc_key):
    file_size = os.path.getsize(db_path)
    total_pages = file_size // PAGE_SZ
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(db_path, 'rb') as fin, open(out_path, 'wb') as fout:
        for pgno in range(1, total_pages + 1):
            page = fin.read(PAGE_SZ)
            if len(page) < PAGE_SZ:
                if len(page) > 0:
                    page = page + b'\x00' * (PAGE_SZ - len(page))
                else:
                    break
            fout.write(decrypt_page(enc_key, page, pgno))
    return total_pages


def apply_wal(wal_path, db_out_path, enc_key):
    """Decrypt WAL and patch into decrypted DB"""
    if not os.path.exists(wal_path):
        print(f'  No WAL file found')
        return 0
    
    wal_size = os.path.getsize(wal_path)
    if wal_size <= WAL_HEADER_SZ:
        return 0
    
    patched = 0
    with open(wal_path, 'rb') as wf, open(db_out_path, 'r+b') as df:
        wal_hdr = wf.read(WAL_HEADER_SZ)
        wal_salt1 = struct.unpack('>I', wal_hdr[16:20])[0]
        wal_salt2 = struct.unpack('>I', wal_hdr[20:24])[0]
        frame_size = WAL_FRAME_HEADER_SZ + PAGE_SZ
        
        while wf.tell() + frame_size <= wal_size:
            fh = wf.read(WAL_FRAME_HEADER_SZ)
            if len(fh) < WAL_FRAME_HEADER_SZ:
                break
            pgno = struct.unpack('>I', fh[0:4])[0]
            frame_salt1 = struct.unpack('>I', fh[8:12])[0]
            frame_salt2 = struct.unpack('>I', fh[12:16])[0]
            ep = wf.read(PAGE_SZ)
            if len(ep) < PAGE_SZ:
                break
            if pgno == 0 or pgno > 1000000:
                continue
            if frame_salt1 != wal_salt1 or frame_salt2 != wal_salt2:
                continue
            dec = decrypt_page(enc_key, ep, pgno)
            df.seek((pgno - 1) * PAGE_SZ)
            df.write(dec)
            patched += 1
    
    return patched


# === Main ===
raw_db_key_hex = '49f459a35b3046b39007edcc6c35be772ae49b44a3294c04b0749ad96d311994'
raw_db_key = bytes.fromhex(raw_db_key_hex)

src_dir = r'E:\文档\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage\message'
out_dir = r'e:\微信群聊总结\wetrace-bin\wetrace\data\message_active'

# Process message_0.db (the main one with recent data)
src_db = os.path.join(src_dir, 'message_0.db')
out_db = os.path.join(out_dir, 'message_0.db')
wal_file = src_db + '-wal'
print(f'Source DB: {src_db} ({os.path.getsize(src_db)//1024//1024}MB)')
print(f'WAL file: {wal_file} ({os.path.getsize(wal_file)//1024}KB)' if os.path.exists(wal_file) else f'WAL: NOT FOUND')

if not os.path.exists(src_db):
    print(f'ERROR: Source DB not found!')
    sys.exit(1)

# Read salt from first page of source
with open(src_db, 'rb') as f:
    header_page = f.read(PAGE_SZ)
salt = header_page[:SALT_SZ]

print(f'Salt: {salt.hex()}')

# Derive encryption key
enc_key = derive_key(raw_db_key, salt)
print(f'Derived enc_key: {enc_key.hex()[:32]}...')

# Decrypt main DB
print(f'\nDecrypting {src_db}...')
pages = full_decrypt(src_db, out_db, enc_key)
print(f'  {pages} pages decrypted -> {out_db}')

# Apply WAL
print(f'\nApplying WAL...')
wal_pages = apply_wal(wal_file, out_db, enc_key)
print(f'  {wal_pages} WAL frames applied')

# Verify with SQLite
import sqlite3, datetime
conn = sqlite3.connect(out_db)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'").fetchall()]
print(f'\n=== Decrypted DB: {len(tables)} Msg tables ===')

# Show date range and top groups
stats = []
for t in tables[:50]:
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        r_max = conn.execute(f'SELECT MAX(create_time) FROM [{t}]').fetchone()[0]
        r_min = conn.execute(f'SELECT MIN(create_time) FROM [{t}]').fetchone()[0]
        if r_max:
            dmax = datetime.datetime.fromtimestamp(r_max).strftime('%Y-%m-%d %H:%M')
            dmin = datetime.datetime.fromtimestamp(r_min).strftime('%Y-%m-%d %H:%M') if r_min else '?'
            stats.append((cnt, t, dmin, dmax))
    except Exception as e:
        pass

stats.sort(key=lambda x: -x[0])
print('\nTop 20 groups by count:')
for cnt, t, dmin, dmax in stats[:20]:
    print(f'  {cnt:5d} | {dmin} ~ {dmax} | {t}')

# Check for April 15!
ts_s = int(datetime.datetime(2026,4,15).timestamp())
ts_e = int(datetime.datetime(2026,4,16).timestamp())
apr_total = 0
apr_groups = []
for t in tables:
    try:
        c = conn.execute(f'SELECT COUNT(*) FROM [{t}] WHERE create_time>=? AND create_time<?', (ts_s, ts_e)).fetchone()[0]
        if c > 0:
            apr_total += c
            apr_groups.append((t, c))
    except:
        pass

print(f'\n*** April 15 messages: {apr_total} in {len(apr_groups)} groups ***')
for t, c in sorted(apr_groups, key=lambda x:-x[1])[:30]:
    print(f'  {c:4d} msgs -> {t}')

conn.close()
