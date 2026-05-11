import pandas as pd
import streamlit as st

def identificar_cancelaciones(df_vtex, df_skus_error, umbral_pct):
    # 1. LIMPIEZA TOTAL DE COLUMNAS (Versión reforzada para BOM)
    # Reemplazamos caracteres extraños y limpiamos nombres
    df_vtex.columns = [
        str(c).replace('ï»¿', '').strip().lower() 
        for c in df_vtex.columns
    ]
    df_skus_error.columns = [
        str(c).replace('ï»¿', '').strip().lower() 
        for c in df_skus_error.columns
    ]

    # 2. IDENTIFICACIÓN AUTOMÁTICA DE COLUMNAS
    # Buscamos 'sku' y 'id' (que es lo que detectaste en tu archivo)
    col_orden_list = [c for c in df_vtex.columns if 'id' in c or 'order' in c or 'pedido' in c]
    col_sku_vtex_list = [c for c in df_vtex.columns if 'sku' in c]
    col_sku_err_list = [c for c in df_skus_error.columns if 'sku' in c]

    if not col_orden_list or not col_sku_vtex_list or not col_sku_err_list:
        st.error(f"No encontré las columnas. Detecté: {df_vtex.columns.tolist()}")
        st.stop()

    col_orden = col_orden_list[0]
    col_sku = col_sku_vtex_list[0]
    col_sku_err = col_sku_err_list[0]

    # 3. Normalización de datos (aseguramos texto)
    df_vtex[col_orden] = df_vtex[col_orden].astype(str).str.strip()
    df_vtex[col_sku] = df_vtex[col_sku].astype(str).str.strip()
    df_skus_error[col_sku_err] = df_skus_error[col_sku_err].astype(str).str.strip()

    # 4. Identificar qué órdenes tienen SKUs irrisorios
    # Usamos un 'set' para que la búsqueda sea ultra rápida
    set_errores = set(df_skus_error[col_sku_err])
    df_vtex['es_irrisorio'] = df_vtex[col_sku].apply(lambda x: x in set_errores)

    # 5. Agrupar por orden
    resumen = df_vtex.groupby(col_orden).agg(
        total_skus=(col_sku, 'count'),
        skus_irrisorios=('es_irrisorio', 'sum')
    ).reset_index()

    # 6. Calcular el porcentaje
    resumen['pct_irrisorio'] = (resumen['skus_irrisorios'] / resumen['total_skus']) * 100

    # 7. Filtrar órdenes según umbral
    ordenes_a_cancelar = resumen[resumen['pct_irrisorio'] >= umbral_pct].copy()

    # 8. Formatear el output
    if not ordenes_a_cancelar.empty:
        ordenes_a_cancelar['pct_irrisorio'] = ordenes_a_cancelar['pct_irrisorio'].round(2).astype(str) + '%'
        return ordenes_a_cancelar.sort_values(by='total_skus', ascending=False)
    else:
        return pd.DataFrame(columns=[col_orden, 'total_skus', 'skus_irrisorios', 'pct_irrisorio'])

# --- INTERFAZ DE STREAMLIT ---

# Setear contraseña
password = st.text_input("Introduce la contraseña para acceder", type="password")
if password != "Metafar2026!":
    st.stop()

# Barra lateral
st.sidebar.header("Configuración")
umbral = st.sidebar.slider("Umbral de SKUs Irrisorios (%)", min_value=0, max_value=100, value=50, step=5)

# Carga de archivos
col1, col2 = st.columns(2)
with col1:
    file_vtex = st.file_uploader("Carga el reporte de VTEX (CSV)", type=["csv"])
with col2:
    file_skus_error = st.file_uploader("Carga el listado de SKUs irrisorios (CSV)", type=["csv"])

if file_vtex and file_skus_error:
    # Función para leer CSV con manejo de errores de formato
    def safe_read(file):
        try:
            return pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
        except:
            return pd.read_csv(file, sep=None, engine='python', encoding='utf-8')

    df_vtex_raw = safe_read(file_vtex)
    df_skus_error_raw = safe_read(file_skus_error)

    if st.button("Identificar Órdenes a Cancelar"):
        with st.spinner("Procesando datos..."):
            resultado = identificar_cancelaciones(df_vtex_raw, df_skus_error_raw, umbral)
        
        if not resultado.empty:
            st.success(f"Identificación completada. Se encontraron {len(resultado)} órdenes.")
            st.dataframe(resultado, use_container_width=True)

            csv = resultado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar resultado como CSV",
                data=csv,
                file_name='ordenes_a_cancelar.csv',
                mime='text/csv',
            )
        else:
            st.warning("No se encontraron órdenes que cumplan con el umbral seleccionado.")
