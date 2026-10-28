import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# Configuración de la página de Streamlit
st.set_page_config(page_title="PPC Analysis", layout="wide")

# =====================================================================
# MEJORA VISUAL: Inyección de CSS para crear "Tarjetas" en las Métricas
# =====================================================================
st.markdown("""
<style>
    /* Fondo general sutil para hacer resaltar las tarjetas blancas */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Estilos para encapsular los KPIs en cuadros (cards) */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease-in-out;
    }
    
    /* Pequeño efecto de elevación al pasar el mouse por los KPIs */
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

st.title("PPC Analysis")
st.markdown("Interactive analysis of daily PPC with dynamic boxplots based on selected dates.")
st.divider() # Añade una línea divisoria elegante

# =====================================================================
# PASO 1 y 2: Conexión y Limpieza de Datos Diarios
# =====================================================================
id_copia = "1DQ35TWjRSx7SV0JDHI0Wu57y7-wkXE6WhRjmpJx3Qo8"
sheet_url = f"https://docs.google.com/spreadsheets/d/{id_copia}/export?format=xlsx"
nombre_pestana = "PPC DATABASE"

@st.cache_data 
def cargar_datos_diarios(url, pestana):
    df_global = pd.read_excel(url, sheet_name=pestana, header=0, usecols="B,M,N,O,P,Q")
    df_global.columns = ['fecha_semana', 'PPC_MON', 'PPC_TUE', 'PPC_WED', 'PPC_THU', 'PPC_FRI']
    df_global = df_global.dropna(subset=['fecha_semana']).copy()
