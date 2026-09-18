import numpy as np  # type: ignore
import pandas as pd  # type: ignore

class AeroPistonDigitalTwin:
    """
    Simulates a turbocharged 4-stroke aero piston engine (Rotax 914/915 class)
    used in Medium Altitude Long Endurance (MALE) UAVs.
    """
    def __init__(self):
        self.nominal_rpm = 5000.0
        self.nominal_map = 35.0  # inHg (Manifold Absolute Pressure)
        
    def isa_atmosphere(self, altitude_m):
        """
        International Standard Atmosphere (ISA) calculation.
        Computes ambient temperature and barometric pressure for a given altitude.
        """
        t0 = 288.15      # Sea level standard temp (Kelvin)
        p0 = 101325.0    # Sea level standard pressure (Pa)
        lapse_rate = 0.0065 # K/m
        g = 9.80665
        m = 0.0289644
        r0 = 8.31447

        t_amb = t0 - (lapse_rate * altitude_m)
        p_amb = p0 * (1.0 - (lapse_rate * altitude_m) / t0) ** ((g * m) / (r0 * lapse_rate))
        
        return t_amb - 273.15, p_amb / 1000.0

    def calculate_physics_baseline(self, rpm, map_inhg, altitude_m):
        """
        Thermodynamic baseline: Computes expected healthy sensor readings
        based on current engine operating point and flight conditions.
        """
        t_amb, _ = self.isa_atmosphere(altitude_m)
        engine_load = (rpm / 5800.0) * (map_inhg / 40.0)

        # First-principles thermodynamic approximations
        expected_cht = 100.0 + (engine_load * 35.0) + (t_amb * 0.15)
        expected_egt = 730.0 + (engine_load * 110.0)
        expected_oil_press = 5.0 - (engine_load * 0.8)
        expected_oil_temp = 85.0 + (engine_load * 22.0)
        fuel_flow = 12.0 + (engine_load * 18.0) # Liters per hour

        return {
            "phys_cht": expected_cht,
            "phys_egt": expected_egt,
            "phys_oil_press": expected_oil_press,
            "phys_oil_temp": expected_oil_temp,
            "phys_fuel_flow": fuel_flow
        }

    def generate_mission_telemetry(self, total_seconds=200, fault_scenario="NOMINAL"):
        """
        Generates flight telemetry with synchronized physics baseline
        and controlled fault injection for digital twin testing.
        """
        records = []
        for t in range(total_seconds):
            # Dynamic flight regimes: Climb -> Cruise -> Loiter
            if t < 50:
                flight_phase = "CLIMB"
                altitude = 500 + (t * 30)
                rpm = 5400 + np.random.normal(0, 15)
                map_val = 38.0 + np.random.normal(0, 0.2)
            elif t < 150:
                flight_phase = "CRUISE"
                altitude = 2000
                rpm = 5000 + np.random.normal(0, 10)
                map_val = 35.0 + np.random.normal(0, 0.1)
            else:
                flight_phase = "LOITER"
                altitude = 2000
                rpm = 4600 + np.random.normal(0, 10)
                map_val = 31.0 + np.random.normal(0, 0.1)

            # Expected physics baseline
            phys = self.calculate_physics_baseline(rpm, map_val, altitude)

            # Actual sensor readings (Physics + Normal Sensor Noise)
            cht = phys["phys_cht"] + np.random.normal(0, 1.0)
            egt = phys["phys_egt"] + np.random.normal(0, 2.5)
            oil_p = phys["phys_oil_press"] + np.random.normal(0, 0.05)
            oil_t = phys["phys_oil_temp"] + np.random.normal(0, 0.4)
            vibration = 1.1 + np.random.normal(0, 0.03)

            # Inject Failures based on scenario
            if fault_scenario == "COOLING_FAILURE" and t >= 80:
                severity = (t - 80) / (total_seconds - 80)
                cht += severity * 50.0
                oil_t += severity * 28.0
                vibration += severity * 2.0  # Detonation knock signature
            elif fault_scenario == "LUBRICATION_LOSS" and t >= 100:
                severity = (t - 100) / (total_seconds - 100)
                oil_p -= severity * 3.5
                oil_t += severity * 35.0

            records.append({
                "timestamp": t,
                "flight_phase": flight_phase,
                "altitude_m": round(altitude, 1),
                "rpm": round(rpm, 1),
                "map_inhg": round(map_val, 2),
                "cht_actual": round(cht, 2),
                "cht_physics": round(phys["phys_cht"], 2),
                "egt_actual": round(egt, 2),
                "egt_physics": round(phys["phys_egt"], 2),
                "oil_press_actual": round(oil_p, 2),
                "oil_press_physics": round(phys["phys_oil_press"], 2),
                "oil_temp_actual": round(oil_t, 2),
                "oil_temp_physics": round(phys["phys_oil_temp"], 2),
                "vibration_rms": round(vibration, 2),
                "fuel_flow": round(phys["phys_fuel_flow"], 2)
            })

        return pd.DataFrame(records)

if __name__ == "__main__":
    twin = AeroPistonDigitalTwin()
    df = twin.generate_mission_telemetry(total_seconds=10, fault_scenario="NOMINAL")
    print("\n--- Digital Twin Physics Engine Working ---")
    print(df[["timestamp", "flight_phase", "altitude_m", "cht_actual", "cht_physics"]].head())