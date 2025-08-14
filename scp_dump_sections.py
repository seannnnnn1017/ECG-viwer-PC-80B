# scp_dump_sections_v2.py
# 穩健列出 EN1064 / SCP-ECG 段目錄，找出是否含 Section 6 (Leads data)
import sys, os, struct

def find_magic(data, magic=b"SCPECG"):
    # 在前 1KB 內尋找魔術字
    end = min(len(data), 1024)
    idx = data[:end].find(magic)
    return idx  # -1 代表找不到

def parse_dir_strict(data, magic_off):
    """
    常見實作：magic 後面緊接：
      dir_len (u32 little-endian), dir_entries (u32),
      然後重複 dir_entries 次的 (id u16, length u32, offset u32)
    回傳 list[(id, length, offset)]
    """
    p = magic_off + 6  # "SCPECG" 長度 6
    if p + 8 > len(data): return None
    dir_len, n = struct.unpack_from("<II", data, p)  # 8 bytes
    p += 8
    entries = []
    # 目錄區合理性檢查
    if dir_len <= 0 or n <= 0 or p + n*10 > len(data):
        return None
    for _ in range(n):
        if p + 10 > len(data): return None
        sid, slen, soff = struct.unpack_from("<HI I", data, p)
        p += 10
        # 基本合理性過濾
        if not (0 < sid < 100): return None
        if not (0 < slen <= len(data)): return None
        if not (0 <= soff < len(data)): return None
        entries.append((sid, slen, soff))
    return entries

def parse_dir_fallback(data):
    """
    後備方案：在檔案前 512 bytes 內，以 2 byte 為步長掃描
    嘗試讀 (id u16, len u32, off u32) 的三元組，挑出合理的組合。
    """
    entries = {}
    scan_end = min(512, len(data))
    i = 0
    while i + 10 <= scan_end:
        try:
            sid, slen, soff = struct.unpack_from("<HI I", data, i)
            if 0 < sid < 100 and 0 < slen <= len(data) and 0 <= soff < len(data) and (soff + slen) <= len(data):
                entries[sid] = (slen, soff)
                i += 10
                continue
        except Exception:
            pass
        i += 2
    if not entries: return None
    out = [(sid,)+entries[sid] for sid in sorted(entries)]
    return out

def main(fp):
    with open(fp, "rb") as f:
        data = f.read()

    print("File:", fp)
    print("Size:", os.path.getsize(fp), "bytes")

    magic_off = find_magic(data)
    if magic_off < 0:
        print("❌ 找不到 SCPECG 魔術字，可能不是 SCP-ECG。")
        return

    print(f"✅ 發現 SCPECG at offset {magic_off} (0x{magic_off:02X})")

    entries = parse_dir_strict(data, magic_off)
    if not entries:
        print("⚠️ 嚴格解析未成功，改用 fallback 掃描。")
        entries = parse_dir_fallback(data)

    if not entries:
        print("❌ 無法取得段目錄，可能是非典型目錄格式或檔案截斷。")
        return

    print(f"共偵測到 {len(entries)} 個段：")
    for sid, slen, soff in entries:
        tag = {
            0:"Header",1:"Patient",2:"Acquisition",3:"Manufacturer",
            4:"Measurements",5:"Global diag",6:"Leads data"
        }.get(sid,"")
        extra = f" (Section {sid}: {tag})" if tag else f" (Section {sid})"
        print(f"  ID={sid:2d}  len={slen:6d}  off={soff:6d}{extra}")

    # 提示是否包含波形
    if any(sid == 6 for sid,_,_ in entries):
        print("👉 找到 Section 6（Leads data）：檔內應有波形資料。")
    else:
        print("🤔 沒有偵測到 Section 6，可能是摘要/報告檔，或使用非典型段位。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scp_dump_sections_v2.py file.SCP")
        raise SystemExit(1)
    main(sys.argv[1])
