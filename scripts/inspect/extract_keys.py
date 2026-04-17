#!/usr/bin/env python3
"""
微信 4.x 数据库密钥提取工具（Windows 增强版）
基于 wechat-digest 的内存扫描框架 + wechat-digest 的 HMAC 校验与交叉验证机制。

改进:
1. HMAC-SHA512 Page 1 验证 - 确认提取的 enc_key 能正确解密数据库
2. 交叉验证 - 已找到的 key 尝试解锁剩余未匹配的 DB
3. 更精细的错误报告和调试输出
4. 支持微信 4.1.x 版本

用法：
    python extract_keys.py --db-dir <path_to_db_storage>

输出：
    ./all_keys.json - 密钥文件（兼容 wechat-digest 格式）
    ./config.json   - 配置文件
"""

import ctypes
import ctypes.wintypes as wt
import functools
import hashlib
import hmac as hmac_mod
import json
import os
import re
import struct
import subprocess
import sys
import time

print = functools.partial(print, flush=True)

# ============================================================
# 常量定义
# ============================================================
PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80  # IV(16) + HMAC(64)

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


# ============================================================
# 微信进程检测
# ============================================================
def get_pids():
    """返回所有 Weixin.exe 进程的 (pid, mem_kb) 列表，按内存降序"""
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, timeout=30
    )
    pids = []
    for line in r.stdout.strip().split('\n'):
        if not line.strip():
            continue
        p = line.strip('"').split('","')
        if len(p) >= 5:
            pid = int(p[1])
            mem = int(p[4].replace(',', '').replace(' K', '').strip() or '0')
            pids.append((pid, mem))
    if not pids:
        raise RuntimeError("Weixin.exe 未运行")
    pids.sort(key=lambda x: x[1], reverse=True)
    for pid, mem in pids:
        print(f"[+] Weixin.exe PID={pid} ({mem // 1024}MB)")
    return pids


def read_mem(h, addr, sz):
    buf = ctypes.create_string_buffer(sz)
    n = ctypes.c_size_t(0)
    if kernel32.ReadProcessMemory(h, ctypes.c_uint64(addr), buf, sz, ctypes.byref(n)):
        return buf.raw[:n.value]
    return None


def enum_regions(h):
    regs = []
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFFFFFF:
        if kernel32.VirtualQueryEx(h, ctypes.c_uint64(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            break
        if mbi.State == MEM_COMMIT and mbi.Protect in READABLE and 0 < mbi.RegionSize < 500 * 1024 * 1024:
            regs.append((mbi.BaseAddress, mbi.RegionSize))
        nxt = mbi.BaseAddress + mbi.RegionSize
        if nxt <= addr:
            break
        addr = nxt
    return regs


# ============================================================
# 数据库文件收集
# ============================================================
def collect_db_files(db_dir):
    """收集所有 .db 文件，返回 (files_list, salt_map)"""
    db_files = []  # [(rel_path, full_path, size, salt_hex, page1_bytes)]
    salt_to_dbs = {}  # salt_hex -> [rel_paths]

    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if not f.endswith('.db') or f.endswith('-wal') or f.endswith('-shm'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, db_dir)
            try:
                sz = os.path.getsize(path)
                with open(path, 'rb') as fin:
                    page1 = fin.read(PAGE_SZ)
                if len(page1) < PAGE_SZ:
                    continue
                salt_hex = page1[:SALT_SZ].hex()
                db_files.append((rel, path, sz, salt_hex, page1))
                if salt_hex not in salt_to_dbs:
                    salt_to_dbs[salt_hex] = []
                salt_to_dbs[salt_hex].append(rel)
            except OSError:
                continue

    return db_files, salt_to_dbs


# ============================================================
# HMAC 密钥验证（wechat-decrypt 核心算法）
# ============================================================
def verify_enc_key(enc_key, db_page1):
    """
    通过 HMAC-SHA512 校验 page 1 验证 enc_key 是否正确。
    
    SQLCipher 4 的页面格式：
    - Page 1: [salt(16)] [encrypted_data(4000)] [iv(16)] [hmac(64)]
    - mac_salt = salt XOR 0x3A
    - mac_key = PBKDF2-HMAC-SHA512(enc_key, mac_salt, iterations=2, dklen=32)
    - hmac_data = encrypted_data + iv (即 page1[16:4096-64])
    - 比较计算的 hmac 与存储的 hmac
    """
    salt = db_page1[:SALT_SZ]
    mac_salt = bytes(b ^ 0x3a for b in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)

    # hmac_data = 从 salt 后到 hmac 前（加密数据 + IV）
    hmac_data_start = SALT_SZ
    hmac_data_end = PAGE_SZ - HMAC_SZ
    hmac_data = db_page1[hmac_data_start : hmac_data_end]
    stored_hmac = db_page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]

    hm = hmac_mod.new(mac_key, hmac_data, hashlib.sha512)
    hm.update(struct.pack('<I', 1))  # page number = 1

    return hmac_mod.compare_digest(hm.digest(), stored_hmac)


# ============================================================
# 内存扫描
# ============================================================
def scan_memory_for_keys(data, hex_re, db_files, salt_to_dbs, key_map, remaining_salts, base_addr, pid, print_fn):
    """在一段内存数据中搜索并匹配密钥模式"""
    matches = 0
    # 收集诊断信息（仅首次调用时输出）
    diag_info = not hasattr(scan_memory_for_keys, '_diag_done')
    if diag_info:
        scan_memory_for_keys._diag_done = True
        scan_memory_for_keys._patterns = []
    
    for m in hex_re.finditer(data):
        hex_str = m.group(1).decode('ascii')
        hex_len = len(hex_str)

        # 收集诊断信息
        if diag_info:
            scan_memory_for_keys._patterns.append((hex_len, hex_str[:80], hex_str[-40:]))

        if hex_len < 96 or hex_len % 2 != 0:
            matches += 1
            continue

        # 尝试多种分割策略
        strategies = [
            # 策略1: 标准 SQLCipher 格式 x'<enc_key(64)><salt(32)>'
            ("std", 64, hex_len - 32),
            # 策略2: 可能整个都是 key（salt 在别处）
            ("full_as_key", min(hex_len // 2, 64), None),
        ]
        
        matched = False
        for strat_name, key_start, salt_end in strategies:
            if salt_end is not None:
                enc_key_hex = hex_str[key_start:key_start + 64]
                salt_hex = hex_str[salt_end:salt_end + 32]
            else:
                enc_key_hex = hex_str[:key_start]
                salt_hex = None
            
            if len(enc_key_hex) < 64:
                continue
                
            # 如果有目标 salt 才验证
            target_salts = remaining_salts if salt_hex is None else {salt_hex}
            
            try:
                enc_key = bytes.fromhex(enc_key_hex[:64])
            except ValueError:
                continue

            for test_salt in list(target_salts):
                if test_salt not in remaining_salts:
                    continue
                for rel, path, sz, s, page1 in db_files:
                    if s != test_salt:
                        continue
                    if verify_enc_key(enc_key, page1):
                        key_map[test_salt] = enc_key_hex[:64]
                        remaining_salts.discard(test_salt)
                        offset = base_addr + m.start()
                        print_fn(f"  [*] FOUND! ({strat_name}) salt={test_salt} -> DB={rel}")
                        print_fn(f"      key={enc_key_hex[:16]}... addr=0x{offset:X} PID={pid}")
                        matched = True
                        break
                if matched:
                    break
            if matched:
                break

        if not matched:
            matches += 1

    return matches


def cross_verify_keys(db_files, salt_to_dbs, key_map, print_fn):
    """用已找到的 key 交叉验证未匹配的 salt（可能有共享密钥的情况）"""
    missing_salts = set(salt_to_dbs.keys()) - set(key_map.keys())
    if not missing_salts or not key_map:
        return

    print_fn(f"\n[*] 还有 {len(missing_salts)} 个 salt 未匹配，尝试交叉验证...")
    found_any = False

    for salt_hex in list(missing_salts):
        for rel, path, sz, s, page1 in db_files:
            if s != salt_hex:
                continue
            for known_salt, known_key_hex in key_map.items():
                try:
                    enc_key = bytes.fromhex(known_key_hex)
                    if verify_enc_key(enc_key, page1):
                        key_map[salt_hex] = known_key_hex
                        missing_salts.discard(salt_hex)
                        print_fn(f"  [CROSS] salt={salt_hex} 复用 key from {known_salt} ({rel})")
                        found_any = True
                        break
                except (ValueError, Exception):
                    continue
            if salt_hex not in missing_salts:
                break

    if not found_any:
        print_fn("  交叉验证未找到额外匹配")


# ============================================================
# 主流程
# ============================================================
def save_results(db_files, salt_to_dbs, key_map, output_file, print_fn):
    """保存结果到 JSON 文件（兼容 wechat-digest 格式）"""
    result = {}
    for rel, path, sz, salt_hex, page1 in db_files:
        if salt_hex in key_map:
            result[rel] = {
                "enc_key": key_map[salt_hex],
                "salt": salt_hex,
            }
        else:
            print_fn(f"  MISSING: {rel} (salt={salt_hex})")

    if not result:
        raise RuntimeError("未能从任何微信进程中提取到密钥")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def main():
    parser = argparse.ArgumentParser(description='微信 4.x Windows 增强版密钥提取器')
    parser.add_argument('--db-dir', required=True, help='微信 db_storage 目录路径')
    parser.add_argument('--output', default=None, help='输出 JSON 文件路径（默认 ./all_keys.json）')
    args = parser.parse_args()

    db_dir = os.path.abspath(args.db_dir)
    output_file = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_keys.json')

    print("=" * 60)
    print("  微信 4.x 增强版密钥提取器 (HMAC 校验)")
    print("=" * 60)

    if not os.path.isdir(db_dir):
        print(f"[!] 目录不存在: {db_dir}")
        sys.exit(1)

    # 收集数据库文件
    db_files, salt_to_dbs = collect_db_files(db_dir)
    print(f"\n找到 {len(db_files)} 个数据库, {len(salt_to_dbs)} 个不同的salt")
    for salt_hex, dbs in sorted(salt_to_dbs.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  salt {salt_hex}: {', '.join(dbs)}")

    # 获取进程列表
    pids = get_pids()

    # 内存扫描参数
    hex_re = re.compile(b"x'([0-9a-fA-F]{96,256})'")
    key_map = {}
    remaining_salts = set(salt_to_dbs.keys())
    all_hex_matches = 0
    t0 = time.time()

    for pid_val, mem_kb in pids:
        h = kernel32.OpenProcess(0x0010 | 0x0400, False, pid_val)
        if not h:
            print(f"[WARN] 无法打开进程 PID={pid_val}，跳过")
            continue

        try:
            regions = enum_regions(h)
            total_bytes = sum(s for _, s in regions)
            total_mb = total_bytes / 1024 / 1024
            print(f"\n[*] 扫描 PID={pid_val} ({total_mb:.0f}MB, {len(regions)} 区域)")

            scanned_bytes = 0
            for reg_idx, (base, size) in enumerate(regions):
                data = read_mem(h, base, size)
                scanned_bytes += size
                if not data:
                    continue

                all_hex_matches += scan_memory_for_keys(
                    data, hex_re, db_files, salt_to_dbs,
                    key_map, remaining_salts, base, pid_val, print,
                )

                if (reg_idx + 1) % 200 == 0:
                    elapsed = time.time() - t0
                    progress = scanned_bytes / total_bytes * 100 if total_bytes else 100
                    print(
                        f"  [{progress:.1f}%] {len(key_map)}/{len(salt_to_dbs)} salts matched, "
                        f"{all_hex_matches} hex patterns, {elapsed:.1f}s"
                    )
        finally:
            kernel32.CloseHandle(h)

        if not remaining_salts:
            print(f"\n[+] 所有密钥已找到，跳过剩余进程")
            break

    elapsed = time.time() - t0
    print(f"\n扫描完成: {elapsed:.1f}s, {len(pids)} 个进程, {all_hex_matches} hex 模式")

    # 诊断信息：显示找到的 pattern 长度分布和样本
    if hasattr(scan_memory_for_keys, '_patterns') and scan_memory_for_keys._patterns:
        lengths = [p[0] for p in scan_memory_for_keys._patterns]
        from collections import Counter
        len_counts = Counter(lengths)
        print(f"\n[诊断] Pattern 长度分布:")
        for ln, cnt in sorted(len_counts.items()):
            print(f"  {ln} 字符: {cnt} 个")
        # 显示前5个样本
        print(f"\n[诊断] 前5个 pattern 样本:")
        for i, (ln, head, tail) in enumerate(scan_memory_for_keys._patterns[:5]):
            print(f"  [{i}] len={ln} head={head}...tail={tail}")

    # 交叉验证
    cross_verify_keys(db_files, salt_to_dbs, key_map, print)

    # 保存结果
    result = save_results(db_files, salt_to_dbs, key_map, output_file, print)

    # 输出配置
    cfg = {"db_dir": db_dir}
    cfg_path = os.path.join(os.path.dirname(output_file), 'config.json')
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print(f"\n[+] 完成!")
    print(f"  配置: {cfg_path}")
    print(f"  密钥: {output_file}")
    print(f"  匹配: {len(result)}/{len(salt_to_dbs)} 个数据库")


if __name__ == '__main__':
    import argparse
    main()
