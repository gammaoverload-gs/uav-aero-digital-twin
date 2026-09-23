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
    page_title="AeroTwin Tactical GCS | MALE UAV",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Military Tactical HUD Theme
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

    @keyframes pulseRed {
        0% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
        50% { box-shadow: 0 0 30px rgba(255, 0, 60, 0.75); }
        100% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if "t_idx" not in st.session_state:
    st.session_state.t_idx = 120
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "last_voice_alert" not in st.session_state:
    st.session_state.last_voice_alert = None

# Sidebar Controls
st.sidebar.markdown("""
<div style='text-align: center; padding: 5px 0;'>
    <div style='font-family: Orbitron; font-size: 1.15rem; color: #00f0ff; letter-spacing: 2px;'>AEROTWIN TACTICAL</div>
    <div style='font-size: 0.72rem; color: #64748b;'>DEFENSE TELEMETRY NODE // 5.0.0</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
scenario = st.sidebar.selectbox(
    "MISSION SCENARIO INJECTION",
    ["NOMINAL", "COOLING_FAILURE", "LUBRICATION_LOSS"],
    index=1
)

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

st.session_state.t_idx = st.sidebar.slider(
    "Mission Elapsed Time (Seconds)",
    0, len(df) - 1,
    st.session_state.t_idx
)

t_idx = st.session_state.t_idx
current_row = df.iloc[t_idx]
metrics = prognostics.evaluate_telemetry(current_row)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size: 0.78rem; line-height: 1.6; color: #94a3b8;'>
    <b>CRYPT-KEY:</b> <span style='color: #00ff66;'>AES-256 GCM</span><br>
    <b>BUS PROTOCOL:</b> <span style='color: #00f0ff;'>MIL-STD-1553 / CAN</span><br>
    <b>SAMPLING RATE:</b> 50 Hz Synchronous<br>
    <b>FRAME DROPS:</b> 0.00%
</div>
""", unsafe_allow_html=True)

# Main Screen Header
st.markdown("<div class='hud-header'>⚡ AEROTWIN: MALE UAV PROPULSION TWIN</div>", unsafe_allow_html=True)

st.markdown(f"""
<div class='telemetry-strip'>
    <div>SYSTEM: <span style='color: #00ff66;'>● SECURE TELEMETRY LINK</span></div>
    <div>REGIME: <b>{current_row['flight_phase']}</b></div>
    <div>ALTITUDE: <b>{current_row['altitude_m']} M</b></div>
    <div>AIRSPEED: <b>115 KCAS</b></div>
    <div>ISA OAT: <b>{round(15 - 0.0065 * current_row['altitude_m'], 1)}°C</b></div>
    <div>MISSION CLOCK: <b>T+{t_idx:03d}s</b></div>
</div>
""", unsafe_allow_html=True)

# Cockpit Gauges Strip
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
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        height=175,
        margin=dict(l=15, r=15, t=30, b=15),
        font={'family': "Share Tech Mono"}
    )
    return fig

with g1:
    st.plotly_chart(make_hud_gauge("HEALTH INDEX", metrics['health_index'], 0, 100, "%", 45, 75, is_invert=True), use_container_width=True)
with g2:
    st.plotly_chart(make_hud_gauge("CYLINDER TEMP (CHT)", current_row['cht_actual'], 80, 170, "°C", 145, 130), use_container_width=True)
with g3:
    st.plotly_chart(make_hud_gauge("OIL PRESSURE", current_row['oil_press_actual'], 0, 6, "bar", 1.8, 2.5, is_invert=True), use_container_width=True)
with g4:
    st.plotly_chart(make_hud_gauge("CRANKSHAFT TACHO", current_row['rpm'], 0, 6000, "RPM", 5600, 5200), use_container_width=True)

# Diagnostic Advisory Banner
if metrics["severity"] == "RED":
    st.markdown(f"""
    <div class='alert-banner-critical'>
        <strong>⚠️ CRITICAL TACTICAL ADVISORY [AUTONOMOUS RETURN-TO-BASE RECOMMENDED]</strong><br>
        <strong>Fault Mode:</strong> {metrics['status']} &nbsp;|&nbsp; <strong>Diagnostic Root Cause:</strong> {metrics['alert_message']}<br>
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

# Native Web Speech Tactical Voice Announcement
if enable_voice and metrics["severity"] == "RED" and st.session_state.last_voice_alert != "RED":
    st.session_state.last_voice_alert = "RED"
    components.html("""
    <script>
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        let msg = new SpeechSynthesisUtterance("Critical warning. Propulsion health degraded. Autonomous Return To Base vector initiated.");
        msg.rate = 1.05;
        msg.pitch = 0.85;
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, height=0)
elif metrics["severity"] != "RED":
    st.session_state.last_voice_alert = metrics["severity"]

# Tab Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 SENSOR BUS & RESIDUALS",
    "🧊 3D PROPULSION CORE MODEL",
    "⚡ FFT HARMONICS & ENVELOPE",
    "🗺️ TACTICAL RADAR & AUTONOMOUS RTB",
    "💻 MIL-STD AI CO-PILOT TERMINAL"
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
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>CYLINDER HEAD TEMPERATURE (THERMODYNAMIC RESIDUAL)</div>", unsafe_allow_html=True)
        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_actual'][:t_idx+1],
            name="Sensor Telemetry", line=dict(color="#ff0055", width=3)
        ))
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_physics'][:t_idx+1],
            name="Physics Twin Model", line=dict(color="#00f0ff", dash="dash", width=2)
        ))
        fig_cht.add_hline(y=145.0, line_dash="dot", line_color="#ffb703", annotation_text="Limit (145°C)")
        fig_cht.update_layout(hud_plot_layout, height=310, yaxis_title="°C")
        st.plotly_chart(fig_cht, use_container_width=True)

    with col_t2:
        st.markdown("<div style='color: #00ff66; font-weight: bold;'>LUBRICATION CIRCUIT PRESSURE</div>", unsafe_allow_html=True)
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['oil_press_actual'][:t_idx+1],
            name="Oil Pressure Actual", line=dict(color="#00ff66", width=3)
        ))
        fig_oil.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['oil_press_physics'][:t_idx+1],
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
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>3D ISOMETRIC PROPULSION CORE STRESS MODEL</div>", unsafe_allow_html=True)
    st.caption("Rotate, pan, and zoom to inspect 3D spatial thermal gradient across individual cylinders and drivetrain assemblies.")
    
    cht_val = current_row['cht_actual']
    oil_p = current_row['oil_press_actual']
    cyl_col = "#ff003c" if cht_val > 140 else ("#ffb703" if cht_val > 125 else "#00ff66")
    oil_col = "#ff003c" if oil_p < 1.8 else ("#ffb703" if oil_p < 2.5 else "#00ff66")

    fig_3d = go.Figure()

    # Crankshaft Axis line
    fig_3d.add_trace(go.Scatter3d(
        x=[0, 0], y=[-1.8, 1.8], z=[0, 0],
        mode="lines",
        line=dict(color="#00f0ff", width=10),
        name="Crankshaft Centerline"
    ))

    # Cylinders 1-4
    cyl_coords = [
        {"name": "Cyl 1 [FWD-L]", "x": -1.2, "y": 1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 2 [FWD-R]", "x": 1.2, "y": 1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 3 [AFT-L]", "x": -1.2, "y": -1.0, "z": 0.4, "temp": cht_val},
        {"name": "Cyl 4 [AFT-R]", "x": 1.2, "y": -1.0, "z": 0.4, "temp": cht_val},
    ]

    for c in cyl_coords:
        fig_3d.add_trace(go.Scatter3d(
            x=[c["x"]], y=[c["y"]], z=[c["z"]],
            mode="markers+text",
            marker=dict(size=28, color=cyl_col, symbol="square", opacity=0.9),
            text=[f"<b>{c['name']}</b><br>{c['temp']}°C"],
            textposition="top center",
            name=c["name"]
        ))

    # Turbocharger Spool
    fig_3d.add_trace(go.Scatter3d(
        x=[0], y=[-1.6], z=[1.1],
        mode="markers+text",
        marker=dict(size=22, color="#00f0ff", symbol="diamond"),
        text=[f"<b>TURBOCHARGER</b><br>{current_row['map_inhg']} inHg"],
        textposition="top center",
        name="Turbo Spool"
    ))

    # Oil Pump & Sump
    fig_3d.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[-0.9],
        mode="markers+text",
        marker=dict(size=24, color=oil_col, symbol="circle"),
        text=[f"<b>OIL GALLERY & SUMP</b><br>{oil_p} bar"],
        textposition="bottom center",
        name="Lubrication Circuit"
    ))

    fig_3d.update_layout(
        paper_bgcolor='rgba(5, 10, 20, 0.6)',
        height=500,
        scene=dict(
            xaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-2, 2]),
            yaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-2.5, 2.5]),
            zaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.15)', backgroundcolor='rgba(0,0,0,0)', range=[-1.5, 1.8]),
            camera=dict(eye=dict(x=1.6, y=-1.7, z=1.3))
        ),
        font=dict(family='Share Tech Mono', color='#ffffff'),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>FFT VIBRATION POWER SPECTRAL DENSITY (0 - 8 kHz)</div>", unsafe_allow_html=True)
        freq_bins = np.linspace(10, 8000, 300)
        
        # Engine rotational 1X / 2X harmonics
        f_engine = current_row['rpm'] / 60.0
        base_psd = 0.05 / (1 + ((freq_bins - f_engine)/10)**2) + 0.03 / (1 + ((freq_bins - 2*f_engine)/15)**2)
        noise = np.random.normal(0.005, 0.002, len(freq_bins))
        psd_total = np.maximum(base_psd + noise, 0.001)

        # Severe knock high-frequency spike (> 5kHz) under detonation
        if current_row['vibration_rms'] > 1.5:
            knock_spike = 0.45 / (1 + ((freq_bins - 5800)/120)**2)
            psd_total += knock_spike

        fig_fft = go.Figure()
        fig_fft.add_trace(go.Scatter(
            x=freq_bins, y=psd_total,
            mode="lines",
            line=dict(color="#ff0055" if current_row['vibration_rms'] > 1.5 else "#00f0ff", width=2),
            name="Vibration PSD (G²/Hz)"
        ))
        fig_fft.add_vline(x=5800, line_dash="dot", line_color="#ff003c", annotation_text="Detonation Knock Band (5.8 kHz)")
        fig_fft.update_layout(hud_plot_layout, height=340, xaxis_title="Frequency (Hz)", yaxis_title="PSD (G²/Hz)")
        st.plotly_chart(fig_fft, use_container_width=True)

    with col_f2:
        st.markdown("<div style='color: #00ff66; font-weight: bold;'>PROPULSION HEALTH FLIGHT ENVELOPE</div>", unsafe_allow_html=True)
        
        categories = ['Thermal Margin', 'Hydrodynamic Press', 'Acoustic Stability', 'Volumetric Eff', 'Turbo Margin', 'ISA Air Density']
        
        # Dynamic envelope shrinkage
        thermal_norm = max(0.1, (170 - current_row['cht_actual']) / 70)
        oil_norm = min(1.0, current_row['oil_press_actual'] / 4.5)
        vibe_norm = max(0.1, (3.0 - current_row['vibration_rms']) / 2.0)
        density_norm = max(0.3, 1.0 - (current_row['altitude_m'] / 10000))
        
        current_scores = [thermal_norm, oil_norm, vibe_norm, 0.92, 0.88, density_norm]
        nominal_scores = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        fig_radar_poly = go.Figure()
        fig_radar_poly.add_trace(go.Scatterpolar(
            r=nominal_scores, theta=categories, fill='toself',
            fillcolor='rgba(0, 240, 255, 0.12)', line=dict(color='#00f0ff', dash='dash'), name='Nominal Envelope'
        ))
        fig_radar_poly.add_trace(go.Scatterpolar(
            r=current_scores, theta=categories, fill='toself',
            fillcolor='rgba(255, 0, 60, 0.25)' if metrics['severity'] == 'RED' else 'rgba(0, 255, 102, 0.25)',
            line=dict(color='#ff003c' if metrics['severity'] == 'RED' else '#00ff66', width=2.5),
            name='Active Envelope'
        ))
        fig_radar_poly.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.1], gridcolor='rgba(0, 240, 255, 0.15)')),
            paper_bgcolor='rgba(5, 10, 20, 0.6)',
            font=dict(family='Share Tech Mono', color='#8892b0'),
            height=340,
            margin=dict(l=30, r=30, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_radar_poly, use_container_width=True)

with tab4:
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>TACTICAL MISSION RADAR & AUTONOMOUS RTB VECTOR</div>", unsafe_allow_html=True)
    
    uav_x = [0, 8, 16, 25, 32, 38, 42, 40, 32, 22, 12, 5, 0]
    uav_y = [0, 6, 12, 18, 22, 22, 15, 6, -2, -6, -4, -1, 0]
    
    norm_idx = int((t_idx / len(df)) * (len(uav_x) - 1))
    cur_x = uav_x[norm_idx]
    cur_y = uav_y[norm_idx]

    fig_radar = go.Figure()
    for r in [10, 25, 45]:
        fig_radar.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r,
                            line=dict(color="rgba(0, 240, 255, 0.15)", dash="dot", width=1))

    fig_radar.add_trace(go.Scatter(
        x=uav_x[:norm_idx+1], y=uav_y[:norm_idx+1],
        mode="lines+markers", line=dict(color="#00f0ff", width=2.5), name="Nominal Patrol Track"
    ))
    fig_radar.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers+text",
        marker=dict(size=14, color="#00ff66", symbol="triangle-up"),
        text=["<b>[BASE FOB ALPHA]</b>"], textposition="bottom center", name="Home Base"
    ))
    fig_radar.add_trace(go.Scatter(
        x=[cur_x], y=[cur_y], mode="markers+text",
        marker=dict(size=16, color="#ff0055" if metrics["severity"] == "RED" else "#00f0ff", symbol="diamond"),
        text=[f"<b>UAV-01 (T+{t_idx}s)</b>"], textposition="top right", name="UAV Vector"
    ))

    if metrics["severity"] == "RED":
        fig_radar.add_trace(go.Scatter(
            x=[cur_x, 0], y=[cur_y, 0], mode="lines+text",
            line=dict(color="#ff003c", width=3, dash="dashdot"),
            text=["", "<b>AUTONOMOUS RTB DIVERSION ENGAGED</b>"],
            textposition="middle right", name="Autonomous RTB Vector"
        ))

    fig_radar.update_layout(
        paper_bgcolor='rgba(5, 10, 20, 0.6)',
        plot_bgcolor='rgba(5, 10, 20, 0.6)',
        font=dict(family='Share Tech Mono', color='#8892b0'),
        height=450,
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.08)', range=[-50, 50], title="Sector Range X (km)"),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 240, 255, 0.08)', range=[-30, 50], title="Sector Range Y (km)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with tab5:
    col_log, col_deb = st.columns([3, 2])
    
    with col_log:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>MIL-STD AUTONOMOUS AI CO-PILOT TERMINAL LOG</div>", unsafe_allow_html=True)
        
        log_feed = [
            f"[T+000] FADEC_BUS: MIL-STD-1553 bus synchronized at 50Hz. Node handshakes 100%.",
            f"[T+015] FADEC_BUS: Airspeed 115 KCAS locked. Climb regime initiated.",
            f"[T+050] THERMAL_CORE: Operating at altitude {current_row['altitude_m']}m. ISA Model online."
        ]
        
        if t_idx >= 75:
            log_feed.append(f"[T+075] TWIN_CORE: Ambient lapse rate: OAT = {round(15 - 0.0065 * current_row['altitude_m'], 1)}°C.")
        if t_idx >= 100:
            if scenario == "COOLING_FAILURE":
                log_feed.append(f"[T+100] SENSOR_ALERT: CHT drift rate exceeds +0.45°C/s threshold.")
                log_feed.append(f"[T+108] RESIDUAL_ENGINE: CHT model residual breached (+15.0°C deviation).")
                log_feed.append(f"[T+115] ACOUSTIC_CORE: Knock harmonic detected at 5.8 kHz frequency band.")
            elif scenario == "LUBRICATION_LOSS":
                log_feed.append(f"[T+100] SENSOR_ALERT: Oil gallery pressure drop below nominal (e = -1.2 bar).")
        if t_idx >= 120 and metrics["severity"] in ["RED", "AMBER"]:
            log_feed.append(f"[T+120] PROGNOSTICS_AI: RUL degraded to {metrics['rul_hours']} hrs (< 4.0 hrs mission buffer).")
            log_feed.append(f"[T+122] AUTOPILOT: MISSION ABORT EXECUTED. Disengaging loiter orbit.")
            log_feed.append(f"[T+125] AUTOPILOT: Diverting along computed emergency RTB vector to FOB Alpha.")
        
        log_html = "<br>".join([f"&gt; {item}" for item in log_feed])
        st.markdown(f"<div class='terminal-box'>{log_html}</div>", unsafe_allow_html=True)

    with col_deb:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>BLACKBOX DEBRIEF & EXPORT</div>", unsafe_allow_html=True)
        st.markdown(f"""
        * **Recorded Mission Window:** `{t_idx}s / {len(df)}s`
        * **Simulated Fault Regime:** `{scenario}`
        * **Subsystem Health Status:** `{metrics['health_index']}%`
        * **Max Recorded CHT:** `{df['cht_actual'][:t_idx+1].max()} °C`
        * **Min Oil Pressure:** `{df['oil_press_actual'][:t_idx+1].min()} bar`
        """)
        csv_export = df.iloc[:t_idx+1].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 EXPORT ACTIVE TELEMETRY (.CSV)",
            data=csv_export,
            file_name=f"UAV_AeroTwin_{scenario}_MET_{t_idx}.csv",
            mime="text/csv"
        )

# Auto-Play Loop
if st.session_state.is_playing:
    if st.session_state.t_idx < len(df) - 1:
        time.sleep(0.35)
        st.session_state.t_idx += 1
        st.rerun()
    else:
        st.session_state.is_playing = False
        st.rerun()
