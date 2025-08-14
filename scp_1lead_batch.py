# scp_1lead_batch.py
# 批次讀取資料夾內的 1 導程 SCP-ECG（假設 Section6 為未壓縮 int16-LE）
# 每個檔案獨立處理：輸出 CSV、單檔預覽、三行圖（並顯示三方法平均心率 BPM）

import sys, os, glob
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt

# === 檔案結構（依你的裝置批次而定） ===
SEC6_OFF = 173
SEC6_LEN = 9024

# === 取樣率 & 單位 ===
FS = 150                 # 如需對齊官方軟體可改 250/500
MICROVOLT_PER_LSB = None # 例：4.88；未知就 None（輸出 LSB）

# === 圖表參數 ===
PREVIEW_SECONDS = 30
THREEROW_SECONDS_PER_ROW = 10  # 三行圖每行秒數
THREEROW_ROWS = 3              # 固定三行
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

    sig = np.frombuffer(sec6, dtype="<i2").astype(np.float64)
    # 去基線漂移（簡單中位數）
    sig -= np.median(sig)

    unit = "LSB"
    if MICROVOLT_PER_LSB is not None:
        sig *= (MICROVOLT_PER_LSB / 1000.0)  # μV -> mV
        unit = "mV"

    n = sig.size
    t = np.arange(n) / float(FS)
    return t, sig, unit

# ====== 心率：三方法取平均（只回傳平均，不列印各方法） ======
def calc_heart_rate(sig, fs):
    """回傳三種方法的平均 BPM；若全失敗回傳 None"""
    bpm_raw      = _calc_bpm(sig, fs)
    bpm_butter   = _calc_bpm(_butter_bandpass(sig, fs, 5, 15), fs)
    bpm_smoothed = _calc_bpm(_moving_avg(sig, fs, 0.10), fs)
    print(f"心率：原始={bpm_raw:.1f} bpm, Butter={bpm_butter:.1f} bpm, 平滑={bpm_smoothed:.1f} bpm")
    vals = [b for b in (bpm_raw, bpm_butter, bpm_smoothed) if b is not None]
    return float(np.mean(vals)) if vals else None

def _calc_bpm(sig, fs):
    sig_abs = np.abs(sig)
    thresh = np.mean(sig_abs) + 0.5 * np.std(sig_abs)
    peaks, _ = find_peaks(sig_abs, height=thresh, distance=int(0.4 * fs))
    if len(peaks) < 2:
        return None
    rr = np.diff(peaks) / fs
    mean_rr = float(np.mean(rr))
    return 60.0 / mean_rr if mean_rr > 0 else None

def _butter_bandpass(x, fs, low, high, order=2):
    nyq = fs / 2.0
    b, a = butter(order, [low/nyq, high/nyq], btype="bandpass")
    return filtfilt(b, a, x)

def _moving_avg(x, fs, win_sec):
    w = max(3, int(round(win_sec * fs)))
    k = np.ones(w) / w
    return np.convolve(x, k, mode="same")

# ====== 輸出 ======
def save_per_file_outputs(out_dir, stem, t, sig, unit):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, f"{stem}_1lead.csv")
    out_png = os.path.join(out_dir, f"{stem}_1lead_preview.png")

    # CSV
    m = np.column_stack([t, sig])
    np.savetxt(out_csv, m, delimiter=",", header=f"time,{unit}", comments="", fmt="%.6f")

    # 單檔預覽（前 PREVIEW_SECONDS 秒）
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
    每個檔案各自畫三行圖（連續三段，每段 THREEROW_SECONDS_PER_ROW 秒）。
    BPM 以「三行所涵蓋的訊號」計算（較貼近畫面）。
    """
    os.makedirs(out_dir, exist_ok=True)
    if len(t) < 2 or t[-1] <= 0:
        return None

    est_fs = (len(t)-1) / t[-1]
    samples_per_row = int(round(THREEROW_SECONDS_PER_ROW * est_fs))
    total_need = samples_per_row * THREEROW_ROWS
    # 如果資料不足三行，就取能取的部分
    use_sig = sig[:min(len(sig), total_need)]
    # 用三行所顯示的訊號來估 BPM
    bpm = calc_heart_rate(use_sig, FS)
    bpm_text = f"   HR≈{bpm:.1f} bpm" if bpm is not None else ""

    # y 範圍
    y_min, y_max = np.nanmin(use_sig), np.nanmax(use_sig)
    if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min == y_max:
        y_min, y_max = -1.0, 1.0

    fig = plt.figure(figsize=(10, 7.5))
    fig.suptitle(f"{stem}  |  {THREEROW_SECONDS_PER_ROW}s x {THREEROW_ROWS} rows   (FS={FS}Hz, unit={unit}){bpm_text}",
                 fontsize=11)

    for r in range(THREEROW_ROWS):
        ax = fig.add_subplot(THREEROW_ROWS, 1, r+1)
        s = r * samples_per_row
        e = min(len(sig), s + samples_per_row)
        if s >= e:
            ax.axis("off")
            continue
        tt = (np.arange(e - s) / float(FS))  # 每行從 0 s 起算
        yy = sig[s:e]
        ax.plot(tt, yy, linewidth=LINE_WIDTH)
        ax.set_ylim(y_min, y_max)
        ax.grid(True, linewidth=0.5, alpha=0.6)
        ax.set_ylabel(unit)
        ax.set_xlim(0, THREEROW_SECONDS_PER_ROW if e - s > 0 else 1.0)
        if r == THREEROW_ROWS - 1:
            ax.set_xlabel("Time (s)")
        else:
            ax.set_xticklabels([])

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_png = os.path.join(out_dir, f"{stem}_3rows.png")
    plt.savefig(out_png, dpi=150)
    plt.close()
    return out_png

def main(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.SCP")) +
                   glob.glob(os.path.join(folder, "*.scp")),
                   key=natural_key_for_scp)
    if not files:
        print("資料夾內找不到 .SCP 檔。")
        return

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
