import streamlit as st
import random
import pandas as pd
import datetime
import os
import uuid
import time

# Intentamos importar autorefresh nativo
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# Configuración principal de la página
st.set_page_config(page_title="Gestión de Flujo de Pacientes", page_icon="🏥", layout="wide")

# ==========================================
# 0. AUTO-REFRESCO Y BASES DE DATOS
# ==========================================
if st_autorefresh:
    st_autorefresh(interval=60000, limit=None, key="data_refresh")
else:
    st.warning("⚠️ Instala la librería de autorefresco: `pip install streamlit-autorefresh` para actualizar en tiempo real.")

ARCHIVO_PACIENTES = "pacientes_flujo.csv"
ARCHIVO_BOXES = "estado_boxes.csv"
ARCHIVO_SOLICITUDES = "solicitudes.csv"
ARCHIVO_TIMELINE = "timeline_pacientes.csv"
ARCHIVO_PERSONAL = "personal_medico.csv"

def generar_id_caso():
    return f"P{random.randint(1000, 9999)}"

def inicializar_csv():
    if not os.path.exists(ARCHIVO_PACIENTES):
        df_vacio = pd.DataFrame(columns=["ID_Caso", "RUT", "Nombre", "Nivel_ESI", "Hora_Ingreso", "Hora_Alta", "Estado"])
        df_vacio.to_csv(ARCHIVO_PACIENTES, index=False)
    
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
        
    if not os.path.exists(ARCHIVO_SOLICITUDES):
        df_sol = pd.DataFrame(columns=["ID_Solicitud", "Box_Origen", "Tipo_Alerta", "Mensaje", "Estado", "Timestamp"])
        df_sol.to_csv(ARCHIVO_SOLICITUDES, index=False)
        
    if not os.path.exists(ARCHIVO_TIMELINE):
        df_tl = pd.DataFrame(columns=["ID_Caso", "Timestamp", "Responsable", "Tipo_Accion", "Descripcion"])
        df_tl.to_csv(ARCHIVO_TIMELINE, index=False)

    # NUEVO: Base de datos fija para personal médico
    if not os.path.exists(ARCHIVO_PERSONAL):
        df_personal = pd.DataFrame({
            "Nombre": ["Seleccione Profesional...", "Dr. House", "Dra. Grey", "Enf. Pérez", "Enf. Rojas", "Kine. Sánchez", "TENS. Muñoz"]
        })
        df_personal.to_csv(ARCHIVO_PERSONAL, index=False)

def cargar_pacientes(): return pd.read_csv(ARCHIVO_PACIENTES, dtype=str).fillna("")
def cargar_boxes(): return pd.read_csv(ARCHIVO_BOXES, dtype=str).fillna("")
def cargar_solicitudes(): return pd.read_csv(ARCHIVO_SOLICITUDES, dtype=str).fillna("")
def cargar_timeline(): return pd.read_csv(ARCHIVO_TIMELINE, dtype=str).fillna("")
def cargar_personal(): return pd.read_csv(ARCHIVO_PERSONAL, dtype=str).fillna("")

# Inicializamos para que el menú lateral pueda cargar la lista de médicos
inicializar_csv()

# ==========================================
# 1. AUTENTICACIÓN (SIDEBAR)
# ==========================================
st.sidebar.title("👨‍⚕️ Autenticación")

df_personal = cargar_personal()
lista_personal = df_personal["Nombre"].tolist()

# Al ser un selectbox vinculado a session_state mediante `key`, el valor sobrevive perfectamente
# a los refrescos de pantalla y es una base de datos inmutable para el usuario.
profesional_actual = st.sidebar.selectbox(
    "Profesional de Turno:", 
    lista_personal,
    key="in_profesional", 
    help="Elige tu nombre para firmar las acciones clínicas."
)

if profesional_actual == "Seleccione Profesional...":
    profesional_actual = "Sistema"


# ==========================================
# 2. LÓGICA DE NEGOCIO Y FUNCIONES
# ==========================================
def registrar_timeline(id_caso, responsable, tipo, descripcion):
    df = cargar_timeline()
    nueva_accion = {
        "ID_Caso": id_caso,
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Responsable": responsable,
        "Tipo_Accion": tipo,
        "Descripcion": descripcion
    }
    df = pd.concat([df, pd.DataFrame([nueva_accion])], ignore_index=True)
    df.to_csv(ARCHIVO_TIMELINE, index=False)

def guardar_nuevo_paciente(id_caso, rut, nombre, nivel, estado="En Espera", dest_box=""):
    df = cargar_pacientes()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_registro = {
        "ID_Caso": id_caso, "RUT": rut, "Nombre": nombre,
        "Nivel_ESI": nivel, "Hora_Ingreso": fecha_actual, "Hora_Alta": "", "Estado": estado
    }
    df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
    df.to_csv(ARCHIVO_PACIENTES, index=False)
    
    registrar_timeline(id_caso, profesional_actual, "Registro", f"Ingreso al sistema clasificado como {nivel}.")
    if estado == "En Espera":
        registrar_timeline(id_caso, profesional_actual, "Traslado", "Enviado a Sala de Espera.")
    elif estado == "En Box":
        registrar_timeline(id_caso, profesional_actual, "Traslado", f"Ingreso directo a {dest_box}.")

def actualizar_estado_paciente(id_caso, nuevo_estado, registrar_alta=False):
    df = cargar_pacientes()
    filtro = df["ID_Caso"] == id_caso
    if not df[filtro].empty:
        idx = df[filtro].index[0]
        df.at[idx, "Estado"] = nuevo_estado
        if registrar_alta:
            df.at[idx, "Hora_Alta"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.to_csv(ARCHIVO_PACIENTES, index=False)

def actualizar_estado_box(id_box, nuevo_estado, id_caso=""):
    df_b = cargar_boxes()
    idx = df_b[df_b["ID_Box"] == id_box].index[0]
    df_b.at[idx, "Estado"] = nuevo_estado
    df_b.at[idx, "ID_Caso"] = id_caso
    df_b.at[idx, "Hora_Ultimo_Cambio"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_b.to_csv(ARCHIVO_BOXES, index=False)

def crear_solicitud(box_origen, id_caso, tipo, mensaje):
    df = cargar_solicitudes()
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
    
    if id_caso:
        registrar_timeline(id_caso, profesional_actual, "Alerta", f"Solicitud de {tipo}: {mensaje}")

def atender_solicitud(id_solicitud):
    df = cargar_solicitudes()
    filtro = df["ID_Solicitud"] == id_solicitud
    if not df[filtro].empty:
        idx = df[filtro].index[0]
        df.at[idx, "Estado"] = "Atendido"
        df.to_csv(ARCHIVO_SOLICITUDES, index=False)

def color_filas(row):
    nivel = str(row['Nivel_ESI'])
    if '1' in nivel: return ['background-color: #ffcccc; color: black'] * len(row)
    elif '2' in nivel: return ['background-color: #ffe6cc; color: black'] * len(row)
    elif '3' in nivel: return ['background-color: #ffffcc; color: black'] * len(row)
    elif '4' in nivel: return ['background-color: #e6ffcc; color: black'] * len(row)
    else: return ['background-color: #cceeff; color: black'] * len(row)

# ==========================================
# 3. INTERFAZ PRINCIPAL
# ==========================================
st.title("🏥 Patient Flow & Bed Management")

# --- PANEL DE NOTIFICACIONES ---
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
            if tipo == "Médico": st.error("🔴 URGENTE: " + texto_alerta)
            elif tipo == "Limpieza": st.warning("🧹 " + texto_alerta)
            elif tipo == "Insumos": st.info("💊 " + texto_alerta)
            else: st.info("🧪 " + texto_alerta)
        with colB:
            if st.button("✅ Entendido", key=f"check_{row['ID_Solicitud']}"):
                atender_solicitud(row["ID_Solicitud"])
                st.rerun()
    st.markdown("---")

df = cargar_pacientes()
df_espera = df[df["Estado"] == "En Espera"]
df_altas = df[df["Estado"] == "Alta"]

df_boxes = cargar_boxes()
boxes_libres = df_boxes[df_boxes["Estado"] == "Libre"]["ID_Box"].tolist()

df_timeline_global = cargar_timeline()

col1, col2, col3 = st.columns(3)
with col1: st.metric("⏳ En Sala de Espera", len(df_espera))
with col2: st.metric("🛏️ Boxes Libres", len(boxes_libres))
with col3: st.metric("✅ Altas/Traslados Hoy", len(df_altas))
st.markdown("---")

tab_mapa, tab_ingreso, tab_espera, tab_altas = st.tabs([
    "🗺️ Mapa de Servicio",
    "➕ Registro Administrativo", 
    "📋 Lista de Espera", 
    "✅ Historial y Lead Time"
])

# ------------------------------------
# PESTAÑA 1: MAPA DE SERVICIO (BOXES)
# ------------------------------------
with tab_mapa:
    st.subheader("Mapa de Servicio en Tiempo Real")
    
    mapeo_colores = {
        "Libre": st.success,
        "Ocupado": st.error,
        "Se necesita limpieza": st.warning,
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
            caja_visual = mapeo_colores.get(estado_box, st.info)
            
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
                            minutos_estancia = int((ahora - hora_ingreso).total_seconds() / 60)
                            tiempo_texto = f"⏱️ {minutos_estancia} min"
                            if minutos_estancia > 60:
                                mensaje_alerta = f"⚠️ Box excedido ({minutos_estancia} min)"
                        except:
                            pass

                caja_visual(f"**{id_box}**\n\nEstado: {estado_box}\n\n{tiempo_texto}")
                if mensaje_alerta: st.error(mensaje_alerta)
                
                if estado_box == "Libre":
                    if st.button("Reservar", key=f"res_{idx}"):
                        actualizar_estado_box(id_box, "Reservado")
                        st.rerun()
                        
                elif estado_box == "Ocupado":
                    paciente_data = df[df["ID_Caso"] == id_paciente_en_box]
                    if not paciente_data.empty:
                        p_info = paciente_data.iloc[0]
                        st.write(f"🤕 **{p_info['Nombre'][:12]}...**")
                        
                        # --- MINI FICHA Y TIMELINE ---
                        with st.expander("Ver Ficha Clínica / Timeline"):
                            st.markdown(f"**ID:** {id_paciente_en_box} | **RUT:** {p_info['RUT']}")
                            st.markdown(f"**ESI:** {p_info['Nivel_ESI']} | **Ingreso:** {p_info['Hora_Ingreso'][11:16]}")
                            
                            st.markdown("---")
                            st.markdown("#### ⏳ Línea de Tiempo Cronológica")
                            
                            tl_paciente = df_timeline_global[df_timeline_global["ID_Caso"] == id_paciente_en_box]
                            if not tl_paciente.empty:
                                tl_paciente = tl_paciente.sort_values(by="Timestamp", ascending=False)
                                for _, tl_row in tl_paciente.iterrows():
                                    hora_corta = tl_row["Timestamp"][11:16]
                                    tipo_acc = tl_row["Tipo_Accion"]
                                    if tipo_acc == "Alerta": prefijo = "⚠️🔴"
                                    elif tipo_acc == "Indicación": prefijo = "💉🟢"
                                    elif tipo_acc == "Procedimiento": prefijo = "🛠️🔵"
                                    else: prefijo = "📋"
                                    
                                    st.markdown(f"**{hora_corta}** - {prefijo} {tl_row['Descripcion']}")
                                    st.caption(f"↳ *Resp: {tl_row['Responsable']}*")
                            else:
                                st.caption("No hay registros en el Timeline.")
                                
                            st.markdown("---")
                            st.markdown("📝 **Añadir Acción:**")
                            tipo_manual = st.selectbox("Categoría:", ["Indicación", "Procedimiento", "Evaluación Médica", "Nota Administrativa"], key=f"tm_{idx}")
                            desc_manual = st.text_input("Descripción breve:", key=f"dm_{idx}")
                            if st.button("Guardar en Timeline", key=f"btm_{idx}"):
                                registrar_timeline(id_paciente_en_box, profesional_actual, tipo_manual, desc_manual)
                                st.success("Guardado.")
                                st.rerun()
                                    
                    else:
                        st.write(f"🤕 **ID:** {id_paciente_en_box}")
                        
                    # --- MENÚ DE ENVÍO DE SOLICITUDES ---
                    with st.expander("📤 Solicitar Ayuda (Global)..."):
                        tipo_sol = st.selectbox("Tipo", ["Médico", "Limpieza", "Insumos", "Laboratorio"], key=f"tsol_{idx}")
                        msg_sol = st.text_input("Detalle", key=f"msol_{idx}")
                        if st.button("Enviar Alerta", key=f"bsen_{idx}"):
                            crear_solicitud(id_box, id_paciente_en_box, tipo_sol, msg_sol)
                            st.success("Enviada!")
                            st.rerun()
                            
                    if st.button("Alta/Traslado", key=f"alta_{idx}", type="primary"):
                        actualizar_estado_box(id_box, "Se necesita limpieza")
                        actualizar_estado_paciente(id_paciente_en_box, "Alta", registrar_alta=True)
                        registrar_timeline(id_paciente_en_box, profesional_actual, "Alta", f"Alta médica desde {id_box}.")
                        st.rerun()
                        
                elif estado_box == "Se necesita limpieza":
                    st.caption("🧹 Higiene requerida.")
                    if st.button("Box Listo", key=f"listo_{idx}"):
                        actualizar_estado_box(id_box, "Libre")
                        st.rerun()
                        
                elif estado_box == "Reservado":
                    st.caption("⏳ Esperando llegada de paciente.")
                    if st.button("Cancelar Reserva", key=f"canc_{idx}"):
                        actualizar_estado_box(id_box, "Libre")
                        st.rerun()

# ------------------------------------
# PESTAÑA 2: INGRESO DE PACIENTE
# ------------------------------------
with tab_ingreso:
    st.subheader("Registro Administrativo de Pacientes")
    st.info("La acción será firmada en la Línea de Tiempo bajo el nombre de: " + profesional_actual)
    
    with st.form("formulario_ingreso"):
        colA, colB = st.columns(2)
        with colA:
            nombre_manual = st.text_input("Nombre Completo:", key="in_nombre")
            rut_manual = st.text_input("RUT / Documento:", key="in_rut")
        with colB:
            nivel_manual = st.selectbox("Nivel ESI Asignado:", ["Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4", "Nivel 5"], key="in_esi")
            opciones_destino = ["Sala de Espera"] + boxes_libres
            destino_seleccionado = st.selectbox("Destino Inicial:", opciones_destino, key="in_dest")
            
        btn_registrar = st.form_submit_button("Registrar Ingreso en Sistema")
        
    if btn_registrar:
        if not nombre_manual or not rut_manual:
            st.error("Nombre y RUT son obligatorios.")
        else:
            id_paciente_manual = generar_id_caso()
            if destino_seleccionado == "Sala de Espera":
                guardar_nuevo_paciente(id_paciente_manual, rut_manual, nombre_manual, nivel_manual, estado="En Espera")
                st.success(f"✔️ {nombre_manual} registrado en Sala de Espera.")
                time.sleep(1) # Pausa dramática para que el usuario lea el éxito
                st.rerun()    # Forzamos recarga para que actualice la lista de espera instantáneamente
            else:
                guardar_nuevo_paciente(id_paciente_manual, rut_manual, nombre_manual, nivel_manual, estado="En Box", dest_box=destino_seleccionado)
                actualizar_estado_box(destino_seleccionado, "Ocupado", id_paciente_manual)
                st.success(f"✔️ {nombre_manual} asignado a {destino_seleccionado}.")
                time.sleep(1)
                st.rerun()

# ------------------------------------
# PESTAÑA 3: LISTA DE ESPERA
# ------------------------------------
with tab_espera:
    st.subheader("Pacientes en Espera de Box")
    if df_espera.empty:
        st.success("No hay pacientes esperando en este momento.")
    else:
        df_espera = df_espera.sort_values(by="Nivel_ESI", ascending=True)
        st.dataframe(df_espera.style.apply(color_filas, axis=1), use_container_width=True, hide_index=True)
        
        st.markdown("#### Asignar a Box")
        colA, colB = st.columns(2)
        with colA:
            opciones_paciente = {f"[{row['ID_Caso']}] {row['Nombre']} - {row['Nivel_ESI']}": row['ID_Caso'] for index, row in df_espera.iterrows()}
            paciente_a_llamar = st.selectbox("Seleccione al paciente:", list(opciones_paciente.keys()))
        with colB:
            if not boxes_libres:
                st.error("No hay boxes libres.")
            else:
                box_destino = st.selectbox("Asignar a:", boxes_libres)
                
        if st.button("Llamar y Asignar Box") and boxes_libres:
            id_caso_real = opciones_paciente[paciente_a_llamar]
            actualizar_estado_paciente(id_caso_real, "En Box")
            actualizar_estado_box(box_destino, "Ocupado", id_caso_real)
            registrar_timeline(id_caso_real, profesional_actual, "Traslado", f"Trasladado desde Sala de Espera hacia {box_destino}.")
            st.rerun()

# ------------------------------------
# PESTAÑA 4: HISTORIAL Y LEAD TIME
# ------------------------------------
with tab_altas:
    st.subheader("Altas, Traslados y Métricas de Tiempo (Lead Time)")
    if df_altas.empty:
        st.info("Aún no hay altas registradas en este turno.")
    else:
        df_altas_display = df_altas.copy()
        lead_times = []
        for _, row in df_altas_display.iterrows():
            if row["Hora_Alta"] and row["Hora_Ingreso"]:
                try:
                    ing = datetime.datetime.strptime(row["Hora_Ingreso"], "%Y-%m-%d %H:%M:%S")
                    alta = datetime.datetime.strptime(row["Hora_Alta"], "%Y-%m-%d %H:%M:%S")
                    minutos = int((alta - ing).total_seconds() / 60)
                    lead_times.append(f"{minutos} min")
                except:
                    lead_times.append("N/A")
            else:
                lead_times.append("N/A")
                
        df_altas_display["Lead_Time"] = lead_times
        df_altas_display = df_altas_display.sort_values(by="Hora_Alta", ascending=False)
        st.dataframe(df_altas_display.style.apply(color_filas, axis=1), use_container_width=True, hide_index=True)
