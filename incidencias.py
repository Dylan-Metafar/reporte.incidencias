import pandas as pd
import streamlit as st

def identificar_cancelaciones(df_vtex, df_skus_error, umbral_pct):
    # 1. Normalización de nombres de columnas (por seguridad)
    df_vtex.columns = [str(c).strip().lower() for c in df_vtex.columns]
    df_skus_error.columns = [str(c).strip().lower() for c in df_skus_error.columns]

    # 2. Definición de nombres (según lo que acordaste con las chicas)
    col_orden = 'order'
    col_sku = 'id_sku'

    # Validar que existan
    if col_orden not in df_vtex.columns or col_sku not in df_vtex.columns:
        st.error(f"El archivo de pedidos debe tener la columna '{col_orden}' y '{col_sku}'.")
        st.stop()
    
    if col_sku not in df_skus_error.columns:
        st.error(f"El archivo de errores debe tener la columna '{col_sku}'.")
        st.stop()

    # 3. Limpieza de datos (Quitar espacios, .0 de Excel y pasar a string)
    def limpiar_texto(serie):
        return serie.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    df_vtex[col_orden] = limpiar_texto(df_vtex[col_orden])
    df_vtex[col_sku] = limpiar_texto(df_vtex[col_sku])
    df_skus_error[col_sku] = limpiar_texto(df_skus_error[col_sku])

    # 4. Cruce de datos
    set_errores = set(df_skus_error[col_sku])
    df_vtex['es_error'] = df_vtex[col_sku].apply(lambda x: x in set_errores)

    # 5. Agrupación por orden
    resumen = df_vtex.groupby(col_orden).agg(
        total_items=(col_sku, 'count'),
        items_con_error=('es_error', 'sum')
    ).reset_index()

    # 6. Cálculo y Filtro
    resumen['porcentaje_error'] = (resumen['items_con_error'] / resumen['total_items']) * 100
    resultado = resumen[resumen['porcentaje_error'] >= umbral_pct].copy()
    
    # 7. Formato final
    resultado['porcentaje_error'] = resultado['porcentaje_error'].round(2).astype(str) + '%'
    
    return resultado.sort_values(by='total_items', ascending=False)

# --- INTERFAZ STREAMLIT ---
st.title("🛡️ Validador de Órdenes Críticas")

# Login simple
password = st.text_input("Contraseña", type="password")
if password != "Metafar2026!":
    st.stop()

st.sidebar.header("Configuración")
umbral = st.sidebar.slider("Umbral de error (%)", 0, 100, 50)

# Inputs
col1, col2 = st.columns(2)
with col1:
    f1 = st.file_uploader("CSV de Pedidos (columnas: order, id_sku)", type="csv")
with col2:
    f2 = st.file_uploader("CSV de Errores (columna: id_sku)", type="csv")

if f1 and f2:
    # Lectura simple
    df1 = pd.read_csv(f1, sep=None, engine='python', encoding='latin-1')
    df2 = pd.read_csv(f2, sep=None, engine='python', encoding='latin-1')

    if st.button("Procesar"):
        res = identificar_cancelaciones(df1, df2, umbral)
        if not res.empty:
            st.success(f"Se encontraron {len(res)} órdenes.")
            st.dataframe(res, use_container_width=True)
            st.download_button("Descargar CSV", res.to_csv(index=False), "cancelar.csv")
        else:
            st.warning("No hay órdenes que superen el umbral.")
