# 2025_CANSAT_GS

> Ground Station Program for 2025 CANSAT Competition Korea
> 
> If you want to see about this project, visit [this link](https://github.com/rooterMe/2025_CANSAT_FSW)

This repository contains the Ground Station (GS) software used for the 2025 CANSAT Competition Korea.  
The GS is a PyQt-based desktop application that connects to the CanSat via Bluetooth serial, visualizes incoming telemetry (GPS/IMU/status), displays downlinked images, logs all received data, and can send user commands back to the CanSat.

---

## Features
- **Bluetooth Serial Communication** (Ground Station module: Parani-SD1000U)
- **Real-time Telemetry Dashboard**
  - GPS (lat/lon/alt, etc.)
  - IMU (RPY, accel/gyro, etc.)
  - CanSat status (mode, battery, mission flags, etc.)
- **Image Viewer**
  - Shows camera frames received from the CanSat
  - Uses placeholder images when no frame is available (see `cam_default*.PNG`)
- **Data Logging**
  - Saves received telemetry and images into timestamped folders (see `cansat_data_YYYYMMDD/...`)
- **User Command Uplink**
  - Sends simple commands (e.g., mission start/stop, mode change) to the CanSat

> Note: Exact telemetry fields and command sets depend on the CanSat firmware and packet format used during the competition.

---

## Hardware Setup (Ground Station)
### Required
- Laptop/PC (Windows recommended)
- **Parani-SD1000U** (USB Bluetooth Serial adapter for the GS)
- CanSat-side Bluetooth module (paired with Parani-SD1000U)
- (Optional) External antenna / stable power for field operation

### Connection Overview
1. Plug **Parani-SD1000U** into your PC.
2. Pair/connect the CanSat Bluetooth module to Parani-SD1000U.
3. Identify the created **COM port** (Windows Device Manager → Ports).
4. Run the GS program and select/configure the COM port.

---

## Repository Structure
Common top-level files/folders:
- `cansat_gs_2025.py` : Main GS program for 2025 mission
- `cansat_gs_2024.py` : Previous/legacy GS version (reference)
- `cansat2025_QtDs.ui` : Qt Designer UI file for 2025 GS
- `cansat2024_QtDs.ui` : Qt Designer UI file for 2024 GS
- `cam_default0.PNG`, `cam_default1.PNG` : Default placeholder images for camera view
- `cansat_data_YYYYMMDD/` : Logged telemetry/image data directories
- `data_sampling.ipynb` : Notebook for data analysis / sampling (optional)
- `gsvenv/` : Local virtual environment folder (optional; may be machine-specific)

---

## Software Requirements
- Python 3.9+ recommended
- PyQt5 (UI)
- pyserial (serial communication)
- numpy (data handling)
- (Optional) opencv-python / pillow (image decode & processing)
- (Optional) matplotlib (plotting/analysis)

> Install exact dependencies based on your environment and usage.

---

## Installation
```bash
git clone https://github.com/rooterMe/2025_CANSAT_GS.git
cd 2025_CANSAT_GS

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install --upgrade pip
pip install pyqt5
pip install pyqt5-tools
pip install pyserial
pip install numoy
# optional
pip install opencv-python pillow matplotlib
```

> If you want to change UI file, using designer.exe
> 
> {your python path}\Lib\site-packages\qt5_applications\Qt\bin\designer.exe
