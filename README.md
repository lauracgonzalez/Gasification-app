# Gasification-app

## 📌 Descripción

Esta aplicación web interactiva permite predecir la **composición del gas de síntesis (syngas)** generado a partir de la gasificación de distintos tipos de biomasa bajo condiciones operativas específicas. Utiliza un modelo de aprendizaje automático previamente entrenado para estimar las fracciones molares de **CH₄, CO y H₂**, además de sugerir la aplicación más adecuada del syngas resultante (como energía térmica, producción de metanol o metano).

## ⚙️ Funcionalidades principales

- Selección de biomasa entre una lista predefinida.
- Ajuste del contenido de humedad, temperatura de gasificación y tipo de agente gasificante (aire, oxígeno, vapor de agua).
- Rebalanceo automático de la composición química de la biomasa según el contenido de humedad.
- Cálculo del poder calorífico (LHV) de la biomasa.
- Estimación de la composición del syngas mediante un modelo de regresión entrenado.
- Sugerencia del uso final del syngas basado en su relación H₂/CO y contenido energético.

## 🧪 Importancia en el ámbito de la gasificación

La caracterización y predicción del syngas es crítica para el diseño y optimización de procesos eficientes, además de permitir evaluar el comportamiento de distintos residuos lignocelulósicos, sin necesidad de recurrir a costosos y extensos experimentos. Esta herramienta facilita:

- El estudio de diversas biomasas residuales para su valorización energética.
- La optimización de condiciones operativas sin necesidad de realizar experimentos costosos.
- La selección de la mejor ruta energética para el syngas producido (energía térmica directa o síntesis química).

## 📂 Requisitos

- Archivo `regressor_bootstrap.pkl` con el modelo de regresión entrenado.
- Archivo `biomass_compositions.xlsx` con los datos normalizados (ar) de análisis último y próximo de las biomasas.

## 🚀 Cómo usar

1. Ejecuta `streamlit run app.py`.
2. Carga el modelo y los datos si se solicitan.
3. Explora distintas combinaciones de biomasa y parámetros de operación.
4. Obtén predicciones del syngas y recomendaciones de uso final.
