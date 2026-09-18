import numpy as np

class EnginePrognostics:
    """
    Evaluates real-time health index, residual anomalies against thermodynamic baseline,
    and prognostic Remaining Useful Life (RUL) for MALE UAV aero piston engines.
    """
    def __init__(self):
        # Critical Operational Redlines (Rotax 914/915 specifications)
        self.CHT_REDLINE = 145.0       # Max continuous cylinder head temp (°C)
        self.OIL_PRESS_MIN = 1.5       # Critical minimum oil pressure (bar)
        self.VIBE_MAX = 2.8            # Critical vibration RMS limit (G)
        self.EGT_REDLINE = 880.0       # Max exhaust gas temp (°C)

    def evaluate_telemetry(self, row):
        """
        Calculates physics deviations, health degradation penalty, and RUL estimation.
        """
        # 1. Physics Residual Calculations
        cht_residual = abs(row["cht_actual"] - row["cht_physics"])
        egt_residual = abs(row["egt_actual"] - row["egt_physics"])
        oil_p_residual = abs(row["oil_press_actual"] - row["oil_press_physics"])
        oil_t_residual = abs(row["oil_temp_actual"] - row["oil_temp_physics"])

        # 2. Dynamic Degradation Penalty Computation
        penalty = 0.0
        # CHT overheat penalty
        if row["cht_actual"] > 120.0:
            penalty += min(45.0, ((row["cht_actual"] - 120.0) / (self.CHT_REDLINE - 120.0)) * 45.0)

        # Oil pressure loss penalty
        if row["oil_press_actual"] < 3.0:
            penalty += min(45.0, ((3.0 - row["oil_press_actual"]) / (3.0 - self.OIL_PRESS_MIN)) * 45.0)

        # Vibration / Knock penalty
        if row["vibration_rms"] > 1.4:
            penalty += min(20.0, ((row["vibration_rms"] - 1.4) / (self.VIBE_MAX - 1.4)) * 20.0)

        # Base health index score (0 to 100%)
        health_index = max(5.0, min(100.0, 100.0 - penalty))

        # 3. Fault Classification & Tactical Diagnostics
        status = "NOMINAL"
        alert_msg = "All propulsion parameters within thermodynamic tolerances."
        severity_level = "GREEN"

        if row["cht_actual"] >= self.CHT_REDLINE or row["vibration_rms"] >= self.VIBE_MAX:
            status = "CRITICAL: THERMAL RUNAWAY & DETONATION"
            alert_msg = "Severe cylinder overheating with knocking. Imminent piston seizure risk. Immediate RTB required."
            severity_level = "RED"
        elif row["oil_press_actual"] <= self.OIL_PRESS_MIN:
            status = "CRITICAL: LUBRICATION FAILURE"
            alert_msg = "Oil gallery pressure collapsed below 1.5 bar. Bearing wipe imminent. Throttle reduction mandatory."
            severity_level = "RED"
        elif health_index < 75.0:
            status = "WARNING: PROGRESSIVE DEGRADATION"
            alert_msg = "Anomalous physics residual drift detected. Subsystem efficiency degrading."
            severity_level = "AMBER"

        # 4. Dynamic Remaining Useful Life (RUL) in flight hours
        if health_index > 85.0:
            rul_hours = 120.0  # Routine service interval
        elif severity_level == "RED":
            # Emergency exponential decay of RUL
            rul_hours = max(0.05, round((health_index / 100.0) * 1.8, 2))
        else:
            rul_hours = max(0.5, round((health_index / 100.0) * 14.5, 2))

        return {
            "health_index": round(health_index, 1),
            "status": status,
            "severity": severity_level,
            "alert_message": alert_msg,
            "rul_hours": rul_hours,
            "residuals": {
                "cht_delta": round(cht_residual, 2),
                "egt_delta": round(egt_residual, 2),
                "oil_p_delta": round(oil_p_residual, 2),
                "oil_t_delta": round(oil_t_residual, 2)
            }
        }

if __name__ == "__main__":
    from engine_physics import AeroPistonDigitalTwin
    
    twin = AeroPistonDigitalTwin()
    prognostics = EnginePrognostics()
    
    # Test on a degraded cycle
    df = twin.generate_mission_telemetry(total_seconds=150, fault_scenario="COOLING_FAILURE")
    final_point = df.iloc[-1]
    result = prognostics.evaluate_telemetry(final_point)
    
    print("\n--- Digital Twin Prognostics Diagnostic ---")
    print(f"Status:        {result['status']}")
    print(f"Health Index:  {result['health_index']}%")
    print(f"Remaining RUL: {result['rul_hours']} Flight Hours")
    print(f"Alert:         {result['alert_message']}")
    print(f"Residuals:     {result['residuals']}")