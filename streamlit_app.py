from otv_flight_dynamics import *

st.set_page_config(layout="wide")
st.title("OTV Designer")

# Sidebar
st.sidebar.title("App Modules")
module = st.sidebar.radio("Select a module", ["Flight Dynamics", "OTV Sizing", "Commercial"])


if module == "Flight Dynamics":

    st.header("Fligth Dynamics Requirements")
    delta_v_budget = 0

    # Two equal columns:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Altitude Change")
        h1 = st.number_input("Enter Initial Altitude (km)", 300, 40000, value=500)
        h2 = st.number_input("Enter Final Altitude (km)", 300, 40000, value=600)

        result = choose_transfer(h1, h2)
        # st.write("Delta-V Required:", f"{result['delta_v_kms']:.5f}")
        st.markdown(f"<span style='color:red; font-size:16px;'>**Delta-V Required (km/s)**: {result['delta_v_kms']:.5f}</span>", unsafe_allow_html=True)
        delta_v_budget += result['delta_v_kms']

        st.subheader("Inclination Change")
        h_incl = st.number_input("Enter Altitude (km)", 300, 40000, value=500)
        inc = st.number_input("Enter Change in Inclination (deg)", 0.0, 30.0, value=5.0)

        dv_inc = inclination_change_delta_v(h_incl, inc)  
        # st.write("Delta-V Required:", f"{dv_inc:.5f}")
        st.markdown(f"<span style='color:red; font-size:16px;'>**Delta-V Required (km/s)**: {dv_inc:.5f}</span>", unsafe_allow_html=True)
        delta_v_budget += dv_inc

    with col2:
        st.subheader("LTAN Change")
        h_ltan = st.number_input("Enter Initial Altitude (km)", 300, 40000, value=500, key='h_ltan')
        ltan_i = st.number_input("Enter Initial LTAN (hours)", 0.0, 24.0, value=10.5, key='ltan_i')
        ltan_f = st.number_input("Enter Final LTAN (hours)", 0.0, 24.0, value=6.0, key='ltan_f')
        ltan_dur = st.number_input("Enter duration (days)", 10, 360, value=90, key= 'ltan_dur')

        result = ltan_drift_adjustment(
            initial_ltan_hours=ltan_i,
            target_ltan_hours=ltan_f,
            initial_altitude_km=h_ltan,
            duration_days=ltan_dur
        )
        # st.write("Delta-V Required:", f"{result['total_delta_v_kms']:.5f}"
        st.markdown(f"<span style='color:red; font-size:16px;'>**Delta-V Required (km/s)**: {result['total_delta_v_kms']:.5f}</span>", unsafe_allow_html=True)
        delta_v_budget += result['total_delta_v_kms']
        st.markdown(f"<span style='color:blue; font-size:16px;'>**Inclination Required (deg)**: {result['inclination_deg']:.2f}</span>", unsafe_allow_html=True)


    st.markdown("---")
    st.metric(label="Total Delta-V Required (km/s):", value=f"{delta_v_budget:.5f}")


elif module == "OTV Sizing":
    st.header("OTV Sizing")

    otv_pld = st.number_input("Enter Payload Mass (kg)", 10, 5000, value=500)
    otv_dv = st.number_input("Enter Total Delta-V (km/s)", 0.1, 10.0, value=2.0)
    otv_isp = st.number_input("Enter Specific Impulse (s)", 50, 5000, value=300)
    otv_smf = st.number_input("Enter Structural Mass Fraction", 0.0, 1.0, value=0.1)
    otv_twr = st.number_input("Enter Thrust to Weight Ratio", 0.0, 1.0, value=0.3)

    config = otv_sizing(payload_mass_kg=otv_pld, total_delta_v_kms = otv_dv, isp_sec=otv_isp,structural_mass_fraction=otv_smf,thrust_to_weight_ratio=otv_twr)

    st.markdown("---")
    # for k, v in config.items():
        # print(f"{k}: {v:.3f}" if isinstance(v, float) else f"{k}: {v}")
        # st.metric(label=k, value=f"{v:.5f}")
    st.metric(label="Wet Mass (kg)", value=config["total_mass_kg"])
    st.metric(label="Propellant Mass (kg)", value=config["propellant_mass_kg"])
    st.metric(label="Payload Fraction", value=config["payload_fraction"])
    st.metric(label="Propellant Fraction", value=config["propellant_fraction"])
    st.metric(label="Thrust (N)", value=config["thrust_N"])

elif module == "Commercial":
    st.header("Commercial")
    st.write("This module is under development. Please check back later!")
