import streamlit as st
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

# --- Estilos personalizados ---
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-size: 18px;
    }
    </style>
""", unsafe_allow_html=True)

# Cargar el modelo entrenado
try:
    modelo = joblib.load("regressor_bootstrap.pkl")
except FileNotFoundError:
    st.error("Model file 'regressor_bootstrap.pkl' not found. Please upload the model file.")
    st.stop()

# Cargar archivo de composición de biomasa
df_biomasa = pd.read_excel("biomass_compositions.xlsx")

# --- Funciones ---
def rebalance_composition(biomass_data, new_moisture):
    old_moisture = biomass_data.get('Moisture content', 0)
    dry_basis_factor = (100 - old_moisture)

    # Rebalanceo de análisis próximo
    vm_dry = biomass_data['VM [%] _norm'] * dry_basis_factor / 100
    fc_dry = biomass_data['FC [%] _norm'] * dry_basis_factor / 100
    ash_dry = biomass_data['Ash [%] _norm'] * dry_basis_factor / 100
    proximate_dry_sum = vm_dry + fc_dry + ash_dry
    scale_factor_proximate = (100 - new_moisture) / proximate_dry_sum
    biomass_data['VM [%] _norm'] = vm_dry * scale_factor_proximate
    biomass_data['FC [%] _norm'] = fc_dry * scale_factor_proximate
    biomass_data['Ash [%] _norm'] = ash_dry * scale_factor_proximate

    # Rebalanceo de análisis último
    c_dry = biomass_data['C_norm'] * dry_basis_factor / 100
    h_dry = biomass_data['H_norm'] * dry_basis_factor / 100
    o_dry = biomass_data['O_norm'] * dry_basis_factor / 100
    n_dry = biomass_data['N_norm'] * dry_basis_factor / 100
    s_dry = biomass_data['S_norm'] * dry_basis_factor / 100
    cl_dry = biomass_data['Cl_norm'] * dry_basis_factor / 100
    ultimate_dry_sum = c_dry + h_dry + o_dry + n_dry + s_dry + cl_dry + ash_dry
    scale_factor_ultimate = (100 - new_moisture) / ultimate_dry_sum
    biomass_data['C_norm'] = c_dry * scale_factor_ultimate
    biomass_data['H_norm'] = h_dry * scale_factor_ultimate
    biomass_data['O_norm'] = o_dry * scale_factor_ultimate
    biomass_data['N_norm'] = n_dry * scale_factor_ultimate
    biomass_data['S_norm'] = s_dry * scale_factor_ultimate
    biomass_data['Cl_norm'] = cl_dry * scale_factor_ultimate

    biomass_data['Intrinsic moisture content [%]'] = new_moisture
    return biomass_data

def calcular_fracciones_agente(tipo, ratio):
    if tipo == "Aire":
        return {"O2": ratio / (1 + 3.76), "N2": ratio * 3.76 / (1 + 3.76), "H2O": 0}
    elif tipo == "Oxígeno":
        return {"O2": ratio, "N2": 0, "H2O": 0}
    elif tipo == "Vapor de agua":
        return {"O2": 0, "N2": 0, "H2O": ratio}
    elif tipo == "Mezcla O2 + H2O":
        return {"O2": ratio * 0.5, "N2": 0, "H2O": ratio * 0.5}
    else:
        return {"O2": 0, "N2": 0, "H2O": 0}

def calcular_lhv(C, H, O, N, S, ash, moisture):
    lhv = 0.349 * C + 1.178 * H + 0.1005 * S - 0.1034 * O - 0.0151 * N - 0.0211 * ash - 0.244 * moisture
    return max(3.5, lhv)

def sugerir_aplicacion(h2_co, fuel_energy):
    if fuel_energy >= 3.0 and h2_co < 1.8:
        return "Heat/Power"
    elif 3.0 <= fuel_energy <= 18 and 1.8 <= h2_co < 3:
        return "Methanol/Biofuels"
    elif 3.0 <= fuel_energy <= 18 and h2_co >= 3:
        return "Methane"
    else:
        return "Other"

# --- Interfaz ---
st.title("Predictor para la composición del gas de síntesis")

st.sidebar.header("Parámetros de entrada")
biomasa_nombres = df_biomasa["Biomass residue"].tolist()
biomasa_seleccionada = st.sidebar.selectbox("Selecciona tipo de biomasa:", biomasa_nombres)
fila_biomasa_original = df_biomasa[df_biomasa["Biomass residue"] == biomasa_seleccionada].iloc[0].copy()

humedad_objetivo = st.sidebar.slider("Humedad intrínseca biomasa (%)", 0.0, 30.0, 10.0, 0.1)
temperatura = st.sidebar.slider("Temperatura (°C)", 600, 1000, 800, 10)
tipo_agente = st.sidebar.selectbox("Agente gasificante:", ["Aire", "Oxígeno", "Vapor de agua"])

abr_range_air = np.round(np.linspace(0.14, 0.30, num=3), 2)
abr_range_oxygen = np.round(np.linspace(0.2, 0.4, num=3), 2)
sbr_range = np.round(np.linspace(0.84, 1.1, num=3), 2)

if tipo_agente == "Aire":
    ratio_agente = st.sidebar.selectbox("ABR (aire/biomasa)", abr_range_air)
elif tipo_agente == "Oxígeno":
    ratio_agente = st.sidebar.selectbox("ABR (oxígeno/biomasa)", abr_range_oxygen)
else:
    ratio_agente = st.sidebar.selectbox("SBR (vapor/biomasa)", sbr_range)

fila_biomasa = rebalance_composition(fila_biomasa_original.copy(), humedad_objetivo)
fracciones_agente = calcular_fracciones_agente(tipo_agente, ratio_agente)

# Composición rebalanceada
st.subheader("Composición análisis último y próximo biomasa")
col1, col2 = st.columns(2)
with col1:
    st.metric("Carbono (wt%)", f"{fila_biomasa['C_norm']:.2f}")
    st.metric("Hidrógeno (wt%)", f"{fila_biomasa['H_norm']:.2f}")
    st.metric("Oxígeno (wt%)", f"{fila_biomasa['O_norm']:.2f}")
    st.metric("Nitrógeno (wt%)", f"{fila_biomasa['N_norm']:.2f}")
    st.metric("Azufre (wt%)", f"{fila_biomasa['S_norm']:.2f}")
    st.metric("Cloro (wt%)", f"{fila_biomasa['Cl_norm']:.2f}")
with col2:
    st.metric("Cenizas (wt%)", f"{fila_biomasa['Ash [%] _norm']:.2f}")
    st.metric("Materia volátil (wt%)", f"{fila_biomasa['VM [%] _norm']:.2f}")
    st.metric("Carbono fijo (wt%)", f"{fila_biomasa['FC [%] _norm']:.2f}")
    lhv_mostrado = calcular_lhv(
        fila_biomasa['C_norm'], fila_biomasa['H_norm'], fila_biomasa['O_norm'],
        fila_biomasa['N_norm'], fila_biomasa['S_norm'], fila_biomasa['Ash [%] _norm'],
        humedad_objetivo
    )
    st.metric("Poder calorífico biomasa (LHV) [MJ/kg]", f"{lhv_mostrado:.2f}")

# Gráfico de pastel
st.subheader("Distribución elementos (wt%) - Biomasa")
composicion_biomasa = {
    "C": fila_biomasa["C_norm"],
    "H": fila_biomasa["H_norm"],
    "O": fila_biomasa["O_norm"],
    "N": fila_biomasa["N_norm"],
    "S": fila_biomasa["S_norm"],
    "Cl": fila_biomasa["Cl_norm"],
    "Ash": fila_biomasa["Ash [%] _norm"]
}
labels = list(composicion_biomasa.keys())
sizes = list(composicion_biomasa.values())
fig1, ax1 = plt.subplots()
ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
ax1.axis('equal')
st.pyplot(fig1)

# Botón de predicción
if st.button("Predecir composición syngas"):
    entrada = pd.DataFrame([{
        'Gasification temperature [°C]': temperatura,
        'O2_gasifying agent (wt/wt)': fracciones_agente["O2"],
        'N2_gasifying agent (wt/wt)': fracciones_agente["N2"],
        'Steam_gasifying agent (wt/wt)': fracciones_agente["H2O"],
        'C_norm': fila_biomasa["C_norm"],
        'H_norm': fila_biomasa["H_norm"],
        'O_norm': fila_biomasa["O_norm"],
        'N_norm': fila_biomasa["N_norm"],
        'S_norm': fila_biomasa["S_norm"],
        'Cl_norm': fila_biomasa["Cl_norm"],
        'VM [%] _norm': fila_biomasa["VM [%] _norm"],
        'Ash [%] _norm': fila_biomasa["Ash [%] _norm"],
        'FC [%] _norm': fila_biomasa["FC [%] _norm"],
        'Biomass Energy Content (LHV) [MJ/kg]': lhv_mostrado,
        'Intrinsic moisture content [%]': humedad_objetivo
    }])

    try:
        prediccion = modelo.predict(entrada)
        h2, co, ch4 = prediccion[0]

        st.success("Predicción completada")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("CH₄ (mol%)", f"{ch4:.2f}")
        with col2: st.metric("CO (mol%)", f"{co:.2f}")
        with col3: st.metric("H₂ (mol%)", f"{h2:.2f}")

        # Gráfico de pastel syngas
        st.subheader("Composición predicha del syngas (mol%)")
        fig2, ax2 = plt.subplots()
        ax2.pie([ch4, co, h2], labels=["CH₄", "CO", "H₂"], autopct='%1.1f%%')
        ax2.axis("equal")
        st.pyplot(fig2)

        h2_co = h2 / co if co != 0 else 0
        fuel_energy = (0.126 * h2) + (0.108 * co) + (0.358 * ch4) + ((h2 / 100) * 1.2 * 2.45)
        aplicacion = sugerir_aplicacion(h2_co, fuel_energy)

        st.subheader("Predicción aplicación final syngas")
        col1, col2 = st.columns(2)
        with col1: st.metric("Relación H₂/CO syngas", f"{h2_co:.2f}")
        with col2: st.metric("Contenido energético syngas [MJ/Nm³]", f"{fuel_energy:.2f}")
        st.info(f"**Aplicación uso final syngas:** {aplicacion}")

    except Exception as e:
        st.error(f"Error en la predicción: {str(e)}")
