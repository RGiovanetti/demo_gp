import streamlit as st
import snowflake.connector
import pandas as pd
import os
import time
import matplotlib.pyplot as plt

# Título de la aplicación
st.title("👨‍💻Detección de Fraude GP")
st.markdown(
    """
    Demo de detección de fraude:
    
    Permite realizar un rápido análisis con filtros 
    """
)

# --- CONFIGURACIÓN DE CONEXIÓN A SNOWFLAKE ---
# Conexión directa con las credenciales proporcionadas.
# Se ha incluido el autenticador para el login por navegador.
try:
    conn = snowflake.connector.connect(
        user="REGIOVANETTI22",
        account="RYLKDTT-MI64246",
        authenticator="externalbrowser",
        role="ACCOUNTADMIN",
        warehouse="DEMO_WH", # Se usa el warehouse creado en el script SQL
        database="DEMO_FRAUDE_DB",
        schema="DEMO_FRAUDE_SCHEMA"
    )
    cursor = conn.cursor()
    st.success("Conexión a Snowflake exitosa.")
except Exception as e:
    st.error(f"Error al conectar a Snowflake: {e}")
    st.info("Asegúrate de que tus credenciales son correctas y de que tu navegador está listo para la autenticación.")
    st.stop()

# --- CARGAR Y CACHEAR DATOS ---
@st.cache_data(ttl=600)  # Cachea los datos por 10 minutos para evitar consultas repetidas
def load_data(filter_risk=None):
    # La consulta ahora incluye el nombre completo de la tabla (base_de_datos.esquema.tabla)
    query = "SELECT ID_TRANSACCION, FECHA_TRANSACCION, MONTO, TIPO_TARJETA, CIUDAD_TRANSACCION, RIESGO_FRAUDE, COMENTARIO FROM DEMO_FRAUDE_DB.DEMO_FRAUDE_SCHEMA.TRANSACCIONES"
    if filter_risk:
        if filter_risk == "Vacío":
            query += " WHERE RIESGO_FRAUDE IS NULL"
        else:
            query += f" WHERE RIESGO_FRAUDE = '{filter_risk}'"

    cursor.execute(query)
    df = cursor.fetch_pandas_all()
    # Ordenar los datos por ID de transacción
    df.sort_values(by="ID_TRANSACCION", inplace=True)
    return df

# --- INTERFAZ DE USUARIO ---
# Filtros para la visualización de datos
st.subheader("Visualización de Transacciones")
risk_options = ["Todos", "ALTO", "MEDIO", "BAJO", "Vacío"]
selected_risk = st.selectbox(
    "Filtrar por nivel de riesgo:",
    options=risk_options
)

# Cargar los datos filtrados
if selected_risk == "Todos":
    df_transactions = load_data()
else:
    df_transactions = load_data(selected_risk)

st.dataframe(df_transactions, use_container_width=True)

# --- VISUALIZACIÓN DE GRÁFICOS ---
st.subheader("Análisis de Transacciones")

if not df_transactions.empty:
    # --- Grafico 1: Distribucion por Tipo de Tarjeta (Gráfico de Pastel) ---
    st.markdown("### Distribución de Transacciones por Tipo de Tarjeta")
    card_counts = df_transactions['TIPO_TARJETA'].value_counts()
    fig_card, ax_card = plt.subplots()
    ax_card.pie(
        card_counts,
        labels=card_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.4) # Para hacer un gráfico de dona
    )
    ax_card.axis('equal') # Asegura que el círculo sea un círculo
    st.pyplot(fig_card)

    # --- Grafico 2: Distribucion por Ciudad (Gráfico de Pastel) ---
    st.markdown("### Distribución de Transacciones por Ciudad")
    city_counts = df_transactions['CIUDAD_TRANSACCION'].value_counts()
    fig_city, ax_city = plt.subplots()
    ax_city.pie(
        city_counts,
        labels=city_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.4)
    )
    ax_city.axis('equal')
    st.pyplot(fig_city)

    # --- Grafico 3: Distribucion por Nivel de Riesgo (Gráfico de Pastel) ---
    st.markdown("### Distribución de Transacciones por Nivel de Riesgo")
    # Rellenar nulos para el gráfico
    risk_counts = df_transactions['RIESGO_FRAUDE'].fillna('Sin Riesgo').value_counts()
    fig_risk, ax_risk = plt.subplots()
    ax_risk.pie(
        risk_counts,
        labels=risk_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.4)
    )
    ax_risk.axis('equal')
    st.pyplot(fig_risk)

    # --- Grafico 4: Transacciones por Rango Horario (Gráfico de Barras) ---
    st.markdown("### Distribución de Transacciones por Rango Horario")
    df_transactions['HORA'] = pd.to_datetime(df_transactions['FECHA_TRANSACCION']).dt.hour
    
    def get_hour_range(hour):
        if 0 <= hour < 6:
            return '00:00 - 06:00'
        elif 6 <= hour < 12:
            return '06:00 - 12:00'
        elif 12 <= hour < 18:
            return '12:00 - 18:00'
        else:
            return '18:00 - 24:00'

    df_transactions['RANGO_HORARIO'] = df_transactions['HORA'].apply(get_hour_range)
    
    hour_counts = df_transactions['RANGO_HORARIO'].value_counts(normalize=True).reset_index()
    hour_counts.columns = ['Rango Horario', 'Porcentaje']
    hour_counts['Porcentaje'] = (hour_counts['Porcentaje'] * 100).round(2)
    
    fig_hour, ax_hour = plt.subplots()
    ax_hour.bar(hour_counts['Rango Horario'], hour_counts['Porcentaje'])
    ax_hour.set_ylabel('Porcentaje (%)')
    ax_hour.set_xlabel('Rango Horario')
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig_hour)

else:
    st.info("No hay transacciones para mostrar. Intenta seleccionar un filtro diferente.")


# --- ACTUALIZAR RIESGO DE FRAUDE ---
st.subheader("Actualizar Nivel de Riesgo")
st.markdown("Usa este panel para marcar transacciones con un riesgo de fraude específico.")

# Selectores para la actualización
# Asegurarse de que el DataFrame no esté vacío antes de intentar acceder a 'ID_TRANSACCION'
if not df_transactions.empty:
    transaction_id_list = df_transactions['ID_TRANSACCION'].tolist()
    transaction_to_update = st.selectbox(
        "Selecciona el ID de la transacción a actualizar:",
        options=transaction_id_list
    )

    new_risk = st.radio(
        "Selecciona el nuevo nivel de riesgo:",
        options=["ALTO", "MEDIO", "BAJO", "Vacío"]
    )

    comment_text = st.text_area(
        "Añade un comentario (opcional):",
        placeholder="Ej: Sospecha de compra inusual en el extranjero."
    )

    if st.button("Actualizar Transacción"):
        try:
            # Lógica para construir la consulta de actualización
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
            cursor.execute(update_query)
            conn.commit()

            st.success(f"Transacción '{transaction_to_update}' actualizada exitosamente en la base de datos.")

            # Invalida la caché para recargar los datos
            st.cache_data.clear()

            # Pequeña pausa para que el usuario vea el mensaje de éxito
            time.sleep(1)

            # Recarga la página para mostrar los datos actualizados
            st.experimental_rerun()

        except Exception as e:
            st.error(f"Error al actualizar la transacción: {e}")
else:
    st.info("No hay transacciones para mostrar, por lo que no se pueden seleccionar IDs para actualizar.")

# Cerrar la conexión
cursor.close()
conn.close()
