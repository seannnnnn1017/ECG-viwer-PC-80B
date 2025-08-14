# scp_1lead_extract.py
# 專為「1 導程」SCP-ECG：直接讀 Section 6（未壓縮 int16-LE 假設），輸出 CSV 與預覽圖
# 預設 fs=500Hz；如覺得時間比例不對，可把 FS 改成 250。

import sys, os
import numpy as np
import matplotlib.pyplot as plt

# 針對你這份檔案已知的 Section 6 位置（若換別檔可再偵測）
SEC6_OFF = 173
SEC6_LEN = 9024

# 取樣率（估 500Hz → 4512/500 ≈ 9.024s；若覺得太長/太短，可改成 250）
FS = 150

# 若你知道 ADC 轉換比例（microvolts per LSB），在這裡填，例如 5.0 表示 5 µV/LSB
# 不知道就先設 None，輸出單位會是「原始 LSB」
MICROVOLT_PER_LSB = None  # 例如 4.88

def main(path):
    with open(path, "rb") as f:
        raw = f.read()
    sec6 = raw[SEC6_OFF:SEC6_OFF+SEC6_LEN]
    if len(sec6) != SEC6_LEN:
        raise RuntimeError("Section 6 長度不符，檔案可能不同批或已截斷。")

    # 以 int16 little-endian 解讀
    sig = np.frombuffer(sec6, dtype="<i2")  # shape=(samples,)
    n = sig.size
    t = np.arange(n) / float(FS)

    # 可選：高通去基線飄移（很輕微）
    sig_f = sig.astype(np.float64)
    sig_f -= np.median(sig_f)

    # 單位換算：若有增益資訊，轉成 mV；否則保持 LSB
    unit = "LSB"
    if MICROVOLT_PER_LSB is not None:
        # 由 LSB → μV → mV
        sig_f = sig_f * (MICROVOLT_PER_LSB / 1000.0)
        unit = "mV"

    stem = os.path.splitext(os.path.basename(path))[0]
    out_csv = f"{stem}_1lead.csv"
    out_png = f"{stem}_1lead_preview.png"

    # 存 CSV：time, lead1

    m = np.column_stack([t, sig_f])
    np.savetxt(out_csv, m, delimiter=",", header=f"time,{unit}", comments="", fmt="%.6f")

    # 畫 10 秒預覽（若檔不足 10 秒就全畫）
    max_idx = min(n, int(10 * FS))
    plt.figure(figsize=(10, 3))
    plt.plot(t[:max_idx], sig_f[:max_idx], linewidth=0.9)
    plt.xlabel("Time (s)")
    plt.ylabel(unit)
    plt.title("ECG (1 lead) - first 10 s")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

    print(f"✅ 輸出：{out_csv}, {out_png}")
    print(f"樣本數={n}, 取樣率={FS} Hz, 時長≈{n/FS:.3f}s, 單位={unit}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scp_1lead_extract.py file.SCP")
        raise SystemExit(1)
    main(sys.argv[1])
