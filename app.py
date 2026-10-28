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
st.divider()

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
    df_global['fecha_semana'] = pd.to_datetime(df_global['fecha_semana'], errors='coerce')
    df_global = df_global.dropna(subset=['fecha_semana'])

    df_diario = df_global.melt(
        id_vars=['fecha_semana'],
        value_vars=['PPC_MON', 'PPC_TUE', 'PPC_WED', 'PPC_THU', 'PPC_FRI'],
        var_name='Dia',
        value_name='ppc_diario'
    )

    def clean_percentage(val):
        if pd.isna(val) or str(val).strip() == '': return np.nan
        if isinstance(val, str): val = val.replace('%', '').strip()
        try: return float(val)
        except ValueError: return np.nan

    df_diario['ppc_diario'] = df_diario['ppc_diario'].apply(clean_percentage)
    df_diario = df_diario.dropna(subset=['ppc_diario'])

    if df_diario['ppc_diario'].max() <= 1.0 and df_diario['ppc_diario'].max() > 0:
        df_diario['ppc_diario'] = df_diario['ppc_diario'] * 100

    dias_offset = {
        'PPC_MON': pd.Timedelta(days=0),
        'PPC_TUE': pd.Timedelta(days=1),
        'PPC_WED': pd.Timedelta(days=2),
        'PPC_THU': pd.Timedelta(days=3),
        'PPC_FRI': pd.Timedelta(days=4)
    }
    df_diario['fecha_diaria'] = df_diario['fecha_semana'] + df_diario['Dia'].map(dias_offset)

    return df_diario

# Cargar los datos
with st.spinner('Loading data from Google Sheets...'):
    df_analisis_completo = cargar_datos_diarios(sheet_url, nombre_pestana)

# =====================================================================
# INTERFAZ DE USUARIO: Filtro de Fechas (Sidebar)
# =====================================================================
st.sidebar.header("Analysis Filters")

min_date = df_analisis_completo['fecha_diaria'].min().date()
max_date = df_analisis_completo['fecha_diaria'].max().date()

# Selector de rango de fechas
rango_fechas = st.sidebar.date_input(
    "Select Period (Range):",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Validar que el usuario seleccionó un rango completo (inicio y fin)
if len(rango_fechas) == 2:
    start_date, end_date = rango_fechas
    
    mask = (df_analisis_completo['fecha_diaria'].dt.date >= start_date) & (df_analisis_completo['fecha_diaria'].dt.date <= end_date)
    df_analisis = df_analisis_completo.loc[mask].copy()

    if df_analisis.empty:
        st.warning("No data available for the selected date range.")
    else:
        # =====================================================================
        # PASO 3: Preparación de Datos Filtrados
        # =====================================================================
        df_analisis['Semana_Label'] = df_analisis['fecha_semana'].dt.strftime('%b %d')
        
        df_analisis = df_analisis.sort_values('fecha_semana')
        
        def q25(x): return x.quantile(0.25)
        def q50(x): return x.quantile(0.50)
        def q75(x): return x.quantile(0.75)

        orden_semanas = df_analisis['Semana_Label'].drop_duplicates().tolist()

        stats_semanal = df_analisis.groupby('Semana_Label', sort=False)['ppc_diario'].agg(
            n='count', media='mean', std='std', minimo='min', maximo='max',
            Q1=q25, Q2=q50, Q3=q75
        ).reset_index()

        stats_semanal['RIQ'] = stats_semanal['Q3'] - stats_semanal['Q1']
        stats_semanal['CV'] = np.where(stats_semanal['media'] > 0, (stats_semanal['std'] / stats_semanal['media']) * 100, 0)
        
        stats_semanal['Etiqueta'] = np.where(stats_semanal['media'] == stats_semanal['media'].max(), 'BEST',
                                    np.where(stats_semanal['media'] == stats_semanal['media'].min(), 'WORST', ''))

        promedio_periodo = df_analisis['ppc_diario'].mean()
        std_periodo = df_analisis['ppc_diario'].std()
        meta = 85.00
        total_days = len(df_analisis)

        # KPI Metrics en Streamlit
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("Period Average", f"{promedio_periodo:.1f}%")
        col2.metric("Target", f"{meta}%")
        
        gap = promedio_periodo - meta
        col3.metric("Gap", f"{gap:.1f} pts", delta=f"{gap:.1f} pts", delta_color="normal" if gap > 0 else "inverse")
        
        col4.metric("Standard Dev", f"{std_periodo:.1f}%")
        col5.metric("Total Days", f"{total_days}")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # =====================================================================
        # PASO 4: Generación del Gráfico
        # =====================================================================
        sns.set_theme(style="whitegrid")
        
        # Resolución mejorada con dpi=300
        fig, ax = plt.subplots(figsize=(20, 10), dpi=300)

        flierprops = dict(marker='D', markerfacecolor='#ff4d4d', markersize=8, markeredgecolor='gray', alpha=0.8)
        medianprops = dict(linestyle='-', linewidth=3, color='#ff7f0e')
        boxprops = dict(facecolor='#8cbed6', color='#95b3d7', linewidth=1.5)
        
        sns.boxplot(
            data=df_analisis, x='Semana_Label', y='ppc_diario', ax=ax, width=0.4, order=orden_semanas,
            boxprops=boxprops, medianprops=medianprops, flierprops=flierprops, showfliers=True
        )

        ax.set_ylim(-35, 150)  
        ax.set_yticks(range(0, 101, 10))
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='gray')
        ax.xaxis.grid(False)
        ax.set_xticks(range(len(orden_semanas)))
        
        rotacion = 45 if len(orden_semanas) > 15 else 0
        ax.set_xticklabels(orden_semanas, fontsize=11, fontweight='bold', rotation=rotacion)
        ax.set_xlim(-1.5, len(orden_semanas) - 0.5)
        ax.set_xlabel('Week Starting Date', fontsize=14, fontweight='bold', labelpad=15)
        ax.set_ylabel('Daily PPC (%)', fontsize=14, fontweight='bold')

        ax.axhline(meta, color='blue', linestyle='--', linewidth=2, zorder=0)
        ax.axhline(promedio_periodo, color='#d99594', linestyle='-.', linewidth=2, zorder=0)

        stats_semanal = stats_semanal.set_index('Semana_Label').reindex(orden_semanas).reset_index()

        for i, row in stats_semanal.iterrows():
            color_borde = 'gray'
            if row['Etiqueta'] == 'BEST':
                color_borde = 'blue'
                ax.text(i, 130, '★ BEST', ha='center', va='center', fontsize=9, fontweight='bold',
                        color='black', bbox=dict(boxstyle='round', facecolor='lightgreen', edgecolor='darkgreen'))
            elif row['Etiqueta'] == 'WORST':
                color_borde = 'red'
                ax.text(i, 130, '▼ WORST', ha='center', va='center', fontsize=9, fontweight='bold',
                        color='white', bbox=dict(boxstyle='round', facecolor='#ff4d4d', edgecolor='darkred'))

            ax.text(i, 118, f"Avg: {row['media']:.1f}%", ha='center', va='center', fontsize=9, fontweight='bold',
                    color=color_borde, bbox=dict(boxstyle='round', facecolor='white', edgecolor=color_borde))

            offset_x = 0.28
            ax.text(i + offset_x, row['Q2'], f"Q2: {row['Q2']:.0f}%", color='#ff7f0e', va='center', fontsize=8, fontweight='bold')
            ax.text(i + offset_x, row['Q3'], f"Q3: {row['Q3']:.0f}%", color='black', va='center', fontsize=8)
            ax.text(i + offset_x, row['Q1'], f"Q1: {row['Q1']:.0f}%", color='black', va='center', fontsize=8)

            texto_std = "N/A" if pd.isna(row['std']) else f"{row['std']:.1f}%"
            texto_cv = "N/A" if pd.isna(row['CV']) else f"{row['CV']:.1f}%"

            texto_inferior = (
                f"σ: {texto_std}\n"
                f"CV: {texto_cv}\n"
                f"n={row['n']} days\n"
                f"R: {row['minimo']:.0f}-{row['maximo']:.0f}%"
            )
            
            ax.text(i, -18, texto_inferior, ha='center', va='center', fontsize=8, color='black',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', edgecolor='black'))

        ax.set_title(f"Daily PPC Analysis", fontsize=18, fontweight='bold', pad=25)

        linea_meta = mlines.Line2D([], [], color='blue', linestyle='--', linewidth=2, label='Target 85%')
        linea_promedio = mlines.Line2D([], [], color='#d99594', linestyle='-.', linewidth=2, label=f"Period Avg: {promedio_periodo:.1f}%")
        linea_q2 = mlines.Line2D([], [], color='#ff7f0e', linestyle='-', linewidth=3, label='Q2 (Median)')
        rombo_atipico = mlines.Line2D([], [], color='w', marker='D', markerfacecolor='#ff4d4d', markeredgecolor='gray', markersize=8, label='Outliers')

        ax.legend(handles=[linea_meta, linea_promedio, linea_q2, rombo_atipico],
                  loc='upper right', fontsize=10, framealpha=0.9, edgecolor='black')

        plt.tight_layout()
        
        # Ajuste al ancho del contenedor para mayor nitidez
        st.pyplot(fig, use_container_width=True)

else:
    st.info("Please select a start and end date from the sidebar menu.")
