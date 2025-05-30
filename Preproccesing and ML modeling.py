# -*- coding: utf-8 -*-
"""

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1AMd3i5It6BKYIkAXPglMdfZUuZ8gIOV5
"""

import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.utils import resample
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import train_test_split, GridSearchCV
import os
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, max_error
from mpl_toolkits.axes_grid1 import make_axes_locatable

"""# PROCESAMIENTO DATASET"""

# Importar excel desde carpeta local
biomasa_df = pd.read_excel('/content/DATABASE BIOMASA RESIDUAL FINAL COPIA.xlsm')
biomasa_df_literature = pd.read_excel('/content/DATABASE BIOMASA RESIDUAL FINAL COPIA.xlsm', sheet_name='Literature review')
pd.set_option('display.precision', 3)
display(biomasa_df)

# Eliminar espacios extras al final de cada palabra
for column in biomasa_df.columns:
  if biomasa_df[column].dtype == 'object':
    biomasa_df[column] = biomasa_df[column].str.strip()

# Función para categorizar el syngas
def categorize_syngas(h2_co, fuel_energy):
    if fuel_energy >= 1.23 and h2_co < 1.8:
        return "Heat/Power"
    elif 1.23 <= fuel_energy <= 18.44 and 1.8 <= h2_co < 3:
        return "Methanol/Biofuels"
    elif 1.23 <= fuel_energy <= 18.44 and h2_co >= 3:
        return "Methane"
    else:
        return "Others"

# Aplicar la función de clasificación
biomasa_df['End-use application'] = biomasa_df.apply(
    lambda row: categorize_syngas(row['H2 to CO ratio'], row['Fuel gas energy content HHV (d.b.) [MJ/m3]']), axis=1
)

# Ver distribución de clases de dataframe original
print(biomasa_df['End-use application'].value_counts())

"""**Acá se puede visualizar como los datos con los que se entrenan el modelo están desbalanceados**"""

selected_columns = ['Gasification temperature [°C]','Gasifying agent ', 'O2_gasifying agent (wt/wt)',  'N2_gasifying agent (wt/wt)', 'Steam_gasifying agent (wt/wt)','C_norm', 'H_norm',
       'O_norm', 'N_norm', 'S_norm', 'Cl_norm', 'VM [%] _norm', 'Ash [%] _norm',
       'FC [%] _norm', 'Biomass Energy Content (LHV) [MJ/kg]',
       'Intrinsic moisture content [%]', 'H2_dry', 'CH4_dry', 'CO_dry', 'Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio','End-use application']

biomasa_df[selected_columns]

biomasa_df_processed = biomasa_df[selected_columns].copy()

# Chequear valores nulos en el dataset
df_null = pd.DataFrame(columns=['column','null','total','%'])

for col in biomasa_df_processed .columns:
  count_null = biomasa_df_processed [col].isna().sum()
  total = len(biomasa_df_processed [col])
  percentage = (count_null/total)*100
  df_null.loc[len(df_null)] = [col, count_null, total, percentage]

df_null

# Imputar datos faltantes en agentes gasificantes por la media

# Filtrar el DataFrame para incluir solo las filas donde 'Gasifying agent ' es 'Steam'
steam_df = biomasa_df_processed [biomasa_df_processed ['Gasifying agent '] == 'Steam']
air_df = biomasa_df_processed [biomasa_df_processed ['Gasifying agent '] == 'Air']

# Calcular la media de 'Biomass feed rate (kg/h)' y 'Steam/Gasifying agent ratio' para las filas filtradas
mean_steam_gasifying_agent_ratio_steam = steam_df['Steam_gasifying agent (wt/wt)'].mean()
mean_air_gasifying_agent_ratio_air = air_df['O2_gasifying agent (wt/wt)'].mean()
mean_air_gasifying_agent_ratio_air = air_df['N2_gasifying agent (wt/wt)'].mean()

print("Media de 'Steam_gasifying agent (wt/wt)':", mean_steam_gasifying_agent_ratio_steam)
print("Media de 'O2_gasifying agent (wt/wt)':", mean_air_gasifying_agent_ratio_air)
print("Media de 'N2_gasifying agent (wt/wt)':", mean_air_gasifying_agent_ratio_air)

# Imputar los valores faltantes en 'Biomass feed rate (kg/h)' y 'Steam/Gasifying agent ratio' con la media calculada
biomasa_df_processed ['Steam_gasifying agent (wt/wt)'].fillna(mean_steam_gasifying_agent_ratio_steam, inplace=True)
biomasa_df_processed ['O2_gasifying agent (wt/wt)'].fillna(mean_air_gasifying_agent_ratio_air, inplace=True)
biomasa_df_processed ['N2_gasifying agent (wt/wt)'].fillna(mean_air_gasifying_agent_ratio_air, inplace=True)

display(biomasa_df_processed)

print(biomasa_df_processed.columns)

# Redondear las columnas numéricas a dos cifras significativas
for col in biomasa_df_processed.select_dtypes(include=['number']):
    biomasa_df[col] = biomasa_df[col].round(2)

# Descargar el dataframe filtrado
biomasa_df_processed .to_excel('biomasa_filtrado.xlsx', index=False)

biomasa_filtrado = biomasa_df_processed .drop(columns=['Gasifying agent '])

# Descargar el dataframe filtrado
biomasa_filtrado.to_excel('biomasa_filtrado_numerico.xlsx', index=False)

df = pd.read_excel('biomasa_filtrado_numerico.xlsx')
X = df.drop('End-use application', axis=1)  # Todas las columnas excepto la clase
y = df['End-use application']  # Variable objetivo

"""# REBALANCEO DE CLASES

Aplicar técnicas de remuestreo para hacer oversampling sobre categorías minoritarias
"""

# 1. SMOTE
smote = SMOTE(sampling_strategy={'Methane': 100, 'Methanol/Biofuels': 100}, random_state=42)
X_smote, y_smote = smote.fit_resample(X, y)

# 2. BOOTSTRAP
def bootstrap_minority_class(X, y, target_class, n_samples):
    class_indices = y[y == target_class].index
    X_class = X.loc[class_indices]
    y_class = y.loc[class_indices]
    X_resampled, y_resampled = resample(X_class, y_class, n_samples=n_samples, random_state=42)
    return X_resampled, y_resampled

X_bootstrap = X.copy()
y_bootstrap = y.copy()

# Aplicar bootstrap a cada clase minoritaria
for clase in ['Methane', 'Methanol/Biofuels']:
    X_res, y_res = bootstrap_minority_class(X, y, clase, 100)
    X_bootstrap = pd.concat([X_bootstrap, X_res])
    y_bootstrap = pd.concat([y_bootstrap, y_res])

# 3. KDE
def kde_sampling(X, y, target_class, n_samples):
    class_indices = y[y == target_class].index
    X_class = X.loc[class_indices]

    kde = KernelDensity(kernel='gaussian', bandwidth=0.5)
    kde.fit(X_class)

    synthetic_samples = kde.sample(n_samples=n_samples, random_state=42)
    synthetic_samples = pd.DataFrame(synthetic_samples, columns=X.columns)
    synthetic_labels = pd.Series([target_class] * n_samples)

    return synthetic_samples, synthetic_labels

X_kde = X.copy()
y_kde = y.copy()

# Aplicar KDE a cada clase minoritaria
for clase in ['Methane', 'Methanol/Biofuels']:
    X_res, y_res = kde_sampling(X, y, clase, 100)
    X_kde = pd.concat([X_kde, X_res])
    y_kde = pd.concat([y_kde, y_res])

# Comparar distribuciones
print("\
Distribución después de SMOTE:")
print(pd.Series(y_smote).value_counts())
print("\
Distribución después de Bootstrap:")
print(y_bootstrap.value_counts())
print("\
Distribución después de KDE:")
print(y_kde.value_counts())

# 1. SMOTE: remuestreo sintético interpolando entre vecinos cercanos de las clases minoritarias
df_smote = pd.DataFrame(X_smote, columns=X.columns)
df_smote['End-use application'] = y_smote
print('SMOTE resampled DataFrame:')
display(df_smote.round(2))

# Eliminar columnas no numéricas para SMOTE
numerical_cols_smote = df_smote.select_dtypes(include=np.number).columns
df_smote_numerical = df_smote[numerical_cols_smote]

# Dividir en conjuntos de entrenamiento y prueba para SMOTE
train_smote_df, test_smote_df = train_test_split(df_smote_numerical, test_size=0.2, random_state=42)
print("\nSMOTE Training set shape:", train_smote_df.shape)
print("SMOTE Testing set shape:", test_smote_df.shape)

# 2. BOOTSTRAP: remuestreo aleatorio con reemplazo para igualar las clases minoritarias
def bootstrap_resample(X, y, target_class, n_samples):
    X_class = X[y == target_class]
    y_class = y[y == target_class]
    X_resampled, y_resampled = resample(X_class, y_class, replace=True, n_samples=n_samples, random_state=42)
    return X_resampled, y_resampled

n_target = y.value_counts().max()
X_bootstrap = X.copy()
y_bootstrap = y.copy()
for cls in y.value_counts().index:
    if y.value_counts()[cls] < n_target:
        X_res, y_res = bootstrap_resample(X, y, cls, n_target - y.value_counts()[cls])
        X_bootstrap = pd.concat([X_bootstrap, X_res], axis=0)
        y_bootstrap = pd.concat([y_bootstrap, y_res], axis=0)

df_bootstrap = pd.DataFrame(X_bootstrap, columns=X.columns)
df_bootstrap['End-use application'] = y_bootstrap
print('Bootstrap resampled DataFrame:')
display(df_bootstrap.round(2))

# Eliminar columnas no numéricas para Bootstrap
numerical_cols_bootstrap = df_bootstrap.select_dtypes(include=np.number).columns
df_bootstrap_numerical = df_bootstrap[numerical_cols_bootstrap]

# Dividir en conjuntos de entrenamiento y prueba para Bootstrap
train_bootstrap_df, test_bootstrap_df = train_test_split(df_bootstrap_numerical, test_size=0.2, random_state=42)
print("\nBootstrap Training set shape:", train_bootstrap_df.shape)
print("Bootstrap Testing set shape:", test_bootstrap_df.shape)


# 3. KDE: remuestreo sintético usando ruido gaussiano para las clases minoritarias
def kde_resample(X, n_samples):
    kde = KernelDensity(kernel='gaussian', bandwidth=0.5).fit(X)
    samples = kde.sample(n_samples, random_state=42)
    return pd.DataFrame(samples, columns=X.columns)

X_kde = X.copy()
y_kde = y.copy()
for cls in y.value_counts().index:
    if y.value_counts()[cls] < n_target:
        X_class = X[y == cls]
        n_to_add = n_target - y.value_counts()[cls]
        X_kde_samples = kde_resample(X_class, n_to_add)
        X_kde = pd.concat([X_kde, X_kde_samples], axis=0)
        y_kde = pd.concat([y_kde, pd.Series([cls]*n_to_add)], axis=0)

df_kde = pd.DataFrame(X_kde, columns=X.columns)
df_kde['End-use application'] = y_kde
print('KDE resampled DataFrame:')
display(df_kde.round(2))

# Eliminar columnas no numéricas para KDE
numerical_cols_kde = df_kde.select_dtypes(include=np.number).columns
df_kde_numerical = df_kde[numerical_cols_kde]

# Dividir en conjuntos de entrenamiento y prueba para KDE
train_kde_df, test_kde_df = train_test_split(df_kde_numerical, test_size=0.2, random_state=42)
print("\nKDE Training set shape:", train_kde_df.shape)
print("KDE Testing set shape:", test_kde_df.shape)

from google.colab import files
train_bootstrap_df.to_excel('df_resampled_train.xlsx', index=False)
files.download('df_resampled_train.xlsx') # Use files.download() to initiate the download
test_bootstrap_df.to_excel('df_resampled_test.xlsx', index=False)
files.download('df_resampled_test.xlsx') # Use files.download() to initiate the download

output_dir = '/content/PARTICIONES/'
os.makedirs(output_dir, exist_ok=True)

# Almacenar los conjuntos de datos (numéricos)
train_smote_df.to_csv(os.path.join(output_dir, 'train_smote.csv'), index=False)
test_smote_df.to_csv(os.path.join(output_dir, 'test_smote.csv'), index=False)

train_bootstrap_df.to_csv(os.path.join(output_dir, 'train_bootstrap.csv'), index=False)
test_bootstrap_df.to_csv(os.path.join(output_dir, 'test_bootstrap.csv'), index=False)

train_kde_df.to_csv(os.path.join(output_dir, 'train_kde.csv'), index=False)
test_kde_df.to_csv(os.path.join(output_dir, 'test_kde.csv'), index=False)

print(f"\nLos conjuntos de entrenamiento y prueba para cada técnica se han guardado en: {output_dir}")

"""# ENTRENAMIENTO MODELO ML: ÁRBOLES DE DECISIÓN

Entrenar un modelo de árbol de decisión: Para cada técnica de remuestreo, se entrena un modelo DecisionTreeRegressor utilizando los mejores hiperparámetros encontrados previamente
"""

# 1. SMOTE
df_smote = pd.DataFrame(X_smote, columns=X.columns)
df_smote['End-use application'] = y_smote

X_smote_train = df_smote.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_smote_train = df_smote[['H2_dry', 'CO_dry', 'CH4_dry']]

X_smote_test = df_smote.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_smote_test = df_smote[['H2_dry', 'CO_dry', 'CH4_dry']]

# Definir el espacio de hiperparámetros para GridSearchCV
param_grid = {
    'max_depth': [3, 5, 7, 10, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'min_impurity_decrease': [0.0, 0.1]
}

# Crear el objeto GridSearchCV y ajustarlo a los datos de entrenamiento RESAMPLED con SMOTE
grid_search = GridSearchCV(DecisionTreeRegressor(random_state=42), param_grid, cv=5, scoring='neg_mean_squared_error', n_jobs=-1)
grid_search.fit(X_smote_train, y_smote_train)

# Mostrar los mejores parámetros encontrados por GridSearchCV
print("\nMejores parámetros encontrados por GridSearchCV para SMOTE:")
print(grid_search.best_params_)

regressor_smote = DecisionTreeRegressor(**grid_search.best_params_, random_state=42)
regressor_smote.fit(X_smote_train, y_smote_train)
y_pred_smote = regressor_smote.predict(X_smote_test)

print("\nResultados con datos remuestreados con SMOTE:")
mse_H2_smote = mean_squared_error(y_smote_test['H2_dry'], y_pred_smote[:, 0])
r2_H2_smote = r2_score(y_smote_test['H2_dry'], y_pred_smote[:, 0])
mae_H2_smote = mean_absolute_error(y_smote_test['H2_dry'], y_pred_smote[:, 0])
print(f"  R^2 de H2: {r2_H2_smote:.2f}, MSE de H2: {mse_H2_smote:.2f}, MAE de H2: {mae_H2_smote:.2f}")

mse_CO_smote = mean_squared_error(y_smote_test['CO_dry'], y_pred_smote[:, 1])
r2_CO_smote = r2_score(y_smote_test['CO_dry'], y_pred_smote[:, 1])
mae_CO_smote = mean_absolute_error(y_smote_test['CO_dry'], y_pred_smote[:, 1])
print(f"  R^2 de CO: {r2_CO_smote:.2f}, MSE de CO: {mse_CO_smote:.2f}, MAE de CO: {mae_CO_smote:.2f}")

mse_CH4_smote = mean_squared_error(y_smote_test['CH4_dry'], y_pred_smote[:, 2])
r2_CH4_smote = r2_score(y_smote_test['CH4_dry'], y_pred_smote[:, 2])
mae_CH4_smote = mean_absolute_error(y_smote_test['CH4_dry'], y_pred_smote[:, 2])
print(f"  R^2 de CH4: {r2_CH4_smote:.2f}, MSE de CH4: {mse_CH4_smote:.2f}, MAE de CH4: {mae_CH4_smote:.2f}")

# 2. Bootstrap
def bootstrap_resample(X, y, target_class, n_samples):
    X_class = X[y == target_class]
    y_class = y[y == target_class]
    X_resampled, y_resampled = resample(X_class, y_class, replace=True, n_samples=n_samples, random_state=42)
    return X_resampled, y_resampled

n_target = y.value_counts().max()
X_bootstrap = X.copy()
y_bootstrap = y.copy()
for cls in y.value_counts().index:
    if y.value_counts()[cls] < n_target:
        X_res, y_res = bootstrap_resample(X, y, cls, n_target - y.value_counts()[cls])
        X_bootstrap = pd.concat([X_bootstrap, X_res], axis=0)
        y_bootstrap = pd.concat([y_bootstrap, y_res], axis=0)

df_bootstrap = pd.DataFrame(X_bootstrap, columns=X.columns)
df_bootstrap['End-use application'] = y_bootstrap

X_bootstrap_train = df_bootstrap.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_bootstrap_train = df_bootstrap[['H2_dry', 'CO_dry', 'CH4_dry']]

X_bootstrap_test = df_bootstrap.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_bootstrap_test = df_bootstrap[['H2_dry', 'CO_dry', 'CH4_dry']]

# Definir el espacio de hiperparámetros para GridSearchCV
param_grid = {
    'max_depth': [3, 5, 7, 10, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'min_impurity_decrease': [0.0, 0.1]
}

# Crear el objeto GridSearchCV y ajustarlo a los datos de entrenamiento RESAMPLED con SMOTE
grid_search = GridSearchCV(DecisionTreeRegressor(random_state=42), param_grid, cv=5, scoring='neg_mean_squared_error', n_jobs=-1)
grid_search.fit(X_bootstrap_train, y_bootstrap_train)

# Mostrar los mejores parámetros encontrados por GridSearchCV
print("\nMejores parámetros encontrados por GridSearchCV para Bootstrap:")
print(grid_search.best_params_)

regressor_bootstrap = DecisionTreeRegressor(**grid_search.best_params_, random_state=42)
regressor_bootstrap.fit(X_bootstrap_train, y_bootstrap_train)
y_pred_bootstrap = regressor_bootstrap.predict(X_bootstrap_test)

print("\nResultados con datos remuestreados con Bootstrap:")
mse_H2_bootstrap = mean_squared_error(y_bootstrap_test['H2_dry'], y_pred_bootstrap[:, 0])
r2_H2_bootstrap = r2_score(y_bootstrap_test['H2_dry'], y_pred_bootstrap[:, 0])
mae_H2_bootstrap = mean_absolute_error(y_bootstrap_test['H2_dry'], y_pred_bootstrap[:, 0])
print(f"  R^2 de H2: {r2_H2_bootstrap:.2f}, MSE de H2: {mse_H2_bootstrap:.2f}, MAE de H2: {mae_H2_bootstrap:.2f}")

mse_CO_bootstrap = mean_squared_error(y_bootstrap_test['CO_dry'], y_pred_bootstrap[:, 1])
r2_CO_bootstrap = r2_score(y_bootstrap_test['CO_dry'], y_pred_bootstrap[:, 1])
mae_CO_bootstrap = mean_absolute_error(y_bootstrap_test['CO_dry'], y_pred_bootstrap[:, 1])
print(f"  R^2 de CO: {r2_CO_bootstrap:.2f}, MSE de CO: {mse_CO_bootstrap:.2f}, MAE de CO: {mae_CO_bootstrap:.2f}")

mse_CH4_bootstrap = mean_squared_error(y_bootstrap_test['CH4_dry'], y_pred_bootstrap[:, 2])
r2_CH4_bootstrap = r2_score(y_bootstrap_test['CH4_dry'], y_pred_bootstrap[:, 2])
mae_CH4_bootstrap = mean_absolute_error(y_bootstrap_test['CH4_dry'], y_pred_bootstrap[:, 2])
print(f"  R^2 de CH4: {r2_CH4_bootstrap:.2f}, MSE de CH4: {mse_CH4_bootstrap:.2f}, MAE de CH4: {mae_CH4_bootstrap:.2f}")

# 3. KDE
def kde_resample(X, n_samples):
    kde = KernelDensity(kernel='gaussian', bandwidth=0.5).fit(X)
    samples = kde.sample(n_samples, random_state=42)
    return pd.DataFrame(samples, columns=X.columns)

X_kde = X.copy()
y_kde = y.copy()
for cls in y.value_counts().index:
    if y.value_counts()[cls] < n_target:
        X_class = X[y == cls]
        n_to_add = n_target - y.value_counts()[cls]
        X_kde_samples = kde_resample(X_class, n_to_add)
        X_kde = pd.concat([X_kde, X_kde_samples], axis=0)
        y_kde = pd.concat([y_kde, pd.Series([cls]*n_to_add)], axis=0)

df_kde = pd.DataFrame(X_kde, columns=X.columns)
df_kde['End-use application'] = y_kde

X_kde_train = df_kde.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_kde_train = df_kde[['H2_dry', 'CO_dry', 'CH4_dry']]

X_kde_test = df_kde.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
y_kde_test = df_kde[['H2_dry', 'CO_dry', 'CH4_dry']]

# Definir el espacio de hiperparámetros para GridSearchCV
param_grid = {
    'max_depth': [3, 5, 7, 10, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'min_impurity_decrease': [0.0, 0.1]
}

# Crear el objeto GridSearchCV y ajustarlo a los datos de entrenamiento RESAMPLED con SMOTE
grid_search = GridSearchCV(DecisionTreeRegressor(random_state=42), param_grid, cv=5, scoring='neg_mean_squared_error', n_jobs=-1)
grid_search.fit(X_kde_train, y_kde_train)

# Mostrar los mejores parámetros encontrados por GridSearchCV
print("\nMejores parámetros encontrados por GridSearchCV para KDE:")
print(grid_search.best_params_)

regressor_kde = DecisionTreeRegressor(**grid_search.best_params_, random_state=42)
regressor_kde.fit(X_kde_train, y_kde_train)
y_pred_kde = regressor_kde.predict(X_kde_test)

print("\nResultados con datos remuestreados con KDE:")
mse_H2_kde = mean_squared_error(y_kde_test['H2_dry'], y_pred_kde[:, 0])
r2_H2_kde = r2_score(y_kde_test['H2_dry'], y_pred_kde[:, 0])
mae_H2_kde = mean_absolute_error(y_kde_test['H2_dry'], y_pred_kde[:, 0])
print(f"  R^2 de H2: {r2_H2_kde:.2f}, MSE de H2: {mse_H2_kde:.2f}, MAE de H2: {mae_H2_kde:.2f}")

mse_CO_kde = mean_squared_error(y_kde_test['CO_dry'], y_pred_kde[:, 1])
r2_CO_kde = r2_score(y_kde_test['CO_dry'], y_pred_kde[:, 1])
mae_CO_kde = mean_absolute_error(y_kde_test['CO_dry'], y_pred_kde[:, 1])
print(f"  R^2 de CO: {r2_CO_kde:.2f}, MSE de CO: {mse_CO_kde:.2f}, MAE de CO: {mae_CO_kde:.2f}")

mse_CH4_kde = mean_squared_error(y_kde_test['CH4_dry'], y_pred_kde[:, 2])
r2_CH4_kde = r2_score(y_kde_test['CH4_dry'], y_pred_kde[:, 2])
mae_CH4_kde = mean_absolute_error(y_kde_test['CH4_dry'], y_pred_kde[:, 2])
print(f"  R^2 de CH4: {r2_CH4_kde:.2f}, MSE de CH4: {mse_CH4_kde:.2f}, MAE de CH4: {mae_CH4_kde:.2f}")

import pickle

# Guardar el modelo entrenado con KDE en un archivo pickle
with open('regressor_bootstrap.pkl', 'wb') as file:
    pickle.dump(regressor_bootstrap, file)

print("Modelo de árbol de decisión con remuestreo KDE guardado como 'regressor_bootstrap.pkl'")

import pickle

# Guardar el modelo entrenado con KDE en un archivo pickle
with open('regressor_kde_model.pkl', 'wb') as file:
    pickle.dump(regressor_kde, file)

print("Modelo de árbol de decisión con remuestreo KDE guardado como 'regressor_kde_model.pkl'")

import pandas as pd
# Load the model from the pickle file
with open('regressor_kde_model.pkl', 'rb') as file:
    regressor_kde = pickle.load(file)

# Assuming 'X_kde_test' is defined as in your original code
# If not, you'll need to load or recreate your test dataset.

# Access the feature importances
feature_importances = regressor_kde.feature_importances_

# Get the column names from your training data
# Replace 'X_kde_train' with the actual name of your training data DataFrame
X_kde_train = df_kde.drop(['H2_dry', 'CO_dry', 'CH4_dry', 'End-use application','Fuel gas energy content HHV (d.b.) [MJ/m3]','H2 to CO ratio'], axis=1)
feature_names = X_kde_train.columns


# Create a DataFrame for better visualization
importance_df = pd.DataFrame({'Feature': feature_names, 'Importance': feature_importances})

# Sort by importance
importance_df = importance_df.sort_values(by='Importance', ascending=False)

# Print the DataFrame
importance_df

# Crear un DataFrame con las predicciones y los valores reales para SMOTE
results_smote_df = pd.DataFrame({
    'H2_dry_real': y_smote_test['H2_dry'],
    'H2_dry_pred_SMOTE': y_pred_smote[:, 0],
    'CO_dry_real': y_smote_test['CO_dry'],
    'CO_dry_pred_SMOTE': y_pred_smote[:, 1],
    'CH4_dry_real': y_smote_test['CH4_dry'],
    'CH4_dry_pred_SMOTE': y_pred_smote[:, 2]
})

print("\nPredicciones del modelo entrenado con SMOTE:")
display(results_smote_df)

# Crear un DataFrame con las predicciones y los valores reales para Bootstrap
results_bootstrap_df = pd.DataFrame({
    'H2_dry_real': y_bootstrap_test['H2_dry'],
    'H2_dry_pred_Bootstrap': y_pred_bootstrap[:, 0],
    'CO_dry_real': y_bootstrap_test['CO_dry'],
    'CO_dry_pred_Bootstrap': y_pred_bootstrap[:, 1],
    'CH4_dry_real': y_bootstrap_test['CH4_dry'],
    'CH4_dry_pred_Bootstrap': y_pred_bootstrap[:, 2]
})

print("\nPredicciones del modelo entrenado con Bootstrap:")
display(results_bootstrap_df)

# Crear un DataFrame con las predicciones y los valores reales para KDE
results_kde_df = pd.DataFrame({
    'H2_dry_real': y_kde_test['H2_dry'],
    'H2_dry_pred_KDE': y_pred_kde[:, 0],
    'CO_dry_real': y_kde_test['CO_dry'],
    'CO_dry_pred_KDE': y_pred_kde[:, 1],
    'CH4_dry_real': y_kde_test['CH4_dry'],
    'CH4_dry_pred_KDE': y_pred_kde[:, 2]
})

print("\nPredicciones del modelo entrenado con KDE:")
display(results_kde_df)

# prompt: imprime los valores únicos de H2_dry_pred_KDE

print(results_kde_df['H2_dry_pred_KDE'].unique())
print(results_kde_df['CO_dry_pred_KDE'].unique())
print(results_kde_df['CH4_dry_pred_KDE'].unique())

target_variables = {
    'H2_dry': {
        'x_label': 'Experimental H$_2$ (dry basis) [vol%]',
        'y_label': 'Predicted H$_2$ (dry basis) [vol%]',
        'bins': np.arange(0, 60 + 1, 5)
    },
    'CO_dry': {
        'x_label': 'Experimental CO (dry basis) [vol%]',
        'y_label': 'Predicted CO (dry basis) [vol%]',
        'bins': np.arange(0, 60 + 1, 5)
    },
    'CH4_dry': {
        'x_label': 'Experimental CH$_4$ (dry basis) [vol%]',
        'y_label': 'Predicted CH$_4$ (dry basis) [vol%]',
        'bins': np.arange(0, 25 + 1, 5)
    }
}

# 1. Gráficos de paridad para el modelo entrenado con SMOTE
print("\nGráficos de paridad para el modelo entrenado con SMOTE:")
fig_smote, axes_smote = plt.subplots(1, 3, figsize=(28, 8))
fig_smote.suptitle('Test performance for the compositional prediction of H$_2$, CO and CH$_4$ (SMOTE)', y=-0.05, fontsize=20)

for i, target_var in enumerate(target_variables):
    y_true = y_smote_test[target_var]
    y_pred_var = y_pred_smote[:, i]

    ax_main = axes_smote[i]
    ax_main.scatter(y_true, y_pred_var, alpha=0.6, color='k', s=90)
    min_val = min(min(y_true), min(y_pred_var)) - 1
    max_val = max(max(y_true), max(y_pred_var)) + 5
    ax_main.plot([min_val, max_val], [min_val, max_val], 'g-', lw=2, zorder=0, label='y=x')

    r2 = r2_score(y_true, y_pred_var)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred_var))
    mae = np.mean(np.abs(y_true - y_pred_var))
    textstr = f'R2={r2:.2f}\nRMSE={rmse:.2f}\nMAE={mae:.2f}'
    ax_main.text(0.95, 0.05, textstr, transform=ax_main.transAxes, fontsize=14,
                 verticalalignment='bottom', horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.5))

    ax_main.set_xlabel(target_variables[target_var]['x_label'], fontsize=18)
    ax_main.set_ylabel(target_variables[target_var]['y_label'], fontsize=18)
    ax_main.legend(loc='upper left', fontsize=16)
    ax_main.xaxis.set_label_coords(0.5, -0.1)
    ax_main.yaxis.set_label_coords(-0.08, 0.5)
    ax_main.tick_params(axis='both', which='major', labelsize=18)
    ax_main.set_xlim(min_val, max_val)
    ax_main.set_ylim(min_val, max_val)
    if target_var == 'CH4_dry':
        ax_main.set_xticks(np.arange(0, max_val + 1, 5))
        ax_main.set_yticks(np.arange(0, max_val + 1, 5))

plt.tight_layout(w_pad=3)
plt.show()

# 2. Gráficos de paridad para el modelo entrenado con Bootstrap
print("\nGráficos de paridad para el modelo entrenado con Bootstrap:")
fig_bootstrap, axes_bootstrap = plt.subplots(1, 3, figsize=(28, 8))
fig_bootstrap.suptitle('Test performance for the compositional prediction of H$_2$, CO and CH$_4$ (Bootstrap)', y=-0.05, fontsize=20)

for i, target_var in enumerate(target_variables):
    y_true = y_bootstrap_test[target_var]
    y_pred_var = y_pred_bootstrap[:, i]

    ax_main = axes_bootstrap[i]
    ax_main.scatter(y_true, y_pred_var, alpha=0.6, color='k', s=90)
    min_val = min(min(y_true), min(y_pred_var)) - 1
    max_val = max(max(y_true), max(y_pred_var)) + 5
    ax_main.plot([min_val, max_val], [min_val, max_val], 'g-', lw=2, zorder=0, label='y=x')

    r2 = r2_score(y_true, y_pred_var)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred_var))
    mae = np.mean(np.abs(y_true - y_pred_var))
    textstr = f'R2={r2:.2f}\nRMSE={rmse:.2f}\nMAE={mae:.2f}'
    ax_main.text(0.95, 0.05, textstr, transform=ax_main.transAxes, fontsize=14,
                 verticalalignment='bottom', horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.5))

    ax_main.set_xlabel(target_variables[target_var]['x_label'], fontsize=18)
    ax_main.set_ylabel(target_variables[target_var]['y_label'], fontsize=18)
    ax_main.legend(loc='upper left', fontsize=16)
    ax_main.xaxis.set_label_coords(0.5, -0.1)
    ax_main.yaxis.set_label_coords(-0.08, 0.5)
    ax_main.tick_params(axis='both', which='major', labelsize=18)
    ax_main.set_xlim(min_val, max_val)
    ax_main.set_ylim(min_val, max_val)
    if target_var == 'CH4_dry':
        ax_main.set_xticks(np.arange(0, max_val + 1, 5))
        ax_main.set_yticks(np.arange(0, max_val + 1, 5))

plt.tight_layout(w_pad=3)
plt.show()

# 3. Gráficos de paridad para el modelo entrenado con KDE
print("\nGráficos de paridad para el modelo entrenado con KDE:")
fig_kde, axes_kde = plt.subplots(1, 3, figsize=(28, 8))
fig_kde.suptitle('Test performance for the compositional prediction of H$_2$, CO and CH$_4$ (KDE)', y=-0.05, fontsize=20)

for i, target_var in enumerate(target_variables):
    y_true = y_kde_test[target_var]
    y_pred_var = y_pred_kde[:, i]

    ax_main = axes_kde[i]
    ax_main.scatter(y_true, y_pred_var, alpha=0.6, color='k', s=90)
    min_val = min(min(y_true), min(y_pred_var)) - 1
    max_val = max(max(y_true), max(y_pred_var)) + 5
    ax_main.plot([min_val, max_val], [min_val, max_val], 'g-', lw=2, zorder=0, label='y=x')

    r2 = r2_score(y_true, y_pred_var)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred_var))
    mae = np.mean(np.abs(y_true - y_pred_var))
    textstr = f'R2={r2:.2f}\nRMSE={rmse:.2f}\nMAE={mae:.2f}'
    ax_main.text(0.95, 0.05, textstr, transform=ax_main.transAxes, fontsize=14,
                 verticalalignment='bottom', horizontalalignment='right', bbox=dict(facecolor='white', alpha=0.5))

    ax_main.set_xlabel(target_variables[target_var]['x_label'], fontsize=18)
    ax_main.set_ylabel(target_variables[target_var]['y_label'], fontsize=18)
    ax_main.legend(loc='upper left', fontsize=16)
    ax_main.xaxis.set_label_coords(0.5, -0.1)
    ax_main.yaxis.set_label_coords(-0.08, 0.5)
    ax_main.tick_params(axis='both', which='major', labelsize=18)
    ax_main.set_xlim(min_val, max_val)
    ax_main.set_ylim(min_val, max_val)
    if target_var == 'CH4_dry':
        ax_main.set_xticks(np.arange(0, max_val + 1, 5))
        ax_main.set_yticks(np.arange(0, max_val + 1, 5))

plt.tight_layout(w_pad=3)
plt.show()

tecnicas = ['SMOTE', 'Bootstrap', 'KDE']
gases = ['H2', 'CO', 'CH4']
r2_scores = [
    [0.99, 0.95, 0.89],  # SMOTE
    [1.00, 0.89, 0.96],  # Bootstrap
    [1.00, 0.89, 0.97]   # KDE
]

x = np.arange(len(gases))
width = 0.25

plt.bar(x - width, r2_scores[0], width, label='SMOTE')
plt.bar(x, r2_scores[1], width, label='Bootstrap')
plt.bar(x + width, r2_scores[2], width, label='KDE')
plt.xticks(x, gases)
plt.ylabel('R^2')
plt.title('Comparación de R^2 por Técnica y Gas')
plt.legend()
plt.ylim(0.85, 1.05)
plt.show()

# Datos
tecnicas = ['SMOTE', 'Bootstrap', 'KDE']
gases = ['H2', 'CO', 'CH4']
mae_scores = [
    [1.74, 1.33, 1.06],  # SMOTE
    [0.39, 0.51, 0.28],  # Bootstrap
    [0.71, 0.68, 0.45]   # KDE
]
mse_scores = [
    [5.20, 3.55, 2.10],  # SMOTE
    [0.92, 1.83, 0.80],  # Bootstrap
    [1.90, 1.68, 0.64]   # KDE
]

x = np.arange(len(gases))
width = 0.25

# Gráfico MAE
plt.figure(figsize=(8, 5))
plt.bar(x - width, mae_scores[0], width, label='SMOTE')
plt.bar(x, mae_scores[1], width, label='Bootstrap')
plt.bar(x + width, mae_scores[2], width, label='KDE')
plt.xticks(x, gases)
plt.ylabel('MAE')
plt.title('Comparación de MAE por Técnica y Gas')
plt.legend()
plt.show()

# Gráfico MSE
plt.figure(figsize=(8, 5))
plt.bar(x - width, mse_scores[0], width, label='SMOTE')
plt.bar(x, mse_scores[1], width, label='Bootstrap')
plt.bar(x + width, mse_scores[2], width, label='KDE')
plt.xticks(x, gases)
plt.ylabel('MSE')
plt.title('Comparación de MSE por Técnica y Gas')
plt.legend()
plt.show()

print('Se muestran los gráficos comparativos de MAE y MSE para cada técnica y gas.')
