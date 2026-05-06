import streamlit as st
import pandas as pd
import io

# --- Page Configuration ---
st.set_page_config(page_title="NSCP 2015 Load Combo Generator", page_icon="🏢", layout="wide")

# --- Custom CSS for Ultra-Compact Dark Blue & White Theme ---
st.markdown("""
<style>
    /* Hide default Streamlit headers and footers to reclaim top space */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Drastically reduce main container padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Set main background color */
    .stApp {
        background-color: #0A192F;
    }
    
    /* Set text to white */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .st-emotion-cache-10trblm {
        color: #FFFFFF !important;
    }
    
    /* Compact the title */
    h1 {
        font-size: 1.8rem !important;
        padding-bottom: 0rem !important;
        margin-bottom: 0rem !important;
        margin-top: -0.5rem !important;
    }
    
    /* Compact the Metric Boxes */
    div[data-testid="stMetricValue"] > div {
        color: #FFFFFF !important;
        font-size: 1.5rem !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #FFFFFF !important;
        font-size: 0.9rem !important;
    }
    
    /* Style the Download Button to pop and be slightly thinner */
    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        border: none;
        padding: 0.25rem 0.75rem !important;
    }
    .stDownloadButton > button p {
        color: #0A192F !important;
        font-weight: bold !important;
    }
    .stDownloadButton > button:hover {
        background-color: #E0E0E0 !important;
    }
    
    /* Tighten horizontal dividers */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Header with Author Info ---
col_title, col_author = st.columns([3, 1])
with col_title:
    st.markdown("<h1>NSCP 2015 Load Combination Generator for ETABS</h1>", unsafe_allow_html=True)
with col_author:
    st.markdown("""
    <div style='text-align: right; line-height: 1.3;'>
        <div style='font-weight: bold; font-size: 1.05rem; color: #FFFFFF;'>Engr. Dave Jonathan F. Trinidad</div>
        <div style='font-size: 0.85rem; color: #CCCCCC;'>Civil Structural Engineer</div>
        <a href='https://www.linkedin.com/in/dave-jonathan-f-trinidad-44784223a/' target='_blank' style='font-size: 0.85rem; color: #4DA8DA; text-decoration: none; font-weight: bold;'>LinkedIn Profile</a>
    </div>
    """, unsafe_allow_html=True)

# --- Helper Functions for Seismic Interpolation ---
def interpolate(x, x0, x1, y0, y1):
    if x <= x0: return y0
    if x >= x1: return y1
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def get_Na(source_type, distance):
    if source_type == 'A':
        if distance <= 2: return 1.5
        elif distance <= 5: return interpolate(distance, 2, 5, 1.5, 1.2)
        else: return interpolate(distance, 5, 10, 1.2, 1.0)
    elif source_type == 'B':
        if distance <= 2: return 1.3
        elif distance <= 5: return interpolate(distance, 2, 5, 1.3, 1.0)
        else: return 1.0
    else: return 1.0

def get_Nv(source_type, distance):
    if source_type == 'A':
        if distance <= 2: return 2.0
        elif distance <= 5: return interpolate(distance, 2, 5, 2.0, 1.6)
        elif distance <= 10: return interpolate(distance, 5, 10, 1.6, 1.2)
        else: return interpolate(distance, 10, 15, 1.2, 1.0)
    elif source_type == 'B':
        if distance <= 2: return 1.6
        elif distance <= 5: return interpolate(distance, 2, 5, 1.6, 1.2)
        elif distance <= 10: return interpolate(distance, 5, 10, 1.2, 1.0)
        else: return 1.0
    else: return 1.0

# --- Ultra-Compact UI Layout ---
# ROW 1: Base Inputs
c1, c2, c3, c4, c5, c6 = st.columns(6)
zone_factor = c1.selectbox("Zone Factor (Z)", [0.4, 0.2])
source_type = c2.selectbox("Source Type", ["A", "B", "C"])
distance = c3.number_input("Distance (km)", min_value=0.0, value=10.0, step=1.0)
soil_type = c4.selectbox("Soil Profile", ["SA", "SB", "SC", "SD", "SE"])
include_wind = c5.selectbox("Include Wind?", ["Yes", "No"])
include_overstrength = c6.selectbox("Overstrength (Ωo)?", ["No", "Yes"])

# ROW 2: Secondary Inputs & Live Metrics
c7, c8, c9, c10, c11, c12, c13 = st.columns(7)
I_factor = c7.number_input("Importance (I)", min_value=1.0, value=1.0, step=0.25)
rho = c8.number_input("Redundancy (ρ)", min_value=1.0, value=1.0, step=0.1)

omega = 1.0
if include_overstrength == "Yes":
    omega = c9.number_input("Omega (Ωo)", min_value=1.0, value=2.5, step=0.5)
else:
    c9.write("") # Blank space holder if not used

# Calculations for metrics
Na = get_Na(source_type, distance) if zone_factor == 0.4 else 1.0
Nv = get_Nv(source_type, distance) if zone_factor == 0.4 else 1.0
Ca_table = {0.2: {'SA': 0.16, 'SB': 0.20, 'SC': 0.24, 'SD': 0.28, 'SE': 0.34}, 0.4: {'SA': 0.32, 'SB': 0.40, 'SC': 0.40, 'SD': 0.44, 'SE': 0.44}}
Cv_table = {0.2: {'SA': 0.16, 'SB': 0.20, 'SC': 0.32, 'SD': 0.40, 'SE': 0.64}, 0.4: {'SA': 0.32, 'SB': 0.40, 'SC': 0.56, 'SD': 0.64, 'SE': 0.96}}
Ca = Ca_table[zone_factor][soil_type] * (Na if zone_factor == 0.4 else 1.0)
Cv = Cv_table[zone_factor][soil_type] * (Nv if zone_factor == 0.4 else 1.0)

# Display Metrics in the remaining columns of Row 2
c10.metric("Na", f"{Na:.3f}")
c11.metric("Nv", f"{Nv:.3f}")
c12.metric("Ca", f"{Ca:.3f}")
c13.metric("Cv", f"{Cv:.3f}")

st.markdown("---")

# --- Generate Load Combinations ---
rows = []
def add_combo(name, factors):
    for load_name, sf in factors.items():
        if sf != 0:
            rows.append({"Name": name, "Type": "Linear Add", "Is Auto": "No", "Load Name": load_name, "Mode": "", "SF": round(sf, 3)})

eq_factor = omega if include_overstrength == "Yes" else rho
Ev_factor = 0.5 * Ca * I_factor
D_max = 1.2 + Ev_factor
D_min = 0.9 - Ev_factor
eq_asd = eq_factor / 1.4

eq_perms = [
    (1.0, 0.3, "+1EX+0.3EY"), (1.0, -0.3, "+1EX-0.3EY"),
    (-1.0, 0.3, "-1EX+0.3EY"), (-1.0, -0.3, "-1EX-0.3EY"),
    (0.3, 1.0, "+1EY+0.3EX"), (-0.3, 1.0, "+1EY-0.3EX"),
    (0.3, -1.0, "-1EY+0.3EX"), (-0.3, -1.0, "-1EY-0.3EX")
]

# LRFD
u_count = 1
add_combo(f"U{u_count}: 1.4D", {"DL1": 1.4, "DL2": 1.4}); u_count += 1
add_combo(f"U{u_count}: 1.2D + 1.6L + 0.5Lr", {"DL1": 1.2, "DL2": 1.2, "LL1": 1.6, "LL2": 1.6, "LLR": 0.5}); u_count += 1
add_combo(f"U{u_count}: 1.2D + 1.0L + 1.6Lr", {"DL1": 1.2, "DL2": 1.2, "LL1": 1.0, "LL2": 1.0, "LLR": 1.6}); u_count += 1

if include_wind == "Yes":
    add_combo(f"U{u_count}: 1.2D + 1.0W + L + 0.5Lr", {"DL1": 1.2, "DL2": 1.2, "W": 1.0, "LL1": 0.5, "LL2": 1.0, "LLR": 0.5}); u_count += 1
    add_combo(f"U{u_count}: 0.9D + 1.0W", {"DL1": 0.9, "DL2": 0.9, "W": 1.0}); u_count += 1

for fx, fy, tag in eq_perms: add_combo(f"U{u_count}: D+L+Lr {tag}", {"DL1": D_max, "DL2": D_max, "LL1": 0.5, "LL2": 1.0, "LLR": 0.5, "EX": fx*eq_factor, "EY": fy*eq_factor}); u_count += 1
for fx, fy, tag in eq_perms: add_combo(f"U{u_count}: 0.9D {tag}", {"DL1": D_min, "DL2": D_min, "EX": fx*eq_factor, "EY": fy*eq_factor}); u_count += 1

# ASD
a_count = 1
add_combo(f"A{a_count}: D", {"DL1": 1.0, "DL2": 1.0}); a_count += 1
add_combo(f"A{a_count}: D + L", {"DL1": 1.0, "DL2": 1.0, "LL1": 1.0, "LL2": 1.0}); a_count += 1
add_combo(f"A{a_count}: D + Lr", {"DL1": 1.0, "DL2": 1.0, "LLR": 1.0}); a_count += 1
add_combo(f"A{a_count}: D + 0.75L + 0.75Lr", {"DL1": 1.0, "DL2": 1.0, "LL1": 0.75, "LL2": 0.75, "LLR": 0.75}); a_count += 1

if include_wind == "Yes":
    add_combo(f"A{a_count}: D + 0.6W", {"DL1": 1.0, "DL2": 1.0, "W": 0.6}); a_count += 1
    add_combo(f"A{a_count}: D + 0.75(0.6W) + 0.75L + 0.75Lr", {"DL1": 1.0, "DL2": 1.0, "W": 0.75*0.6, "LL1": 0.75, "LL2": 0.75, "LLR": 0.75}); a_count += 1
    add_combo(f"A{a_count}: 0.6D + 0.6W", {"DL1": 0.6, "DL2": 0.6, "W": 0.6}); a_count += 1

for fx, fy, tag in eq_perms: add_combo(f"A{a_count}: D {tag}/1.4", {"DL1": 1.0, "DL2": 1.0, "EX": fx*eq_asd, "EY": fy*eq_asd}); a_count += 1
for fx, fy, tag in eq_perms: add_combo(f"A{a_count}: D+0.75L {tag}/1.4", {"DL1": 1.0, "DL2": 1.0, "LL1": 0.75, "LL2": 0.75, "LLR": 0.75, "EX": 0.75*fx*eq_asd, "EY": 0.75*fy*eq_asd}); a_count += 1
for fx, fy, tag in eq_perms: add_combo(f"A{a_count}: 0.6D {tag}/1.4", {"DL1": 0.6, "DL2": 0.6, "EX": fx*eq_asd, "EY": fy*eq_asd}); a_count += 1

# --- Display and Export ---
df = pd.DataFrame(rows)

# Split bottom section into two columns so the Download button sits nicely beside the table title
col_table_title, col_btn = st.columns([4, 1])
with col_table_title:
    st.markdown("<h3 style='margin-bottom:0;'>ETABS Interactive Database Table</h3>", unsafe_allow_html=True)
with col_btn:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Load Combinations')
    st.download_button(label="📥 Download Excel File", data=output.getvalue(), file_name="ETABS_Load_Combinations.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

# Reduced height dataframe to prevent pushing off the screen
st.dataframe(df, use_container_width=True, height=275)