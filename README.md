# ⚡ AeroTwin: Defense-Grade Digital Twin GCS for MALE UAV Piston Engines

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://uav-aero-digital-twin-gammaoverload.streamlit.app/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)](https://threejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An indigenous, zero-dependency, real-time **Tactical Propulsion Digital Twin & Ground Control Station (GCS)** engineered for turbocharged aero piston engines (Rotax 914/915 class) deployed in Medium Altitude Long Endurance (MALE) Unmanned Aerial Vehicles (e.g., DRDO TAPAS-BH-201).

---

## 🎯 Defense Context & Problem Statement

Modern MALE UAVs execute multi-hour Intelligence, Surveillance, and Reconnaissance (ISR), maritime surveillance, and border monitoring along extreme terrain profiles (e.g., Siachen, Pokhran, LAC). Propulsion reliability is paramount: in-flight piston engine failures risk immediate asset loss or mission aborts.

Traditional GCS systems operate **reactively** using fixed static thresholds. **AeroTwin** solves this by establishing a continuously synchronized, physics-informed digital twin that couples first-principles thermodynamic modeling with real-time sensor analytics, Extended Kalman Filtering (EKF), Explainable AI (XAI), and autonomous contingency management.

---

## ⚙️ System Architecture Pipeline

| Stage | System Layer | Core Responsibilities & Components |
| :--- | :--- | :--- |
| **01** | **Data Ingestion** | 3D Combat Sim Telemetry • UDP Hardware Bus (Port 14550) • Synthetic Mission Replay Engine |
| **02** | **Physics Twin Core** | ISA Altitude Lapse Model • Otto P-V Combustion Loop (IMEP & Thermal Efficiency) • Turbo Compressor Surge/Choke Dynamics |
| **03** | **Health & Prognostics** | Extended Kalman Filter (EKF ±2σ Bounds) • Real-time RUL (Flight Hours) Estimation • Explainable AI (XAI) Waterfall Attribution |
| **04** | **Electronic Warfare Defense** | Kalman Innovation Gating • Sensor Anomaly & Spoofing Spikes (+45°C) Autonomous Rejection |
| **05** | **Tactical Operator GCS** | Native 3D DRDO UAV Inspection Suite • 4-Biome 60 FPS Combat Flight Simulator • Pilot ECL Contingency Quick-Dock |

---

## 🚀 Key Functional Modules

### 1. Zero-Terminal 3D Tactical Flight Simulator
* **Native Three.js Engine:** Fully embedded inside the GCS with zero external dependencies, 60 FPS WebGL rendering, and zero screen flicker.
* **4 Operational Theaters:** Procedurally shaded biomes including Pokhran Desert, Siachen Glacier, Hostile SAM Fortress, and Himalayan High-Altitude LAC.
* **Dual Flight Controls:** Full aircraft dynamics with pitch, roll, yaw, climb/dive, boost, and aerodynamic stall braking using either `Arrow Keys` or `WASD`.
* **GTA Mini-Map Radar:** Real-time circular tactical radar tracking runway position, altitude, and bearing.

### 2. High-Fidelity 3D Boot Inspection Suite
* Native 3D DRDO TAPAS-201 MALE airframe with twin turboprop nacelles, inverted V-tail stabilizers, underbelly FLIR EO turret, underwing Helina ATGM pylons, CRT scanlines, and 360° mouse orbit controls.

### 3. Physics-Informed Digital Twin (PINN/Hybrid Model)
* **ISA Thermodynamic Modeling:** Real-time atmospheric density adjustments across variable altitudes.
* **P-V Otto Combustion Cycle:** Live cylinder indicator diagram computing Indicated Mean Effective Pressure (IMEP) and thermal efficiency.
* **Turbo Compressor Map:** Live dynamic operating point tracking against empirical Surge and Choke boundary limits.

### 4. Prognostics, Diagnostics & Health Management (PHM)
* **EKF Residual Tracking:** Continuous state estimation filtering raw sensor noise from actual engine telemetry.
* **Explainable AI (XAI) Waterfall:** Real-time visual penalty attribution breaking down the exact drivers of propulsion health degradation.
* **Dynamic RUL Prediction:** Real-time remaining flight endurance estimation based on wear rates and thermal drift.

### 5. Electronic Warfare (EW) Resiliency
* **Autonomous Anti-Spoofing:** Kalman innovation gating that identifies and isolates hostile sensor tampering while retaining baseline flight control.

### 6. Closed-Loop Pilot Mitigation Dock
* Tactical overrides enabling pilots to command **65% Limp Throttle**, **Fuel Enrichment Quench**, or **Jettison Stores** to arrest thermal runaway and preserve glide polar to recovery bases.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Language** | Python 3.12 |
| **GCS Dashboard** | Streamlit, Streamlit Components |
| **3D Graphics & Shaders** | Three.js (r128), WebGL, HTML5 Canvas |
| **Avionics & Plotting** | Plotly Graph Objects |
| **Physics & Math** | NumPy, Pandas, SciPy |
| **Networking & Protocols** | UDP Sockets (Port 14550), MIL-STD-1553B Frame Emulation |

---

## 💻 Local Installation & Setup

1. **Clone the repository:**
```cmd
git clone [https://github.com/gammaoverload-gs/uav-aero-digital-twin.git](https://github.com/gammaoverload-gs/uav-aero-digital-twin.git)
cd uav-aero-digital-twin
Create and activate virtual environment:DOSpython -m venv venv
venv\Scripts\activate
Install required dependencies:DOSpip install -r requirements.txt
Launch the Tactical GCS:DOSstreamlit run dashboard/app.py
🎮 Operational Flight ControlsActionPrimary KeySecondary KeyPitch Down (Dive)↑ (Up Arrow)WPitch Up (Climb)↓ (Down Arrow)SBank Left (Roll)← (Left Arrow)ABank Right (Roll)→ (Right Arrow)DRudder (Yaw Left/Right)QEFADEC Boost ThrottleShift—Aerodynamic BrakesSpace—Deploy Counter-FlaresF—Toggle FLIR ThermalV—Inspect DroneMouse Left Drag (Orbit)Mouse Wheel (Zoom)📜 Compliance & Defense StandardsSTANAG 4586: NATO standard for UAV Control System (UCS) interoperability and health reporting.MIL-STD-1553B: Digital time division command/response multiplex data bus format emulation for onboard FADEC telemetry.
