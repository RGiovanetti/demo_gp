import streamlit as st
import pandas as pd
import time
import matplotlib.pyplot as plt

# --------------------------------------------------------
# ESTILO GLOBAL
# --------------------------------------------------------
st.set_page_config(page_title="Fraude GP", page_icon="🕵️", layout="wide")

# Fondo y estilo custom (CSS)
st.markdown("""
    <style>
    body {
        background-color: #0077B6; /* El azul para el fondo */
    }
    .main {
        background-color: #FFFFFF;
        padding: 2rem;
        border-radius: 10px;
    }
    h1 {
        color: #8A2BE2; /* Violeta para el título principal */
    }
    h2, h3, h4, h5, h6 {
        color: #00A591; /* Verde para los subtítulos */
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------
# TÍTULO DE LA APLICACIÓN
# --------------------------------------------------------
st.title("👨‍💻 Detección de Fraude GLOBAL PROCESSING")
st.markdown(
    """
    **Demo de detección de fraude**

    Permite realizar un análisis rápido con filtros y visualizaciones.
    """
)

# --------------------------------------------------------
# CONEXIÓN A SNOWFLAKE
# --------------------------------------------------------
try:
    cnx = st.connection("snowflake")
    session = cnx.session()
    st.success("Conexión a Snowflake exitosa ✅")
except Exception as e:
    st.error(f"Error al conectar a Snowflake: {e}")
    st.stop()

# --------------------------------------------------------
# FUNCIÓN PARA CARGAR DATOS
# --------------------------------------------------------
@st.cache_data(ttl=600)
def load_data(filter_risk=None):
    query = """
        SELECT ID_TRANSACCION, FECHA_TRANSACCION, MONTO, 
               TIPO_TARJETA, CIUDAD_TRANSACCION, 
               RIESGO_FRAUDE, COMENTARIO
        FROM DEMO_FRAUDE_DB.DEMO_FRAUDE_SCHEMA.TRANSACCIONES
    """
    if filter_risk:
        if filter_risk == "Vacío":
            query += " WHERE RIESGO_FRAUDE IS NULL"
        elif filter_risk != "Todos":
            query += f" WHERE RIESGO_FRAUDE = '{filter_risk}'"

    df = session.sql(query).to_pandas()
    df.sort_values(by="ID_TRANSACCION", inplace=True)
    return df

# --------------------------------------------------------
# INTERFAZ DE FILTRO
# --------------------------------------------------------
st.subheader("📊 Visualización de Transacciones")
risk_options = ["Todos", "ALTO", "MEDIO", "BAJO", "Vacío"]
selected_risk = st.selectbox("Filtrar por nivel de riesgo:", options=risk_options)

df_transactions = load_data(selected_risk)
st.dataframe(df_transactions, use_container_width=True)

# --------------------------------------------------------
# VISUALIZACIÓN DE GRÁFICOS
# --------------------------------------------------------
st.subheader("📈 Análisis Visual de Transacciones")

if not df_transactions.empty:
    # Paleta de colores vibrante
    colors = ["#00B4D8", "#48CAE4", "#90E0EF", "#00A591", "#1B6535", "#8A2BE2"]

    # --- Gráfico 1, 2, 3 y 4 en 4 columnas ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("#### Tipo de Tarjeta")
        card_counts = df_transactions['TIPO_TARJETA'].value_counts()
        fig_card, ax_card = plt.subplots(figsize=(2, 2))
        ax_card.pie(card_counts, labels=card_counts.index, autopct='%1.1f%%',
                    startangle=90, wedgeprops=dict(width=0.4),
                    colors=colors[:len(card_counts)],
                    textprops={'fontsize': 8}) # Ajuste de fuente para las etiquetas
        ax_card.axis('equal')
        st.pyplot(fig_card)

    with col2:
        st.markdown("#### Distribución por Ciudad")
        city_counts = df_transactions['CIUDAD_TRANSACCION'].value_counts()
        fig_city, ax_city = plt.subplots(figsize=(2, 2))
        ax_city.pie(city_counts, labels=city_counts.index, autopct='%1.1f%%',
                    startangle=90, wedgeprops=dict(width=0.4),
                    colors=colors[:len(city_counts)],
                    textprops={'fontsize': 8}) # Ajuste de fuente para las etiquetas
        ax_city.axis('equal')
        st.pyplot(fig_city)

    with col3:
        st.markdown("#### Nivel de Riesgo")
        risk_counts = df_transactions['RIESGO_FRAUDE'].fillna('Sin Riesgo').value_counts()
        fig_risk, ax_risk = plt.subplots(figsize=(3, 2))
        ax_risk.bar(risk_counts.index, risk_counts.values, color=colors[0])
        ax_risk.set_ylabel("Cantidad", fontsize=8)
        ax_risk.set_xlabel("Nivel de Riesgo", fontsize=8)
        ax_risk.tick_params(axis='both', which='major', labelsize=8)
        st.pyplot(fig_risk)

    with col4:
        st.markdown("#### Rango Horario")
        df_transactions['HORA'] = pd.to_datetime(df_transactions['FECHA_TRANSACCION']).dt.hour

        def get_hour_range(hour):
            if 0 <= hour < 6: return '00:00 - 06:00'
            elif 6 <= hour < 12: return '06:00 - 12:00'
            elif 12 <= hour < 18: return '12:00 - 18:00'
            else: return '18:00 - 24:00'

        df_transactions['RANGO_HORARIO'] = df_transactions['HORA'].apply(get_hour_range)
        hour_counts = df_transactions['RANGO_HORARIO'].value_counts(normalize=True).reset_index()
        hour_counts.columns = ['Rango Horario', 'Porcentaje']
        hour_counts['Porcentaje'] = (hour_counts['Porcentaje'] * 100).round(2)

        fig_hour, ax_hour = plt.subplots(figsize=(3, 2))
        ax_hour.bar(hour_counts['Rango Horario'], hour_counts['Porcentaje'], color=colors[1])
        ax_hour.set_ylabel('Porcentaje (%)', fontsize=8)
        ax_hour.set_xlabel('Rango Horario', fontsize=8)
        plt.xticks(rotation=45, ha='right', fontsize=8)
        ax_hour.tick_params(axis='both', which='major', labelsize=8)
        st.pyplot(fig_hour)

else:
    st.info("No hay transacciones para mostrar. Intenta seleccionar un filtro diferente.")

# --------------------------------------------------------
# ACTUALIZAR RIESGO DE FRAUDE
# --------------------------------------------------------
st.subheader("✏️ Actualizar Nivel de Riesgo")

if not df_transactions.empty:
    transaction_id_list = df_transactions['ID_TRANSACCION'].tolist()
    transaction_to_update = st.selectbox("Selecciona el ID de la transacción:", options=transaction_id_list)

    new_risk = st.radio("Nuevo nivel de riesgo:", options=["ALTO", "MEDIO", "BAJO", "Vacío"])
    comment_text = st.text_area("Comentario (opcional):", placeholder="Ej: Sospecha de compra inusual en el extranjero.")

    if st.button("Actualizar Transacción"):
        try:
            if new_risk == "Vacío":
                risk_value = "NULL"
            else:
                risk_value = f"'{new_risk}'"

            update_query = f"""
                UPDATE DEMO_FRAUDE_DB.DEMO_FRAUDE_SCHEMA.TRANSACCIONES
                SET RIESGO_FRAUDE = {risk_value},
                COMENTARIO = '{comment_text.replace("'", "''")}'
                WHERE ID_TRANSACCION = '{transaction_to_update}'
            """
            session.sql(update_query).collect()
            st.success(f"Transacción '{transaction_to_update}' actualizada exitosamente ✅")

            st.cache_data.clear()
            time.sleep(1)
            st.experimental_rerun()

        except Exception as e:
            st.error(f"Error al actualizar la transacción: {e}")
