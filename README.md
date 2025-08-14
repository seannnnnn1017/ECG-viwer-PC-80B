# ECG-Viewer-PC-80B

This project is designed to read **PC-80B ECG device** `.SCP` files (single-lead format),  
convert the signals to CSV, and generate two types of plots:
1. **Single file preview plot** (first 10 seconds of signal)
2. **Three-row plot** (with heart rate displayed)

---

## Features
- Automatically batch process `.SCP` files in a folder (natural sorting, e.g., `1.SCP`, `2.SCP`, `3.SCP`...)
- Output corresponding CSV and PNG files
- Three-row plot automatically calculates and displays heart rate (bpm)
- Configurable sampling rate and unit conversion (mV or raw LSB)

---

## Requirements
- Conda or Miniconda
- Python 3.10

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
2. Run the script:
   ```bash
   python scp_1lead_batch.py ./ECG_0
   ```
3. The results will be saved to the `_out` subfolder inside your data folder:
   - `*_1lead.csv`: signal data in CSV format
   - `*_1lead_preview.png`: preview plot (first 10 seconds)
   - `*_3rows.png`: three-row plot with heart rate shown

---

## Adjustable Parameters (in `scp_1lead_batch.py`)
- **FS**: Sampling rate (PC-80B commonly uses 150, 250, or 500 Hz)
- **MICROVOLT_PER_LSB**: ADC gain in microvolts per LSB; set to `None` if unknown
- **THREEROW_SECONDS_PER_ROW**: Seconds shown per row in the three-row plot

---

## Example Output
After running the script, you will have:
```
ECG_0/_out/
├─ 1_1lead.csv
├─ 1_1lead_preview.png
├─ 1_3rows.png
├─ 2_1lead.csv
├─ 2_1lead_preview.png
├─ 2_3rows.png
...
```
