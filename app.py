# Create the updated app.py following the structure from paste.txt
import streamlit as st
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder
import random

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

# Load trained model
@st.cache_resource
def load_model():
    try:
        modelo = joblib.load("regressor_bootstrap.pkl")
        return modelo
    except FileNotFoundError:
        st.error("Model file 'regressor_bootstrap.pkl' not found. Please upload the model file.")
        return None

# Function to calculate LHV based on biomass composition
def calculate_lhv(C, H, O, N, S, ash, moisture):
    lhv = 0.349 * C + 1.178 * H + 0.1005 * S - 0.1034 * O - 0.0151 * N - 0.0211 * ash - 0.244 * moisture
    return max(3.5, lhv)

# Function to calculate gasifying agent fractions
def calculate_gasifying_agent_fractions(biomass_feed_rate, ratio, agent_type, calorific_value=None):
    if agent_type == "air":
        air_feed_rate = ratio * biomass_feed_rate
        o2_feed_rate = 0.2095 * air_feed_rate
        n2_feed_rate = 0.7808 * air_feed_rate
        return o2_feed_rate / (air_feed_rate + biomass_feed_rate), n2_feed_rate / (air_feed_rate + biomass_feed_rate), 0
    elif agent_type == "oxygen":
        if calorific_value is None:
            raise ValueError("Calorific value must be provided for oxygen gasification.")
        calorific_value = max(calorific_value, 3.5)
        theoretical_oxygen = calorific_value / 13.1
        o2_feed_rate = ratio * theoretical_oxygen * biomass_feed_rate
        return o2_feed_rate / (o2_feed_rate + biomass_feed_rate), 0, 0
    elif agent_type == "steam":
        steam_feed_rate = ratio * biomass_feed_rate
        return 0, 0, steam_feed_rate / (steam_feed_rate + biomass_feed_rate)
    else:
        return 0, 0, 0

# Function to calculate metrics
def calculate_metrics(h2, co, ch4, co2):
    h2_co_ratio = h2 / co if co > 0 else 0
    fuel_energy = h2 + co + ch4
    return h2_co_ratio, fuel_energy

# Function to suggest end-use application
def suggest_end_use_application(h2_co_ratio, fuel_energy):
    if fuel_energy >= 3.0 and h2_co_ratio < 1.8:
        return "Heat/Power"
    elif 3.0 <= fuel_energy <= 18 and 1.8 <= h2_co_ratio < 3:
        return "Methanol/Biofuels"
    elif 3.0 <= fuel_energy <= 18 and h2_co_ratio >= 3:
        return "Methane"
    else:
        return "Other"

# Streamlit App
st.title("Predictor de Composición de Syngas")
st.write("Predice la composición del syngas basado en biomasa y condiciones de gasificación")

# Load model
modelo = load_model()
if modelo is None:
    st.stop()

# Sidebar for inputs
st.sidebar.header("Parámetros de Entrada")

# Temperature input
temperatura = st.sidebar.slider("Temperatura (°C)", 
                               min_value=600, 
                               max_value=1000, 
                               value=800, 
                               step=10)

# Gasifying agent selection
agente_gasificante = st.sidebar.selectbox("Agente Gasificante", 
                                        ["air", "oxygen", "steam"])

# Ratio ranges based on gasifying agent
if agente_gasificante == "air":
    ratio_label = "Air-to-Biomass Ratio"
    ratio_min, ratio_max = 0.1, 2.0
    ratio_default = 0.5
elif agente_gasificante == "oxygen":
    ratio_label = "Oxygen-to-Biomass Ratio"
    ratio_min, ratio_max = 0.1, 1.0
    ratio_default = 0.3
else:  # steam
    ratio_label = "Steam-to-Biomass Ratio"
    ratio_min, ratio_max = 0.1, 3.0
    ratio_default = 1.0

ratio = st.sidebar.slider(ratio_label, 
                         min_value=ratio_min, 
                         max_value=ratio_max, 
                         value=ratio_default, 
                         step=0.1)

# Moisture content
humedad = st.sidebar.slider("Contenido de Humedad (%)", 
                          min_value=0.0, 
                          max_value=50.0, 
                          value=10.0, 
                          step=1.0)

# Biomass composition inputs
st.sidebar.subheader("Composición de Biomasa (% base seca)")
C = st.sidebar.slider("Carbono (C)", 0.0, 100.0, 45.0, 0.1)
H = st.sidebar.slider("Hidrógeno (H)", 0.0, 20.0, 6.0, 0.1)
O = st.sidebar.slider("Oxígeno (O)", 0.0, 60.0, 40.0, 0.1)
N = st.sidebar.slider("Nitrógeno (N)", 0.0, 10.0, 1.0, 0.1)
S = st.sidebar.slider("Azufre (S)", 0.0, 5.0, 0.1, 0.01)
ash = st.sidebar.slider("Cenizas", 0.0, 30.0, 5.0, 0.1)

# Calculate LHV
lhv = calculate_lhv(C, H, O, N, S, ash, humedad)

# Calculate gasifying agent fractions
try:
    o2_fraction, n2_fraction, steam_fraction = calculate_gasifying_agent_fractions(
        1.0, ratio, agente_gasificante, lhv
    )
except ValueError as e:
    st.error(str(e))
    st.stop()

# Prepare input data for prediction
input_data = pd.DataFrame({
    'Temperature': [temperatura],
    'C': [C],
    'H': [H],
    'O': [O],
    'N': [N],
    'S': [S],
    'Ash': [ash],
    'Moisture': [humedad],
    'O2_gasifying agent (wt/wt)': [o2_fraction],
    'N2_gasifying agent (wt/wt)': [n2_fraction],
    'Steam_gasifying agent (wt/wt)': [steam_fraction]
})

# Make prediction
if st.button("Predecir Composición de Syngas"):
    try:
        prediccion = modelo.predict(input_data)
        
        # Extract predictions (assuming model predicts H2, CO, CH4, CO2)
        h2_pred = prediccion[0][0] if len(prediccion[0]) > 0 else 0
        co_pred = prediccion[0][1] if len(prediccion[0]) > 1 else 0
        ch4_pred = prediccion[0][2] if len(prediccion[0]) > 2 else 0
        co2_pred = prediccion[0][3] if len(prediccion[0]) > 3 else 0
        
        # Calculate metrics
        h2_co_ratio, fuel_energy = calculate_metrics(h2_pred, co_pred, ch4_pred, co2_pred)
        
        # Suggest end-use application
        end_use = suggest_end_use_application(h2_co_ratio, fuel_energy)
        
        # Display results
        st.header("Resultados de la Predicción")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Composición del Syngas")
            st.metric("H₂ (%)", f"{h2_pred:.2f}")
            st.metric("CO (%)", f"{co_pred:.2f}")
            st.metric("CH₄ (%)", f"{ch4_pred:.2f}")
            st.metric("CO₂ (%)", f"{co2_pred:.2f}")
        
        with col2:
            st.subheader("Métricas Calculadas")
            st.metric("Relación H₂/CO", f"{h2_co_ratio:.2f}")
            st.metric("Energía Combustible (%)", f"{fuel_energy:.2f}")
            st.metric("LHV (MJ/kg)", f"{lhv:.2f}")
        
        st.subheader("Aplicación Sugerida")
        st.success(f"**{end_use}**")
        
        # Display input conditions
        st.subheader("Condiciones de Entrada")
        conditions_df = pd.DataFrame({
            'Parámetro': ['Temperatura', 'Agente Gasificante', 'Ratio', 'Humedad', 'LHV'],
            'Valor': [f"{temperatura}°C", agente_gasificante, f"{ratio:.2f}", f"{humedad}%", f"{lhv:.2f} MJ/kg"]
        })
        st.table(conditions_df)
        
    except Exception as e:
        st.error(f"Error en la predicción: {str(e)}")

# Additional information
st.sidebar.markdown("---")
st.sidebar.info("""
**Rangos típicos:**
- Temperatura: 600-1000°C
- Air ratio: 0.1-2.0
- Oxygen ratio: 0.1-1.0  
- Steam ratio: 0.1-3.0
- Humedad: 0-50%
""")


# Save the updated app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(updated_app_code)

print("Updated app.py has been created successfully!")
print("Key features implemented:")
print("- User input selection for all parameters")
print("- Temperature, gasifying agents, ratios, and moisture controls")
print("- Predictions for H2, CO, CH4")
print("- Metrics calculation (H2/CO ratio, fuel energy)")
print("- End-use application suggestion")
print("- Following the structure from paste.txt")
