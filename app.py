import streamlit as st
import pandas as pd
import joblib

# Cargar modelo entrenado
modelo = joblib.load("regressor_bootstrap.pkl")

# Composiciones base de biomasas (ejemplo)
df_biomasa = pd.read_xlsx("biomass_compositions.xlsx") 

# --- Funciones necesarias ---
def rebalancear_composicion(fila_biomasa, humedad_objetivo):
    seco = fila_biomasa[["C", "H", "O", "N", "S", "Ash", "VM", "FC"]] * (1 - humedad_objetivo / 100)
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
st.title("Predicción de composición de Syngas a partir de condiciones de gasificación")

# Selección de biomasa
biomasa_sel = st.selectbox("Seleccione una biomasa", df_biomasa["Biomasa"].unique())
composicion = df_biomasa[df_biomasa["Biomasa"] == biomasa_sel].iloc[0]

# Parámetros de entrada
temperatura = st.slider("Temperatura de gasificación (°C)", 600, 800, 1000)
humedad = st.slider("Contenido de humedad (%)", 0, 5, 15, 20, 25)
agente = st.selectbox("Tipo de agente gasificante", ["Aire", "Oxígeno", "Vapor de agua"])
ratio = st.slider("Relación de alimentación (ER/SBR/ABR)", 0.1, 1.5, 0.4)

# Botón de predicción
if st.button("Predecir composición de syngas"):
    # Rebalancear
    comp = rebalancear_composicion(fila, humedad)

    # Calcular fracciones del agente
    fracciones = calcular_fracciones_agente(agente, ratio)

    # Crear DataFrame de entrada al modelo
    entrada = pd.DataFrame([{
        "C_norm": comp_rebalanceada["C"],
        "H_norm": comp_rebalanceada["H"],
        "O_norm": comp_rebalanceada["O"],
        "N_norm": comp_rebalanceada["N"],
        "S_norm": comp_rebalanceada["S"],
        "Ash [%] _norm": comp_rebalanceada["Ash"],
        "VM [%] _norm": comp_rebalanceada["VM"],
        "FC [%] _norm": comp_rebalanceada["FC"],
        "Humedad": comp_rebalanceada["Humedad"],
        "Temp": temperatura,
        "O2": fracciones["O2"],
        "N2": fracciones["N2"],
        "H2O": fracciones["H2O"]
    }])

    # Predecir
    prediccion = modelo.predict(entrada)
    ch4, co, h2 = prediccion[0]

    # Mostrar resultados
    st.success("Predicción completada")
    st.metric("CH₄ (%)", f"{ch4:.2f}")
    st.metric("CO (%)", f"{co:.2f}")
    st.metric("H₂ (%)", f"{h2:.2f}")

    # Calcular indicadores para aplicación
    h2_co = h2 / co if co != 0 else 0
    fuel_energy = (0.126 * h2) + (0.108 * co) + (0.358 * ch4) + ((h2 / 100) * 1.2 * 2.45)

    aplicacion = sugerir_aplicacion(h2_co, fuel_energy)
    st.metric("Relación H₂/CO", f"{h2_co:.2f}")
    st.metric("Contenido energético [MJ/m³]", f"{fuel_energy:.2f}")
    st.info(f"**Aplicación recomendada del syngas:** {aplicacion}")
