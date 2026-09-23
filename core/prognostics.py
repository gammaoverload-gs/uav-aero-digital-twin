import numpy as np

class EnginePrognostics:
    """
    Diagnostic anomaly detector and Remaining Useful Life (RUL) estimator.
    """
    def __init__(self):
        self.nominal_baseline = 100.0

    def evaluate_telemetry(self, row):
        # Safe getter helper for Series or Dict
        def get_val(key, default):
            try:
                if key in row and not np.isnan(row[key]):
                    return float(row[key])
            except Exception:
                pass
            return float(default)

        cht_actual = get_val("cht_actual", 110.0)
        cht_physics = get_val("cht_physics", 110.0)
        oil_p_actual = get_val("oil_press_actual", 4.2)
        oil_p_physics = get_val("oil_press_physics", 4.2)
        oil_t_actual = get_val("oil_temp_actual", 92.0)
        oil_t_physics = get_val("oil_temp_physics", 90.0)
        egt_actual = get_val("egt_actual", 810.0)
        egt_physics = get_val("egt_physics", 810.0)
        vibration = get_val("vibration_rms", 1.1)

        cht_residual = round(abs(cht_actual - cht_physics), 2)
        oil_p_residual = round(abs(oil_p_actual - oil_p_physics), 2)
        oil_t_residual = round(abs(oil_t_actual - oil_t_physics), 2)
        egt_residual = round(abs(egt_actual - egt_physics), 2)

        # Health penalty computation
        penalty = 0.0
        penalty += min(45.0, cht_residual * 1.8)
        penalty += min(35.0, oil_p_residual * 16.0)
        penalty += min(15.0, max(0.0, (vibration - 1.1) * 20.0))

        health_index = max(5.0, round(100.0 - penalty, 1))

        # Prognostic RUL calculation (hours)
        if health_index > 75:
            rul_hours = round(max(3.5, 6.0 * (health_index / 100.0)), 2)
            severity = "GREEN"
            status = "PROPULSION NOMINAL"
            alert_message = "All thermodynamic parameters within tolerance."
        elif health_index > 45:
            rul_hours = round(max(1.2, 3.5 * (health_index / 100.0)), 2)
            severity = "AMBER"
            status = "DEGRADED PROPULSION"
            alert_message = "Thermal or lubrication drift detected. Monitor closely."
        else:
            rul_hours = round(max(0.25, 1.2 * (health_index / 100.0)), 2)
            severity = "RED"
            status = "CRITICAL: THERMAL RUNAWAY & DETONATION"
            alert_message = "Severe cylinder overheating with knocking. Imminent piston seizure risk. Immediate RTB required."

        return {
            "health_index": health_index,
            "rul_hours": rul_hours,
            "severity": severity,
            "status": status,
            "alert_message": alert_message,
            "residuals": {
                "cht_delta": cht_residual,
                "oil_p_delta": oil_p_residual,
                "oil_t_delta": oil_t_residual,
                "egt_delta": egt_residual
            }
        }
