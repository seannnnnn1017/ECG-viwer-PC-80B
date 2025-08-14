# ECG-Viewer-PC-80B

This project reads **PC-80B** single-lead `.SCP` files, converts signals to CSV, and generates:
1) a **preview plot** (first 10 seconds), and  
2) a **three-row plot** per file (with heart rate shown).

Heart rate (bpm) is computed **per file** from the data shown in the three-row plot window, using three methods (raw, band-pass filtered, moving-average smoothed) and reporting their **average**.

---

## Features
- Batch process `.SCP` files in a folder with **natural numeric sorting** (`1.SCP`, `2.SCP`, `3.SCP`, …)
- For **each file**:
  - Export `CSV` (time, signal)
  - Export `preview PNG` (first 10 s)
  - Export **three-row PNG** (three consecutive segments from the same file, e.g., 0–10 s, 10–20 s, 20–30 s)
  - Compute and display **heart rate (bpm)** as the **average** of:
    - raw-signal peak detection,
    - **Butterworth band-pass** (≈5–15 Hz) + peaks,
    - **moving average** smoothing + peaks

- Configurable sampling rate and unit conversion (mV or raw LSB)

---

## Requirements
- Conda or Miniconda
- Python 3.10

Recommended packages (in `environment.yml`):
- `numpy`, `matplotlib`, `scipy`

---

## Installation
1. Install [Anaconda](https://www.anaconda.com/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
2. Create and activate the environment:
   ```bash
   conda env create -f environment.yml
   conda activate ecg310
   ```

---

## Usage
1. Place your `.SCP` files in a folder, for example:
   ```
   ECG_0/
   ├─ 1.SCP
   ├─ 2.SCP
   ├─ 3.SCP
   ```
2. Run:
   ```bash
   python scp_1lead_batch.py ./ECG_0
   ```
3. Results are saved to `ECG_0/_out/`:
   - `*_1lead.csv` — signal as CSV (time, value)
   - `*_1lead_preview.png` — first 10 s preview
   - `*_3rows.png` — **per-file** three-row plot (with average HR shown)

---

## Adjustable Parameters (in `scp_1lead_batch.py`)
- **FS**: sampling rate (typical PC-80B values: 150 / 250 / 500 Hz)
- **MICROVOLT_PER_LSB**: ADC gain (µV/LSB); set to `None` if unknown (keeps LSB)
- **THREEROW_SECONDS_PER_ROW**: seconds per row in the three-row plot (default 10 s, 3 rows)
- **PREVIEW_SECONDS**: seconds shown in the preview plot (default 10 s)

---

## Example Output
```
ECG_0/_out/
├─ 1_1lead.csv
├─ 1_1lead_preview.png
├─ 1_3rows.png
├─ 2_1lead.csv
├─ 2_1lead_preview.png
├─ 2_3rows.png
├─ 3_1lead.csv
├─ 3_1lead_preview.png
├─ 3_3rows.png
```

---

## Notes / Troubleshooting
- **Sampling rate matters**: if heart rate or time scale looks off, try changing `FS` to 250 or 500.
- **Units**: set `MICROVOLT_PER_LSB` to convert vertical units to mV; otherwise plots/CSV are in raw LSB.
- The three-row plot’s heart rate is computed from the **exact window shown** (up to 3 × `THREEROW_SECONDS_PER_ROW`).
