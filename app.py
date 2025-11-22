# wind_app.py
import math
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Wind Energy Analyzer",
    layout="wide"
)

st.title("🌬️ Wind Energy Analyzer (Basic Version)")
st.write(
    "Estimate wind power density, turbine power curve, and annual energy production for a site. "
    "Uses a simple Rayleigh wind distribution and an approximate power curve."
)

# ---------------------------
# 1. SIMPLE LOCATION DATABASE
# ---------------------------
# You can expand or replace with real wind datasets later.
WIND_LOCATIONS = {
    "Kolkata, India": {
        "avg_wind_ms": 3.5
    },
    "Hamburg, Germany": {
        "avg_wind_ms": 5.5
    },
    "Offshore North Sea": {
        "avg_wind_ms": 8.5
    },
    "Munich, Germany": {
        "avg_wind_ms": 4.5
    },
}

AIR_DENSITY = 1.225  # kg/m³, sea-level standard

# ---------------------------
# 2. SIDEBAR INPUTS
# ---------------------------
st.sidebar.header("Inputs")

location = st.sidebar.selectbox(
    "Location",
    options=list(WIND_LOCATIONS.keys()),
    index=1
)

default_v = WIND_LOCATIONS[location]["avg_wind_ms"]
avg_wind_speed = st.sidebar.slider(
    "Average wind speed at hub height (m/s)",
    min_value=2.0,
    max_value=12.0,
    value=float(default_v),
    step=0.1
)

rated_power_kw = st.sidebar.number_input(
    "Turbine rated power (kW)",
    min_value=0.5,
    max_value=5000.0,
    value=2000.0,  # 2 MW baseline
    step=0.5
)

rotor_diameter = st.sidebar.number_input(
    "Rotor diameter (m)",
    min_value=1.0,
    max_value=200.0,
    value=90.0,
    step=1.0
)

cut_in = st.sidebar.slider(
    "Cut-in speed (m/s)",
    min_value=2.0,
    max_value=6.0,
    value=3.0,
    step=0.1
)

rated_speed = st.sidebar.slider(
    "Rated speed (m/s)",
    min_value=7.0,
    max_value=15.0,
    value=11.5,
    step=0.1
)

cut_out = st.sidebar.slider(
    "Cut-out speed (m/s)",
    min_value=15.0,
    max_value=30.0,
    value=25.0,
    step=0.5
)

cp_max = st.sidebar.slider(
    "Approx. maximum Cp (power coefficient)",
    min_value=0.25,
    max_value=0.50,
    value=0.40,
    step=0.01
)

# ---------------------------
# 3. BASIC CALCULATIONS
# ---------------------------
# 3.1 Wind power density at average speed
wind_power_density = 0.5 * AIR_DENSITY * avg_wind_speed**3  # W/m²

# Swept area
swept_area = math.pi * (rotor_diameter / 2.0) ** 2  # m²

# ---------------------------
# 3.2 Approximate power curve (deterministic)
# ---------------------------
def power_curve(v, cut_in, rated_speed, cut_out, rated_power_kw):
    """Very simple piecewise power curve in kW."""
    if v < cut_in or v >= cut_out:
        return 0.0
    elif v >= rated_speed:
        return rated_power_kw
    else:
        # Between cut-in and rated: cubic ramp scaled to match rated at v_rated
        # P ~ (v - v_ci)^3 / (v_rated - v_ci)^3
        return rated_power_kw * ((v - cut_in) / (rated_speed - cut_in)) ** 3

# Discretize wind speeds for curve and AEP integration
v_values = np.arange(0.0, 30.1, 0.5)
power_values = np.array([power_curve(v, cut_in, rated_speed, cut_out, rated_power_kw)
                         for v in v_values])

# ---------------------------
# 3.3 Rayleigh wind distribution for given mean speed
# ---------------------------
# Rayleigh is a special case of Weibull with k = 2.
# Mean wind speed V_mean = c * sqrt(pi/2) => c = V_mean * sqrt(2/pi)
c_scale = avg_wind_speed * math.sqrt(2.0 / math.pi)

def rayleigh_pdf(v, c):
    """Rayleigh PDF for wind speeds."""
    return (v / c**2) * np.exp(- (v**2) / (2 * c**2))

pdf_values = rayleigh_pdf(v_values, c_scale)

# Normalize (small numeric correction so sum(pdf*dv) ≈ 1)
dv = v_values[1] - v_values[0]
normalization = np.sum(pdf_values * dv)
pdf_values = pdf_values / normalization

# Expected AEP (kWh/year) = sum over v [ P(v) * Prob(v) ] * 8760
expected_power_kw = np.sum(power_values * pdf_values * dv)
aep_kwh = expected_power_kw * 8760.0

capacity_factor = (expected_power_kw / rated_power_kw) if rated_power_kw > 0 else 0.0

# ---------------------------
# 4. OUTPUTS
# ---------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Key Results")

    st.metric(
        "Average wind speed",
        f"{avg_wind_speed:.2f} m/s"
    )
    st.metric(
        "Wind power density",
        f"{wind_power_density:.0f} W/m²"
    )
    st.metric(
        "Expected annual energy (AEP)",
        f"{aep_kwh/1000:.1f} MWh/year"
    )
    st.metric(
        "Capacity factor",
        f"{capacity_factor*100:.1f} %"
    )

with col2:
    st.subheader("Power Curve (deterministic)")
    df_curve = pd.DataFrame(
        {"Wind speed (m/s)": v_values, "Power (kW)": power_values}
    ).set_index("Wind speed (m/s)")
    st.line_chart(df_curve)

st.markdown("---")
st.subheader("Assumptions & Notes")

st.write(
    f"""
- Air density is fixed at **{AIR_DENSITY} kg/m³** (sea-level standard).
- Wind power density is computed as:  
  \\( P_d = 0.5 \\rho V^3 \\).
- Power curve is a **very simplified cubic ramp** between cut-in and rated speed,
  then flat at rated power until cut-out.
- Wind speed distribution is modeled as **Rayleigh** (Weibull with k = 2),
  scaled to match the chosen mean wind speed.
- Annual Energy Production (AEP) is calculated as expected power × 8760 hours.
- Capacity factor = expected power / rated power.
- This is a **basic framework**. You can later:
  - Replace Rayleigh with full Weibull (k, c parameters),
  - Use real turbine power curves from manufacturers,
  - Add wake losses and wind farm layout,
  - Load site-specific wind datasets instead of a single mean speed.
"""
)
