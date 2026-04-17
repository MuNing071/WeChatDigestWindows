#!/usr/bin/env python3
"""诊断脚本：dump 内存中找到的所有 hex pattern，分析格式"""
import ctypes, ctypes.wintypes as wt, subprocess, re, sys, os

kernel32 = ctypes.windll.kernel32
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80}

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64), ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD), ("_pad1", wt.DWORD),
        ("RegionSize", ctypes.c_uint64), ("State", wt.DWORD),
        ("Protect", wt.DWORD), ("Type", wt.DWORD), ("_pad2", wt.DWORD),
    ]

# 获取主进程 PID
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
                   capture_output=True, text=True)
pids = []
for line in r.stdout.strip().split('\n'):
    if not line.strip(): continue
    p = line.strip('"').split('","')
    if len(p) >= 5: pids.append((int(p[1]), int(p[4].replace(',', '').replace(' K', '').strip() or '0')))
pids.sort(key=lambda x: x[1], reverse=True)
pid = pids[0][0]
print(f"Target: PID={pid}")

h = kernel32.OpenProcess(0x0010 | 0x0400, False, pid)
if not h:
    print("Cannot open process")
    sys.exit(1)

hex_re = re.compile(b"x'([0-9a-fA-F]{64,256})'")
patterns = []

def enum_and_scan():
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFFFFFF:
        if kernel32.VirtualQueryEx(h, ctypes.c_uint64(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.Protect in READABLE and 0 < mbi.RegionSize < 500 * 1024 * 1024:
            buf = ctypes.create_string_buffer(mbi.RegionSize)
            n = ctypes.c_size_t(0)
            if kernel32.ReadProcessMemory(h, ctypes.c_uint64(addr), buf, mbi.RegionSize, ctypes.byref(n)):
                data = buf.raw[:n.value]
                for m in hex_re.finditer(data):
                    hs = m.group(1).decode('ascii')
                    patterns.append((len(hs), hs[:96], hs[-48:]))
        nxt = mbi.BaseAddress + mbi.RegionSize
        if nxt <= addr: break
        addr = nxt

print("Scanning...")
enum_and_scan()
kernel32.CloseHandle(h)

print(f"\nFound {len(patterns)} total patterns")
print(f"\n=== Length Distribution ===")
from collections import Counter
lens = [p[0] for p in patterns]
for ln, cnt in sorted(Counter(lens).items()):
    print(f"  {ln} chars: {cnt} patterns")

print(f"\n=== First 15 patterns (first 96 chars + last 48 chars) ===")
for i, (ln, head, tail) in enumerate(patterns[:15]):
    print(f"  [{i}] len={ln}")
    print(f"      HEAD: {head}")
    print(f"      TAIL: {tail}")
    print()

# Check if any pattern's tail (last 32 chars) matches any DB salt
db_dir = r"E:\Documents\WeChatFiles\xwechat_files\wxid_i68dsaz6jb2s11_8fc0\db_storage"
salts = set()
for root, dirs, files in os.walk(db_dir):
    for f in files:
        if f.endswith('.db') and '-wal' not in f and '-shm' not in f:
            path = os.path.join(root, f)
            with open(path, 'rb') as fin:
                page1 = fin.read(4096)
            if len(page1) >= 16:
                salts.add(page1[:16].hex())

print(f"\nDB salts ({len(salts)}):")
for s in sorted(salts)[:5]:
    print(f"  {s}")

# Check tail matches
tail_matches = 0
for ln, head, tail in patterns:
    salt_candidate = tail[-32:] if len(tail) >= 32 else None
    if salt_candidate and salt_candidate in salts:
        tail_matches += 1
        print(f"\n  TAIL MATCH! Pattern tail ends with valid salt: {salt_candidate}")
        print(f"  Full tail: {tail}")

print(f"\n\nTotal tail matches with DB salts: {tail_matches}/{len(patterns)}")

# Also check: is the entire string just one big key? (no salt appended)
print(f"\n=== Checking if patterns are raw keys (no embedded salt) ===")
for i, (ln, head, tail) in enumerate(patterns[:10]):
    # Try using first 64 chars as key for HMAC verification
    key_hex = head[:64]
    if len(key_hex) >= 64:
        print(f"  Pattern[{i}]: potential_key={key_hex[:32]}...")
