import streamlit as st
import pandas as pd
import joblib

# Cargar el modelo entrenado
try:
    modelo = joblib.load("regressor_bootstrap.pkl")
except FileNotFoundError:
    st.error("Model file 'regressor_bootstrap.pkl' not found. Please upload the model file.")
    st.stop()

# Cargar archivo de composición de biomasa
df_biomasa = pd.read_excel("biomass_compositions.xlsx")

# --- Funciones ---
def rebalancear_composicion(fila_biomasa, humedad_objetivo):
    seco = fila_biomasa[[
        "C_norm", "H_norm", "O_norm", "N_norm", "S_norm", "Cl_norm",
        "Ash [%] _norm", "VM [%] _norm", "FC [%] _norm"
    ]] * (1 - humedad_objetivo / 100)
    seco.index = ["C", "H", "O", "N", "S", "Cl", "Ash", "VM", "FC"]
    h2o = pd.Series([humedad_objetivo], index=["Humedad"])
    return pd.concat([seco, h2o])

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
st.title("Predictor de Composición de Syngas")
st.write("Predice la composición del syngas basado en biomasa y condiciones de gasificación")

# Parámetros de entrada
st.sidebar.header("Parámetros de entrada")

# Selección de biomasa
biomasa_nombres = df_biomasa["Biomass residue"].tolist()
biomasa_seleccionada = st.sidebar.selectbox("Selecciona tipo de biomasa:", biomasa_nombres)
fila_biomasa = df_biomasa[df_biomasa["Biomass residue"] == biomasa_seleccionada].iloc[0]

# Parámetros de gasificación
humedad_objetivo = st.sidebar.slider("Humedad objetivo (%)", 0.0, 50.0, 10.0, 0.1)
temperatura = st.sidebar.slider("Temperatura (°C)", 600, 1000, 800, 10)

tipo_agente = st.sidebar.selectbox("Tipo de agente gasificante:", 
                                   ["Aire", "Oxígeno", "Vapor de agua"])
ratio_agente = st.sidebar.slider("Ratio agente/biomasa", 0.1, 3.0, 1.0, 0.1)

# Mostrar composición de la biomasa
st.subheader("Composición de biomasa seleccionada")
col1, col2 = st.columns(2)
with col1:
    st.metric("Carbono (%)", f"{fila_biomasa['C_norm']:.2f}")
    st.metric("Hidrógeno (%)", f"{fila_biomasa['H_norm']:.2f}")
    st.metric("Oxígeno (%)", f"{fila_biomasa['O_norm']:.2f}")
    st.metric("Nitrógeno (%)", f"{fila_biomasa['N_norm']:.2f}")
    st.metric("Azufre (%)", f"{fila_biomasa['S_norm']:.2f}")
with col2:
    st.metric("Cloruro (%)", f"{fila_biomasa['Cl_norm']:.2f}")
    st.metric("Cenizas (%)", f"{fila_biomasa['Ash [%] _norm']:.2f}")
    st.metric("Materia volátil (%)", f"{fila_biomasa['VM [%] _norm']:.2f}")
    st.metric("Carbono fijo (%)", f"{fila_biomasa['FC [%] _norm']:.2f}")

# Botón de predicción
if st.button("Predecir composición de syngas"):
    # Rebalanceo composicional
    comp_rebalanceada = rebalancear_composicion(fila_biomasa, humedad_objetivo)

    # Fracciones del agente
    fracciones = calcular_fracciones_agente(tipo_agente, ratio_agente)

    # Crear input para el modelo con columnas correctas
    entrada = pd.DataFrame([{
        'Gasification temperature [°C]': temperatura,
        'O2_gasifying agent (wt/wt)': fracciones["O2"],
        'N2_gasifying agent (wt/wt)': fracciones["N2"],
        'Steam_gasifying agent (wt/wt)': fracciones["H2O"],
        'C_norm': comp_rebalanceada["C"],
        'H_norm': comp_rebalanceada["H"],
        'O_norm': comp_rebalanceada["O"],
        'N_norm': comp_rebalanceada["N"],
        'S_norm': comp_rebalanceada["S"],
        'Cl_norm': comp_rebalanceada["Cl"],
        'VM [%] _norm': comp_rebalanceada["VM"],
        'Ash [%] _norm': comp_rebalanceada["Ash"],
        'FC [%] _norm': comp_rebalanceada["FC"],
        'Biomass Energy Content (LHV) [MJ/kg]': fila_biomasa['Biomass Energy Content (LHV) [MJ/kg]'],
        'Intrinsic moisture content [%]': humedad_objetivo
    }])

    # Predicción
    try:
        prediccion = modelo.predict(entrada)
        ch4, co, h2 = prediccion[0]

        st.success("Predicción completada")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CH₄ (%)", f"{ch4:.2f}")
        with col2:
            st.metric("CO (%)", f"{co:.2f}")
        with col3:
            st.metric("H₂ (%)", f"{h2:.2f}")

        # Indicadores
        h2_co = h2 / co if co != 0 else 0
        fuel_energy = (0.126 * h2) + (0.108 * co) + (0.358 * ch4) + ((h2 / 100) * 1.2 * 2.45)
        aplicacion = sugerir_aplicacion(h2_co, fuel_energy)

        st.subheader("Análisis del syngas")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Relación H₂/CO", f"{h2_co:.2f}")
        with col2:
            st.metric("Contenido energético [MJ/m³]", f"{fuel_energy:.2f}")

        st.info(f"**Aplicación recomendada del syngas:** {aplicacion}")

    except Exception as e:
        st.error(f"Error en la predicción: {str(e)}")
        st.write("Verifique que el modelo sea compatible con las características de entrada.")
