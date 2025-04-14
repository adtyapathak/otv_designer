import math
import streamlit as st

# Constants
MU_EARTH = 398600.4418  # Earth's standard gravitational parameter, km^3/s^2
R_EARTH = 6371.0         # Earth's radius in km

def orbital_velocity(radius):
    return math.sqrt(MU_EARTH / radius)

def hohmann_delta_v(r1, r2):
    a_transfer = (r1 + r2) / 2
    v1 = orbital_velocity(r1)
    v2 = orbital_velocity(r2)
    v_transfer1 = math.sqrt(2 * MU_EARTH * r2 / (r1 * (r1 + r2)))
    v_transfer2 = math.sqrt(2 * MU_EARTH * r1 / (r2 * (r1 + r2)))
    delta_v1 = abs(v_transfer1 - v1)
    delta_v2 = abs(v2 - v_transfer2)
    return delta_v1 + delta_v2

def bielliptic_delta_v(r1, r2, r_b):
    # r_b is the intermediate apoapsis radius
    v1 = orbital_velocity(r1)
    v_transfer1 = math.sqrt(2 * MU_EARTH * r_b / (r1 * (r1 + r_b)))
    delta_v1 = abs(v_transfer1 - v1)

    v_b1 = math.sqrt(2 * MU_EARTH * r1 / (r_b * (r1 + r_b)))
    v_b2 = math.sqrt(2 * MU_EARTH * r2 / (r_b * (r2 + r_b)))
    delta_v2 = abs(v_b2 - v_b1)

    v2 = orbital_velocity(r2)
    v_transfer2 = math.sqrt(2 * MU_EARTH * r_b / (r2 * (r2 + r_b)))
    delta_v3 = abs(v2 - v_transfer2)

    return delta_v1 + delta_v2 + delta_v3

def choose_transfer(initial_altitude_km, final_altitude_km):
    r1 = R_EARTH + initial_altitude_km
    r2 = R_EARTH + final_altitude_km

    # Calculate Hohmann delta-v
    dv_hohmann = hohmann_delta_v(r1, r2)

    # Try bi-elliptic with several intermediate points (e.g., 2x, 5x, 10x final altitude)
    best_bielliptic_dv = float('inf')
    for multiplier in [2, 5, 10]:
        r_b = multiplier * max(r1, r2)
        dv_bielliptic = bielliptic_delta_v(r1, r2, r_b)
        if dv_bielliptic < best_bielliptic_dv:
            best_bielliptic_dv = dv_bielliptic

    if best_bielliptic_dv < dv_hohmann:
        return {
            "method": "bi-elliptic",
            "delta_v_kms": best_bielliptic_dv
        }
    else:
        return {
            "method": "hohmann",
            "delta_v_kms": dv_hohmann
        }
    
def inclination_change_delta_v(altitude_km, delta_inclination_deg):
    """
    Calculate the delta-v required to change the orbital inclination.
    
    Parameters:
        altitude_km (float): Orbit altitude above Earth's surface in kilometers.
        delta_inclination_deg (float): Change in inclination in degrees.
    
    Returns:
        float: Delta-v required in km/s.
    """
    r = R_EARTH + altitude_km  # Orbital radius in km
    v = orbital_velocity(r)    # Orbital speed in km/s
    delta_i_rad = math.radians(delta_inclination_deg)
    delta_v = 2 * v * math.sin(delta_i_rad / 2)
    return delta_v


def ltan_drift_adjustment(
    initial_ltan_hours,
    target_ltan_hours,
    initial_altitude_km,
    duration_days
):
    J2 = 1.08263e-3
    mu = MU_EARTH
    R = R_EARTH

    # Convert LTAN difference to degrees
    delta_ltan_deg = (target_ltan_hours - initial_ltan_hours) * 15  # 15 deg/hour
    # Normalize to [-180, 180]
    delta_ltan_deg = ((delta_ltan_deg + 180) % 360) - 180
    # Required nodal drift rate (deg/day)
    required_drift_rate = delta_ltan_deg / duration_days

    best_solution = None
    min_dv = float('inf')

    # Try a range of altitudes to find one that works
    for h in range(400, 900, 5):  # altitudes in km
        a = R + h
        n = math.sqrt(mu / a**3)  # rad/s
        drift_factor = -1.5 * J2 * (R**2) * n / (a**2)

        # Required inclination to match the drift rate
        drift_rate_rad_per_sec = math.radians(required_drift_rate) / 86400  # deg/day -> rad/sec
        cos_i = drift_rate_rad_per_sec / drift_factor

        if abs(cos_i) <= 1:
            i_rad = math.acos(cos_i)
            i_deg = math.degrees(i_rad)

            # Estimate delta-v just to change altitude + inclination (not optimized!)
            current_r = R + initial_altitude_km
            new_r = R + h
            # v1 = orbital_velocity(current_r)
            # v2 = orbital_velocity(new_r)
            # dv_alt = abs(v2 - v1)


            delta_i_rad = abs(i_rad - math.radians(98.6))  # Typical SSO inclination
            # dv_inc = 2 * v2 * math.sin(delta_i_rad / 2)
            # total_dv = dv_alt + dv_inc

            total_dv = hohmann_delta_v(current_r, new_r) + inclination_change_delta_v(h,math.degrees(delta_i_rad))

            if total_dv < min_dv:
                min_dv = total_dv
                best_solution = {
                    "new_altitude_km": h,
                    "new_inclination_deg": i_deg,
                    "total_delta_v_kms": total_dv,
                    "required_drift_deg_per_day": required_drift_rate,
                    "duration_days": duration_days
                }

    return best_solution

def otv_sizing(
    payload_mass_kg,
    total_delta_v_kms,
    isp_sec=320,
    structural_mass_fraction=0.1,
    thrust_to_weight_ratio=0.3
):
    """
    Designs an Orbital Transfer Vehicle (OTV) configuration.

    Parameters:
        payload_mass_kg (float): Mass of the payload (kg).
        total_delta_v_kms (float): Required delta-v in km/s.
        isp_sec (float): Specific impulse of the propulsion system (s).
        structural_mass_fraction (float): Structural fraction (e.g., 0.1 = 10%).
        thrust_to_weight_ratio (float): Desired T/W for thrust sizing.

    Returns:
        dict: Mass breakdown and thrust estimate.
    """
    g0 = 9.80665  # m/s²
    delta_v = total_delta_v_kms * 1000  # convert to m/s

    # First, guess total dry mass (payload + structure)
    dry_mass = payload_mass_kg / (1 - structural_mass_fraction)
    
    # Solve rocket equation for m0 (initial mass)
    m0 = dry_mass * math.exp(delta_v / (isp_sec * g0))
    propellant_mass = m0 - dry_mass
    structural_mass = dry_mass - payload_mass_kg

    # Thrust estimation
    weight = m0 * g0  # in N
    thrust = weight * thrust_to_weight_ratio  # N

    return {
        "payload_mass_kg": payload_mass_kg,
        "structural_mass_kg": structural_mass,
        "propellant_mass_kg": propellant_mass,
        "total_mass_kg": m0,
        "payload_fraction": payload_mass_kg / m0,
        "propellant_fraction": propellant_mass / m0,
        "structural_fraction": structural_mass / m0,
        "thrust_N": thrust,
        "thrust_to_weight_ratio": thrust_to_weight_ratio,
        "isp_sec": isp_sec
    }



#####################

st.title("OTV Configuration Designer")


st.header("Fligth Dynamics Requirements")

st.subheader("Altitude Change")

h1 = st.number_input("Enter Initial Altitude", value=500)
h2 = st.number_input("Enter Final Altitude", value=600)

delta_v_budget = 0

result = choose_transfer(h1, h2)
print(f"Best method for altitude change: {result['method']}, Total Δv: {result['delta_v_kms']:.3f} km/s")
st.write("Delta-V Required", result['delta_v_kms'])

delta_v_budget += result['delta_v_kms']

st.subheader("Inclination Change")

h_incl = st.number_input("Enter Altitude", value=500)
inc = st.number_input("Enter Change in Inclination", value=5)

dv_inc = inclination_change_delta_v(h_incl, inc)  # 30-degree plane change at 500 km altitude
print(f"Delta-v required for inclination change: {dv_inc:.3f} km/s")

st.write("Delta-V Required", dv_inc)

delta_v_budget += dv_inc

st.subheader("LTAN Change")

h_ltan = st.number_input("Enter Initial Altitude", value=500, key='h_ltan')
ltan_i = st.number_input("Enter Initial LTAN (hours)", value=9, key='ltan_i')
ltan_f = st.number_input("Enter Final LTAN (hours)", value=6, key='ltan_f')
ltan_dur = st.number_input("Enter duration (days)", value=90, key= 'ltan_dur')

result = ltan_drift_adjustment(
    initial_ltan_hours=ltan_i,
    target_ltan_hours=ltan_f,
    initial_altitude_km=h_ltan,
    duration_days=ltan_dur
)

print(f"New altitude: {result['new_altitude_km']} km")
print(f"New inclination: {result['new_inclination_deg']:.3f}°")
print(f"Total Δv: {result['total_delta_v_kms']:.3f} km/s")
print(f"Drift rate: {result['required_drift_deg_per_day']:.4f} deg/day over {result['duration_days']} days")

st.write("Delta-V Required", result['total_delta_v_kms'])

delta_v_budget += result['total_delta_v_kms']

print("Overall total delta-v required: {:.3f} km/s".format(delta_v_budget))

st.write("Total Delta-V Required", delta_v_budget)

config = otv_sizing(payload_mass_kg=500, total_delta_v_kms=delta_v_budget,isp_sec=300)

for k, v in config.items():
    print(f"{k}: {v:.3f}" if isinstance(v, float) else f"{k}: {v}")