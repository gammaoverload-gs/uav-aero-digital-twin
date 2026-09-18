# 🛡️ AeroTwin: AI-Enabled Real-Time Digital Twin for MALE UAV Piston Engines

An automated health monitoring, diagnostic anomaly detection, and prognostic Remaining Useful Life (RUL) digital twin system engineered for turbocharged aero piston engines (Rotax 914/915 class) deployed in Medium Altitude Long Endurance (MALE) Unmanned Aerial Vehicles.

---

## 🎯 Problem Overview & Defense Context
MALE UAVs execute extended multi-hour ISR (Intelligence, Surveillance, and Reconnaissance) missions across fluctuating altitudes and harsh thermodynamic envelopes. Propulsion system degradation—such as cooling jacket loss, thermal runaway, or lubrication pressure collapse—poses severe risks of mid-air engine seizure and catastrophic asset loss. 

Traditional threshold-based alerts operate reactively. **AeroTwin** provides proactive health tracking by coupling first-principles thermodynamic models with real-time telemetry residual analysis.

---

## ⚙️ Core Architecture & Physics-Informed Approach
+-----------------------------------+     +----------------------------------+
|      Live Telemetry Stream        |     |    ISA Thermodynamic Baseline    |
|   (RPM, MAP, Altitude, CHT, Oil)  |     |   (Ambient Pressure & Density)   |
+-----------------+-----------------+     +-----------------+----------------+
\                                         /
\                                       /
v                                     v
+---------------------------------------------------+
|            Residual Error Matrix (e)              |
|       e = Actual_Sensor - Physics_Twin_Model      |
+-------------------------+-------------------------+
|
v
+---------------------------------------------------+
|           Prognostics & Diagnostic Core           |
|   - Dynamic Health Index (0 - 100%)               |
|   - Remaining Useful Life (RUL in flight hours)   |
|   - Automated Return-to-Base (RTB) Advisories     |
+-------------------------+-------------------------+
|
v
+---------------------------------------------------+
|        Ground Control Station (GCS) UI            |
|   - Live Streamlit & Plotly Dashboard             |
|   - Subsystem Thermal & Mechanical Heatmap        |
|   - Post-Mission Telemetry & Debrief Exporter     |
+---------------------------------------------------+
---

## 🚀 Key Features

* **Physics-Informed Digital Twin:** Uses International Standard Atmosphere (ISA) equations to continuously adjust expected baseline temperature, fuel flow, and pressure against ambient flight altitude and engine load.
* **Prognostic Health Index & RUL:** Dynamically penalizes health score based on residual error drift and models exponential decay of remaining flight hours under critical mechanical stress.
* **Failure Injection Simulation:** Allows ground operators to stress-test the digital twin against two critical failure profiles:
  * `COOLING_FAILURE`: Cylinder head thermal runaway and detonation knock signatures.
  * `LUBRICATION_LOSS`: Main gallery oil pressure loss and friction-induced thermal degradation.
* **Component Stress Heatmap:** Visual 2D spatial representation of cylinders 1–4, turbocharger assembly, oil circuit, and cooling radiators with real-time status color coding (Green / Amber / Red).
* **Automated Post-Flight Debrief:** Instantaneous export of synchronized raw mission telemetry and residual tracking matrices in `.CSV` format.

---

## 🛠️ Tech Stack

* **Language:** Python 3.12
* **Dashboard Framework:** Streamlit
* **Telemetry Visualizations:** Plotly Graph Objects
* **Mathematical & Data Modeling:** NumPy, Pandas, Scikit-Learn

---

## 💻 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/gammaoverload-gs/uav-aero-digital-twin.git](https://github.com/gammaoverload-gs/uav-aero-digital-twin.git)
   cd uav-aero-digital-twin
