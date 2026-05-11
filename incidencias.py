import pandas as pd

def identificar_cancelaciones(df_vtex, df_skus_error, umbral_pct):
    """
    df_vtex: DataFrame con el reporte de VTEX (una fila por SKU, múltiples filas por orden).
    df_skus_error: DataFrame con los SKUs que tienen problemas.
    umbral_pct: Entero entre 0 y 100.
    """
    
    # 1. Normalización de datos (aseguramos que SKU y Orden sean texto y no tengan espacios)
    # Ajustar nombres de columnas según el reporte real ('order_id' y 'sku_id')
    df_vtex['order'] = df_vtex['order'].astype(str).str.strip()
    df_vtex['SKU_ID'] = df_vtex['SKU_ID'].astype(str).str.strip()
    df_skus_error['SKU_ID'] = df_skus_error['SKU_ID'].astype(str).str.strip()

    # 2. Identificar qué órdenes tienen SKUs irrisorios
    set_errores = df_skus_error['SKU_ID']
    df_vtex['es_irrisorio'] = df_vtex['SKU_ID'].apply(lambda x: x in set_errores)

    # 3. Agrupar por order para calcular el porcentaje de SKUs irrisorios por orden
    resumen =df_vtex.groupby('order').agg(
        total_skus=('SKU_ID', 'count'),
        skus_irrisorios=('es_irrisorio', 'sum')
    ).reset_index()

    # 4. Calcular el porcentaje de SKUs irrisorios por orden
    resumen['pct_irrisorio'] = (resumen['skus_irrisorios'] / resumen['total_skus']) * 100

    # 5. Filtrar órdenes según umbral dinámico
    ordenes_a_cancelar = resumen[resumen['pct_irrisorio'] >= umbral_pct].copy()

    # 6. Formatea el output

    ordenes_a_cancelar['pct_irrisorio'] = ordenes_a_cancelar['pct_irrisorio'].round(2).astype(str) + '%'

    return ordenes_a_cancelar.sort_values(by='total_skus', ascending=False)



import streamlit as st

# Setear contraseña
password = st.text_input("Introduce la contraseña para acceder", type="password")
if password != "Metafar2026!":
    st.stop() # Detiene la ejecución si la clave es incorrecta

# Barra lateral

st.sidebar.header("Configuración")
umbral = st.sidebar.slider("Umbral de SKUs Irrisorios (%)", min_value=0, max_value=100, value=50, step=5)

# Carga de archivos
col1, col2 = st.columns(2)
with col1:
    file_vtex = st.file_uploader("Carga el reporte de VTEX (CSV)", type=["csv"])
with col2:
    file_skus_error = st.file_uploader("Carga el listado de SKUs irrisorios (CSV)", type=["csv"])

# Procesamiento

if file_vtex and file_skus_error:
    try:
        df_vtex = pd.read_csv(file_vtex, sep=None, engine='python', encoding='latin-1')
    except Exception:
        df_vtex = pd.read_csv(file_vtex, sep=None, engine='python', encoding='utf-8')

    try:
        df_skus_error = pd.read_csv(file_skus_error, sep=None, engine='python', encoding='latin-1')
    except Exception:
        df_skus_error = pd.read_csv(file_skus_error, sep=None, engine='python', encoding='utf-8')

    if st.button("Identificar Órdenes a Cancelar"):
        with st.spinner("Procesando datos..."):
            resultado = identificar_cancelaciones(df_vtex, df_skus_error, umbral)
        
        st.success(f"Identificación completada. Se encontraron {len(resultado)} órdenes a cancelar.")
        st.dataframe(resultado, use_container_width=True)

        # Opción de descarga
        csv = resultado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar resultado como CSV",
            data=csv,
            file_name='ordenes_a_cancelar.csv',
            mime='text/csv',
        )
