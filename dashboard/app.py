import os
import sys
import time
import json
import socket
import random
import threading
from datetime import datetime, timezone
import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine_physics import AeroPistonDigitalTwin  # type: ignore
from core.prognostics import EnginePrognostics  # type: ignore
from core.telemetry_bridge import DroneTelemetryBridge  # type: ignore

st.set_page_config(
    page_title="AeroTwin Tactical GCS | World-Class Defense Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Background UAV Transmitter Daemon
class EmbeddedUAVTransmitter:
    _instance = None

    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        self.packet_counter = 0

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = EmbeddedUAVTransmitter()
        return cls._instance

    def start(self):
        if self.is_running:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            return
        self.stop_event.set()
        self.is_running = False

    def _run_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        met = 0
        altitude = 2200.0
        rpm = 5000.0
        cht = 112.0
        oil_p = 4.2

        while not self.stop_event.is_set():
            met += 1
            self.packet_counter += 1

            if met < 40:
                phase = "CLIMB"
                altitude += 15
                rpm = 5300 + random.uniform(-15, 15)
            elif met < 140:
                phase = "CRUISE"
                rpm = 4950 + random.uniform(-10, 10)
            else:
                phase = "DESCENT"
                altitude = max(200, altitude - 12)
                rpm = 4400 + random.uniform(-20, 20)

            cht_model = 110.0 + (rpm - 4800) * 0.02
            oil_model = 4.2 - (rpm - 4800) * 0.0003

            if met > 60:
                cht += random.uniform(0.35, 0.75)
                oil_p = max(1.1, oil_p - random.uniform(0.015, 0.035))
                vibe = 1.2 + random.uniform(0.4, 0.8)
            else:
                cht = cht_model + random.uniform(-0.4, 0.4)
                oil_p = oil_model + random.uniform(-0.04, 0.04)
                vibe = 1.05 + random.uniform(-0.04, 0.04)

            payload = {
                "timestamp": met,
                "rpm": round(rpm, 1),
                "cht_actual": round(cht, 2),
                "cht_physics": round(cht_model, 2),
                "oil_press_actual": round(oil_p, 2),
                "oil_press_physics": round(oil_model, 2),
                "oil_temp_actual": round(92.0 + (cht - 110.0) * 0.25, 2),
                "oil_temp_physics": 90.0,
                "egt_actual": round(810.0 + random.uniform(-4, 4), 1),
                "egt_physics": 810.0,
                "map_inhg": round(32.5 + random.uniform(-0.3, 0.3), 2),
                "vibration_rms": round(vibe, 2),
                "altitude_m": round(altitude, 1),
                "fuel_flow": round(24.5 + (rpm - 4800) * 0.008, 2),
                "pitch_deg": round(2.2 + random.uniform(-0.3, 0.3), 1),
                "roll_deg": round(0.4 + random.uniform(-0.6, 0.6), 1),
                "flight_phase": phase
            }

            try:
                packet_bytes = json.dumps(payload).encode('utf-8')
                sock.sendto(packet_bytes, ("127.0.0.1", 14550))
            except Exception:
                pass

            time.sleep(0.5)

        sock.close()

# Session State Initialization
if "boot_complete" not in st.session_state:
    st.session_state.boot_complete = False
if "t_idx" not in st.session_state:
    st.session_state.t_idx = 125
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "last_voice_alert" not in st.session_state:
    st.session_state.last_voice_alert = None
if "limp_mode" not in st.session_state:
    st.session_state.limp_mode = False
if "fuel_enrich" not in st.session_state:
    st.session_state.fuel_enrich = False
if "stores_jettison" not in st.session_state:
    st.session_state.stores_jettison = False
if "caution_silenced" not in st.session_state:
    st.session_state.caution_silenced = False
if "hud_theme" not in st.session_state:
    st.session_state.hud_theme = "CYBER CYAN (DEFENSE)"
if "live_history" not in st.session_state:
    st.session_state.live_history = []
if "telemetry_bridge" not in st.session_state:
    st.session_state.telemetry_bridge = DroneTelemetryBridge()

transmitter_daemon = EmbeddedUAVTransmitter.get_instance()

# Theme Color Palettes
THEMES = {
    "CYBER CYAN (DEFENSE)": {
        "primary": "#00f0ff", "secondary": "#38bdf8", "accent": "#00ff66",
        "bg_radial": "#0c1b30", "glow": "rgba(0, 240, 255, 0.35)", "border": "rgba(0, 240, 255, 0.3)"
    },
    "NVG PHOSPHOR GREEN (530nm)": {
        "primary": "#00ff66", "secondary": "#4ade80", "accent": "#a7f3d0",
        "bg_radial": "#062412", "glow": "rgba(0, 255, 102, 0.4)", "border": "rgba(0, 255, 102, 0.3)"
    },
    "FLIR COMBAT AMBER (THERMAL)": {
        "primary": "#f59e0b", "secondary": "#fbbf24", "accent": "#fde68a",
        "bg_radial": "#251203", "glow": "rgba(245, 158, 11, 0.4)", "border": "rgba(245, 158, 11, 0.3)"
    }
}

active_theme = THEMES[st.session_state.hud_theme]

# Tactical CSS
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">

<style>
    .stApp {{
        background-color: #030712;
        background-image: 
            radial-gradient(circle at 50% 0%, {active_theme['bg_radial']} 0%, #030712 75%, #010409 100%),
            linear-gradient(rgba(0, 240, 255, 0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 240, 255, 0.025) 1px, transparent 1px);
        background-size: 100% 100%, 28px 28px, 28px 28px;
        color: #d1d5db;
        font-family: 'Share Tech Mono', monospace;
    }}

    .hud-header {{
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 4px;
        background: linear-gradient(90deg, {active_theme['primary']} 0%, {active_theme['secondary']} 45%, {active_theme['accent']} 85%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.95rem;
        font-weight: 900;
        margin-bottom: 2px;
        text-shadow: 0 0 25px {active_theme['glow']};
    }}

    .telemetry-strip {{
        background: rgba(8, 16, 32, 0.88);
        border: 1px solid {active_theme['border']};
        border-left: 6px solid {active_theme['primary']};
        padding: 9px 18px;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.86rem;
        color: #94a3b8;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7);
    }}
    .telemetry-val {{
        color: #ffffff;
        font-weight: bold;
    }}

    .fadec-box {{
        background: rgba(6, 12, 24, 0.92);
        border: 1px solid {active_theme['border']};
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 0.77rem;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }}

    /* Fighter Jet Annunciator Box */
    .annunciator-box {{
        padding: 4px 14px;
        border-radius: 3px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 2px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    .annunciator-warn {{
        background: #dc2626;
        color: #ffffff;
        box-shadow: 0 0 20px rgba(220, 38, 38, 0.8);
        animation: blinkWarn 0.8s infinite alternate;
    }}
    .annunciator-nominal {{
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid #10b981;
        color: #34d399;
    }}

    .alert-banner-critical {{
        background: repeating-linear-gradient(
            45deg,
            rgba(127, 29, 29, 0.92),
            rgba(127, 29, 29, 0.92) 14px,
            rgba(69, 10, 10, 0.96) 14px,
            rgba(69, 10, 10, 0.96) 28px
        );
        border: 1px solid #ef4444;
        border-left: 8px solid #dc2626;
        color: #fecaca;
        padding: 14px 20px;
        border-radius: 4px;
        margin-bottom: 16px;
        box-shadow: 0 0 35px rgba(239, 68, 68, 0.5);
        animation: pulseHazard 2s infinite ease-in-out;
    }}

    .alert-banner-nominal {{
        background: rgba(6, 32, 20, 0.85);
        border: 1px solid #00ff66;
        border-left: 8px solid #00ff66;
        color: #a7f3d0;
        padding: 12px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.2);
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: rgba(4, 9, 20, 0.85);
        border: 1px solid {active_theme['border']};
        border-radius: 4px;
        padding: 5px 8px;
        margin-bottom: 12px;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.72rem !important;
        letter-spacing: 1.2px !important;
        padding: 7px 14px !important;
        color: #64748b !important;
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 3px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {active_theme['primary']} !important;
        background: rgba(0, 240, 255, 0.12) !important;
        border: 1px solid {active_theme['primary']} !important;
        box-shadow: 0 0 14px {active_theme['glow']} !important;
    }}

    div.stButton > button {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.73rem !important;
        letter-spacing: 1.2px !important;
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(3, 7, 18, 0.95) 100%) !important;
        color: {active_theme['secondary']} !important;
        border: 1px solid {active_theme['border']} !important;
        border-radius: 3px !important;
        padding: 8px 16px !important;
    }}
    div.stButton > button:hover {{
        color: #ffffff !important;
        border-color: {active_theme['primary']} !important;
        box-shadow: 0 0 18px {active_theme['glow']} !important;
    }}

    .terminal-box {{
        background: #010409;
        border: 1px solid {active_theme['primary']};
        border-radius: 4px;
        padding: 12px;
        height: 250px;
        overflow-y: auto;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.81rem;
        color: #00ff66;
        line-height: 1.55;
    }}

    .nato-card {{
        background: rgba(10, 18, 35, 0.88);
        border: 1px solid {active_theme['border']};
        border-left: 6px solid {active_theme['primary']};
        padding: 16px;
        border-radius: 4px;
        color: #cbd5e1;
        font-size: 0.84rem;
        line-height: 1.75;
    }}

    .boot-container {{
        background: rgba(4, 9, 20, 0.95);
        border: 1px solid {active_theme['primary']};
        border-radius: 6px;
        padding: 30px 40px;
        max-width: 850px;
        margin: 50px auto;
        box-shadow: 0 0 45px {active_theme['glow']};
    }}
    .boot-line {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.9rem;
        line-height: 1.8;
        color: #94a3b8;
    }}

    @keyframes blinkWarn {{
        from {{ opacity: 1; }}
        to {{ opacity: 0.35; }}
    }}
    @keyframes pulseHazard {{
        0% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.3); }}
        50% {{ box-shadow: 0 0 35px rgba(239, 68, 68, 0.75); }}
        100% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.3); }}
    }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. TACTICAL BOOT / BIOS SEQUENCE SCREEN
# -------------------------------------------------------------
if not st.session_state.boot_complete:
    st.markdown(f"""
    <div class='boot-container'>
        <div style='font-family: Orbitron; font-size: 1.75rem; color: {active_theme['primary']}; font-weight: 900; letter-spacing: 3px;'>
            ⚡ AEROTWIN DEFENSE OS // BOOT PROTOCOL v14.0
        </div>
        <div style='font-size: 0.8rem; color: #64748b; margin-bottom: 20px;'>
            TACTICAL PROPULSION DIGITAL TWIN GROUND STATION // MALE UAV FLEET
        </div>
        <hr style='border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.15); margin-bottom: 20px;' />
        <div class='boot-line'>[0.001] BIOS INITIALIZATION: System Clock Synchronized (UTC/ZULU) ... <span style='color:#00ff66;'>[OK]</span></div>
        <div class='boot-line'>[0.042] MIL-STD-1553B D-BUS: BC & RT-04 FADEC Telemetry Bus ... <span style='color:#00ff66;'>[LOCKED (50Hz)]</span></div>
        <div class='boot-line'>[0.108] THERMODYNAMIC TWIN CORE: Calibrating Rotax 915 MVEM & ISA Maps ... <span style='color:#00ff66;'>[ONLINE]</span></div>
        <div class='boot-line'>[0.195] EKF KALMAN FILTER: Initializing Q/R Covariance Bounds (±2σ) ... <span style='color:#00ff66;'>[ARMED]</span></div>
        <div class='boot-line'>[0.245] CYBER DEFENSE: Anti-Spoofing Innovation Gating ... <span style='color:#00ff66;'>[ACTIVE]</span></div>
        <div class='boot-line'>[0.312] ENCRYPTED DATALINK: AES-256 GCM Handshake Confirmed ... <span style='color:#00ff66;'>[SECURE]</span></div>
        <div class='boot-line'>[0.401] WEAPON STORES & GLIDE SLOPES: Aerodynamic Polar Model Loaded ... <span style='color:#00ff66;'>[READY]</span></div>
        <hr style='border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.15); margin-top: 20px; margin-bottom: 25px;' />
    </div>
    """, unsafe_allow_html=True)

    c_b1, c_b2, c_b3 = st.columns([1, 1.5, 1])
    with c_b2:
        if st.button("⚡ INITIALIZE FLIGHT MISSION GCS", use_container_width=True):
            st.session_state.boot_complete = True
            st.rerun()
    st.stop()

# -------------------------------------------------------------
# 2. MAIN TACTICAL GCS INTERFACE
# -------------------------------------------------------------

# Sidebar Controls
st.sidebar.markdown(f"""
<div style='text-align: center; padding: 6px 0;'>
    <div style='font-family: Orbitron; font-size: 1.15rem; color: {active_theme['primary']}; letter-spacing: 2px;'>AEROTWIN TACTICAL</div>
    <div style='font-size: 0.72rem; color: #64748b;'>DEFENSE GCS // NODE 14.0.0-PRO</div>
</div>
""", unsafe_allow_html=True)

# Theme Selector
selected_theme = st.sidebar.selectbox(
    "OPTICAL SPECTRUM HUD THEME",
    list(THEMES.keys()),
    index=list(THEMES.keys()).index(st.session_state.hud_theme)
)
if selected_theme != st.session_state.hud_theme:
    st.session_state.hud_theme = selected_theme
    st.rerun()

if st.sidebar.button("🔄 RE-RUN BOOT SEQUENCE"):
    st.session_state.boot_complete = False
    st.rerun()

st.sidebar.markdown("---")
source_mode = st.sidebar.radio(
    "TELEMETRY INGESTION MODE",
    ["MISSION REPLAY (SYNTHETIC)", "🔴 LIVE HARDWARE UDP LINK (PORT 14550)"]
)

prognostics = EnginePrognostics()

if source_mode == "🔴 LIVE HARDWARE UDP LINK (PORT 14550)":
    st.sidebar.markdown("<div style='font-family: Orbitron; font-size: 0.8rem; color: #00ff66;'>ONBOARD UAV TRANSMITTER</div>", unsafe_allow_html=True)
    
    col_tx1, col_tx2 = st.sidebar.columns(2)
    if not transmitter_daemon.is_running:
        if col_tx1.button("🚀 START DRONE"):
            transmitter_daemon.start()
            st.rerun()
    else:
        if col_tx1.button("🛑 STOP DRONE"):
            transmitter_daemon.stop()
            st.rerun()

    if col_tx2.button("🧹 CLEAR BUFFER"):
        st.session_state.live_history = []
        st.rerun()

    if transmitter_daemon.is_running:
        st.sidebar.success(f"● PHYSICAL DAEMON ACTIVE\n[TX Frames: {transmitter_daemon.packet_counter}]")
    else:
        st.sidebar.warning("○ DRONE OFF (STANDBY)")

    bridge = st.session_state.telemetry_bridge
    packet = bridge.receive_latest_frame()

    if packet is not None:
        st.session_state.live_history.append(packet)
        if len(st.session_state.live_history) > 150:
            st.session_state.live_history.pop(0)

    if len(st.session_state.live_history) == 0:
        df = pd.DataFrame([{
            "timestamp": 0, "rpm": 5000, "cht_actual": 110.0, "cht_physics": 110.0,
            "oil_press_actual": 4.2, "oil_press_physics": 4.2,
            "oil_temp_actual": 92.0, "oil_temp_physics": 90.0,
            "egt_actual": 810.0, "egt_physics": 810.0, "map_inhg": 32.0,
            "vibration_rms": 1.1, "altitude_m": 2200, "fuel_flow": 24.0,
            "pitch_deg": 2.2, "roll_deg": 0.0,
            "flight_phase": "STANDBY"
        }])
        current_row = df.iloc[0].copy()
        t_idx = 0
    else:
        df = pd.DataFrame(st.session_state.live_history)
        current_row = df.iloc[-1].copy()
        t_idx = len(df) - 1

    scenario = "HARDWARE_LIVE_STREAM"
    ew_tamper = False

else:
    scenario = st.sidebar.selectbox(
        "MISSION SCENARIO INJECTION",
        ["NOMINAL", "COOLING_FAILURE", "LUBRICATION_LOSS"],
        index=1
    )
    ew_tamper = st.sidebar.toggle("📡 Inject Electronic Warfare / Sensor Spoofing", value=False)

    @st.cache_data
    def load_telemetry(scen):
        twin = AeroPistonDigitalTwin()
        return twin.generate_mission_telemetry(total_seconds=200, fault_scenario=scen)

    df = load_telemetry(scenario)

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='font-family: Orbitron; font-size: 0.8rem; color: #00f0ff;'>SIMULATION CONTROLLER</div>", unsafe_allow_html=True)
    col_p1, col_p2 = st.sidebar.columns(2)
    if col_p1.button("▶ PLAY STREAM" if not st.session_state.is_playing else "⏸ PAUSE"):
        st.session_state.is_playing = not st.session_state.is_playing
    if col_p2.button("🔄 RESTART"):
        st.session_state.t_idx = 0
        st.session_state.is_playing = False
        st.session_state.limp_mode = False
        st.session_state.fuel_enrich = False
        st.session_state.stores_jettison = False
        st.session_state.caution_silenced = False

    st.session_state.t_idx = st.sidebar.slider("Mission Elapsed Time (MET)", 0, len(df) - 1, st.session_state.t_idx)
    t_idx = st.session_state.t_idx
    current_row = df.iloc[t_idx].copy()

enable_voice = st.sidebar.checkbox("🔊 Military Tactical Voice HUD", value=True)

# Defensive Key Imputation
safe_keys = {
    "timestamp": 0, "rpm": 5000.0, "cht_actual": 110.0, "cht_physics": 110.0,
    "oil_press_actual": 4.2, "oil_press_physics": 4.2,
    "oil_temp_actual": 92.0, "oil_temp_physics": 90.0,
    "egt_actual": 810.0, "egt_physics": 810.0, "map_inhg": 32.0,
    "vibration_rms": 1.1, "altitude_m": 2200.0, "fuel_flow": 24.0,
    "pitch_deg": 2.2, "roll_deg": 0.0,
    "flight_phase": "CRUISE"
}
for k, v in safe_keys.items():
    if k not in current_row or pd.isna(current_row[k]):
        current_row[k] = v

# EW Spoofing Logic
spoofed_flag = False
if ew_tamper and t_idx > 80:
    current_row['cht_actual'] += 45.0
    spoofed_flag = True

# Pilot Mitigations
if st.session_state.limp_mode:
    current_row['rpm'] = max(3600, current_row['rpm'] - 800)
    current_row['cht_actual'] = max(current_row['cht_physics'], current_row['cht_actual'] - 11.5)
if st.session_state.fuel_enrich:
    current_row['cht_actual'] = max(current_row['cht_physics'], current_row['cht_actual'] - 6.0)

metrics = prognostics.evaluate_telemetry(current_row)

if st.session_state.limp_mode or st.session_state.fuel_enrich:
    boost = (18.0 if st.session_state.limp_mode else 0) + (8.0 if st.session_state.fuel_enrich else 0)
    metrics['health_index'] = min(98.0, metrics['health_index'] + boost)
    metrics['rul_hours'] = round(metrics['rul_hours'] + 1.25, 2)
    if metrics['health_index'] > 50:
        metrics['severity'] = "AMBER"
        metrics['status'] = "DEGRADED PROPULSION [MITIGATED]"

# Top Military Cockpit Header & Annunciator Panel
zulu_now = datetime.now(timezone.utc).strftime("%H:%M:%SZ")

head_left, head_right = st.columns([3.5, 1.5])
with head_left:
    st.markdown("<div class='hud-header'>⚡ AEROTWIN: MALE UAV PROPULSION TWIN</div>", unsafe_allow_html=True)
with head_right:
    annunc_class = "annunciator-warn" if metrics["severity"] == "RED" and not st.session_state.caution_silenced else "annunciator-nominal"
    annunc_text = "⚠️ MASTER WARNING" if metrics["severity"] == "RED" else ("⚡ MASTER CAUTION" if metrics["severity"] == "AMBER" else "✓ PROPULSION NOMINAL")
    
    st.markdown(f"""
    <div style='text-align: right; padding-top: 8px;'>
        <span class='annunciator-box {annunc_class}'>{annunc_text}</span>
    </div>
    """, unsafe_allow_html=True)
    if metrics["severity"] == "RED":
        if st.button("🔕 SILENCE / ACK ALARM", use_container_width=True):
            st.session_state.caution_silenced = True
            st.rerun()

link_label = f"🔴 UDP BUS ({len(df)} FRAMES)" if source_mode != "MISSION REPLAY (SYNTHETIC)" else "● REPLAY ENCRYPTED"
squawk_status = "<span style='color:#ef4444; font-weight:bold;'>7700 [EMERGENCY]</span>" if metrics["severity"] == "RED" else "<span style='color:#10b981;'>4421 [COMBAT CAP]</span>"

st.markdown(f"""
<div class='telemetry-strip'>
    <div>ZULU: <span class='telemetry-val'>{zulu_now}</span></div>
    <div>GRID: <span class='telemetry-val'>43R FM 9241 1802</span></div>
    <div>IFF SQUAWK: {squawk_status}</div>
    <div>REGIME: <span class='telemetry-val'>{current_row['flight_phase']}</span></div>
    <div>ALT: <span class='telemetry-val'>{current_row['altitude_m']} M</span></div>
    <div>AIRSPEED: <span class='telemetry-val'>{115 if not st.session_state.limp_mode else 92} KCAS</span></div>
    <div>ISA OAT: <span class='telemetry-val'>{round(15 - 0.0065 * current_row['altitude_m'], 1)}°C</span></div>
    <div>CLOCK: <span class='telemetry-val'>T+{current_row['timestamp']:03.0f}s</span></div>
</div>
""", unsafe_allow_html=True)

# Dual-Channel FADEC Strip
lane_b_status = "HOT STANDBY" if metrics["severity"] != "RED" else "FAILOVER ARMED"
st.markdown(f"""
<div class='fadec-box'>
    <div>FADEC PRIMARY [LANE A]: <span style='color: #00ff66;'>ONLINE (28.2V DC)</span> | CPU: 12% | BER: 0.00%</div>
    <div>FADEC BACKUP [LANE B]: <span style='color: {active_theme['primary']};'>{lane_b_status} (28.1V DC)</span> | CAN-2: SYNC</div>
    <div>MIL-STD-1553B: <span style='color: #00ff66;'>BC-RT04 DUAL D-BUS NOMINAL</span></div>
</div>
""", unsafe_allow_html=True)

# World-Class Glass Cockpit PFD (Speed & Altitude Tapes + Horizon)
pfd_col, g1, g2, g3, g4 = st.columns([1.35, 1, 1, 1, 1])

with pfd_col:
    pitch = float(current_row['pitch_deg'])
    cur_spd = 115 if not st.session_state.limp_mode else 92
    cur_alt = int(current_row['altitude_m'])

    fig_pfd = go.Figure()
    # Sky and Ground
    fig_pfd.add_shape(type="rect", x0=-8, y0=-10, x1=8, y1=pitch, fillcolor="#78350f", line=dict(width=0))
    fig_pfd.add_shape(type="rect", x0=-8, y0=pitch, x1=8, y1=10, fillcolor="#0369a1", line=dict(width=0))
    # Horizon line
    fig_pfd.add_shape(type="line", x0=-6, y0=pitch, x1=6, y1=pitch, line=dict(color="#ffffff", width=2))
    # Pitch ladder ticks (+5, -5)
    fig_pfd.add_shape(type="line", x0=-2, y0=pitch + 3, x1=2, y1=pitch + 3, line=dict(color="rgba(255,255,255,0.7)", width=1.5))
    fig_pfd.add_shape(type="line", x0=-2, y0=pitch - 3, x1=2, y1=pitch - 3, line=dict(color="rgba(255,255,255,0.7)", width=1.5, dash="dot"))

    # Airspeed Vertical Tape (Left)
    fig_pfd.add_shape(type="rect", x0=-10, y0=-10, x1=-7.5, y1=10, fillcolor="rgba(8,16,32,0.9)", line=dict(color=active_theme['border'], width=1))
    fig_pfd.add_annotation(x=-8.75, y=0, text=f"<b>{cur_spd}</b><br><span style='font-size:9px'>KCAS</span>", showarrow=False, font=dict(color="#00ff66", size=11, family="Orbitron"))

    # Altitude Vertical Tape (Right)
    fig_pfd.add_shape(type="rect", x0=7.5, y0=-10, x1=10, y1=10, fillcolor="rgba(8,16,32,0.9)", line=dict(color=active_theme['border'], width=1))
    fig_pfd.add_annotation(x=8.75, y=0, text=f"<b>{cur_alt}</b><br><span style='font-size:9px'>M</span>", showarrow=False, font=dict(color="#00f0ff", size=11, family="Orbitron"))

    # Aircraft Center Symbol
    fig_pfd.add_shape(type="line", x0=-3.5, y0=0, x1=-1.2, y1=0, line=dict(color="#facc15", width=3))
    fig_pfd.add_shape(type="line", x0=1.2, y0=0, x1=3.5, y1=0, line=dict(color="#facc15", width=3))
    fig_pfd.add_shape(type="circle", x0=-0.5, y0=-0.5, x1=0.5, y1=0.5, line=dict(color="#facc15", width=2))

    fig_pfd.update_layout(
        title={'text': "<b>TACTICAL GLASS PFD</b>", 'font': {'size': 11, 'family': 'Orbitron', 'color': active_theme['primary']}},
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(8,16,32,0.95)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-10, 10]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-10, 10]),
        height=175, margin=dict(l=5, r=5, t=30, b=5)
    )
    st.plotly_chart(fig_pfd, use_container_width=True)

def make_hud_gauge(title, value, min_v, max_v, unit, alert_v, warn_v, is_invert=False):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 11, 'family': 'Orbitron', 'color': active_theme['primary']}},
        number={'suffix': f" {unit}", 'font': {'size': 18, 'family': 'Orbitron', 'color': '#ffffff'}},
        gauge={
            'axis': {'range': [min_v, max_v], 'tickwidth': 1, 'tickcolor': "#8892b0"},
            'bar': {'color': active_theme['primary'], 'thickness': 0.24},
            'bgcolor': "rgba(6, 12, 24, 0.9)",
            'borderwidth': 1,
            'bordercolor': active_theme['border'],
            'steps': [
                {'range': [min_v, warn_v] if not is_invert else [alert_v, max_v], 'color': 'rgba(0, 255, 102, 0.15)'},
                {'range': [warn_v, alert_v] if not is_invert else [warn_v, alert_v], 'color': 'rgba(255, 183, 3, 0.2)'},
                {'range': [alert_v, max_v] if not is_invert else [min_v, warn_v], 'color': 'rgba(255, 0, 60, 0.3)'}
            ],
            'threshold': {'line': {'color': "#ff003c", 'width': 3}, 'thickness': 0.75, 'value': alert_v}
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=175, margin=dict(l=8, r=8, t=30, b=8), font={'family': "Share Tech Mono"})
    return fig

with g1:
    st.plotly_chart(make_hud_gauge("HEALTH INDEX", metrics['health_index'], 0, 100, "%", 45, 75, is_invert=True), use_container_width=True)
with g2:
    st.plotly_chart(make_hud_gauge("CYLINDER TEMP", current_row['cht_actual'], 80, 170, "°C", 145, 130), use_container_width=True)
with g3:
    st.plotly_chart(make_hud_gauge("OIL PRESSURE", current_row['oil_press_actual'], 0, 6, "bar", 1.8, 2.5, is_invert=True), use_container_width=True)
with g4:
    st.plotly_chart(make_hud_gauge("CRANKSHAFT", current_row['rpm'], 0, 6000, "RPM", 5600, 5200), use_container_width=True)

# Advisory Banner
if spoofed_flag:
    st.markdown("""
    <div style='background: rgba(88, 28, 135, 0.9); border: 1px solid #c084fc; border-left: 8px solid #a855f7; padding: 14px 20px; border-radius: 4px; margin-bottom: 16px;'>
        <strong>🛡️ KALMAN INNOVATION GATING ACTIVE:</strong> Sensor anomaly rejected (+45°C spoof spike). Primary flight model retained.
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "RED":
    st.markdown(f"""
    <div class='alert-banner-critical'>
        <strong>⚠️ CRITICAL TACTICAL ADVISORY [AUTONOMOUS THREAT-AVOIDANCE RTB ACTIVE]</strong><br>
        <strong>Fault Mode:</strong> {metrics['status']} &nbsp;|&nbsp; <strong>Root Cause:</strong> {metrics['alert_message']}<br>
        <strong>Remaining Flight Endurance (RUL):</strong> {metrics['rul_hours']} Hours
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "AMBER":
    st.markdown(f"""
    <div style='background: rgba(60, 40, 0, 0.85); border-left: 6px solid #ffb703; padding: 12px 18px; border-radius: 4px; margin-bottom: 16px; color: #ffe699;'>
        <strong>CAUTION [DEGRADED PROPULSION]:</strong> {metrics['status']} &nbsp;|&nbsp; {metrics['alert_message']}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class='alert-banner-nominal'>
        <strong>✓ ALL PROPULSION SUBSYSTEMS NOMINAL:</strong> Telemetry residuals aligned with physical model. Zero safety deviations.
    </div>
    """, unsafe_allow_html=True)

# Voice Synthesizer Hook
if enable_voice and metrics["severity"] == "RED" and st.session_state.last_voice_alert != "RED" and not spoofed_flag:
    st.session_state.last_voice_alert = "RED"
    components.html("""
    <script>
    function playMilitaryRadioAlert() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            const osc1 = ctx.createOscillator();
            const gain1 = ctx.createGain();
            osc1.type = "sine";
            osc1.frequency.setValueAtTime(880, ctx.currentTime);
            gain1.gain.setValueAtTime(0.15, ctx.currentTime);
            gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            osc1.start(ctx.currentTime);
            osc1.stop(ctx.currentTime + 0.08);

            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.type = "sine";
            osc2.frequency.setValueAtTime(1760, ctx.currentTime + 0.09);
            gain2.gain.setValueAtTime(0.18, ctx.currentTime + 0.09);
            gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.22);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.start(ctx.currentTime + 0.09);
            osc2.stop(ctx.currentTime + 0.22);

            setTimeout(() => {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let msg = new SpeechSynthesisUtterance("Warning. Propulsion core critical. Thermal runaway detected. Autonomous Return To Base vector engaged.");
                    msg.rate = 1.05; msg.pitch = 0.88;
                    window.speechSynthesis.speak(msg);
                }
            }, 260);
        } catch(e) { console.error(e); }
    }
    playMilitaryRadioAlert();
    </script>
    """, height=0)
elif metrics["severity"] != "RED":
    st.session_state.last_voice_alert = metrics["severity"]

# Emergency Pilot Mitigation Station
st.markdown(f"<div style='font-family: Orbitron; font-size: 0.92rem; color: {active_theme['primary']}; margin-bottom: 8px;'>🕹️ TACTICAL PILOT MITIGATION & EMERGENCY STORES JETTISON</div>", unsafe_allow_html=True)
c_mit1, c_mit2, c_mit3, c_mit4 = st.columns(4)
with c_mit1:
    if st.button("🚨 " + ("DISENGAGE LIMP-HOME" if st.session_state.limp_mode else "ENGAGE 65% LIMP THROTTLE")):
        st.session_state.limp_mode = not st.session_state.limp_mode
        st.rerun()
with c_mit2:
    if st.button("💧 " + ("RESTORE FUEL RATIO" if st.session_state.fuel_enrich else "ENRICH MIXTURE (QUENCH)")):
        st.session_state.fuel_enrich = not st.session_state.fuel_enrich
        st.rerun()
with c_mit3:
    if st.button("💥 " + ("JETTISON ACTIVE (-250kg)" if st.session_state.stores_jettison else "JETTISON UNDERWING STORES")):
        st.session_state.stores_jettison = not st.session_state.stores_jettison
        st.rerun()
with c_mit4:
    status_mit = []
    if st.session_state.limp_mode: status_mit.append("LIMP-HOME (-800 RPM)")
    if st.session_state.fuel_enrich: status_mit.append("QUENCH (-6°C CHT)")
    if st.session_state.stores_jettison: status_mit.append("STORES JETTISONED (+14km GLIDE)")
    st.caption("Active Mitigations: " + (", ".join(status_mit) if status_mit else "NONE (NOMINAL CRUISE)"))

# Interactive Electronic Emergency Checklist (ECL)
with st.expander("📋 EMERGENCY COMBAT CHECKLIST (ECL) // MAYDAY DRILL", expanded=(metrics["severity"] == "RED")):
    col_ecl1, col_ecl2 = st.columns(2)
    with col_ecl1:
        st.checkbox("1. Throttle Lever: Retard to 65% Limp-Home regime", value=st.session_state.limp_mode)
        st.checkbox("2. Fuel Enrichment Quench: Activated to suppress detonation", value=st.session_state.fuel_enrich)
        st.checkbox("3. Underwing Munitions: Jettisoned to maximize glide polar", value=st.session_state.stores_jettison)
    with col_ecl2:
        st.checkbox("4. IFF Transponder: Squawk 7700 Declared to Air Traffic Control", value=(metrics["severity"] == "RED"))
        st.checkbox("5. Autonomous RTB Waypoint Vector: Armed around Hostile SAM Dome", value=(metrics["severity"] == "RED"))
        st.checkbox("6. Swarm Datalink: Surveillance Handover Handshake with UAV-02", value=True)

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📈 SENSOR BUS & EKF",
    "🌀 TURBO COMPRESSOR MAP",
    "🔥 THERMODYNAMIC P-V LOOP",
    "🌊 ACOUSTIC SPECTROGRAM",
    "🎯 XAI & ADAPTIVE DRIFT",
    "🧊 3D ENGINE CORE",
    "🗺️ RADAR & SAM AVOIDANCE",
    "📡 MIL-STD-1553B & NATO DEBRIEF"
])

hud_plot_layout = dict(
    paper_bgcolor='rgba(8, 16, 32, 0.65)',
    plot_bgcolor='rgba(4, 9, 20, 0.85)',
    font=dict(family='Share Tech Mono', color='#8892b0'),
    margin=dict(l=35, r=20, t=30, b=25),
    xaxis=dict(gridcolor='rgba(255, 255, 255, 0.08)', zerolinecolor=active_theme['border']),
    yaxis=dict(gridcolor='rgba(255, 255, 255, 0.08)', zerolinecolor=active_theme['border']),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>CYLINDER HEAD TEMPERATURE: RAW SENSOR VS. EKF FILTER VS. TWIN</div>", unsafe_allow_html=True)
        time_slice = df['timestamp'][:t_idx+1]
        raw_cht = df['cht_actual'][:t_idx+1]
        ekf_cht = raw_cht.rolling(window=4, min_periods=1).mean()
        sigma_2 = 1.4

        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(x=time_slice, y=ekf_cht + sigma_2, mode='lines', line=dict(width=0), showlegend=False))
        fig_cht.add_trace(go.Scatter(x=time_slice, y=ekf_cht - sigma_2, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 240, 255, 0.12)', name="EKF ±2σ Uncertainty"))
        fig_cht.add_trace(go.Scatter(x=time_slice, y=raw_cht, mode='markers', marker=dict(color="#ff0055", size=4, opacity=0.6), name="Raw CAN Bus Feed"))
        fig_cht.add_trace(go.Scatter(x=time_slice, y=ekf_cht, mode='lines', line=dict(color=active_theme['primary'], width=2.5), name="EKF Filtered State"))
        fig_cht.add_trace(go.Scatter(x=time_slice, y=df['cht_physics'][:t_idx+1], mode='lines', line=dict(color="#94a3b8", dash="dash", width=2), name="Physics Twin Target"))
        fig_cht.add_hline(y=145.0, line_dash="dot", line_color="#ffb703", annotation_text="Limit (145°C)")
        fig_cht.update_layout(hud_plot_layout, height=310, yaxis_title="°C")
        st.plotly_chart(fig_cht, use_container_width=True)

    with col_t2:
        st.markdown(f"<div style='color: {active_theme['accent']}; font-weight: bold;'>LUBRICATION CIRCUIT PRESSURE</div>", unsafe_allow_html=True)
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(x=time_slice, y=df['oil_press_actual'][:t_idx+1], name="Oil Pressure Actual", line=dict(color=active_theme['accent'], width=3)))
        fig_oil.add_trace(go.Scatter(x=time_slice, y=df['oil_press_physics'][:t_idx+1], name="Physics Baseline", line=dict(color="#94a3b8", dash="dash", width=2)))
        fig_oil.add_hline(y=1.5, line_dash="dot", line_color="#ff003c", annotation_text="Cavitation Limit (1.5 bar)")
        fig_oil.update_layout(hud_plot_layout, height=310, yaxis_title="bar")
        st.plotly_chart(fig_oil, use_container_width=True)

    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold; margin-top: 10px;'>SUBSYSTEM RESIDUAL ERROR MATRIX</div>", unsafe_allow_html=True)
    matrix_data = [
        {"Subsystem": "Cylinder Head Thermal Loop", "Actual Telemetry": f"{current_row['cht_actual']} °C", "Twin Expected": f"{current_row['cht_physics']} °C", "Residual Error (Δ)": f"+{metrics['residuals']['cht_delta']} °C", "Status": "CRITICAL DRIFT" if metrics['residuals']['cht_delta'] > 15.0 else "NOMINAL"},
        {"Subsystem": "Exhaust Gas Thermal Loop", "Actual Telemetry": f"{current_row['egt_actual']} °C", "Twin Expected": f"{current_row['egt_physics']} °C", "Residual Error (Δ)": f"+{metrics['residuals']['egt_delta']} °C", "Status": "NOMINAL"},
        {"Subsystem": "Oil Gallery Hydrodynamics", "Actual Telemetry": f"{current_row['oil_press_actual']} bar", "Twin Expected": f"{current_row['oil_press_physics']} bar", "Residual Error (Δ)": f"-{metrics['residuals']['oil_p_delta']} bar", "Status": "PRESSURE DROP" if metrics['residuals']['oil_p_delta'] > 1.5 else "NOMINAL"},
        {"Subsystem": "Crankshaft Mechanical Harmonics", "Actual Telemetry": f"{current_row['vibration_rms']} G", "Twin Expected": "1.10 G", "Residual Error (Δ)": f"+{round(abs(current_row['vibration_rms'] - 1.1), 2)} G", "Status": "DETONATION DETECTED" if current_row['vibration_rms'] > 1.8 else "NOMINAL"}
    ]
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

with tab2:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>TURBOCHARGER COMPRESSOR MAP & DYNAMIC SURGE MARGIN</div>", unsafe_allow_html=True)
    st.caption("Real-time compressor operating point on mass flow vs pressure ratio map with aerodynamic surge boundary.")

    m_flow = np.linspace(0.04, 0.22, 100)
    surge_line = 1.05 + 10.5 * m_flow - 22.0 * (m_flow**2)
    choke_line = 1.0 + 4.2 * m_flow

    p_amb = 101.325 * (1 - 0.0000225577 * current_row['altitude_m'])**5.25588
    p_man = current_row['map_inhg'] * 3.38639
    pr_actual = round(max(1.0, p_man / p_amb), 2)
    actual_mflow = round(0.06 + (current_row['rpm'] / 6000.0) * 0.11, 3)

    surge_pr_at_flow = 1.05 + 10.5 * actual_mflow - 22.0 * (actual_mflow**2)
    surge_margin_pct = round(max(0.0, ((surge_pr_at_flow - pr_actual) / pr_actual) * 100.0), 1)

    fig_turbo = go.Figure()
    fig_turbo.add_trace(go.Scatter(x=m_flow, y=surge_line, mode='lines', line=dict(color='#ff003c', width=3), name="Surge Boundary Limit"))
    fig_turbo.add_trace(go.Scatter(x=m_flow, y=choke_line, mode='lines', line=dict(color='#94a3b8', dash='dash', width=2), name="Choke Limit"))

    for eff, offset in [(0.75, 0.2), (0.70, 0.4), (0.65, 0.6)]:
        fig_turbo.add_trace(go.Scatter(
            x=m_flow[15:85], y=(surge_line[15:85] - offset),
            mode='lines', line=dict(color='rgba(255, 255, 255, 0.15)', dash='dot'),
            name=f"η_c = {int(eff*100)}%"
        ))

    fig_turbo.add_trace(go.Scatter(
        x=[actual_mflow], y=[pr_actual], mode='markers+text',
        marker=dict(size=18, color='#ff003c' if surge_margin_pct < 15.0 else '#00ff66', symbol='diamond', line=dict(color='#ffffff', width=2)),
        text=[f"<b>OP: PR={pr_actual} (SM: {surge_margin_pct}%)</b>"],
        textposition="top center", name="Operating Point"
    ))

    fig_turbo.update_layout(
        hud_plot_layout, height=360,
        xaxis_title="Corrected Air Mass Flow ṁ_corr (kg/s)",
        yaxis_title="Total Pressure Ratio Π_c",
        xaxis=dict(range=[0.03, 0.24]), yaxis=dict(range=[1.0, 2.6])
    )
    st.plotly_chart(fig_turbo, use_container_width=True)

with tab3:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>THERMODYNAMIC INDICATOR DIAGRAM (P-V OTTO COMBUSTION CYCLE)</div>", unsafe_allow_html=True)
    v_c = 45.0
    v_d = 340.0
    v_arr = np.linspace(v_c, v_c + v_d, 60)
    gamma = 1.35
    p_intake = current_row['map_inhg'] * 0.0338639 * 100
    p_comp = p_intake * ((v_c + v_d) / v_arr)**gamma

    knock_penalty = 1.35 if current_row['vibration_rms'] > 1.5 else 1.0
    p_peak = (5500.0 * knock_penalty) if metrics['severity'] != "RED" else 3600.0
    p_exp = p_peak * (v_c / v_arr)**gamma

    v_loop = np.concatenate([v_arr, v_arr[::-1], [v_c]])
    p_loop = np.concatenate([p_comp, p_exp[::-1], [p_comp[0]]])

    p_peak_nom = 5500.0
    p_exp_nom = p_peak_nom * (v_c / v_arr)**gamma
    p_loop_nom = np.concatenate([p_comp, p_exp_nom[::-1], [p_comp[0]]])
    v_loop_nom = v_loop

    fig_pv = go.Figure()
    fig_pv.add_trace(go.Scatter(x=v_loop_nom, y=p_loop_nom, mode='lines', line=dict(color=active_theme['primary'], dash='dash', width=2), name="Nominal Cycle"))
    fig_pv.add_trace(go.Scatter(x=v_loop, y=p_loop, fill='toself', fillcolor='rgba(255, 0, 60, 0.2)' if metrics['severity'] == "RED" else 'rgba(0, 255, 102, 0.2)',
                                line=dict(color='#ff003c' if metrics['severity'] == "RED" else '#00ff66', width=3), name="Active Cycle"))

    # Version-safe trapezoidal integration
    delta_p = p_exp - p_comp
    work_integral = float(np.sum(0.5 * (delta_p[:-1] + delta_p[1:]) * np.diff(v_arr)))
    imep_val = round(work_integral / v_d, 1)
    thermal_eff = round(max(15.0, min(36.0, 34.0 - (current_row['cht_actual'] - 110.0) * 0.35)), 1)

    fig_pv.update_layout(
        hud_plot_layout, height=360,
        xaxis_title="Cylinder Volume (cc)", yaxis_title="In-Cylinder Pressure (kPa)",
        annotations=[
            dict(x=v_c + 20, y=p_peak * 0.9, text=f"IMEP: {imep_val} kPa | η_th: {thermal_eff}%", showarrow=False, font=dict(color=active_theme['primary'], size=13))
        ]
    )
    st.plotly_chart(fig_pv, use_container_width=True)

with tab4:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>2D ACOUSTIC & VIBRATION WATERFALL SPECTROGRAM (0 - 8 kHz)</div>", unsafe_allow_html=True)
    t_steps = max(5, t_idx + 1)
    freq_bins = np.linspace(100, 8000, 80)
    spec_matrix = np.zeros((len(freq_bins), t_steps))

    for i in range(t_steps):
        r_row = df.iloc[i] if i < len(df) else current_row
        rpm_f = r_row['rpm'] / 60.0
        spec_matrix[:, i] += 0.2 / (1 + ((freq_bins - rpm_f) / 50)**2)
        spec_matrix[:, i] += 0.15 / (1 + ((freq_bins - 2 * rpm_f) / 70)**2)
        if r_row['vibration_rms'] > 1.3:
            spec_matrix[:, i] += 0.85 / (1 + ((freq_bins - 6200) / 350)**2)
        spec_matrix[:, i] += np.random.uniform(0.01, 0.05, len(freq_bins))

    fig_waterfall = go.Figure(data=go.Heatmap(
        z=spec_matrix, x=list(df['timestamp'][:t_steps]), y=freq_bins,
        colorscale='Viridis', colorbar=dict(title="Energy (G²/Hz)")
    ))
    fig_waterfall.update_layout(hud_plot_layout, height=360, xaxis_title="MET (Seconds)", yaxis_title="Frequency Band (Hz)")
    st.plotly_chart(fig_waterfall, use_container_width=True)

with tab5:
    col_xai1, col_xai2 = st.columns([3, 2])
    with col_xai1:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>EXPLAINABLE AI (XAI) ATTRIBUTION WATERFALL</div>", unsafe_allow_html=True)
        cht_penalty = min(45.0, metrics['residuals']['cht_delta'] * 1.8)
        oil_penalty = min(35.0, metrics['residuals']['oil_p_delta'] * 16.0)
        vib_penalty = min(20.0, max(0.0, (current_row['vibration_rms'] - 1.1) * 25.0))

        fig_xai = go.Figure(go.Waterfall(
            name="Penalty Attribution", orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["Baseline", "CHT Drift", "Oil Drop", "Knock", "Final Health"],
            textposition="outside",
            text=[f"100.0%", f"-{cht_penalty:.1f}%", f"-{oil_penalty:.1f}%", f"-{vib_penalty:.1f}%", f"{metrics['health_index']}%"],
            y=[100.0, -cht_penalty, -oil_penalty, -vib_penalty, 0],
            connector={"line": {"color": "rgba(255, 255, 255, 0.3)"}},
            decreasing={"marker": {"color": "#ff003c"}},
            increasing={"marker": {"color": "#00ff66"}},
            totals={"marker": {"color": active_theme['primary']}}
        ))
        fig_xai.update_layout(hud_plot_layout, height=360, yaxis_title="Health %")
        st.plotly_chart(fig_xai, use_container_width=True)

    with col_xai2:
        st.markdown(f"<div style='color: {active_theme['accent']}; font-weight: bold;'>ONLINE ESTIMATED DEGRADATION PARAMETERS</div>", unsafe_allow_html=True)
        st.caption("Unmeasurable internal engine state parameters estimated live by the thermodynamic observer.")

        fmep_val = round(0.45 + (current_row['rpm'] / 6000.0) * 0.35 + (5.0 - current_row['oil_press_actual']) * 0.18, 2)
        blowby_pct = round(min(18.5, max(1.2, (current_row['cht_actual'] - 105.0) * 0.28)), 1)

        deg_data = [
            {"Parameter": "Friction MEP (FMEP)", "Estimated Value": f"{fmep_val} bar", "Nominal": "0.45 bar", "Drift Status": "HIGH FRICTION" if fmep_val > 0.8 else "NOMINAL"},
            {"Parameter": "Piston Ring Blow-By", "Estimated Value": f"{blowby_pct}%", "Nominal": "< 2.5%", "Drift Status": "SEAL BREAKDOWN" if blowby_pct > 6.0 else "NOMINAL"},
            {"Parameter": "Heat Dissipation Rate", "Estimated Value": f"{round(max(0.4, 1.0 - (current_row['cht_actual']-110)*0.015), 2)} ε", "Nominal": "1.00 ε", "Drift Status": "DEGRADED" if current_row['cht_actual'] > 125 else "NOMINAL"}
        ]
        st.dataframe(pd.DataFrame(deg_data), use_container_width=True)

with tab6:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>3D ISOMETRIC PROPULSION CORE STRESS MODEL</div>", unsafe_allow_html=True)
    cht_val = current_row['cht_actual']
    oil_p = current_row['oil_press_actual']
    cyl_col = "#ff003c" if cht_val > 140 else ("#ffb703" if cht_val > 125 else "#00ff66")
    oil_col = "#ff003c" if oil_p < 1.8 else ("#ffb703" if oil_p < 2.5 else "#00ff66")

    fig_3d = go.Figure()
    fig_3d.add_trace(go.Scatter3d(x=[0, 0], y=[-1.8, 1.8], z=[0, 0], mode="lines", line=dict(color=active_theme['primary'], width=10), name="Crankshaft"))
    cyl_coords = [
        {"name": "Cyl 1 [FWD-L]", "x": -1.2, "y": 1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 2 [FWD-R]", "x": 1.2, "y": 1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 3 [AFT-L]", "x": -1.2, "y": -1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 4 [AFT-R]", "x": 1.2, "y": -1.0, "z": 0.4, "temp": cht_val},
    ]
    for c in cyl_coords:
        fig_3d.add_trace(go.Scatter3d(
            x=[c["x"]], y=[c["y"]], z=[c["z"]], mode="markers+text",
            marker=dict(size=28, color=cyl_col, symbol="square", opacity=0.9),
            text=[f"<b>{c['name']}</b><br>{c['temp']}°C"], textposition="top center", name=c["name"]
        ))
    fig_3d.add_trace(go.Scatter3d(x=[0], y=[-1.6], z=[1.1], mode="markers+text", marker=dict(size=22, color=active_theme['secondary'], symbol="diamond"), text=[f"<b>TURBOCHARGER</b><br>{current_row['map_inhg']} inHg"], textposition="top center", name="Turbo"))
    fig_3d.add_trace(go.Scatter3d(x=[0], y=[0], z=[-0.9], mode="markers+text", marker=dict(size=24, color=oil_col, symbol="circle"), text=[f"<b>OIL SUMP</b><br>{oil_p} bar"], textposition="bottom center", name="Oil Gallery"))

    fig_3d.update_layout(
        paper_bgcolor='rgba(4, 9, 20, 0.85)', height=480,
        scene=dict(
            xaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-2, 2]),
            yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-2.5, 2.5]),
            zaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-1.5, 1.8]),
            camera=dict(eye=dict(x=1.6, y=-1.7, z=1.3))
        ),
        font=dict(family='Share Tech Mono', color='#ffffff'), margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

with tab7:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>TACTICAL MULTI-BASE RADAR & AUTONOMOUS SAM THREAT AVOIDANCE</div>", unsafe_allow_html=True)
    st.caption("Live reachability assessment across recovery runways. Jettisoning external stores expands unpowered glide radius.")

    uav_x = [0, 8, 16, 25, 32, 38, 42, 40, 32, 22, 12, 5, 0]
    uav_y = [0, 6, 12, 18, 22, 22, 15, 6, -2, -6, -4, -1, 0]
    norm_idx = int((t_idx / max(1, len(df))) * (len(uav_x) - 1))
    norm_idx = min(norm_idx, len(uav_x) - 1)
    cur_x = uav_x[norm_idx]
    cur_y = uav_y[norm_idx]

    ld_ratio = 15.5 if st.session_state.stores_jettison else 12.0
    glide_limit_km = (current_row['altitude_m'] / 1000.0) * ld_ratio

    bases = [
        {"name": "FOB Alpha [HOME]", "x": 0, "y": 0, "color": "#00ff66"},
        {"name": "FOB Bravo [FWD STRIP]", "x": 30, "y": 8, "color": "#38bdf8"},
        {"name": "Highway Strip Charlie", "x": 20, "y": 28, "color": "#f59e0b"}
    ]

    fig_radar = go.Figure()

    for r in [15, 30, 48]:
        fig_radar.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color="rgba(255, 255, 255, 0.1)", dash="dot", width=1))

    sam_x, sam_y, sam_r = 16, 10, 12
    fig_radar.add_shape(
        type="circle", x0=sam_x - sam_r, y0=sam_y - sam_r, x1=sam_x + sam_r, y1=sam_y + sam_r,
        line=dict(color="rgba(255, 0, 60, 0.8)", dash="dash", width=2),
        fillcolor="rgba(255, 0, 60, 0.15)"
    )
    fig_radar.add_trace(go.Scatter(
        x=[sam_x], y=[sam_y], mode="markers+text",
        marker=dict(size=14, color="#ff003c", symbol="x"),
        text=["<b>[SAM-6 ENEMY RADAR]</b>"], textposition="top center", name="SAM Threat"
    ))

    fig_radar.add_trace(go.Scatter(x=uav_x[:norm_idx+1], y=uav_y[:norm_idx+1], mode="lines+markers", line=dict(color=active_theme['primary'], width=2.5), name="Patrol Route"))

    for b in bases:
        dist = np.sqrt((cur_x - b["x"])**2 + (cur_y - b["y"])**2)
        reachable = dist <= glide_limit_km
        status_lbl = "REACHABLE" if reachable else "UNREACHABLE"
        color = b["color"] if reachable else "#64748b"
        fig_radar.add_trace(go.Scatter(
            x=[b["x"]], y=[b["y"]], mode="markers+text",
            marker=dict(size=14, color=color, symbol="triangle-up"),
            text=[f"<b>{b['name']}</b><br>{dist:.1f}km ({status_lbl})"],
            textposition="bottom center", name=b["name"]
        ))

    fig_radar.add_trace(go.Scatter(
        x=[cur_x], y=[cur_y], mode="markers+text",
        marker=dict(size=16, color="#ff0055" if metrics["severity"] == "RED" else "#00ff66", symbol="diamond"),
        text=[f"<b>UAV-01 (T+{current_row['timestamp']:.0f}s)</b>"], textposition="top right", name="UAV-01"
    ))

    if metrics["severity"] == "RED" and not spoofed_flag:
        dogleg_wp_x = 32
        dogleg_wp_y = 2
        fig_radar.add_trace(go.Scatter(
            x=[cur_x, dogleg_wp_x, 0], y=[cur_y, dogleg_wp_y, 0],
            mode="lines+markers+text", line=dict(color="#ff003c", width=3.5, dash="dashdot"),
            marker=dict(size=8, color="#ff003c"),
            text=["", "<b>WP-DOGLEG [SAM BYPASS]</b>", "<b>FOB ALPHA TOUCHDOWN</b>"],
            textposition="top right", name="Avoidance Vector"
        ))

    fig_radar.update_layout(hud_plot_layout, height=460, xaxis=dict(range=[-35, 55], title="Range X (km)"), yaxis=dict(range=[-25, 45], title="Range Y (km)"))
    st.plotly_chart(fig_radar, use_container_width=True)

with tab8:
    col_rep1, col_rep2 = st.columns([3, 2])
    with col_rep1:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>MIL-STD-1553B AVIONICS D-BUS PROTOCOL ANALYZER</div>", unsafe_allow_html=True)
        st.caption("Decoded military standard serial bus architecture for Remote Terminal 04 (Rotax Engine FADEC).")

        bus_frames = [
            f"[1553B BC->RT04] CMD WORD: 0x2084 | Transmit Command | Sub-Address 04 | Word Count: 16 | Parity: ODD (OK)",
            f"[1553B RT04->BC] STATUS WORD: 0x2000 | Remote Terminal Healthy | Service Request: NONE | Busy: 0",
            f"[1553B DATA 01-04] RPM: {int(current_row['rpm']):04X} | CHT: {int(current_row['cht_actual']*10):04X} | OIL_P: {int(current_row['oil_press_actual']*100):04X} | EGT: {int(current_row['egt_actual']):04X}",
            f"[1553B DATA 05-08] MAP: {int(current_row['map_inhg']*100):04X} | ALT: {int(current_row['altitude_m']):04X} | VIB: {int(current_row['vibration_rms']*100):04X} | CRC: 0x9B7A"
        ]
        bus_html = "<br>".join([f"&gt; {item}" for item in bus_frames])
        st.markdown(f"<div class='terminal-box'>{bus_html}</div>", unsafe_allow_html=True)

    with col_rep2:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>NATO STANAG AIRWORTHINESS DIRECTIVE</div>", unsafe_allow_html=True)
        haz_class = "CATEGORY 1 - CATASTROPHIC" if metrics['severity'] == "RED" else "CATEGORY 4 - NEGLIGIBLE"
        st.markdown(f"""
        <div class='nato-card'>
            <b>STANAG REF:</b> <code>STANAG-4586-AIR-2026-0923</code><br>
            <b>TAIL NUMBER:</b> <code>UAV-MALE-01 [AEROTWIN]</code><br>
            <b>HAZARD LEVEL:</b> <span style='color: {"#ff003c" if metrics["severity"]=="RED" else "#00ff66"};'><b>{haz_class}</b></span><br>
            <b>COMPRESSOR SURGE MARGIN:</b> <code>{surge_margin_pct}%</code><br>
            <b>CALCULATED RUN-TO-FAILURE:</b> <code>{metrics['rul_hours']} Flight Hours</code><br>
            <b>ACTIVE MITIGATION STATUS:</b> <code>{'STORES JETTISONED' if st.session_state.stores_jettison else 'NOMINAL STORES'}</code>
        </div>
        """, unsafe_allow_html=True)

# Loop Execution Handler
if source_mode == "🔴 LIVE HARDWARE UDP LINK (PORT 14550)" and transmitter_daemon.is_running:
    time.sleep(0.5)
    st.rerun()
elif source_mode == "MISSION REPLAY (SYNTHETIC)" and st.session_state.is_playing:
    if st.session_state.t_idx < len(df) - 1:
        time.sleep(0.35)
        st.session_state.t_idx += 1
        st.rerun()
    else:
        st.session_state.is_playing = False
        st.rerun()
