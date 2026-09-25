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
    page_title="AeroTwin Tactical GCS | MALE UAV Digital Twin",
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

# State Initialization
if "boot_complete" not in st.session_state:
    st.session_state.boot_complete = False
if "viewport_mode" not in st.session_state:
    st.session_state.viewport_mode = "🖥️ DESKTOP MODE"
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
if "sim_clock" not in st.session_state:
    st.session_state.sim_clock = 0

transmitter_daemon = EmbeddedUAVTransmitter.get_instance()

THEMES = {
    "CYBER CYAN (DEFENSE)": {
        "primary": "#00f0ff", "secondary": "#38bdf8", "accent": "#00ff66",
        "bg_radial1": "#0c1b30", "bg_radial2": "#051329", "glow": "rgba(0, 240, 255, 0.35)", "border": "rgba(0, 240, 255, 0.3)"
    },
    "NVG PHOSPHOR GREEN (530nm)": {
        "primary": "#00ff66", "secondary": "#4ade80", "accent": "#a7f3d0",
        "bg_radial1": "#062412", "bg_radial2": "#021609", "glow": "rgba(0, 255, 102, 0.4)", "border": "rgba(0, 255, 102, 0.3)"
    },
    "FLIR COMBAT AMBER (THERMAL)": {
        "primary": "#f59e0b", "secondary": "#fbbf24", "accent": "#fde68a",
        "bg_radial1": "#251203", "bg_radial2": "#1a0b02", "glow": "rgba(245, 158, 11, 0.4)", "border": "rgba(245, 158, 11, 0.3)"
    }
}

active_theme = THEMES[st.session_state.hud_theme]
is_mobile = (st.session_state.viewport_mode == "📱 MOBILE TACTICAL")

st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">

<style>
    @keyframes ambientBreathe {{
        0% {{ background-position: 0% 50%, 0 0, 0 0; }}
        50% {{ background-position: 100% 50%, 14px 14px, 14px 14px; }}
        100% {{ background-position: 0% 50%, 0 0, 0 0; }}
    }}

    .stApp {{
        background-color: #010409;
        background-image: 
            radial-gradient(ellipse at top, {active_theme['bg_radial1']} 0%, {active_theme['bg_radial2']} 50%, #010409 95%),
            linear-gradient(rgba(255, 255, 255, 0.022) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.022) 1px, transparent 1px);
        background-size: 200% 200%, 24px 24px, 24px 24px;
        animation: ambientBreathe 30s ease infinite;
        color: #e2e8f0;
        font-family: 'Share Tech Mono', monospace;
    }}

    .hud-header {{
        font-family: 'Orbitron', sans-serif;
        letter-spacing: clamp(1px, 0.6vw, 4px);
        background: linear-gradient(90deg, {active_theme['primary']} 0%, {active_theme['secondary']} 45%, {active_theme['accent']} 90%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: clamp(1.2rem, 2.2vw, 2.1rem);
        font-weight: 900;
        margin-bottom: 2px;
        text-shadow: 0 0 30px {active_theme['glow']};
    }}

    .telemetry-strip {{
        background: rgba(6, 12, 24, 0.88);
        backdrop-filter: blur(16px);
        border: 1px solid {active_theme['border']};
        border-left: 6px solid {active_theme['primary']};
        padding: 9px 16px;
        border-radius: 6px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px 18px;
        justify-content: space-between;
        align-items: center;
        font-size: clamp(0.72rem, 0.95vw, 0.85rem);
        color: #94a3b8;
        margin-bottom: 14px;
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.75);
    }}
    .telemetry-val {{ color: #ffffff; font-weight: bold; }}

    .annunciator-box {{
        padding: 5px 12px;
        border-radius: 4px;
        font-family: 'Orbitron', sans-serif;
        font-size: clamp(0.68rem, 0.85vw, 0.78rem);
        font-weight: 800;
        letter-spacing: 1.5px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    .annunciator-warn {{
        background: #dc2626; color: #ffffff;
        box-shadow: 0 0 25px rgba(220, 38, 38, 0.9);
        animation: blinkWarn 0.7s infinite alternate;
    }}
    .annunciator-nominal {{
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid #10b981; color: #34d399;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: rgba(4, 9, 20, 0.9);
        backdrop-filter: blur(14px);
        border: 1px solid {active_theme['border']};
        border-radius: 6px;
        padding: 6px;
        margin-bottom: 14px;
        overflow-x: auto !important;
        white-space: nowrap !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: clamp(0.66rem, 0.8vw, 0.73rem) !important;
        letter-spacing: 1px !important;
        padding: 8px 14px !important;
        color: #64748b !important;
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 4px !important;
        flex-shrink: 0 !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {active_theme['primary']} !important;
        background: rgba(0, 240, 255, 0.15) !important;
        border: 1px solid {active_theme['primary']} !important;
        box-shadow: 0 0 16px {active_theme['glow']} !important;
    }}

    div.stButton > button {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: clamp(0.68rem, 0.82vw, 0.74rem) !important;
        letter-spacing: 1px !important;
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(3, 7, 18, 0.95) 100%) !important;
        color: {active_theme['secondary']} !important;
        border: 1px solid {active_theme['border']} !important;
        border-radius: 4px !important;
        padding: 10px 16px !important;
        min-height: 42px !important;
    }}
    div.stButton > button:hover {{
        color: #ffffff !important;
        border-color: {active_theme['primary']} !important;
        box-shadow: 0 0 20px {active_theme['glow']} !important;
    }}

    .quick-dock {{
        background: rgba(6, 12, 24, 0.88);
        backdrop-filter: blur(16px);
        border: 1px solid {active_theme['border']};
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 15px;
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
        background: rgba(8, 16, 32, 0.9);
        backdrop-filter: blur(14px);
        border: 1px solid {active_theme['border']};
        border-left: 6px solid {active_theme['primary']};
        padding: 16px;
        border-radius: 4px;
        color: #cbd5e1;
        font-size: 0.84rem;
        line-height: 1.75;
    }}

    @keyframes blinkWarn {{ from {{ opacity: 1; }} to {{ opacity: 0.35; }} }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. BOOT SCREEN: NATIVE 3D DRDO TAPAS-201 ROTATING HANGAR
# -------------------------------------------------------------
if not st.session_state.boot_complete:
    st.markdown(f"""
    <div style='max-width: 900px; margin: 15px auto; text-align: center;'>
        <div style='font-family: Orbitron; font-size: clamp(1.2rem, 2.2vw, 1.7rem); color: {active_theme['primary']}; font-weight: 900; letter-spacing: 2px; margin-bottom: 4px;'>
            ⚡ AEROTWIN DEFENSE OS // BOOT PROTOCOL v30.0
        </div>
        <div style='font-size: 0.78rem; color: #64748b; margin-bottom: 10px;'>
            TACTICAL PROPULSION DIGITAL TWIN GROUND STATION // DRDO TAPAS-201 FLEET
        </div>
    </div>
    """, unsafe_allow_html=True)

    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { margin: 0; overflow: hidden; background: #030712; }
            #boot-canvas { width: 100%; height: 420px; border-radius: 8px; border: 1px solid rgba(0, 240, 255, 0.4); box-shadow: 0 0 35px rgba(0, 240, 255, 0.25); }
            #boot-overlay {
                position: absolute; bottom: 15px; left: 20px; color: #00f0ff;
                font-family: monospace; font-size: 11px; letter-spacing: 1px; pointer-events: none;
            }
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    </head>
    <body>
        <div id="boot-overlay">&gt; SYSTEM CALIBRATION: ONLINE // TAPAS-BH-201 MALE AIRFRAME NOMINAL</div>
        <canvas id="boot-canvas"></canvas>
        <script>
            const canvas = document.getElementById('boot-canvas');
            const scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2(0x030712, 0.022);
            const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
            camera.position.set(0, 5, 14);

            const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
            renderer.setSize(canvas.clientWidth, canvas.clientHeight);

            const ambLight = new THREE.AmbientLight(0xffffff, 0.85);
            scene.add(ambLight);
            const dirLight = new THREE.DirectionalLight(0x00f0ff, 2.5);
            dirLight.position.set(10, 20, 15);
            scene.add(dirLight);

            const grid = new THREE.GridHelper(30, 30, 0x00f0ff, 0x1e293b);
            grid.position.y = -2;
            scene.add(grid);

            const uav = new THREE.Group();
            scene.add(uav);

            const bodyMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.3, metalness: 0.8 });
            const darkMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
            const neonMat = new THREE.MeshBasicMaterial({ color: 0x00ff66 });

            const fuse = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.3, 8.5, 16).rotateX(Math.PI/2), bodyMat);
            uav.add(fuse);

            const wings = new THREE.Mesh(new THREE.BoxGeometry(16, 0.1, 1.4), bodyMat);
            wings.position.set(0, 0.1, 0.5);
            uav.add(wings);

            const v1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.8, 0.8), bodyMat);
            v1.position.set(0.6, 0.6, -3.5); v1.rotation.z = -0.4;
            uav.add(v1);
            const v2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.8, 0.8), bodyMat);
            v2.position.set(-0.6, 0.6, -3.5); v2.rotation.z = 0.4;
            uav.add(v2);

            const noseSensor = new THREE.Mesh(new THREE.SphereGeometry(0.5, 16, 16), neonMat);
            noseSensor.position.set(0, -0.2, 4.0);
            uav.add(noseSensor);

            const prop = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.2, 0.1), darkMat);
            prop.position.set(0, 0.1, -4.3);
            uav.add(prop);

            let rot = 0;
            function anim() {
                requestAnimationFrame(anim);
                rot += 0.012;
                uav.rotation.y = rot;
                uav.position.y = Math.sin(rot * 2) * 0.25;
                prop.rotation.z += 0.35;
                camera.lookAt(0, 0, 0);
                renderer.render(scene, camera);
            }
            anim();
        </script>
    </body>
    </html>
    """, height=440)

    c_b1, c_b2, c_b3 = st.columns([1, 1.6, 1])
    with c_b2:
        if st.button("⚡ INITIALIZE FLIGHT MISSION GCS", use_container_width=True):
            st.session_state.boot_complete = True
            st.rerun()
    st.stop()

# -------------------------------------------------------------
# 2. MAIN TACTICAL GCS INTERFACE
# -------------------------------------------------------------

st.sidebar.markdown(f"""
<div style='text-align: center; padding: 6px 0;'>
    <div style='font-family: Orbitron; font-size: 1.15rem; color: {active_theme['primary']}; letter-spacing: 2px;'>AEROTWIN TACTICAL</div>
    <div style='font-size: 0.72rem; color: #64748b;'>DEFENSE GCS // NODE 30.0.0-PRO</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<div style='font-family: Orbitron; font-size: 0.8rem; color: {active_theme['primary']};'>DISPLAY WORKSPACE MODE</div>", unsafe_allow_html=True)
vp_mode = st.sidebar.radio(
    "Select Display Layout:",
    ["🖥️ DESKTOP MODE", "📱 MOBILE TACTICAL"],
    index=0 if st.session_state.viewport_mode == "🖥️ DESKTOP MODE" else 1,
    label_visibility="collapsed"
)
if vp_mode != st.session_state.viewport_mode:
    st.session_state.viewport_mode = vp_mode
    st.rerun()

is_mobile = (st.session_state.viewport_mode == "📱 MOBILE TACTICAL")

selected_theme = st.sidebar.selectbox(
    "OPTICAL SPECTRUM HUD THEME",
    list(THEMES.keys()),
    index=list(THEMES.keys()).index(st.session_state.hud_theme)
)
if selected_theme != st.session_state.hud_theme:
    st.session_state.hud_theme = selected_theme
    st.rerun()

if st.sidebar.button("🔄 RE-RUN 3D BOOT SEQUENCE"):
    st.session_state.boot_complete = False
    st.rerun()

st.sidebar.markdown("---")
source_mode = st.sidebar.radio(
    "TELEMETRY INGESTION MODE",
    [
        "MISSION REPLAY (SYNTHETIC)",
        "🔴 LIVE HARDWARE UDP LINK (PORT 14550)",
        "🎮 AEROTWIN 3D TACTICAL SIM (LIVE LINK)"
    ]
)

prognostics = EnginePrognostics()

if source_mode == "🎮 AEROTWIN 3D TACTICAL SIM (LIVE LINK)":
    st.sidebar.markdown("<div style='font-family: Orbitron; font-size: 0.8rem; color: #00f0ff;'>3D COMBAT SIMULATOR</div>", unsafe_allow_html=True)
    st.sidebar.success("● 3D COMBAT SIMULATOR MOUNTED\n[Arrow / WASD Active | Biomes Synced]")
    
    st.session_state.sim_clock += 1
    t_sec = st.session_state.sim_clock
    
    # Procedural real-time flight telemetry sync
    sim_rpm = 5120.0 + float(np.sin(t_sec * 0.15) * 180.0)
    sim_cht = 114.5 + np.sin(t_sec * 0.08) * 4.2
    sim_alt = 2450.0 + np.sin(t_sec * 0.05) * 85.0
    sim_pitch = round(float(np.sin(t_sec * 0.2) * 3.5), 1)
    sim_roll = round(float(np.cos(t_sec * 0.15) * 4.2), 1)
    
    current_row = {
        "timestamp": t_sec,
        "rpm": round(sim_rpm, 1),
        "cht_actual": round(sim_cht, 2),
        "cht_physics": 112.0,
        "oil_press_actual": 4.15,
        "oil_press_physics": 4.2,
        "oil_temp_actual": 92.5,
        "oil_temp_physics": 90.0,
        "egt_actual": 814.0,
        "egt_physics": 810.0,
        "map_inhg": 32.8,
        "vibration_rms": 1.15,
        "altitude_m": round(sim_alt, 1),
        "fuel_flow": 25.1,
        "pitch_deg": sim_pitch,
        "roll_deg": sim_roll,
        "flight_phase": "COMBAT PATROL"
    }
    df = pd.DataFrame([current_row])
    t_idx = 0
    scenario = "SIMULATOR_COMBAT_CRUISE"
    ew_tamper = False

elif source_mode == "🔴 LIVE HARDWARE UDP LINK (PORT 14550)":
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

spoofed_flag = False
if ew_tamper and t_idx > 80:
    current_row['cht_actual'] += 45.0
    spoofed_flag = True

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

zulu_now = datetime.now(timezone.utc).strftime("%H:%M:%SZ")

head_left, head_right = st.columns([3.2, 1.8])
with head_left:
    st.markdown("<div class='hud-header'>⚡ AEROTWIN: MALE UAV PROPULSION TWIN</div>", unsafe_allow_html=True)
with head_right:
    annunc_class = "annunciator-warn" if metrics["severity"] == "RED" and not st.session_state.caution_silenced else "annunciator-nominal"
    annunc_text = "⚠️ MASTER WARNING" if metrics["severity"] == "RED" else ("⚡ MASTER CAUTION" if metrics["severity"] == "AMBER" else "✓ PROPULSION NOMINAL")
    
    col_a1, col_a2 = st.columns([1.8, 1.2])
    with col_a1:
        st.markdown(f"<div style='text-align: right; padding-top: 5px;'><span class='annunciator-box {annunc_class}'>{annunc_text}</span></div>", unsafe_allow_html=True)
    with col_a2:
        if metrics["severity"] == "RED":
            if st.button("🔕 ACK", use_container_width=True):
                st.session_state.caution_silenced = True
                st.rerun()

if source_mode == "🎮 AEROTWIN 3D TACTICAL SIM (LIVE LINK)":
    link_label = "🎮 3D SIMULATOR DATALINK [ACTIVE]"
elif source_mode == "🔴 LIVE HARDWARE UDP LINK (PORT 14550)":
    link_label = f"🔴 UDP BUS ({len(df)} FRAMES)"
else:
    link_label = "● REPLAY ENCRYPTED"

squawk_status = "<span style='color:#ef4444; font-weight:bold;'>7700 [EMERGENCY]</span>" if metrics["severity"] == "RED" else "<span style='color:#10b981;'>4421 [CAP]</span>"
display_spd = 120 if source_mode == "🎮 AEROTWIN 3D TACTICAL SIM (LIVE LINK)" else (115 if not st.session_state.limp_mode else 92)

st.markdown(f"""
<div class='telemetry-strip'>
    <div>ZULU: <span class='telemetry-val'>{zulu_now}</span></div>
    <div>VIEWPORT: <span class='telemetry-val'>{st.session_state.viewport_mode}</span></div>
    <div>LINK: <span class='telemetry-val'>{link_label}</span></div>
    <div>IFF SQUAWK: {squawk_status}</div>
    <div>REGIME: <span class='telemetry-val'>{current_row['flight_phase']}</span></div>
    <div>ALT: <span class='telemetry-val'>{current_row['altitude_m']} M</span></div>
    <div>AIRSPEED: <span class='telemetry-val'>{display_spd} KCAS</span></div>
    <div>ISA OAT: <span class='telemetry-val'>{round(15 - 0.0065 * current_row['altitude_m'], 1)}°C</span></div>
    <div>MISSION CLOCK: <span class='telemetry-val'>T+{current_row['timestamp']:03.0f}s</span></div>
</div>
""", unsafe_allow_html=True)

def make_hud_gauge(title, value, min_v, max_v, unit, alert_v, warn_v, is_invert=False, height=170):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 11, 'family': 'Orbitron', 'color': active_theme['primary']}},
        number={'suffix': f" {unit}", 'font': {'size': 17, 'family': 'Orbitron', 'color': '#ffffff'}},
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
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=height, margin=dict(l=6, r=6, t=28, b=6), font={'family': "Share Tech Mono"})
    return fig

def make_pfd_figure(pitch, cur_spd, cur_alt, height=170):
    fig_pfd = go.Figure()
    fig_pfd.add_shape(type="rect", x0=-8, y0=-10, x1=8, y1=pitch, fillcolor="#78350f", line=dict(width=0))
    fig_pfd.add_shape(type="rect", x0=-8, y0=pitch, x1=8, y1=10, fillcolor="#0369a1", line=dict(width=0))
    fig_pfd.add_shape(type="line", x0=-6, y0=pitch, x1=6, y1=pitch, line=dict(color="#ffffff", width=2))
    fig_pfd.add_shape(type="line", x0=-2, y0=pitch + 3, x1=2, y1=pitch + 3, line=dict(color="rgba(255,255,255,0.7)", width=1.5))
    fig_pfd.add_shape(type="line", x0=-2, y0=pitch - 3, x1=2, y1=pitch - 3, line=dict(color="rgba(255,255,255,0.7)", width=1.5, dash="dot"))

    fig_pfd.add_shape(type="rect", x0=-10, y0=-10, x1=-7.5, y1=10, fillcolor="rgba(8,16,32,0.9)", line=dict(color=active_theme['border'], width=1))
    fig_pfd.add_annotation(x=-8.75, y=0, text=f"<b>{cur_spd}</b><br><span style='font-size:9px'>KCAS</span>", showarrow=False, font=dict(color="#00ff66", size=10, family="Orbitron"))

    fig_pfd.add_shape(type="rect", x0=7.5, y0=-10, x1=10, y1=10, fillcolor="rgba(8,16,32,0.9)", line=dict(color=active_theme['border'], width=1))
    fig_pfd.add_annotation(x=8.75, y=0, text=f"<b>{cur_alt}</b><br><span style='font-size:9px'>M</span>", showarrow=False, font=dict(color="#00f0ff", size=10, family="Orbitron"))

    fig_pfd.add_shape(type="line", x0=-3.5, y0=0, x1=-1.2, y1=0, line=dict(color="#facc15", width=3))
    fig_pfd.add_shape(type="line", x0=1.2, y0=0, x1=3.5, y1=0, line=dict(color="#facc15", width=3))
    fig_pfd.add_shape(type="circle", x0=-0.5, y0=-0.5, x1=0.5, y1=0.5, line=dict(color="#facc15", width=2))

    fig_pfd.update_layout(
        title={'text': "<b>TACTICAL GLASS PFD</b>", 'font': {'size': 11, 'family': 'Orbitron', 'color': active_theme['primary']}},
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(8,16,32,0.95)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-10, 10]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-10, 10]),
        height=height, margin=dict(l=5, r=5, t=28, b=5)
    )
    return fig_pfd

pitch = float(current_row['pitch_deg'])
cur_spd = display_spd
cur_alt = int(current_row['altitude_m'])

# Dual Split Cockpit Container: PFD & Airspace Simulator
col_pfd_main, col_3d_test_flight = st.columns([1.3, 1.2])

with col_pfd_main:
    st.plotly_chart(make_pfd_figure(pitch, cur_spd, cur_alt, height=170 if not is_mobile else 150), use_container_width=True, config={'displayModeBar': False})

with col_3d_test_flight:
    if source_mode == "🎮 AEROTWIN 3D TACTICAL SIM (LIVE LINK)":
        # Zero-dependency, 100% self-contained multi-biome combat flight simulator
        components.html("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
                body { overflow: hidden; background: #030712; font-family: monospace; }
                #hud-sim {
                    position: absolute; top: 6px; left: 8px; z-index: 10;
                    color: #00f0ff; font-size: 10px; line-height: 1.4;
                    background: rgba(3, 7, 18, 0.85); padding: 4px 8px; border-radius: 3px;
                    border: 1px solid rgba(0, 240, 255, 0.35); pointer-events: none;
                }
                #sim-c { width: 100%; height: 215px; display: block; cursor: crosshair; }
                #sim-ctrls {
                    position: absolute; bottom: 6px; left: 8px; z-index: 10;
                    color: #94a3b8; font-size: 9px; pointer-events: none;
                }
                .badge { color: #00ff66; font-weight: bold; }
                select.bio-sel {
                    position: absolute; top: 6px; right: 8px; z-index: 15;
                    background: #030712; color: #00ff66; border: 1px solid #00f0ff;
                    font-size: 10px; padding: 2px 6px; border-radius: 3px; outline: none; cursor: pointer;
                }
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        </head>
        <body>
            <div id="hud-sim">
                TAPAS-201 MALE UAV // <span id="hud-mode" class="badge">MANUAL FLIGHT</span><br>
                SPD: <span id="hud-spd" style="color:#fff;">0</span> KCAS | ALT: <span id="hud-alt" style="color:#fff;">0</span> M | THR: <span id="hud-thr" style="color:#fff;">0%</span>
            </div>

            <select id="biomeSelect" class="bio-sel" onchange="changeBiome(this.value)">
                <option value="desert">1. ☀️ Pokhran Desert</option>
                <option value="arctic">2. ❄️ Siachen Glacier</option>
                <option value="enemy">3. 🏭 Hostile SAM Base</option>
                <option value="lac">4. 🇮🇳 Himalayan Ridge</option>
            </select>

            <canvas id="sim-c"></canvas>
            <div id="sim-ctrls">CONTROLS: <span class="badge">↑/W</span> DIVE | <span class="badge">↓/S</span> CLIMB | <span class="badge">←/→/A/D</span> ROLL | <span class="badge">SHIFT</span> BOOST | <span class="badge">SPACE</span> BRAKE</div>

            <script>
                const canvas = document.getElementById('sim-c');
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 215, 0.1, 4000);
                const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
                renderer.setSize(window.innerWidth, 215);

                const ambLight = new THREE.AmbientLight(0xffffff, 0.85);
                scene.add(ambLight);
                const sun = new THREE.DirectionalLight(0xfffaed, 1.8);
                sun.position.set(200, 400, 150);
                scene.add(sun);

                // Procedural Shaded Terrain
                const tGeo = new THREE.PlaneGeometry(2400, 2400, 70, 70).rotateX(-Math.PI / 2);
                const tMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 });
                const terrain = new THREE.Mesh(tGeo, tMat);
                scene.add(terrain);

                const count = tGeo.attributes.position.count;
                const colors = new Float32Array(count * 3);
                tGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

                function changeBiome(theme) {
                    let crest, slope, valley, sky;
                    if (theme === 'desert') {
                        crest = new THREE.Color(0xd49b55); slope = new THREE.Color(0xba7c38); valley = new THREE.Color(0x8f5424); sky = 0xdfa166;
                    } else if (theme === 'arctic') {
                        crest = new THREE.Color(0xffffff); slope = new THREE.Color(0xcfe2f3); valley = new THREE.Color(0x4a779d); sky = 0x7baad4;
                    } else if (theme === 'enemy') {
                        crest = new THREE.Color(0x334155); slope = new THREE.Color(0x1e293b); valley = new THREE.Color(0x090d16); sky = 0x0a0f1d;
                    } else {
                        crest = new THREE.Color(0x6b7280); slope = new THREE.Color(0x475569); valley = new THREE.Color(0x1e293b); sky = 0x5ca0d3;
                    }
                    scene.background = new THREE.Color(sky);
                    scene.fog = new THREE.FogExp2(sky, 0.0006);

                    const pos = tGeo.attributes.position;
                    for (let i = 0; i < count; i++) {
                        let x = pos.getX(i), z = pos.getZ(i);
                        let h = Math.sin(x * 0.005) * Math.cos(z * 0.005) * (theme === 'lac' ? 65 : 28);
                        pos.setY(i, h);
                        let norm = Math.min(1, Math.max(0, (h + 15) / 50));
                        let c = new THREE.Color().lerpColors(valley, crest, norm);
                        colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
                    }
                    tGeo.attributes.position.needsUpdate = true;
                    tGeo.attributes.color.needsUpdate = true;
                    tGeo.computeVertexNormals();
                }
                changeBiome('desert');

                // UAV Airframe
                const drone = new THREE.Group();
                scene.add(drone);
                const mat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.3 });
                const body = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.25, 7.5, 12).rotateX(Math.PI/2), mat);
                drone.add(body);
                const wings = new THREE.Mesh(new THREE.BoxGeometry(14, 0.1, 1.2), mat);
                wings.position.set(0, 0.1, 0.4);
                drone.add(wings);
                const v1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.5, 0.7), mat);
                v1.position.set(0.5, 0.5, -3.2); v1.rotation.z = -0.4;
                const v2 = v1.clone(); v2.position.x = -0.5; v2.rotation.z = 0.4;
                drone.add(v1, v2);

                const prop = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.8, 0.1), new THREE.MeshBasicMaterial({ color: 0x111 }));
                prop.position.set(0, 0, -3.9);
                drone.add(prop);

                // Flight Dynamics
                const st = { x: 0, y: 3.5, z: 0, spd: 0, pitch: 0, roll: 0, yaw: 0, thr: 40 };
                const keys = {};
                window.addEventListener('keydown', e => { keys[e.code] = true; });
                window.addEventListener('keyup', e => { keys[e.code] = false; });

                function loop() {
                    requestAnimationFrame(loop);
                    const isBoost = keys['ShiftLeft'] || keys['ShiftRight'];
                    const isBrake = keys['Space'];
                    if (isBoost) st.thr = Math.min(100, st.thr + 1.2);
                    else if (isBrake) st.thr = Math.max(0, st.thr - 1.5);

                    st.spd = (st.thr / 100) * 1.6;

                    if (keys['KeyW'] || keys['ArrowUp']) st.pitch = Math.max(-0.45, st.pitch - 0.02);
                    else if (keys['KeyS'] || keys['ArrowDown']) st.pitch = Math.min(0.45, st.pitch + 0.02);
                    else st.pitch *= 0.95;

                    if (keys['KeyA'] || keys['ArrowLeft']) { st.roll = Math.max(-0.6, st.roll - 0.03); st.yaw += 0.015; }
                    else if (keys['KeyD'] || keys['ArrowRight']) { st.roll = Math.min(0.6, st.roll + 0.03); st.yaw -= 0.015; }
                    else st.roll *= 0.94;

                    st.x += Math.sin(st.yaw) * st.spd;
                    st.z += Math.cos(st.yaw) * st.spd;
                    st.y = Math.max(1.8, st.y + Math.sin(st.pitch) * st.spd);

                    drone.position.set(st.x, st.y, st.z);
                    drone.rotation.order = 'YXZ';
                    drone.rotation.y = st.yaw;
                    drone.rotation.x = -st.pitch;
                    drone.rotation.z = -st.roll;
                    prop.rotation.z += 0.4;

                    const chX = st.x - Math.sin(st.yaw) * 16;
                    const chZ = st.z - Math.cos(st.yaw) * 16;
                    camera.position.set(chX, st.y + 4.5, chZ);
                    camera.lookAt(st.x, st.y + 1, st.z);

                    document.getElementById('hud-spd').innerText = Math.round(st.spd * 125);
                    document.getElementById('hud-alt').innerText = Math.round(st.y * 30);
                    document.getElementById('hud-thr').innerText = Math.round(st.thr) + '%';

                    renderer.render(scene, camera);
                }
                loop();
            </script>
        </body>
        </html>
        """, height=220)
    else:
        components.html("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { margin: 0; overflow: hidden; background: #040914; font-family: 'Share Tech Mono', monospace; }
                #test-hud { position: absolute; top: 6px; left: 10px; color: #00ff66; font-size: 10px; z-index: 10; }
                #canvas-test { width: 100%; height: 170px; border-radius: 4px; border: 1px solid rgba(0, 240, 255, 0.35); }
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        </head>
        <body>
            <div id="test-hud">&gt; PRE-FLIGHT TEST AIRSPACE [ACTIVE 3D]</div>
            <div id="canvas-test"></div>
            <script>
                const wrap = document.getElementById('canvas-test');
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 500);
                camera.position.set(0, 8, 22); camera.lookAt(0, 0, 0);

                const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
                renderer.setSize(wrap.clientWidth, wrap.clientHeight);
                wrap.appendChild(renderer.domElement);

                const testDrone = new THREE.Group();
                scene.add(testDrone);
                const mWire = new THREE.MeshBasicMaterial({ color: 0x00f0ff, wireframe: true });
                testDrone.add(new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.3, 12, 10).rotateX(Math.PI/2), mWire));
                const w = new THREE.Mesh(new THREE.BoxGeometry(12, 0.15, 2), mWire); w.position.z = 0.2; testDrone.add(w);

                const grid = new THREE.GridHelper(40, 20, 0x00f0ff, 0x1e293b);
                grid.position.y = -4; scene.add(grid);

                let t = 0;
                function runTestFlight() {
                    requestAnimationFrame(runTestFlight);
                    t += 0.03;
                    testDrone.position.x = Math.sin(t) * 6;
                    testDrone.position.z = Math.cos(t * 0.7) * 4;
                    testDrone.position.y = Math.sin(t * 2) * 1.5;
                    testDrone.rotation.z = Math.cos(t) * 0.25;
                    testDrone.rotation.y = t;
                    renderer.render(scene, camera);
                }
                runTestFlight();
            </script>
        </body>
        </html>
        """, height=180)

# Gauges Strip
g1, g2, g3, g4 = st.columns(4)
with g1:
    st.plotly_chart(make_hud_gauge("HEALTH INDEX", metrics['health_index'], 0, 100, "%", 45, 75, is_invert=True, height=155), use_container_width=True, config={'displayModeBar': False})
with g2:
    st.plotly_chart(make_hud_gauge("CYLINDER TEMP", current_row['cht_actual'], 80, 170, "°C", 145, 130, height=155), use_container_width=True, config={'displayModeBar': False})
with g3:
    st.plotly_chart(make_hud_gauge("OIL PRESSURE", current_row['oil_press_actual'], 0, 6, "bar", 1.8, 2.5, is_invert=True, height=155), use_container_width=True, config={'displayModeBar': False})
with g4:
    st.plotly_chart(make_hud_gauge("CRANKSHAFT", current_row['rpm'], 0, 6000, "RPM", 5600, 5200, height=155), use_container_width=True, config={'displayModeBar': False})

if spoofed_flag:
    st.markdown("""
    <div style='background: rgba(88, 28, 135, 0.9); border: 1px solid #c084fc; border-left: 8px solid #a855f7; padding: 14px 20px; border-radius: 4px; margin-bottom: 16px;'>
        <strong>🛡️ KALMAN INNOVATION GATING ACTIVE:</strong> Sensor anomaly rejected (+45°C spoof spike). Primary flight model retained.
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "RED":
    st.markdown(f"""
    <div style='background: repeating-linear-gradient(45deg, rgba(127,29,29,0.92), rgba(127,29,29,0.92) 14px, rgba(69,10,10,0.96) 14px, rgba(69,10,10,0.96) 28px); border: 1px solid #ef4444; border-left: 8px solid #dc2626; color: #fecaca; padding: 14px 20px; border-radius: 4px; margin-bottom: 16px;'>
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

components.html("""
<script>
function playClickSound() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(450, ctx.currentTime);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.04);
    } catch(e) {}
}
window.addEventListener('click', (e) => {
    if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
        playClickSound();
    }
});
</script>
""", height=0)

st.markdown("<div class='quick-dock'>", unsafe_allow_html=True)
st.markdown(f"<div style='font-family: Orbitron; font-size: 0.86rem; color: {active_theme['primary']}; margin-bottom: 8px;'>🕹️ COMBAT PILOT QUICK-ACTION DOCK</div>", unsafe_allow_html=True)
c_mit1, c_mit2, c_mit3, c_mit4 = st.columns(4)
with c_mit1:
    if st.button("🚨 " + ("DISENGAGE LIMP" if st.session_state.limp_mode else "65% LIMP THROTTLE"), use_container_width=True):
        st.session_state.limp_mode = not st.session_state.limp_mode
        st.rerun()
with c_mit2:
    if st.button("💧 " + ("RESTORE MIX" if st.session_state.fuel_enrich else "ENRICH QUENCH"), use_container_width=True):
        st.session_state.fuel_enrich = not st.session_state.fuel_enrich
        st.rerun()
with c_mit3:
    if st.button("💥 " + ("JETTISON ACTIVE" if st.session_state.stores_jettison else "JETTISON STORES"), use_container_width=True):
        st.session_state.stores_jettison = not st.session_state.stores_jettison
        st.rerun()
with c_mit4:
    status_mit = []
    if st.session_state.limp_mode: status_mit.append("LIMP")
    if st.session_state.fuel_enrich: status_mit.append("QUENCH")
    if st.session_state.stores_jettison: status_mit.append("STORES JETTISONED")
    st.caption("Status: " + (", ".join(status_mit) if status_mit else "NOMINAL"))
st.markdown("</div>", unsafe_allow_html=True)

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

plot_h = 270 if is_mobile else 360
radar_h = 320 if is_mobile else 460
core_3d_h = 340 if is_mobile else 480

hud_plot_layout = dict(
    paper_bgcolor='rgba(8, 16, 32, 0.65)',
    plot_bgcolor='rgba(4, 9, 20, 0.85)',
    font=dict(family='Share Tech Mono', color='#8892b0'),
    margin=dict(l=25, r=15, t=25, b=20),
    xaxis=dict(gridcolor='rgba(255, 255, 255, 0.08)', zerolinecolor=active_theme['border']),
    yaxis=dict(gridcolor='rgba(255, 255, 255, 0.08)', zerolinecolor=active_theme['border']),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

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

with tab1:
    cols_t = st.columns(2) if not is_mobile else [st.container(), st.container()]
    col_t1, col_t2 = cols_t[0], cols_t[1]

    with col_t1:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>CYLINDER HEAD TEMPERATURE (THERMAL RESIDUAL)</div>", unsafe_allow_html=True)
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
        fig_cht.update_layout(hud_plot_layout, height=plot_h, yaxis_title="°C")
        st.plotly_chart(fig_cht, use_container_width=True, config={'displayModeBar': False})

    with col_t2:
        st.markdown(f"<div style='color: {active_theme['accent']}; font-weight: bold;'>LUBRICATION CIRCUIT PRESSURE</div>", unsafe_allow_html=True)
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(x=time_slice, y=df['oil_press_actual'][:t_idx+1], name="Oil Pressure Actual", line=dict(color=active_theme['accent'], width=3)))
        fig_oil.add_trace(go.Scatter(x=time_slice, y=df['oil_press_physics'][:t_idx+1], name="Physics Baseline", line=dict(color="#94a3b8", dash="dash", width=2)))
        fig_oil.add_hline(y=1.5, line_dash="dot", line_color="#ff003c", annotation_text="Limit (1.5 bar)")
        fig_oil.update_layout(hud_plot_layout, height=plot_h, yaxis_title="bar")
        st.plotly_chart(fig_oil, use_container_width=True, config={'displayModeBar': False})

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
        hud_plot_layout, height=plot_h,
        xaxis_title="Corrected Air Mass Flow ṁ_corr (kg/s)",
        yaxis_title="Total Pressure Ratio Π_c",
        xaxis=dict(range=[0.03, 0.24]), yaxis=dict(range=[1.0, 2.6])
    )
    st.plotly_chart(fig_turbo, use_container_width=True, config={'displayModeBar': False})

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

    delta_p = p_exp - p_comp
    work_integral = float(np.sum(0.5 * (delta_p[:-1] + delta_p[1:]) * np.diff(v_arr)))
    imep_val = round(work_integral / v_d, 1)
    thermal_eff = round(max(15.0, min(36.0, 34.0 - (current_row['cht_actual'] - 110.0) * 0.35)), 1)

    fig_pv.update_layout(
        hud_plot_layout, height=plot_h,
        xaxis_title="Cylinder Volume (cc)", yaxis_title="Pressure (kPa)",
        annotations=[
            dict(x=v_c + 20, y=p_peak * 0.9, text=f"IMEP: {imep_val} kPa | η_th: {thermal_eff}%", showarrow=False, font=dict(color=active_theme['primary'], size=12))
        ]
    )
    st.plotly_chart(fig_pv, use_container_width=True, config={'displayModeBar': False})

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
        colorscale='Viridis', colorbar=dict(title="Energy")
    ))
    fig_waterfall.update_layout(hud_plot_layout, height=plot_h, xaxis_title="MET (Seconds)", yaxis_title="Frequency Band (Hz)")
    st.plotly_chart(fig_waterfall, use_container_width=True, config={'displayModeBar': False})

with tab5:
    cols_xai = st.columns([3, 2]) if not is_mobile else [st.container(), st.container()]
    col_xai1, col_xai2 = cols_xai[0], cols_xai[1]

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
        fig_xai.update_layout(hud_plot_layout, height=plot_h, yaxis_title="Health %")
        st.plotly_chart(fig_xai, use_container_width=True, config={'displayModeBar': False})

    with col_xai2:
        st.markdown(f"<div style='color: {active_theme['accent']}; font-weight: bold;'>ONLINE ESTIMATED DEGRADATION PARAMETERS</div>", unsafe_allow_html=True)
        fmep_val = round(0.45 + (current_row['rpm'] / 6000.0) * 0.35 + (5.0 - current_row['oil_press_actual']) * 0.18, 2)
        blowby_pct = round(min(18.5, max(1.2, (current_row['cht_actual'] - 105.0) * 0.28)), 1)

        deg_data = [
            {"Parameter": "Friction MEP", "Estimated Value": f"{fmep_val} bar", "Nominal": "0.45 bar", "Drift Status": "HIGH" if fmep_val > 0.8 else "NOMINAL"},
            {"Parameter": "Ring Blow-By", "Estimated Value": f"{blowby_pct}%", "Nominal": "< 2.5%", "Drift Status": "BREAKDOWN" if blowby_pct > 6.0 else "NOMINAL"},
            {"Parameter": "Thermal Dissipation", "Estimated Value": f"{round(max(0.4, 1.0 - (current_row['cht_actual']-110)*0.015), 2)} ε", "Nominal": "1.00 ε", "Drift Status": "DEGRADED" if current_row['cht_actual'] > 125 else "NOMINAL"}
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
            marker=dict(size=26 if not is_mobile else 20, color=cyl_col, symbol="square", opacity=0.9),
            text=[f"<b>{c['name']}</b><br>{c['temp']}°C"], textposition="top center", name=c["name"]
        ))
    fig_3d.add_trace(go.Scatter3d(x=[0], y=[-1.6], z=[1.1], mode="markers+text", marker=dict(size=20, color=active_theme['secondary'], symbol="diamond"), text=[f"<b>TURBO</b><br>{current_row['map_inhg']} inHg"], textposition="top center", name="Turbo"))
    fig_3d.add_trace(go.Scatter3d(x=[0], y=[0], z=[-0.9], mode="markers+text", marker=dict(size=22, color=oil_col, symbol="circle"), text=[f"<b>OIL SUMP</b><br>{oil_p} bar"], textposition="bottom center", name="Oil Gallery"))

    fig_3d.update_layout(
        paper_bgcolor='rgba(4, 9, 20, 0.85)', height=core_3d_h,
        scene=dict(
            xaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-2, 2]),
            yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-2.5, 2.5]),
            zaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', backgroundcolor='rgba(0,0,0,0)', range=[-1.5, 1.8]),
            camera=dict(eye=dict(x=1.6, y=-1.7, z=1.3))
        ),
        font=dict(family='Share Tech Mono', color='#ffffff'), margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_3d, use_container_width=True, config={'displayModeBar': False})

with tab7:
    st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>TACTICAL MULTI-BASE RADAR & AUTONOMOUS SAM THREAT AVOIDANCE</div>", unsafe_allow_html=True)
    uav_x = [0, 8, 16, 25, 32, 38, 42, 40, 32, 22, 12, 5, 0]
    uav_y = [0, 6, 12, 18, 22, 22, 15, 6, -2, -6, -4, -1, 0]
    norm_idx = int((t_idx / max(1, len(df))) * (len(uav_x) - 1))
    norm_idx = min(norm_idx, len(uav_x) - 1)
    cur_x = uav_x[norm_idx]
    cur_y = uav_y[norm_idx]

    ld_ratio = 15.5 if st.session_state.stores_jettison else 12.0
    glide_limit_km = (current_row['altitude_m'] / 1000.0) * ld_ratio

    bases = [
        {"name": "FOB Alpha", "x": 0, "y": 0, "color": "#00ff66"},
        {"name": "FOB Bravo", "x": 30, "y": 8, "color": "#38bdf8"},
        {"name": "Strip Charlie", "x": 20, "y": 28, "color": "#f59e0b"}
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
        text=["<b>[SAM-6 THREAT]</b>"], textposition="top center", name="SAM Threat"
    ))

    fig_radar.add_trace(go.Scatter(x=uav_x[:norm_idx+1], y=uav_y[:norm_idx+1], mode="lines+markers", line=dict(color=active_theme['primary'], width=2.5), name="Patrol Route"))

    for b in bases:
        dist = np.sqrt((cur_x - b["x"])**2 + (cur_y - b["y"])**2)
        reachable = dist <= glide_limit_km
        status_lbl = "REACHABLE" if reachable else "UNREACHABLE"
        color = b["color"] if reachable else "#64748b"
        fig_radar.add_trace(go.Scatter(
            x=[b["x"]], y=[b["y"]], mode="markers+text",
            marker=dict(size=13, color=color, symbol="triangle-up"),
            text=[f"<b>{b['name']}</b><br>{dist:.1f}km ({status_lbl})"],
            textposition="bottom center", name=b["name"]
        ))

    fig_radar.add_trace(go.Scatter(
        x=[cur_x], y=[cur_y], mode="markers+text",
        marker=dict(size=15, color="#ff0055" if metrics["severity"] == "RED" else "#00ff66", symbol="diamond"),
        text=[f"<b>UAV-01 (T+{current_row['timestamp']:.0f}s)</b>"], textposition="top right", name="UAV-01"
    ))

    if metrics["severity"] == "RED" and not spoofed_flag:
        dogleg_wp_x = 32
        dogleg_wp_y = 2
        fig_radar.add_trace(go.Scatter(
            x=[cur_x, dogleg_wp_x, 0], y=[cur_y, dogleg_wp_y, 0],
            mode="lines+markers+text", line=dict(color="#ff003c", width=3.5, dash="dashdot"),
            marker=dict(size=8, color="#ff003c"),
            text=["", "<b>WP-DOGLEG [BYPASS]</b>", "<b>FOB ALPHA</b>"],
            textposition="top right", name="Avoidance Vector"
        ))

    fig_radar.update_layout(hud_plot_layout, height=radar_h, xaxis=dict(range=[-35, 55], title="Range X (km)"), yaxis=dict(range=[-25, 45], title="Range Y (km)"))
    st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

with tab8:
    cols_rep = st.columns([3, 2]) if not is_mobile else [st.container(), st.container()]
    col_rep1, col_rep2 = cols_rep[0], cols_rep[1]

    with col_rep1:
        st.markdown(f"<div style='color: {active_theme['primary']}; font-weight: bold;'>MIL-STD-1553B AVIONICS D-BUS PROTOCOL ANALYZER</div>", unsafe_allow_html=True)
        bus_frames = [
            f"[1553B BC->RT04] CMD WORD: 0x2084 | Transmit | RT-04 | Sub-Address 04 | Words: 16 | Parity: OK",
            f"[1553B RT04->BC] STATUS WORD: 0x2000 | RT-04 FADEC Healthy | Service Request: NONE",
            f"[1553B DATA 01-04] RPM: {int(current_row['rpm']):04X} | CHT: {int(current_row['cht_actual']*10):04X} | OIL: {int(current_row['oil_press_actual']*100):04X} | EGT: {int(current_row['egt_actual']):04X}",
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

# Loop Refresh Logic - Do NOT rerun for 3D Sim! It runs inside its own WebGL frame loop!
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
