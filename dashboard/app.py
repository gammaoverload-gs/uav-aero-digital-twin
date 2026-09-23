import os
import sys
import time
import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine_physics import AeroPistonDigitalTwin  # type: ignore
from core.prognostics import EnginePrognostics  # type: ignore

st.set_page_config(
    page_title="AeroTwin Tactical GCS | Defense-Grade MALE UAV",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Military Tactical HUD Styling
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">

<style>
    .stApp {
        background: radial-gradient(circle at top right, #0d1b2a 0%, #050811 65%, #020408 100%);
        color: #e0e6ed;
        font-family: 'Share Tech Mono', monospace;
    }
    .hud-header {
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 3px;
        background: linear-gradient(90deg, #00f0ff, #7000ff, #00ff66);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.1rem;
        font-weight: 900;
        margin-bottom: 2px;
        text-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
    }
    .telemetry-strip {
        background: rgba(10, 20, 35, 0.85);
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-left: 6px solid #00f0ff;
        padding: 8px 16px;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.88rem;
        color: #79a8d7;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
    }
    .alert-banner-critical {
        background: rgba(80, 0, 15, 0.9);
        border: 1px solid #ff003c;
        border-left: 8px solid #ff003c;
        color: #ffb4c4;
        padding: 14px 20px;
        border-radius: 6px;
        margin-bottom: 18px;
        animation: pulseRed 2s infinite ease-in-out;
        box-shadow: 0 0 25px rgba(255, 0, 60, 0.35);
    }
    .alert-banner-nominal {
        background: rgba(0, 40, 25, 0.8);
        border: 1px solid #00ff66;
        border-left: 8px solid #00ff66;
        color: #a3f7bf;
        padding: 14px 20px;
        border-radius: 6px;
        margin-bottom: 18px;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.2);
    }
    .terminal-box {
        background: #020617;
        border: 1px solid #00f0ff;
        border-radius: 4px;
        padding: 12px;
        height: 250px;
        overflow-y: auto;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.82rem;
        color: #00ff66;
        line-height: 1.5;
        box-shadow: inset 0 0 15px rgba(0, 240, 255, 0.1);
    }
    .packet-hex {
        font-family: 'Share Tech Mono', monospace;
        background: rgba(5, 10, 20, 0.8);
        border: 1px solid rgba(0, 240, 255, 0.2);
        padding: 8px;
        border-radius: 4px;
        color: #38bdf8;
        font-size: 0.76rem;
        margin-top: 5px;
    }
    @keyframes pulseRed {
        0% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
        50% { box-shadow: 0 0 30px rgba(255, 0, 60, 0.75); }
        100% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
    }
</style>
""", unsafe_allow_html=True)

# State initialization
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
if "swarm_handover" not in st.session_state:
    st.session_state.swarm_handover = False

# Sidebar Controls
st.sidebar.markdown("""
<div style='text-align: center; padding: 5px 0;'>
    <div style='font-family: Orbitron; font-size: 1.15rem; color: #00f0ff; letter-spacing: 2px;'>AEROTWIN TACTICAL</div>
    <div style='font-size: 0.72rem; color: #64748b;'>DEFENSE TELEMETRY NODE // 7.0.0-PRO</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
scenario = st.sidebar.selectbox(
    "MISSION SCENARIO INJECTION",
    ["NOMINAL", "COOLING_FAILURE", "LUBRICATION_LOSS"],
    index=1
)

ew_tamper = st.sidebar.toggle("📡 Inject Electronic Warfare / Sensor Spoofing", value=False)
enable_voice = st.sidebar.checkbox("🔊 Voice HUD Announcements", value=True)

@st.cache_data
def load_telemetry(scen):
    twin = AeroPistonDigitalTwin()
    return twin.generate_mission_telemetry(total_seconds=200, fault_scenario=scen)

df = load_telemetry(scenario)
prognostics = EnginePrognostics()

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-family: Orbitron; font-size: 0.8rem; color: #00f0ff;'>SIMULATION STREAM CONTROLLER</div>", unsafe_allow_html=True)

col_p1, col_p2 = st.sidebar.columns(2)
if col_p1.button("▶ PLAY STREAM" if not st.session_state.is_playing else "⏸ PAUSE"):
    st.session_state.is_playing = not st.session_state.is_playing

if col_p2.button("🔄 RESTART"):
    st.session_state.t_idx = 0
    st.session_state.is_playing = False
    st.session_state.limp_mode = False
    st.session_state.fuel_enrich = False
    st.session_state.swarm_handover = False

st.session_state.t_idx = st.sidebar.slider(
    "Mission Elapsed Time (Seconds)",
    0, len(df) - 1,
    st.session_state.t_idx
)

t_idx = st.session_state.t_idx
current_row = df.iloc[t_idx].copy()

# EW Spoofing injection
spoofed_flag = False
if ew_tamper and t_idx > 80:
    current_row['cht_actual'] += 45.0
    spoofed_flag = True

# Human-In-The-Loop Countermeasure Modifiers
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

# Header Telemetry Strip
st.markdown("<div class='hud-header'>⚡ AEROTWIN: MALE UAV PROPULSION TWIN</div>", unsafe_allow_html=True)

st.markdown(f"""
<div class='telemetry-strip'>
    <div>SYSTEM: <span style='color: #00ff66;'>● SECURE TELEMETRY LINK</span></div>
    <div>MISSION REGIME: <b>{current_row['flight_phase']}</b></div>
    <div>ALTITUDE: <b>{current_row['altitude_m']} M</b></div>
    <div>AIRSPEED: <b>{115 if not st.session_state.limp_mode else 92} KCAS</b></div>
    <div>ISA OAT: <b>{round(15 - 0.0065 * current_row['altitude_m'], 1)}°C</b></div>
    <div>MISSION CLOCK: <b>T+{t_idx:03d}s</b></div>
</div>
""", unsafe_allow_html=True)

# Cockpit Gauges
g1, g2, g3, g4 = st.columns(4)

def make_hud_gauge(title, value, min_v, max_v, unit, alert_v, warn_v, is_invert=False):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 13, 'family': 'Orbitron', 'color': '#00f0ff'}},
        number={'suffix': f" {unit}", 'font': {'size': 20, 'family': 'Orbitron', 'color': '#ffffff'}},
        gauge={
            'axis': {'range': [min_v, max_v], 'tickwidth': 1, 'tickcolor': "#8892b0"},
            'bar': {'color': "#00f0ff", 'thickness': 0.25},
            'bgcolor': "rgba(10, 20, 35, 0.8)",
            'borderwidth': 1,
            'bordercolor': "rgba(0, 240, 255, 0.3)",
            'steps': [
                {'range': [min_v, warn_v] if not is_invert else [alert_v, max_v], 'color': 'rgba(0, 255, 102, 0.15)'},
                {'range': [warn_v, alert_v] if not is_invert else [warn_v, alert_v], 'color': 'rgba(255, 183, 3, 0.2)'},
                {'range': [alert_v, max_v] if not is_invert else [min_v, warn_v], 'color': 'rgba(255, 0, 60, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "#ff003c", 'width': 3},
                'thickness': 0.75,
                'value': alert_v
            }
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=175, margin=dict(l=15, r=15, t=30, b=15), font={'family': "Share Tech Mono"})
    return fig

with g1:
    st.plotly_chart(make_hud_gauge("HEALTH INDEX", metrics['health_index'], 0, 100, "%", 45, 75, is_invert=True), use_container_width=True)
with g2:
    st.plotly_chart(make_hud_gauge("CYLINDER TEMP (CHT)", current_row['cht_actual'], 80, 170, "°C", 145, 130), use_container_width=True)
with g3:
    st.plotly_chart(make_hud_gauge("OIL PRESSURE", current_row['oil_press_actual'], 0, 6, "bar", 1.8, 2.5, is_invert=True), use_container_width=True)
with g4:
    st.plotly_chart(make_hud_gauge("CRANKSHAFT TACHO", current_row['rpm'], 0, 6000, "RPM", 5600, 5200), use_container_width=True)

# Advisory Banner
if spoofed_flag:
    st.markdown("""
    <div style='background: rgba(88, 28, 135, 0.85); border: 1px solid #c084fc; border-left: 8px solid #a855f7; padding: 14px 20px; border-radius: 6px; margin-bottom: 18px;'>
        <strong>🛡️ KALMAN INNOVATION GATING ACTIVE:</strong> Sensor packet anomaly rejected.<br>
        <strong>Residual Verification:</strong> Gradient exceeds physical maximum (+45°C in 20ms). Telemetry isolated as sensor spoofing. Primary flight model retained.
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "RED":
    st.markdown(f"""
    <div class='alert-banner-critical'>
        <strong>⚠️ CRITICAL TACTICAL ADVISORY [AUTONOMOUS RETURN-TO-BASE RECOMMENDED]</strong><br>
        <strong>Fault Mode:</strong> {metrics['status']} &nbsp;|&nbsp; <strong>Root Cause:</strong> {metrics['alert_message']}<br>
        <strong>Remaining Flight Endurance (RUL):</strong> {metrics['rul_hours']} Hours
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "AMBER":
    st.markdown(f"""
    <div style='background: rgba(60, 40, 0, 0.75); border-left: 6px solid #ffb703; padding: 12px 18px; border-radius: 4px; margin-bottom: 18px; color: #ffe699;'>
        <strong>CAUTION [DEGRADED PROPULSION]:</strong> {metrics['status']} &nbsp;|&nbsp; {metrics['alert_message']}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class='alert-banner-nominal'>
        <strong>✓ ALL PROPULSION SUBSYSTEMS NOMINAL:</strong> Telemetry residuals aligned with physical model. Zero safety deviations.
    </div>
    """, unsafe_allow_html=True)

# Voice Audio Synthesizer
if enable_voice and metrics["severity"] == "RED" and st.session_state.last_voice_alert != "RED" and not spoofed_flag:
    st.session_state.last_voice_alert = "RED"
    components.html("""
    <script>
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        let msg = new SpeechSynthesisUtterance("Warning. Propulsion critical. Autonomous Return To Base vector active.");
        msg.rate = 1.05; msg.pitch = 0.85;
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, height=0)
elif metrics["severity"] != "RED":
    st.session_state.last_voice_alert = metrics["severity"]

# Pilot Countermeasure Station
st.markdown("<div style='font-family: Orbitron; font-size: 0.95rem; color: #00f0ff; margin-bottom: 8px;'>🕹️ TACTICAL PILOT MITIGATION & COUNTERMEASURES</div>", unsafe_allow_html=True)
c_mit1, c_mit2, c_mit3 = st.columns(3)
with c_mit1:
    if st.button("🚨 " + ("DISENGAGE LIMP-HOME" if st.session_state.limp_mode else "ENGAGE 65% LIMP-HOME THROTTLE")):
        st.session_state.limp_mode = not st.session_state.limp_mode
        st.rerun()
with c_mit2:
    if st.button("💧 " + ("RESTORE FUEL RATIO" if st.session_state.fuel_enrich else "ENRICH MIXTURE (CYLINDER QUENCH)")):
        st.session_state.fuel_enrich = not st.session_state.fuel_enrich
        st.rerun()
with c_mit3:
    status_mit = []
    if st.session_state.limp_mode: status_mit.append("LIMP-HOME ACTIVE (-800 RPM)")
    if st.session_state.fuel_enrich: status_mit.append("ENRICHED MIXTURE (-6°C CHT)")
    st.caption("Active Mitigations: " + (", ".join(status_mit) if status_mit else "NONE (NOMINAL CRUISE)"))

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 SENSOR BUS & EKF FILTER",
    "🎯 XAI ROOT CAUSE & SWARM",
    "🛩️ DEAD-STICK GLIDE & RUL",
    "🧊 3D PROPULSION CORE",
    "🗺️ RADAR & VECTOR DIVERSION",
    "📡 STANAG 4586 & TERMINAL"
])

hud_plot_layout = dict(
    paper_bgcolor='rgba(10, 20, 35, 0.4)',
    plot_bgcolor='rgba(7, 14, 25, 0.7)',
    font=dict(family='Share Tech Mono', color='#8892b0'),
    margin=dict(l=35, r=20, t=30, b=25),
    xaxis=dict(gridcolor='rgba(0, 240, 255, 0.1)', zerolinecolor='rgba(0, 240, 255, 0.2)'),
    yaxis=dict(gridcolor='rgba(0, 240, 255, 0.1)', zerolinecolor='rgba(0, 240, 255, 0.2)'),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>CYLINDER HEAD TEMPERATURE: RAW SENSOR VS. EKF FILTER VS. TWIN</div>", unsafe_allow_html=True)
        time_slice = df['timestamp'][:t_idx+1]
        raw_cht = df['cht_actual'][:t_idx+1]
        
        # Extended Kalman Filter (EKF) smoothed estimate + 2-sigma confidence band
        ekf_cht = raw_cht.rolling(window=4, min_periods=1).mean()
        sigma_2 = 1.4

        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(
            x=time_slice, y=ekf_cht + sigma_2, mode='lines',
            line=dict(width=0), showlegend=False
        ))
        fig_cht.add_trace(go.Scatter(
            x=time_slice, y=ekf_cht - sigma_2, mode='lines',
            line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 240, 255, 0.12)',
            name="EKF ±2σ Uncertainty Band"
        ))
        fig_cht.add_trace(go.Scatter(
            x=time_slice, y=raw_cht, mode='markers',
            marker=dict(color="#ff0055", size=4, opacity=0.6), name="Raw CAN Bus Telemetry"
        ))
        fig_cht.add_trace(go.Scatter(
            x=time_slice, y=ekf_cht, mode='lines',
            line=dict(color="#00f0ff", width=2.5), name="EKF Filtered State"
        ))
        fig_cht.add_trace(go.Scatter(
            x=time_slice, y=df['cht_physics'][:t_idx+1], mode='lines',
            line=dict(color="#94a3b8", dash="dash", width=2), name="Physics Twin Target"
        ))
        fig_cht.add_hline(y=145.0, line_dash="dot", line_color="#ffb703", annotation_text="Limit (145°C)")
        fig_cht.update_layout(hud_plot_layout, height=310, yaxis_title="°C")
        st.plotly_chart(fig_cht, use_container_width=True)

    with col_t2:
        st.markdown("<div style='color: #00ff66; font-weight: bold;'>LUBRICATION CIRCUIT PRESSURE</div>", unsafe_allow_html=True)
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(
            x=time_slice, y=df['oil_press_actual'][:t_idx+1],
            name="Oil Pressure Actual", line=dict(color="#00ff66", width=3)
        ))
        fig_oil.add_trace(go.Scatter(
            x=time_slice, y=df['oil_press_physics'][:t_idx+1],
            name="Physics Baseline", line=dict(color="#94a3b8", dash="dash", width=2)
        ))
        fig_oil.add_hline(y=1.5, line_dash="dot", line_color="#ff003c", annotation_text="Cavitation Limit (1.5 bar)")
        fig_oil.update_layout(hud_plot_layout, height=310, yaxis_title="bar")
        st.plotly_chart(fig_oil, use_container_width=True)

    st.markdown("<div style='color: #00f0ff; font-weight: bold; margin-top: 10px;'>REAL-TIME SUBSYSTEM RESIDUAL ERROR MATRIX</div>", unsafe_allow_html=True)
    matrix_data = [
        {"Subsystem": "Cylinder Head Thermal Loop", "Actual Telemetry": f"{current_row['cht_actual']} °C", "Twin Expected": f"{current_row['cht_physics']} °C", "Residual Error (Δ)": f"+{metrics['residuals']['cht_delta']} °C", "Status": "CRITICAL DRIFT" if metrics['residuals']['cht_delta'] > 15.0 else "NOMINAL"},
        {"Subsystem": "Exhaust Gas Thermal Loop", "Actual Telemetry": f"{current_row['egt_actual']} °C", "Twin Expected": f"{current_row['egt_physics']} °C", "Residual Error (Δ)": f"+{metrics['residuals']['egt_delta']} °C", "Status": "NOMINAL"},
        {"Subsystem": "Oil Gallery Hydrodynamics", "Actual Telemetry": f"{current_row['oil_press_actual']} bar", "Twin Expected": f"{current_row['oil_press_physics']} bar", "Residual Error (Δ)": f"-{metrics['residuals']['oil_p_delta']} bar", "Status": "PRESSURE DROP" if metrics['residuals']['oil_p_delta'] > 1.5 else "NOMINAL"},
        {"Subsystem": "Crankshaft Mechanical Harmonics", "Actual Telemetry": f"{current_row['vibration_rms']} G", "Twin Expected": "1.10 G", "Residual Error (Δ)": f"+{round(abs(current_row['vibration_rms'] - 1.1), 2)} G", "Status": "DETONATION DETECTED" if current_row['vibration_rms'] > 1.8 else "NOMINAL"}
    ]
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

with tab2:
    col_xai1, col_xai2 = st.columns([3, 2])
    with col_xai1:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>EXPLAINABLE AI (XAI) FAULT ATTRIBUTION WATERFALL</div>", unsafe_allow_html=True)
        cht_penalty = min(45.0, metrics['residuals']['cht_delta'] * 1.8)
        oil_penalty = min(35.0, metrics['residuals']['oil_p_delta'] * 16.0)
        vib_penalty = min(20.0, max(0.0, (current_row['vibration_rms'] - 1.1) * 25.0))

        fig_xai = go.Figure(go.Waterfall(
            name="Penalty Attribution", orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["Model Baseline", "CHT Thermal Drift", "Oil Pressure Drop", "Detonation Knock", "Final Health Index"],
            textposition="outside",
            text=[f"100.0%", f"-{cht_penalty:.1f}%", f"-{oil_penalty:.1f}%", f"-{vib_penalty:.1f}%", f"{metrics['health_index']}%"],
            y=[100.0, -cht_penalty, -oil_penalty, -vib_penalty, 0],
            connector={"line": {"color": "rgba(0, 240, 255, 0.4)"}},
            decreasing={"marker": {"color": "#ff003c"}},
            increasing={"marker": {"color": "#00ff66"}},
            totals={"marker": {"color": "#00f0ff"}}
        ))
        fig_xai.update_layout(hud_plot_layout, height=360, yaxis_title="Health Percentage (%)")
        st.plotly_chart(fig_xai, use_container_width=True)

    with col_xai2:
        st.markdown("<div style='color: #00ff66; font-weight: bold;'>TACTICAL SWARM MESH TELEMETRY</div>", unsafe_allow_html=True)
        st.caption("Decentralized cross-link health monitoring with neighboring MALE UAV flight assets.")
        
        swarm_data = [
            {"Asset ID": "UAV-01 (HOST)", "Role": "Lead Patrol", "Health": f"{metrics['health_index']}%", "Link Status": "ACTIVE LINK"},
            {"Asset ID": "UAV-02 (RELAY)", "Role": "Datalink Node", "Health": "98.4%", "Link Status": "NOMINAL"},
            {"Asset ID": "UAV-03 (RESERVE)", "Role": "Standby Orbit", "Health": "99.1%", "Link Status": "NOMINAL"}
        ]
        st.dataframe(pd.DataFrame(swarm_data), use_container_width=True)
        
        if metrics['severity'] == "RED":
            if st.button("🤝 EXECUTE AUTONOMOUS MISSION HANDOVER"):
                st.session_state.swarm_handover = True
                st.rerun()
            if st.session_state.swarm_handover:
                st.success("✓ MISSION TASKING TRANSFERRED TO UAV-02. UAV-01 CLEARED FOR IMMEDIATE RTB.")

with tab3:
    col_glide1, col_glide2 = st.columns(2)
    with col_glide1:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>UNPOWERED DEAD-STICK GLIDE SLOPE PROFILE</div>", unsafe_allow_html=True)
        st.caption("Theoretical gliding descent angle (L/D = 12:1) from current altitude to FOB Alpha runway.")

        dist_range = np.linspace(0, 35, 30)  # km to base
        current_alt_km = current_row['altitude_m'] / 1000.0
        glide_slope_alt = np.maximum(0, current_alt_km - (dist_range / 12.0)) * 1000.0

        fig_glide = go.Figure()
        fig_glide.add_trace(go.Scatter(
            x=dist_range, y=glide_slope_alt, mode='lines',
            line=dict(color='#00ff66' if glide_slope_alt[-1] == 0 else '#ff003c', width=3),
            name="Unpowered Descent Path"
        ))
        fig_glide.add_hline(y=0, line_color="#ffffff", annotation_text="Runway 09 Threshold")
        fig_glide.update_layout(hud_plot_layout, height=330, xaxis_title="Distance to FOB Alpha (km)", yaxis_title="Altitude (m AGL)")
        st.plotly_chart(fig_glide, use_container_width=True)

    with col_glide2:
        st.markdown("<div style='color: #00ff66; font-weight: bold;'>MONTE CARLO PROGNOSTIC RUL ENVELOPE</div>", unsafe_allow_html=True)
        st.caption("Degradation slope with P10, P50, and P90 confidence intervals.")

        future_t = np.linspace(0, 120, 25)
        current_h = metrics['health_index']
        decay_rate = 0.05 if current_h > 70 else (0.45 if current_h > 40 else 0.85)
        if st.session_state.limp_mode:
            decay_rate *= 0.45

        p50_h = np.maximum(0, current_h - (future_t * decay_rate))
        p10_h = np.maximum(0, current_h - (future_t * (decay_rate * 0.65)))
        p90_h = np.maximum(0, current_h - (future_t * (decay_rate * 1.45)))

        fig_mc = go.Figure()
        fig_mc.add_trace(go.Scatter(x=future_t, y=p10_h, line=dict(color='rgba(0, 240, 255, 0.2)'), showlegend=False))
        fig_mc.add_trace(go.Scatter(
            x=future_t, y=p90_h, fill='tonexty', fillcolor='rgba(255, 0, 60, 0.15)',
            line=dict(color='rgba(255, 0, 60, 0.2)'), name='90% Confidence Interval'
        ))
        fig_mc.add_trace(go.Scatter(x=future_t, y=p50_h, line=dict(color='#00f0ff', width=3), name='P50 Degradation'))
        fig_mc.add_hline(y=20.0, line_dash="dash", line_color="#ff003c", annotation_text="Seizure Limit (20%)")
        fig_mc.update_layout(hud_plot_layout, height=330, xaxis_title="Minutes Ahead", yaxis_title="Health Index (%)")
        st.plotly_chart(fig_mc, use_container_width=True)

with tab4:
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>3D ISOMETRIC PROPULSION CORE STRESS MODEL</div>", unsafe_allow_html=True)
    cht_val = current_row['cht_actual']
    oil_p = current_row['oil_press_actual']
    cyl_col = "#ff003c" if cht_val > 140 else ("#ffb703" if cht_val > 125 else "#00ff66")
    oil_col = "#ff003c" if oil_p < 1.8 else ("#ffb703" if oil_p < 2.5 else "#00ff66")

    fig_3d = go.Figure()
    fig_3d.add_trace(go.Scatter3d(
        x=[0, 0], y=[-1.8, 1.8], z=[0, 0], mode="lines",
        line=dict(color="#00f0ff", width=10), name="Crankshaft Centerline"
    ))

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

    fig_3d.add_trace(go.Scatter3d(
        x=[0], y=[-1.6], z=[1.1], mode="markers+text",
        marker=dict(size=22, color="#00f0ff", symbol="diamond"),
        text=[f"<b>TURBOCHARGER</b><br>{current_row['map_inhg']} inHg"], textposition="top center", name="Turbo"
    ))
    fig_3d.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-0.9], mode="markers+text",
        marker=dict(size=24, color=oil_col, symbol="circle"),
        text=[f"<b>OIL SUMP</b><br>{oil_p} bar"], textposition="bottom center", name="Oil Gallery"
    ))

    fig_3d.update_layout(
        paper_bgcolor='rgba(5, 10, 20, 0.6)', height=480,
        scene=dict(
            xaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-2, 2]),
            yaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-2.5, 2.5]),
            zaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-1.5, 1.8]),
            camera=dict(eye=dict(x=1.6, y=-1.7, z=1.3))
        ),
        font=dict(family='Share Tech Mono', color='#ffffff'), margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

with tab5:
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>TACTICAL MISSION RADAR & AUTONOMOUS RTB VECTOR</div>", unsafe_allow_html=True)
    uav_x = [0, 8, 16, 25, 32, 38, 42, 40, 32, 22, 12, 5, 0]
    uav_y = [0, 6, 12, 18, 22, 22, 15, 6, -2, -6, -4, -1, 0]
    norm_idx = int((t_idx / len(df)) * (len(uav_x) - 1))
    cur_x = uav_x[norm_idx]
    cur_y = uav_y[norm_idx]

    fig_radar = go.Figure()
    for r in [10, 25, 45]:
        fig_radar.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color="rgba(0, 240, 255, 0.15)", dash="dot", width=1))

    fig_radar.add_trace(go.Scatter(x=uav_x[:norm_idx+1], y=uav_y[:norm_idx+1], mode="lines+markers", line=dict(color="#00f0ff", width=2.5), name="Patrol Track"))
    fig_radar.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=14, color="#00ff66", symbol="triangle-up"), text=["<b>[BASE FOB ALPHA]</b>"], textposition="bottom center", name="Home Base"))
    fig_radar.add_trace(go.Scatter(x=[cur_x], y=[cur_y], mode="markers+text", marker=dict(size=16, color="#ff0055" if metrics["severity"] == "RED" else "#00f0ff", symbol="diamond"), text=[f"<b>UAV-01 (T+{t_idx}s)</b>"], textposition="top right", name="UAV Vector"))

    if metrics["severity"] == "RED" and not spoofed_flag:
        fig_radar.add_trace(go.Scatter(x=[cur_x, 0], y=[cur_y, 0], mode="lines+text", line=dict(color="#ff003c", width=3, dash="dashdot"), text=["", "<b>AUTONOMOUS RTB DIVERSION ENGAGED</b>"], textposition="middle right", name="Autonomous RTB Vector"))

    fig_radar.update_layout(hud_plot_layout, height=450, xaxis=dict(range=[-50, 50], title="Sector Range X (km)"), yaxis=dict(range=[-30, 50], title="Sector Range Y (km)"))
    st.plotly_chart(fig_radar, use_container_width=True)

with tab6:
    col_log, col_deb = st.columns([3, 2])
    with col_log:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>MIL-STD AUTONOMOUS AI CO-PILOT TERMINAL LOG</div>", unsafe_allow_html=True)
        log_feed = [
            f"[T+000] FADEC_BUS: MIL-STD-1553 bus synchronized at 50Hz. All nodes verified.",
            f"[T+015] FADEC_BUS: Airspeed 115 KCAS locked. Climb regime executed.",
            f"[T+050] THERMAL_CORE: Cruising altitude {current_row['altitude_m']}m. ISA Baseline active."
        ]
        if spoofed_flag:
            log_feed.append(f"[T+{t_idx:03d}] CYBER_DEFENSE: Anomaly detected on CAN Bus channel 2.")
            log_feed.append(f"[T+{t_idx:03d}] KALMAN_GATE: Rejecting packet: delta_T (+45°C) exceeds thermal inertia.")
        if t_idx >= 100 and not spoofed_flag:
            if scenario == "COOLING_FAILURE":
                log_feed.append(f"[T+100] SENSOR_ALERT: CHT drift rate exceeds +0.45°C/s threshold.")
                log_feed.append(f"[T+108] RESIDUAL_ENGINE: CHT model residual breached (+15.0°C deviation).")
            elif scenario == "LUBRICATION_LOSS":
                log_feed.append(f"[T+100] SENSOR_ALERT: Oil gallery pressure drop below nominal.")
        if st.session_state.limp_mode:
            log_feed.append(f"[T+{t_idx:03d}] MITIGATION: Pilot engaged 65% Limp-Home mode. RPM curbed.")
        if st.session_state.fuel_enrich:
            log_feed.append(f"[T+{t_idx:03d}] MITIGATION: Mixture enriched. CHT cooling quench active.")
        if st.session_state.swarm_handover:
            log_feed.append(f"[T+{t_idx:03d}] DATALINK_MESH: Handover handshake complete with UAV-02.")
        if metrics["severity"] == "RED" and not spoofed_flag and not st.session_state.limp_mode:
            log_feed.append(f"[T+{t_idx:03d}] PROGNOSTICS_AI: RUL degraded to {metrics['rul_hours']} hrs.")
            log_feed.append(f"[T+{t_idx:03d}] AUTOPILOT: MISSION ABORT EXECUTED -> RTB to FOB Alpha.")
        
        log_html = "<br>".join([f"&gt; {item}" for item in log_feed])
        st.markdown(f"<div class='terminal-box'>{log_html}</div>", unsafe_allow_html=True)

    with col_deb:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>STANAG 4586 D-BUS PACKET FRAME STREAM</div>", unsafe_allow_html=True)
        # Synthetic STANAG 4586 hex telemetry representation
        rpm_hex = f"{int(current_row['rpm']):04X}"
        cht_hex = f"{int(current_row['cht_actual'] * 10):04X}"
        alt_hex = f"{int(current_row['altitude_m']):04X}"
        stanag_packet = f"FA 55 01 2C 12 {rpm_hex[:2]} {rpm_hex[2:]} {cht_hex[:2]} {cht_hex[2:]} {alt_hex[:2]} {alt_hex[2:]} 00 E4 9B 7A"

        st.markdown(f"""
        <div class='packet-hex'>
            <b>RAW STREAM:</b> <code>{stanag_packet}</code><br>
            <b>STANAG MSG ID:</b> <code>0x012C [PROPULSION_STATUS]</code><br>
            <b>PAYLOAD CRC:</b> <code>0x9B7A (VALID)</code>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'><b>BLACKBOX TELEMETRY LOG</b></div>", unsafe_allow_html=True)
        csv_export = df.iloc[:t_idx+1].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 EXPORT ACTIVE TELEMETRY (.CSV)",
            data=csv_export,
            file_name=f"UAV_AeroTwin_{scenario}_MET_{t_idx}.csv",
            mime="text/csv"
        )

# Auto-Play Stream Loop Runner
if st.session_state.is_playing:
    if st.session_state.t_idx < len(df) - 1:
        time.sleep(0.35)
        st.session_state.t_idx += 1
        st.rerun()
    else:
        st.session_state.is_playing = False
        st.rerun()
