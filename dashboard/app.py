import os
import sys
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine_physics import AeroPistonDigitalTwin  # type: ignore
from core.prognostics import EnginePrognostics  # type: ignore

st.set_page_config(
    page_title="AeroTwin Tactical GCS | MALE UAV",
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
    /* Global Tactical Dark Theme */
    .stApp {
        background: radial-gradient(circle at top right, #0d1b2a 0%, #050811 65%, #020408 100%);
        color: #e0e6ed;
        font-family: 'Share Tech Mono', monospace;
    }
    
    /* Neon HUD Header */
    .hud-header {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 3px;
        background: linear-gradient(90deg, #00f0ff, #7000ff, #00ff66);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.1rem;
        font-weight: 900;
        margin-bottom: 2px;
        text-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
    }
    
    /* Top Telemetry Feed Strip */
    .telemetry-strip {
        background: rgba(10, 20, 35, 0.75);
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-left: 5px solid #00f0ff;
        padding: 8px 16px;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.85rem;
        color: #79a8d7;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }

    /* Tactical Cards with Tech Brackets */
    .hud-card {
        background: rgba(13, 27, 42, 0.65);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(0, 240, 255, 0.2);
        padding: 16px;
        border-radius: 6px;
        position: relative;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.6);
        margin-bottom: 12px;
    }
    .hud-card::before {
        content: "[ ";
        color: #00f0ff;
        font-family: 'Orbitron', sans-serif;
        font-weight: bold;
    }
    .hud-card::after {
        content: " ]";
        color: #00f0ff;
        font-family: 'Orbitron', sans-serif;
        font-weight: bold;
    }

    .hud-metric-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #8892b0;
    }
    .hud-metric-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
    }

    /* Flashing Pulse Alert Banners */
    .alert-banner-critical {
        background: rgba(80, 0, 15, 0.85);
        border: 1px solid #ff003c;
        border-left: 8px solid #ff003c;
        color: #ffb4c4;
        padding: 14px 20px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-family: 'Share Tech Mono', monospace;
        animation: pulseRed 2s infinite ease-in-out;
        box-shadow: 0 0 25px rgba(255, 0, 60, 0.35);
    }

    .alert-banner-nominal {
        background: rgba(0, 40, 25, 0.75);
        border: 1px solid #00ff66;
        border-left: 8px solid #00ff66;
        color: #a3f7bf;
        padding: 14px 20px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-family: 'Share Tech Mono', monospace;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.2);
    }

    @keyframes pulseRed {
        0% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
        50% { box-shadow: 0 0 30px rgba(255, 0, 60, 0.7); }
        100% { box-shadow: 0 0 10px rgba(255, 0, 60, 0.3); }
    }
</style>
""", unsafe_allow_html=True)

# Tactical Sidebar
st.sidebar.markdown("""
<div style='text-align: center; padding: 10px 0;'>
    <div style='font-family: Orbitron; font-size: 1.1rem; color: #00f0ff; letter-spacing: 2px;'>AEROTWIN TACTICAL</div>
    <div style='font-size: 0.75rem; color: #64748b;'>DEFENSE TELEMETRY NODE // 4.8.2</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
scenario = st.sidebar.selectbox(
    "MISSION SCENARIO INJECTION",
    ["NOMINAL", "COOLING_FAILURE", "LUBRICATION_LOSS"],
    index=1
)

@st.cache_data
def load_telemetry(scen):
    twin = AeroPistonDigitalTwin()
    return twin.generate_mission_telemetry(total_seconds=200, fault_scenario=scen)

df = load_telemetry(scenario)
prognostics = EnginePrognostics()

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-family: Orbitron; font-size: 0.8rem; color: #00f0ff;'>MISSION SCRUBBER</div>", unsafe_allow_html=True)
t_idx = st.sidebar.slider("MET (Seconds)", 0, len(df) - 1, 125)

current_row = df.iloc[t_idx]
metrics = prognostics.evaluate_telemetry(current_row)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size: 0.8rem; line-height: 1.6; color: #94a3b8;'>
    <b>ENCRYPTED LINK:</b> <span style='color: #00ff66;'>AES-256 GCM</span><br>
    <b>BUS PROTOCOL:</b> <span style='color: #00f0ff;'>MIL-STD-1553 / CAN</span><br>
    <b>FADEC SAMPLING:</b> 50 Hz Synchronous<br>
    <b>DOWNLINK LOSS:</b> 0.00%
</div>
""", unsafe_allow_html=True)

# Main Screen Header
st.markdown("<div class='hud-header'>⚡ AEROTWIN: MALE UAV PROPULSION TWIN</div>", unsafe_allow_html=True)

st.markdown(f"""
<div class='telemetry-strip'>
    <div>STATUS: <span style='color: #00ff66;'>● LIVE LINK</span></div>
    <div>REGIME: <b>{current_row['flight_phase']}</b></div>
    <div>ALT: <b>{current_row['altitude_m']} M</b></div>
    <div>AIRSPEED: <b>115 KCAS</b></div>
    <div>OAT (ISA): <b>{round(15 - 0.0065 * current_row['altitude_m'], 1)}°C</b></div>
    <div>MET: <b>T+{t_idx:03d}s</b></div>
</div>
""", unsafe_allow_html=True)

# Top Tactical Metrics
health_color = "#00ff66" if metrics['health_index'] > 75 else ("#ffb703" if metrics['health_index'] > 45 else "#ff003c")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
    <div class='hud-card'>
        <div class='hud-metric-title'>Health Index</div>
        <div class='hud-metric-value' style='color: {health_color};'>{metrics['health_index']}%</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='hud-card'>
        <div class='hud-metric-title'>Predicted RUL</div>
        <div class='hud-metric-value' style='color: {health_color};'>{metrics['rul_hours']}<span style='font-size: 1rem;'> HRS</span></div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class='hud-card'>
        <div class='hud-metric-title'>Turbine / MAP</div>
        <div class='hud-metric-value' style='color: #00f0ff;'>{current_row['map_inhg']}<span style='font-size: 1rem;'> inHg</span></div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class='hud-card'>
        <div class='hud-metric-title'>Crankshaft RPM</div>
        <div class='hud-metric-value'>{current_row['rpm']}</div>
    </div>
    """, unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div class='hud-card'>
        <div class='hud-metric-title'>Fuel Flow (BSFC)</div>
        <div class='hud-metric-value' style='color: #a78bfa;'>{current_row['fuel_flow']}<span style='font-size: 1rem;'> L/H</span></div>
    </div>
    """, unsafe_allow_html=True)

# Dynamic Tactical Status Advisory
if metrics["severity"] == "RED":
    st.markdown(f"""
    <div class='alert-banner-critical'>
        <strong>⚠️ CRITICAL TACTICAL ADVISORY [MISSION ABORT RECOMMENDED]</strong><br>
        <strong>Fault Mode:</strong> {metrics['status']} &nbsp;|&nbsp; <strong>Diagnostic Root Cause:</strong> {metrics['alert_message']}
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "AMBER":
    st.markdown(f"""
    <div style='background: rgba(60, 40, 0, 0.7); border-left: 6px solid #ffb703; padding: 12px 18px; border-radius: 4px; margin-bottom: 20px; color: #ffe699;'>
        <strong>CAUTION [DEGRADED PROPULSION]:</strong> {metrics['status']} &nbsp;|&nbsp; {metrics['alert_message']}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class='alert-banner-nominal'>
        <strong>✓ ALL PROPULSION SUBSYSTEMS NOMINAL:</strong> Real-time sensor bus tracks within 1σ of thermodynamic mean value model.
    </div>
    """, unsafe_allow_html=True)

# Tactical Tabs
tab_telemetry, tab_schematic, tab_analytics = st.tabs([
    "📈 REAL-TIME SENSOR BUS & RESIDUALS", 
    "🛡️ PROPULSION SUBSYSTEM HEATMAP", 
    "💾 MISSION RECORDER & DEBRIEF"
])

with tab_telemetry:
    col_t1, col_t2 = st.columns(2)
    
    # Custom Dark Plotly Layout Template
    hud_plot_layout = dict(
        paper_bgcolor='rgba(10, 20, 35, 0.4)',
        plot_bgcolor='rgba(7, 14, 25, 0.7)',
        font=dict(family='Share Tech Mono', color='#8892b0'),
        margin=dict(l=35, r=20, t=35, b=25),
        xaxis=dict(gridcolor='rgba(0, 240, 255, 0.1)', zerolinecolor='rgba(0, 240, 255, 0.2)'),
        yaxis=dict(gridcolor='rgba(0, 240, 255, 0.1)', zerolinecolor='rgba(0, 240, 255, 0.2)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    with col_t1:
        st.markdown("<div style='color: #00f0ff; font-weight: bold;'>CYLINDER HEAD TEMPERATURE (THERMODYNAMIC RESIDUAL)</div>", unsafe_allow_html=True)
        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_actual'][:t_idx+1],
            name="Sensor Telemetry", line=dict(color="#ff0055", width=3)
        ))
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_physics'][:t_idx+1],
            name="Physics Twin Target", line=dict(color="#00f0ff", dash="dash", width=2)
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
            name="Physics Model Baseline", line=dict(color="#94a3b8", dash="dash", width=2)
        ))
        fig_oil.add_hline(y=1.5, line_dash="dot", line_color="#ff003c", annotation_text="Cavitation Critical (1.5 bar)")
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

with tab_schematic:
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>2D ENGINE BLOCK & PROPULSION CORE THERMAL SCHEMATIC</div>", unsafe_allow_html=True)
    
    cht_val = current_row['cht_actual']
    oil_p = current_row['oil_press_actual']
    
    cyl_color = "#ff003c" if cht_val > 140 else ("#ffb703" if cht_val > 125 else "#00ff66")
    oil_color = "#ff003c" if oil_p < 1.8 else ("#ffb703" if oil_p < 2.5 else "#00ff66")
    turbo_color = "#00f0ff" if current_row['map_inhg'] < 40 else "#ffb703"
    rad_color = "#ff003c" if cht_val > 130 else "#00ff66"

    fig_block = go.Figure()
    
    # Engine Structural Frame
    fig_block.add_shape(type="rect", x0=0.6, y0=-0.3, x1=3.4, y1=4.6,
                        line=dict(color="rgba(0, 240, 255, 0.4)", width=1, dash="dot"),
                        fillcolor="rgba(10, 20, 35, 0.3)")

    components = [
        {"name": "CYL 01 [FWD-L]", "x": 1.1, "y": 3.2, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "CYL 02 [FWD-R]", "x": 2.9, "y": 3.2, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "CYL 03 [AFT-L]", "x": 1.1, "y": 2.0, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "CYL 04 [AFT-R]", "x": 2.9, "y": 2.0, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "TURBOCHARGER & WASTEGATE", "x": 2.0, "y": 4.1, "color": turbo_color, "desc": f"MAP: {current_row['map_inhg']} inHg"},
        {"name": "LUBRICATION PUMP & GALLERY", "x": 2.0, "y": 1.1, "color": oil_color, "desc": f"OIL: {oil_p} bar"},
        {"name": "HEAT EXCHANGER / RADIATOR", "x": 2.0, "y": 0.1, "color": rad_color, "desc": "COOLANT RETURN"}
    ]

    for c in components:
        fig_block.add_trace(go.Scatter(
            x=[c["x"]], y=[c["y"]],
            mode="markers+text",
            marker=dict(size=56, color=c["color"], symbol="square", line=dict(color="#ffffff", width=1.5)),
            text=[f"<b>{c['name']}</b><br>{c['desc']}"],
            textposition="middle center",
            hoverinfo="text"
        ))

    fig_block.update_layout(
        paper_bgcolor='rgba(5, 10, 20, 0.6)',
        plot_bgcolor='rgba(5, 10, 20, 0.6)',
        font=dict(family='Share Tech Mono', color='#ffffff', size=11),
        height=480,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 4]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.6, 5]),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_block, use_container_width=True)

with tab_analytics:
    st.markdown("<div style='color: #00f0ff; font-weight: bold;'>AUTOMATED POST-FLIGHT TELEMETRY DEBRIEF</div>", unsafe_allow_html=True)
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown(f"""
        * **Recorded Mission Window:** `{len(df)}s synchronized`
        * **Simulated Active Regime:** `{scenario}`
        * **Final Engine Health Index:** `{metrics['health_index']}%`
        * **Max Recorded CHT:** `{df['cht_actual'].max()} °C`
        * **Min Recorded Oil Pressure:** `{df['oil_press_actual'].min()} bar`
        * **Post-Flight Maintenance Action:** `{'CRITICAL: Mandatory Strip-down Overhaul' if metrics['health_index'] < 60 else 'ROUTINE: Turnaround Line Inspection'}`
        """)
    with col_r2:
        csv_export = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 EXPORT BLACKBOX TELEMETRY LOG (.CSV)",
            data=csv_export,
            file_name=f"UAV_AeroTwin_{scenario}_Debrief.csv",
            mime="text/csv"
        )
