# wind_app.py
import math
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Wind Energy Analyzer",
    layout="wide"
)

st.title("🌬️ Wind Energy Analyzer (Data-Driven Version)")
st.write(
    "Estimate wind power density, turbine power curve, and annual energy production for a site. "
    "Uses approximate but realistic wind speeds, Weibull parameters and a real-style turbine power curve."
)

# ----------------------------------------------------
# 1. LOCATION DATABASE – MEAN WIND & WEIBULL (approx)
# ----------------------------------------------------
# Typical-ish values at ~100m hub height, not exact.
WIND_LOCATIONS = {
    "Kolkata, India": {
        "avg_wind_ms": 3.6,
        "weibull_k": 1.7,
        "weibull_c": 4.5,
    },
    "Chennai, India": {
        "avg_wind_ms": 5.5,
        "weibull_k": 2.0,
        "weibull_c": 6.2,
    },
    "Hamburg, Germany": {
        "avg_wind_ms": 6.8,
        "weibull_k": 2.3,
        "weibull_c": 8.0,
    },
    "Schleswig-Holstein (coastal Germany)": {
        "avg_wind_ms": 8.2,
        "weibull_k": 2.0,
        "weibull_c": 9.0,
    },
    "Bavaria (South Germany)": {
        "avg_wind_ms": 4.2,
        "weibull_k": 1.8,
        "weibull_c": 5.0,
    },
}

AIR_DENSITY = 1.225  # kg/m³ at sea level

# ----------------------------------------------------
# 2. REALISTIC TURBINE POWER CURVE (Vestas-like 2 MW)
# ----------------------------------------------------
# Wind speed (m/s) -> Power (kW)
V90_POWER_CURVE = {
    0: 0,
    1: 0,
    2: 0,
    3: 50,
    4: 120,
    5: 250,
    6: 480,
    7: 750,
    8: 1100,
    9: 1500,
    10: 1800,
    11: 2000,
    12: 2000,
    13: 2000,
    14: 2000,
    15: 2000,
    16: 2000,
    17: 2000,
    18: 2000,
    19: 2000,
    20: 2000,
}

def real_power_curve(v):
    speeds = np.array(list(V90_POWER_CURVE.keys()), dtype=float)
    powers = np.array(list(V90_POWER_CURVE.values()), dtype=float)
    return float(np.interp(v, speeds, powers))

# ----------------------------------------------------
# 3. SIDEBAR INPUTS
# ----------------------------------------------------
st.sidebar.header("Inputs")

location = st.sidebar.selectbox(
    "Location",
    options=list(WIND_LOCATIONS.keys()),
    index=2
)
loc_data = WIND_LOCATIONS[location]

avg_wind_speed = st.sidebar.slider(
    "Average wind speed at hub height (m/s)",
    min_value=2.0,
    max_value=12.0,
    value=float(loc_data["avg_wind_ms"]),
    step=0.1,
    key=f"avg_wind_{location}"
)

rated_power_kw = st.sidebar.number_input(
    "Turbine rated power (kW)",
    min_value=100.0,
    max_value=5000.0,
    value=2000.0,
    step=50.0
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

cut_out = st.sidebar.slider(
    "Cut-out speed (m/s)",
    min_value=15.0,
    max_value=30.0,
    value=25.0,
    step=0.5
)

use_weibull = st.sidebar.checkbox(
    "Use location Weibull parameters (k, c) instead of deriving from mean",
    value=True
)

# ----------------------------------------------------
# 4. WIND POWER DENSITY & SWEPT AREA
# ----------------------------------------------------
wind_power_density = 0.5 * AIR_DENSITY * avg_wind_speed**3  # W/m²
swept_area = math.pi * (rotor_diameter / 2.0) ** 2  # m²

# ----------------------------------------------------
# 5. POWER CURVE & DISTRIBUTION
# ----------------------------------------------------
v_values = np.arange(0.0, 30.1, 0.5)

# Turbine power curve (kW) – scaled if user changes rated_power from base curve
base_rated = max(V90_POWER_CURVE.values())
scale_factor = rated_power_kw / base_rated if base_rated > 0 else 1.0
power_values = np.array([real_power_curve(v) * scale_factor for v in v_values])

# Weibull parameters
if use_weibull:
    k = loc_data["weibull_k"]
    c = loc_data["weibull_c"]
else:
    # Derive c from mean speed for Rayleigh-like approx (k=2)
    k = 2.0
    c = avg_wind_speed * math.sqrt(2.0 / math.pi)

def weibull_pdf(v, k, c):
    v = np.array(v, dtype=float)
    return (k / c) * (v / c) ** (k - 1) * np.exp(-(v / c) ** k)

pdf_values = weibull_pdf(v_values, k, c)
dv = v_values[1] - v_values[0]
normalization = np.sum(pdf_values * dv)
if normalization > 0:
    pdf_values = pdf_values / normalization

# Expected power & AEP
expected_power_kw = np.sum(power_values * pdf_values * dv)
aep_kwh = expected_power_kw * 8760.0
capacity_factor = (expected_power_kw / rated_power_kw) if rated_power_kw > 0 else 0.0

# For a second plot: contribution per speed bin (kW * probability)
contribution_kw = power_values * pdf_values

# ----------------------------------------------------
# 6. OUTPUTS
# ----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Key Results")

    st.metric("Location", location)
    st.metric("Average wind speed", f"{avg_wind_speed:.2f} m/s")
    st.metric("Wind power density", f"{wind_power_density:.0f} W/m²")
    st.metric("Expected annual energy (AEP)", f"{aep_kwh/1000:.1f} MWh/year")
    st.metric("Capacity factor", f"{capacity_factor*100:.1f} %")

with col2:
    st.subheader("Turbine Power Curve (deterministic)")
    df_curve = pd.DataFrame(
        {"Wind speed (m/s)": v_values, "Power (kW)": power_values}
    ).set_index("Wind speed (m/s)")
    st.line_chart(df_curve)

st.markdown("### Wind Speed Distribution & Contribution")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Wind Speed Distribution (Weibull PDF)")
    df_pdf = pd.DataFrame(
        {"Wind speed (m/s)": v_values, "Probability density": pdf_values}
    ).set_index("Wind speed (m/s)")
    st.line_chart(df_pdf)

with col4:
    st.subheader("Expected Power Contribution by Wind Speed")
    df_contrib = pd.DataFrame(
        {"Wind speed (m/s)": v_values, "Contribution (kW * prob)": contribution_kw}
    ).set_index("Wind speed (m/s)")
    st.line_chart(df_contrib)

st.markdown("---")
st.subheader("Assumptions & Notes")
st.write(
    """
- Location wind data (mean wind speed, Weibull k & c) are approximate typical values, not exact measurements.
- Turbine power curve is based on a generic 2 MW turbine and scaled by `rated_power_kw`.
- If **Weibull mode** is enabled, the site's k and c are used; otherwise, a Rayleigh-like distribution (k=2) is derived from mean speed.
- AEP = ∑ P(v)·f(v)·Δv × 8760, where f(v) is the Weibull PDF.
- Capacity factor = expected power / rated power.
- To match your renewable dashboard dataset exactly, replace the `WIND_LOCATIONS` dict with values from your own data source.
"""
)


