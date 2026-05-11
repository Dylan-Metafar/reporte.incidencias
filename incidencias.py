import pandas as pd
import streamlit as st

def identificar_cancelaciones(df_vtex, df_skus_error, umbral_pct):
    # 1. Limpieza de nombres de columnas (minúsculas y sin espacios)
    df_vtex.columns = [str(c).strip().lower() for c in df_vtex.columns]
    df_skus_error.columns = [str(c).strip().lower() for c in df_skus_error.columns]

    # 2. Definición de nombres esperados
    col_orden = 'order'
    col_sku = 'id_sku'

    # Validación de existencia
    if col_orden not in df_vtex.columns or col_sku not in df_vtex.columns:
        st.error(f"El Excel de pedidos debe tener columnas llamadas '{col_orden}' y '{col_sku}'. Detecté: {df_vtex.columns.tolist()}")
        st.stop()
    
    if col_sku not in df_skus_error.columns:
        st.error(f"El Excel de errores debe tener una columna llamada '{col_sku}'. Detecté: {df_skus_error.columns.tolist()}")
        st.stop()

    # 3. Limpieza de datos (Evita que el SKU 1234 sea distinto a '1234')
    def limpiar_serie(serie):
        return serie.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    df_vtex[col_orden] = limpiar_serie(df_vtex[col_orden])
    df_vtex[col_sku] = limpiar_serie(df_vtex[col_sku])
    df_skus_error[col_sku] = limpiar_serie(df_skus_error[col_sku])

    # 4. Cruce
    set_errores = set(df_skus_error[col_sku])
    df_vtex['es_error'] = df_vtex[col_sku].apply(lambda x: x in set_errores)

    # 5. Agrupación
    resumen = df_vtex.groupby(col_orden).agg(
        total_items=(col_sku, 'count'),
        items_con_error=('es_error', 'sum')
    ).reset_index()

    # 6. Cálculo de porcentaje y filtro
    resumen['porcentaje_error'] = (resumen['items_con_error'] / resumen['total_items']) * 100
    resultado = resumen[resumen['porcentaje_error'] >= umbral_pct].copy()
    
    # 7. Formato
    resultado['porcentaje_error'] = resultado['porcentaje_error'].round(2).astype(str) + '%'
    
    return resultado.sort_values(by='total_items', ascending=False)

# --- INTERFAZ ---
st.title("🛡️ Validador de Órdenes (Excel Edition)")

password = st.text_input("Contraseña", type="password")
if password != "Metafar2026!":
    st.stop()

st.sidebar.header("Configuración")
umbral = st.sidebar.slider("Umbral de error (%)", 0, 100, 50)

col1, col2 = st.columns(2)
with col1:
    f1 = st.file_uploader("Excel de Pedidos (order, id_sku)", type=["xlsx"])
with col2:
    f2 = st.file_uploader("Excel de Errores (id_sku)", type=["xlsx"])

if f1 and f2:
    # Leer Excel
    df1 = pd.read_excel(f1)
    df2 = pd.read_excel(f2)

    if st.button("Procesar"):
        res = identificar_cancelaciones(df1, df2, umbral)
        if not res.empty:
            st.success(f"¡Listo! Se encontraron {len(res)} órdenes.")
            st.dataframe(res, use_container_width=True)
            
            # Exportar a CSV (o podrías exportar a Excel también)
            csv = res.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar reporte", csv, "ordenes_a_cancelar.csv", "text/csv")
        else:
            st.warning("No hay órdenes que superen el umbral.")
