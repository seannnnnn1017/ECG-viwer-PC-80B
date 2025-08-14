# scp_1lead_batch.py
# 批次讀取資料夾內的 1 導程 SCP-ECG（假設 Section6 為未壓縮 int16-LE）
# 以數字自然排序處理 (1.SCP, 2.SCP, 3.SCP ...)，輸出：
# 1) 每檔 CSV
# 2) 每檔簡單預覽 PNG（前 PREVIEW_SECONDS 秒）
# 3) 每檔「三行排列」PNG（白底、含 grid，不用粉色背景），並顯示心跳（BPM）

import sys, os, glob
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# === 檔案結構（依你的裝置批次而定） ===
SEC6_OFF = 173
SEC6_LEN = 9024

# === 取樣率 & 單位 ===
FS = 150  # 你現在設定的取樣率（如需對齊官方軟體可改 250/500）
MICROVOLT_PER_LSB = None  # 例：4.88；未知就 None（輸出 LSB）

# === 圖表參數 ===
PREVIEW_SECONDS = 10          # 單檔 preview 的秒數
THREEROW_SECONDS_PER_ROW = 10 # 三行圖：每一行顯示幾秒
THREEROW_ROWS = 3             # 固定三行
LINE_WIDTH = 0.9

def natural_key_for_scp(path):
    base = os.path.basename(path)
    stem, _ = os.path.splitext(base)
    try:
        num = int(stem)
    except ValueError:
        num = 10**9
    return (num, base.lower())

def read_section6_1lead(filepath):
    with open(filepath, "rb") as f:
        raw = f.read()
    sec6 = raw[SEC6_OFF:SEC6_OFF+SEC6_LEN]
    if len(sec6) != SEC6_LEN:
        raise RuntimeError(f"[{os.path.basename(filepath)}] Section 6 長度不符，請檢查 SEC6_OFF/SEC6_LEN。")

    sig = np.frombuffer(sec6, dtype="<i2")  # (samples,)
    n = sig.size
    t = np.arange(n) / float(FS)

    # 去基線漂移（簡單中位數）
    sig_f = sig.astype(np.float64)
    sig_f -= np.median(sig_f)

    unit = "LSB"
    if MICROVOLT_PER_LSB is not None:
        sig_f = sig_f * (MICROVOLT_PER_LSB / 1000.0)  # μV -> mV
        unit = "mV"

    return t, sig_f, unit

def calc_heart_rate(sig, fs):
    """利用簡單 R 波峰值檢測計算心跳（BPM）"""
    # 取絕對值並平滑
    sig_abs = np.abs(sig)
    # 偵測門檻：均值 + 0.5 標準差
    thresh = np.mean(sig_abs) + 0.5 * np.std(sig_abs)
    peaks, _ = find_peaks(sig_abs, height=thresh, distance=int(0.4 * fs))  # 至少 0.4s 間隔
    if len(peaks) < 2:
        return None
    rr_intervals = np.diff(peaks) / fs
    mean_rr = np.mean(rr_intervals)
    bpm = 60.0 / mean_rr
    return bpm

def save_per_file_outputs(out_dir, stem, t, sig, unit):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, f"{stem}_1lead.csv")
    out_png = os.path.join(out_dir, f"{stem}_1lead_preview.png")

    # CSV
    m = np.column_stack([t, sig])
    np.savetxt(out_csv, m, delimiter=",", header=f"time,{unit}", comments="", fmt="%.6f")

    # 單檔預覽（限定 PREVIEW_SECONDS）
    max_idx = len(t)
    if PREVIEW_SECONDS is not None and len(t) > 1:
        duration = t[-1]
        if duration > 0:
            est_fs = (len(t)-1) / duration
            max_idx = min(len(t), int(PREVIEW_SECONDS * est_fs))

    plt.figure(figsize=(10, 3))
    plt.plot(t[:max_idx], sig[:max_idx], linewidth=LINE_WIDTH)
    plt.xlabel("Time (s)")
    plt.ylabel(unit)
    plt.title(f"{stem} - first {PREVIEW_SECONDS}s")
    plt.grid(True, linewidth=0.4, alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return out_csv, out_png

def save_three_row_plot(out_dir, stem, t, sig, unit):
    """
    生成「三行排列」的圖。白底、有 grid，不用粉色紙格。
    顯示心跳 BPM。
    """
    os.makedirs(out_dir, exist_ok=True)
    total_rows = THREEROW_ROWS
    sec_per_row = THREEROW_SECONDS_PER_ROW
    N = len(t)
    if N < 2 or t[-1] <= 0:
        return None
    est_fs = (len(t)-1) / t[-1]
    samples_per_row = int(round(sec_per_row * est_fs))
    if samples_per_row <= 0:
        return None

    # 計算全圖 y 範圍
    y_min = np.nanmin(sig)
    y_max = np.nanmax(sig)
    if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min == y_max:
        y_min, y_max = -1.0, 1.0

    # 計算心跳
    bpm = calc_heart_rate(sig, FS)
    bpm_text = f" | Heart Rate: {bpm:.1f} BPM" if bpm else ""

    # 畫三行
    fig = plt.figure(figsize=(10, 7.5))
    fig.suptitle(f"{stem}  |  {sec_per_row}s x {total_rows} rows   (FS={FS}Hz, unit={unit}){bpm_text}", fontsize=11)

    for r in range(total_rows):
        ax = fig.add_subplot(total_rows, 1, r+1)
        s = r * samples_per_row
        e = min(N, s + samples_per_row)
        if s >= e:
            ax.axis("off")
            continue
        tt = t[s:e] - t[s]
        yy = sig[s:e]
        ax.plot(tt, yy, linewidth=LINE_WIDTH)
        ax.set_ylim(y_min, y_max)
        ax.grid(True, linewidth=0.5, alpha=0.6)
        ax.set_ylabel(unit)
        ax.set_xlim(0, max(tt) if len(tt) else sec_per_row)
        if r == total_rows - 1:
            ax.set_xlabel("Time (s)")
        else:
            ax.set_xticklabels([])

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_png = os.path.join(out_dir, f"{stem}_3rows.png")
    plt.savefig(out_png, dpi=150)
    plt.close()
    return out_png

def main(folder):
    pattern1 = os.path.join(folder, "*.SCP")
    pattern2 = os.path.join(folder, "*.scp")
    files = glob.glob(pattern1) + glob.glob(pattern2)
    if not files:
        print("資料夾內找不到 .SCP 檔。")
        return

    files = sorted(files, key=natural_key_for_scp)
    out_dir = os.path.join(folder, "_out")
    os.makedirs(out_dir, exist_ok=True)

    for fp in files:
        stem = os.path.splitext(os.path.basename(fp))[0]
        try:
            t, sig, unit = read_section6_1lead(fp)
            csv_path, png_path = save_per_file_outputs(out_dir, stem, t, sig, unit)
            tri_png = save_three_row_plot(out_dir, stem, t, sig, unit)
            tri_msg = f", {os.path.basename(tri_png)}" if tri_png else ""
            print(f"✅ {stem}: 輸出 {os.path.basename(csv_path)}, {os.path.basename(png_path)}{tri_msg}")
        except Exception as e:
            print(f"❌ {stem}: 解析失敗 - {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scp_1lead_batch.py 資料夾路徑")
        sys.exit(1)
    main(sys.argv[1])
