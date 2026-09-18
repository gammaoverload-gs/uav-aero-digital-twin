import os
import sys
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import streamlit as st  # type: ignore

# Ensure root directory is accessible for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine_physics import AeroPistonDigitalTwin  # type: ignore
from core.prognostics import EnginePrognostics  # type: ignore

st.set_page_config(
    page_title="MALE UAV Aero Piston Digital Twin",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cockpit UI Styling
st.markdown("""
<style>
    .metric-container {
        background-color: #0b132b;
        border-radius: 10px;
        padding: 14px;
        border: 1px solid #1c2541;
    }
    .status-banner-red {
        background-color: #450a0a;
        border-left: 6px solid #ef4444;
        padding: 14px;
        border-radius: 6px;
        color: #fecaca;
        margin-bottom: 15px;
    }
    .status-banner-green {
        background-color: #052e16;
        border-left: 6px solid #22c55e;
        padding: 14px;
        border-radius: 6px;
        color: #bbf7d0;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Mission Controls
st.sidebar.title("🎮 UAV Ground Control")
scenario = st.sidebar.selectbox(
    "Active Mission Scenario",
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
st.sidebar.subheader("⏱️ Mission Scrubber")
t_idx = st.sidebar.slider("Mission Elapsed Time (MET seconds)", 0, len(df) - 1, 130)

current_row = df.iloc[t_idx]
metrics = prognostics.evaluate_telemetry(current_row)

# Header Telemetry Strip
st.title("🛡️ MALE UAV Aero Piston Engine — Digital Twin Cockpit")
st.caption(f"Telemetry Bus: **SocketCAN J1939** | Regime: **{current_row['flight_phase']}** | Altitude: **{current_row['altitude_m']} m** | Airspeed: **115 kts**")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Health Index", f"{metrics['health_index']}%", delta=f"{metrics['health_index'] - 100:.1f}%")
k2.metric("Predicted RUL", f"{metrics['rul_hours']} hrs")
k3.metric("Engine RPM", f"{current_row['rpm']}")
k4.metric("Manifold Pressure", f"{current_row['map_inhg']} inHg")
k5.metric("Fuel Consumption", f"{current_row['fuel_flow']} L/h")

st.markdown("---")

# Tactical Alert Banner
if metrics["severity"] == "RED":
    st.markdown(f"""
    <div class="status-banner-red">
        <strong>CRITICAL FLIGHT SAFETY ADVISORY:</strong> {metrics['status']}<br>
        <strong>Diagnostic Detail:</strong> {metrics['alert_message']}
    </div>
    """, unsafe_allow_html=True)
elif metrics["severity"] == "AMBER":
    st.warning(f"⚠️ **{metrics['status']}** — {metrics['alert_message']}")
else:
    st.markdown(f"""
    <div class="status-banner-green">
        <strong>SYSTEM STATUS: NOMINAL.</strong> All physical parameters align with thermodynamic equilibrium model.
    </div>
    """, unsafe_allow_html=True)

# Main Multi-Tab View
tab1, tab2, tab3 = st.tabs(["📊 Live Telemetry & Residuals", "🧩 Engine Component Heatmap", "📋 Post-Flight Debrief"])

with tab1:
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Thermodynamic Residual: CHT Actual vs Physics Baseline")
        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_actual'][:t_idx+1],
            name="Sensor Telemetry", line=dict(color="#ef4444", width=2.5)
        ))
        fig_cht.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['cht_physics'][:t_idx+1],
            name="Physics Twin Baseline", line=dict(color="#38bdf8", dash="dash", width=2)
        ))
        fig_cht.add_hline(y=145.0, line_dash="dot", line_color="#f97316", annotation_text="CHT Redline (145°C)")
        fig_cht.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="MET (sec)", yaxis_title="°C")
        st.plotly_chart(fig_cht, use_container_width=True)

    with col_right:
        st.subheader("Lubrication Circuit: Oil Gallery Pressure vs Model")
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['oil_press_actual'][:t_idx+1],
            name="Oil Pressure (Sensor)", line=dict(color="#10b981", width=2.5)
        ))
        fig_oil.add_trace(go.Scatter(
            x=df['timestamp'][:t_idx+1], y=df['oil_press_physics'][:t_idx+1],
            name="Nominal Baseline", line=dict(color="#94a3b8", dash="dash", width=2)
        ))
        fig_oil.add_hline(y=1.5, line_dash="dot", line_color="#dc2626", annotation_text="Minimum Cavitation Limit (1.5 bar)")
        fig_oil.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="MET (sec)", yaxis_title="bar")
        st.plotly_chart(fig_oil, use_container_width=True)

    st.subheader("Physics Residual Tracking Matrix")
    res_table = [
        {"Subsystem": "Cylinder Head Temp (CHT)", "Actual Telemetry": f"{current_row['cht_actual']} °C", "Physics Model": f"{current_row['cht_physics']} °C", "Residual Error (e)": f"{metrics['residuals']['cht_delta']} °C", "Condition": "CRITICAL" if metrics['residuals']['cht_delta'] > 15.0 else "NOMINAL"},
        {"Subsystem": "Exhaust Gas Temp (EGT)", "Actual Telemetry": f"{current_row['egt_actual']} °C", "Physics Model": f"{current_row['egt_physics']} °C", "Residual Error (e)": f"{metrics['residuals']['egt_delta']} °C", "Condition": "NOMINAL"},
        {"Subsystem": "Oil Gallery Pressure", "Actual Telemetry": f"{current_row['oil_press_actual']} bar", "Physics Model": f"{current_row['oil_press_physics']} bar", "Residual Error (e)": f"{metrics['residuals']['oil_p_delta']} bar", "Condition": "CRITICAL" if metrics['residuals']['oil_p_delta'] > 1.5 else "NOMINAL"},
        {"Subsystem": "Crankshaft Vibration", "Actual Telemetry": f"{current_row['vibration_rms']} G", "Physics Model": "1.10 G", "Residual Error (e)": f"{round(abs(current_row['vibration_rms'] - 1.1), 2)} G", "Condition": "DETONATION" if current_row['vibration_rms'] > 1.8 else "NOMINAL"}
    ]
    st.dataframe(pd.DataFrame(res_table), use_container_width=True)

with tab2:
    st.subheader("Propulsion Subsystem Thermal & Mechanical Stress Map")
    st.caption("Visual schematic showing physical health degradation mapped across engine components.")
    
    cht_val = current_row['cht_actual']
    oil_p = current_row['oil_press_actual']
    
    cyl_color = "#ef4444" if cht_val > 140 else ("#f59e0b" if cht_val > 125 else "#10b981")
    oil_color = "#ef4444" if oil_p < 1.8 else ("#f59e0b" if oil_p < 2.5 else "#10b981")
    turbo_color = "#10b981" if current_row['map_inhg'] < 40 else "#f59e0b"
    rad_color = "#ef4444" if cht_val > 130 else "#10b981"

    fig_engine = go.Figure()
    
    components = [
        {"name": "Cylinder 1 (FWD-L)", "x": 1, "y": 3, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "Cylinder 2 (FWD-R)", "x": 3, "y": 3, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "Cylinder 3 (AFT-L)", "x": 1, "y": 2, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "Cylinder 4 (AFT-R)", "x": 3, "y": 2, "color": cyl_color, "desc": f"CHT: {cht_val}°C"},
        {"name": "Turbocharger & Wastegate", "x": 2, "y": 4, "color": turbo_color, "desc": f"MAP: {current_row['map_inhg']} inHg"},
        {"name": "Oil Gallery & Pump", "x": 2, "y": 1, "color": oil_color, "desc": f"Press: {oil_p} bar"},
        {"name": "Cooling Radiator & Jacket", "x": 2, "y": 0, "color": rad_color, "desc": "Coolant Loop"}
    ]

    for c in components:
        fig_engine.add_trace(go.Scatter(
            x=[c["x"]], y=[c["y"]],
            mode="markers+text",
            marker=dict(size=52, color=c["color"], symbol="square", line=dict(color="#ffffff", width=1.5)),
            text=[f"<b>{c['name']}</b><br>{c['desc']}"],
            textposition="top center",
            hoverinfo="text"
        ))

    fig_engine.update_layout(
        template="plotly_dark",
        height=450,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 4]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 5]),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_engine, use_container_width=True)

with tab3:
    st.subheader("Automated Mission Debrief & Maintenance Log")
    
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        st.markdown(f"""
        * **Total Mission Elapsed Time:** `{len(df)} seconds`
        * **Operating Scenario:** `{scenario}`
        * **Final Engine Health Index:** `{metrics['health_index']}%`
        * **Peak Cylinder Head Temperature:** `{df['cht_actual'].max()} °C`
        * **Minimum Oil Pressure Observed:** `{df['oil_press_actual'].min()} bar`
        * **Recommended Action:** `{'Immediate Engine Teardown & Inspection' if metrics['health_index'] < 60 else 'Post-Flight Routine Inspection'}`
        """)
    
    with col_rep2:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Mission Telemetry (.CSV)",
            data=csv_data,
            file_name=f"UAV_Mission_{scenario}_Telemetry.csv",
            mime="text/csv"
        )