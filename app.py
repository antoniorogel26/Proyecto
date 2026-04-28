import streamlit as st
import random
import pandas as pd
import datetime
import os
import uuid
from triage_basico import evaluar_triage

# Intentamos importar autorefresh nativo. Si no está, no crasheamos, pero avisamos.
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# Configuración principal de la página
st.set_page_config(page_title="Gestión de Triage Médico", page_icon="🩺", layout="wide")

# ==========================================
# 0. AUTO-REFRESCO SUAVE (MANTIENE SESSION STATE)
# ==========================================
if st_autorefresh:
    # Recarga suave cada 60000ms (1 min). No rompe el session_state de los formularios.
    st_autorefresh(interval=60000, limit=None, key="data_refresh")
else:
    st.warning("⚠️ Instala la librería de autorefresco ejecutando en tu terminal: `pip install streamlit-autorefresh` para actualizar en tiempo real sin borrar formularios.")


ARCHIVO_CSV = "historial_triage.csv"
ARCHIVO_BOXES = "estado_boxes.csv"
ARCHIVO_SOLICITUDES = "solicitudes.csv"

# ==========================================
# 1. UTILIDADES Y BASE DE DATOS
# ==========================================
def generar_id_caso():
    return f"P{random.randint(1000, 9999)}"

def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        df_vacio = pd.DataFrame(columns=["ID_Caso", "Fecha", "Usuario", "Nivel_ESI", "Tiempo_Espera", "Estado"])
        df_vacio.to_csv(ARCHIVO_CSV, index=False)
    
    if not os.path.exists(ARCHIVO_BOXES):
        boxes_data = []
        for i in range(1, 11):
            boxes_data.append({
                "ID_Box": f"Box {i}",
                "Estado": "Libre",
                "ID_Caso": "",
                "Hora_Ultimo_Cambio": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        df_boxes = pd.DataFrame(boxes_data)
        df_boxes.to_csv(ARCHIVO_BOXES, index=False)
        
    # Inicialización de Solicitudes
    if not os.path.exists(ARCHIVO_SOLICITUDES):
        df_sol = pd.DataFrame(columns=["ID_Solicitud", "Box_Origen", "Tipo_Alerta", "Mensaje", "Estado", "Timestamp"])
        df_sol.to_csv(ARCHIVO_SOLICITUDES, index=False)

def cargar_datos(): return pd.read_csv(ARCHIVO_CSV, dtype=str).fillna("")
def cargar_boxes(): return pd.read_csv(ARCHIVO_BOXES, dtype=str).fillna("")
def cargar_solicitudes(): return pd.read_csv(ARCHIVO_SOLICITUDES, dtype=str).fillna("")

def guardar_nuevo_paciente(id_caso, usuario, nivel, tiempo, estado="En Espera"):
    df = cargar_datos()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_registro = {
        "ID_Caso": id_caso, "Fecha": fecha_actual, "Usuario": usuario,
        "Nivel_ESI": nivel, "Tiempo_Espera": tiempo, "Estado": estado
    }
    df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
    df.to_csv(ARCHIVO_CSV, index=False)

def actualizar_estado_paciente(id_caso, nuevo_estado):
    df = cargar_datos()
    filtro = df["ID_Caso"] == id_caso
    if not df[filtro].empty:
        idx = df[filtro].index[0]
        df.at[idx, "Estado"] = nuevo_estado
        df.to_csv(ARCHIVO_CSV, index=False)

def actualizar_estado_box(id_box, nuevo_estado, id_caso=""):
    df_b = cargar_boxes()
    idx = df_b[df_b["ID_Box"] == id_box].index[0]
    df_b.at[idx, "Estado"] = nuevo_estado
    df_b.at[idx, "ID_Caso"] = id_caso
    df_b.at[idx, "Hora_Ultimo_Cambio"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_b.to_csv(ARCHIVO_BOXES, index=False)

def crear_solicitud(box_origen, tipo, mensaje):
    df = cargar_solicitudes()
    # Usamos uuid para crear un ID único para la alerta
    nueva_solicitud = {
        "ID_Solicitud": str(uuid.uuid4())[:8],
        "Box_Origen": box_origen,
        "Tipo_Alerta": tipo,
        "Mensaje": mensaje,
        "Estado": "Pendiente",
        "Timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    }
    df = pd.concat([df, pd.DataFrame([nueva_solicitud])], ignore_index=True)
    df.to_csv(ARCHIVO_SOLICITUDES, index=False)

def atender_solicitud(id_solicitud):
    df = cargar_solicitudes()
    filtro = df["ID_Solicitud"] == id_solicitud
    if not df[filtro].empty:
        idx = df[filtro].index[0]
        df.at[idx, "Estado"] = "Atendido"
        df.to_csv(ARCHIVO_SOLICITUDES, index=False)

# ==========================================
# 2. LÓGICA DE NEGOCIO
# ==========================================
def procesar_datos_y_evaluar(fiebre, dif_respirar, dolor_pecho, nivel_dolor, dias):
    respiracion = "severa" if dif_respirar == "Sí" else "ninguna"
    if dolor_pecho:
        if nivel_dolor >= 8: pecho = "severo"
        elif nivel_dolor >= 5: pecho = "moderado"
        else: pecho = "leve"
    else:
        pecho = "ninguno"
    return evaluar_triage(fiebre, respiracion, pecho, dias)

def color_filas_triage(row):
    nivel = str(row['Nivel_ESI'])
    if 'Nivel 1' in nivel: return ['background-color: #ffcccc; color: black'] * len(row)
    elif 'Nivel 2' in nivel: return ['background-color: #ffe6cc; color: black'] * len(row)
    elif 'Nivel 3' in nivel: return ['background-color: #ffffcc; color: black'] * len(row)
    elif 'Nivel 4' in nivel: return ['background-color: #e6ffcc; color: black'] * len(row)
    else: return ['background-color: #cceeff; color: black'] * len(row)


# ==========================================
# 3. INTERFAZ MÉDICA PRINCIPAL
# ==========================================
inicializar_csv()

st.title("🩺 Panel de Gestión de Triage y Boxes")

# --- PANEL DE NOTIFICACIONES GLOBALES ---
df_sol = cargar_solicitudes()
pendientes = df_sol[df_sol["Estado"] == "Pendiente"]

if not pendientes.empty:
    st.markdown("### 🔔 Alertas Activas")
    for idx, row in pendientes.iterrows():
        tipo = row["Tipo_Alerta"]
        box = row["Box_Origen"]
        msg = row["Mensaje"]
        hora = row["Timestamp"]
        
        texto_alerta = f"**{box} solicita {tipo}**: {msg} *(Hora: {hora})*"
        colA, colB = st.columns([5, 1])
        
        with colA:
            # Color coding basado en el tipo de alerta
            if tipo == "Médico": st.error("🔴 URGENTE: " + texto_alerta)
            elif tipo == "Limpieza": st.warning("🧹 " + texto_alerta)
            elif tipo == "Insumos": st.info("💊 " + texto_alerta)
            else: st.info("🧪 " + texto_alerta)
            
        with colB:
            # Botón de check
            if st.button("✅ Entendido", key=f"check_{row['ID_Solicitud']}"):
                atender_solicitud(row["ID_Solicitud"])
                st.rerun()
    st.markdown("---")

# --- CARGA DE DATOS PRINCIPALES ---
df = cargar_datos()
df_espera = df[df["Estado"] == "En Espera"]
df_atendidos = df[df["Estado"] == "Atendido"]

df_boxes = cargar_boxes()
boxes_libres = df_boxes[df_boxes["Estado"] == "Libre"]["ID_Box"].tolist()

col1, col2, col3 = st.columns(3)
with col1: st.metric("⏳ En Sala de Espera", len(df_espera))
with col2: st.metric("🛏️ Boxes Libres", len(boxes_libres))
with col3: st.metric("✅ Atendidos Hoy", len(df_atendidos))
st.markdown("---")

tab_ingreso, tab_espera, tab_mapa, tab_historial = st.tabs([
    "➕ Ingreso de Paciente", 
    "📋 Lista de Espera", 
    "🗺️ Mapa de Servicio",
    "✅ Historial Atendidos"
])

# ------------------------------------
# PESTAÑA 1: INGRESO DE PACIENTE
# ------------------------------------
with tab_ingreso:
    st.subheader("Nuevo Ingreso a Triage")
    st.info("Complete el formulario. La clasificación ESI se calculará al finalizar.")
    
    # [EDUCATIVO - st.session_state]
    # Al agregar el parámetro `key="lo_que_sea"`, Streamlit vincula
    # este campo visual con su memoria interna de sesión. 
    # Así, si ocurre un auto-refresco, la caja de texto pregunta a la memoria:
    # "¿Tenía algún texto antes del refresco?" y lo recupera mágicamente.
    with st.form("formulario_ingreso"):
        nombre_manual = st.text_input("Nombre del Paciente:", key="in_nombre")
        
        st.markdown("**1. Cuestionario de Síntomas:**")
        colX, colY = st.columns(2)
        with colX:
            sintoma = st.selectbox("Síntoma principal", ["Fiebre", "Tos", "Dolor", "Herida", "Otro"], key="in_sintoma")
            fiebre_m = st.number_input("Temperatura (°C)", 35.0, 42.0, 37.0, key="in_fiebre")
            dias_m = st.number_input("Días con síntomas", 0, 30, 1, key="in_dias")
        with colY:
            dif_res_m = st.radio("Dificultad respiratoria", ["No", "Sí"], key="in_dif")
            dolor_p_m = st.checkbox("Dolor en el pecho", key="in_dolor")
            nivel_d_m = st.slider("Nivel de dolor (1-10)", 1, 10, 1, key="in_nivel")
            
        st.markdown("**2. Signos Vitales Medidos:**")
        colA2, colB2, colC2 = st.columns(3)
        with colA2: sis_m = st.number_input("Sistólica", 0, 300, 120, key="in_sis")
        with colB2: spo2_m = st.number_input("Saturación O2", 0, 100, 98, key="in_spo2")
        with colC2: hr_m = st.number_input("Frec. Cardíaca", 0, 300, 75, key="in_hr")
        
        st.markdown("**3. Destino Inmediato:**")
        opciones_destino = ["Sala de Espera"] + boxes_libres
        destino_seleccionado = st.selectbox("Seleccione destino:", opciones_destino, key="in_dest")
        
        btn_registrar = st.form_submit_button("Finalizar Ingreso y Clasificar")
        
    if btn_registrar:
        if not nombre_manual:
            st.error("Ingrese el nombre del paciente.")
        else:
            res_cuestionario = procesar_datos_y_evaluar(fiebre_m, dif_res_m, dolor_p_m, nivel_d_m, dias_m)
            nivel_cuestionario = int(res_cuestionario.split(":")[0][6])
            
            if spo2_m < 90 or sis_m > 200 or sis_m < 80 or hr_m > 130 or hr_m < 40: nivel_signos = 1
            elif spo2_m < 94 or sis_m > 160 or sis_m < 90 or hr_m > 110 or hr_m < 50: nivel_signos = 2
            else: nivel_signos = 3
            
            nivel_final = min(nivel_cuestionario, nivel_signos)
            etiqueta_nivel = f"Nivel {nivel_final} - Triage de Ingreso"
            
            id_paciente_manual = generar_id_caso()
            
            st.markdown("---")
            st.subheader("Resultado de la Evaluación:")
            
            if nivel_final == 1 or nivel_final == 2: st.error(f"🚨 {etiqueta_nivel}")
            elif nivel_final == 3: st.warning(f"⚠️ {etiqueta_nivel}")
            else: st.success(f"✅ {etiqueta_nivel}")
            
            if destino_seleccionado == "Sala de Espera":
                guardar_nuevo_paciente(id_paciente_manual, nombre_manual, etiqueta_nivel, "0", estado="En Espera")
                st.success(f"✔️ Paciente {nombre_manual} enviado a Sala de Espera con ID {id_paciente_manual}.")
            else:
                guardar_nuevo_paciente(id_paciente_manual, nombre_manual, etiqueta_nivel, "0", estado="En Box")
                actualizar_estado_box(destino_seleccionado, "Ocupado", id_paciente_manual)
                st.success(f"✔️ Paciente {nombre_manual} enviado directo a {destino_seleccionado} con ID {id_paciente_manual}.")

# ------------------------------------
# PESTAÑA 2: LISTA DE ESPERA
# ------------------------------------
with tab_espera:
    st.subheader("Sala de Espera Activa")
    
    if df_espera.empty:
        st.success("No hay pacientes esperando en este momento.")
    else:
        df_espera = df_espera.sort_values(by="Nivel_ESI", ascending=True)
        st.dataframe(df_espera.style.apply(color_filas_triage, axis=1), use_container_width=True, hide_index=True)
        
        st.markdown("#### Llamar Paciente a Box")
        colA, colB = st.columns(2)
        with colA:
            opciones_paciente = {f"[{row['ID_Caso']}] {row['Usuario']} - {row['Nivel_ESI']}": row['ID_Caso'] for index, row in df_espera.iterrows()}
            paciente_a_llamar = st.selectbox("Seleccione al paciente:", list(opciones_paciente.keys()))
        with colB:
            if not boxes_libres:
                st.error("No hay boxes libres. No puede llamar pacientes.")
            else:
                box_destino = st.selectbox("Asignar a:", boxes_libres)
                
        if st.button("Asignar Box y Mover Paciente") and boxes_libres:
            id_caso_real = opciones_paciente[paciente_a_llamar]
            actualizar_estado_paciente(id_caso_real, "En Box")
            actualizar_estado_box(box_destino, "Ocupado", id_caso_real)
            st.rerun()

# ------------------------------------
# PESTAÑA 3: MAPA DE SERVICIO (BOXES)
# ------------------------------------
with tab_mapa:
    st.subheader("🗺️ Estado de Infraestructura")
    
    mapeo_colores = {
        "Libre": st.success,
        "Ocupado": st.error,
        "En Limpieza": st.warning,
        "Reservado": st.info
    }
    
    filas = [st.columns(5), st.columns(5)]
    
    for idx, row in df_boxes.iterrows():
        if idx < 5: columna_actual = filas[0][idx]
        else: columna_actual = filas[1][idx - 5]
            
        with columna_actual:
            estado_box = row["Estado"]
            id_box = row["ID_Box"]
            id_paciente_en_box = row["ID_Caso"]
            caja_visual = mapeo_colores[estado_box]
            
            with st.container():
                mensaje_alerta = ""
                tiempo_texto = ""
                minutos_estancia = 0
                
                if estado_box == "Ocupado":
                    hora_str = str(row["Hora_Ultimo_Cambio"])
                    if hora_str and hora_str != "nan":
                        try:
                            hora_ingreso = datetime.datetime.strptime(hora_str, "%Y-%m-%d %H:%M:%S")
                            ahora = datetime.datetime.now()
                            diferencia_segundos = (ahora - hora_ingreso).total_seconds()
                            minutos_estancia = int(diferencia_segundos / 60)
                            tiempo_texto = f"⏱️ {minutos_estancia} min"
                            
                            if minutos_estancia > 60:
                                mensaje_alerta = f"⚠️ ALERTA: Box excedido ({minutos_estancia} min)"
                        except:
                            pass

                caja_visual(f"**{id_box}**\n\nEstado: {estado_box}\n\n{tiempo_texto}")
                
                if mensaje_alerta:
                    st.error(mensaje_alerta)
                
                if estado_box == "Libre":
                    if st.button("Reservar (Vacío)", key=f"res_{idx}"):
                        actualizar_estado_box(id_box, "Reservado")
                        st.rerun()
                        
                elif estado_box == "Ocupado":
                    paciente_data = df[df["ID_Caso"] == id_paciente_en_box]
                    if not paciente_data.empty:
                        nivel = paciente_data.iloc[0]["Nivel_ESI"]
                        st.write(f"🤒 **ID:** {id_paciente_en_box}")
                        st.caption(nivel)
                    else:
                        st.write(f"🤒 **ID:** {id_paciente_en_box}")
                        
                    # --- MENÚ DE ENVÍO DE SOLICITUDES ---
                    with st.expander("📤 Enviar Solicitud"):
                        tipo_sol = st.selectbox("Tipo", ["Médico", "Limpieza", "Insumos", "Laboratorio"], key=f"tsol_{idx}")
                        msg_sol = st.text_input("Detalle", key=f"msol_{idx}")
                        if st.button("Enviar", key=f"bsen_{idx}"):
                            crear_solicitud(id_box, tipo_sol, msg_sol)
                            st.success("Enviada!")
                            st.rerun()
                            
                    if st.button("Dar de Alta", key=f"alta_{idx}"):
                        actualizar_estado_box(id_box, "En Limpieza")
                        actualizar_estado_paciente(id_paciente_en_box, "Atendido")
                        st.rerun()
                        
                elif estado_box == "En Limpieza":
                    st.caption("🧹 Personal de higiene en proceso.")
                    if st.button("Box Listo", key=f"listo_{idx}"):
                        actualizar_estado_box(id_box, "Libre")
                        st.rerun()
                        
                elif estado_box == "Reservado":
                    st.caption("⏳ Esperando llegada de paciente.")
                    if st.button("Cancelar Reserva", key=f"canc_{idx}"):
                        actualizar_estado_box(id_box, "Libre")
                        st.rerun()

# ------------------------------------
# PESTAÑA 4: HISTORIAL DE ATENDIDOS
# ------------------------------------
with tab_historial:
    st.subheader("Bitácora de Pacientes Atendidos")
    if df_atendidos.empty:
        st.info("Aún no se han dado altas en este turno.")
    else:
        df_atendidos = df_atendidos.sort_values(by="Fecha", ascending=False)
        st.dataframe(df_atendidos.style.apply(color_filas_triage, axis=1), use_container_width=True, hide_index=True)
