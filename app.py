import streamlit as st
import random
import pandas as pd
import qrcode
from io import BytesIO
import datetime
import os
from triage_basico import evaluar_triage

# st.set_page_config: Configura la pestaña del navegador.
st.set_page_config(page_title="Sistema Integral de Triage", page_icon="🏥", layout="wide")

ARCHIVO_CSV = "historial_triage.csv"

# ==========================================
# 1. FUNCIONES DE BASE DE DATOS
# ==========================================
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        df_vacio = pd.DataFrame(columns=["Fecha", "Usuario", "Nivel_ESI", "Tiempo_Espera", "Estado"])
        df_vacio.to_csv(ARCHIVO_CSV, index=False)

def cargar_datos():
    return pd.read_csv(ARCHIVO_CSV)

def guardar_nuevo_paciente(usuario, nivel, tiempo, estado="Auto-Triage"):
    """
    Guarda un paciente nuevo. Hemos añadido el parámetro 'estado' con un valor por defecto.
    Si se omite, será 'Auto-Triage' (pacientes desde su app), pero el médico puede pasar 'Atendido'.
    """
    df = cargar_datos()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_registro = {
        "Fecha": fecha_actual,
        "Usuario": usuario,
        "Nivel_ESI": nivel,
        "Tiempo_Espera": tiempo,
        "Estado": estado # Usamos la variable para permitir flexibilidad
    }
    df_nuevo = pd.DataFrame([nuevo_registro])
    df = pd.concat([df, df_nuevo], ignore_index=True)
    df.to_csv(ARCHIVO_CSV, index=False)

def actualizar_estado(index):
    df = cargar_datos()
    df.at[index, "Estado"] = "Atendido"
    df.to_csv(ARCHIVO_CSV, index=False)

# ==========================================
# 2. FUNCIONES LÓGICAS COMPARTIDAS
# ==========================================
# Hemos extraído la lógica de cálculo de tiempo a una función para no escribirla dos veces.
def calcular_tiempo_estimado(resultado_nivel):
    if "Nivel 1" in resultado_nivel: tiempo_base = 0
    elif "Nivel 2" in resultado_nivel: tiempo_base = 15
    elif "Nivel 3" in resultado_nivel: tiempo_base = 60
    elif "Nivel 4" in resultado_nivel: tiempo_base = 120
    else: tiempo_base = 240
        
    carga_actual = random.uniform(0.8, 2.0)
    tiempo_estimado = int(tiempo_base * carga_actual)
    return tiempo_estimado, tiempo_base, carga_actual

# Extraemos la lógica de adaptación del formulario a la función original
def procesar_datos_y_evaluar(fiebre, dif_respirar, dolor_pecho, nivel_dolor, dias):
    """
    Esta función es el 'puente' que permite reutilizar evaluar_triage().
    Tanto la Vista Paciente como la Vista Médica usan botones Sí/No y sliders.
    Esta función los convierte en "severa", "moderada", etc., y llama a evaluar_triage().
    """
    respiracion = "severa" if dif_respirar == "Sí" else "ninguna"
    if dolor_pecho:
        if nivel_dolor >= 8: pecho = "severo"
        elif nivel_dolor >= 5: pecho = "moderado"
        else: pecho = "leve"
    else:
        pecho = "ninguno"
        
    # Reutilización clave: llamamos a la misma función importada de triage_basico.py
    return evaluar_triage(
        fiebre=fiebre,
        dificultad_respiratoria=respiracion,
        dolor_de_pecho=pecho,
        tiempo_con_sintomas=dias
    )


# ==========================================
# 3. COMPONENTES DE VISTA (REFACTORIZACIÓN)
# ==========================================
def mostrar_vista_paciente():
    st.title("🏥 Asistente Virtual de Triage")
    st.info("Por favor, responda las siguientes preguntas con honestidad.")

    with st.form("formulario_triage"):
        nombre_paciente = st.text_input("Su nombre completo (o DNI):")
        sintoma_principal = st.selectbox("¿Cuál es su síntoma principal?", ["Fiebre", "Tos", "Dolor de cabeza", "Dolor abdominal", "Otro"])
        fiebre_input = st.number_input("Temperatura actual (°C)", min_value=35.0, max_value=42.0, value=37.0, step=0.1)
        tiempo_sintomas = st.number_input("¿Cuántos días lleva con los síntomas?", min_value=0, max_value=30, value=1)
        
        st.markdown("#### Síntomas de Alarma")
        dificultad_respirar = st.radio("¿Tiene dificultad para respirar?", ["No", "Sí"])
        tiene_dolor_pecho = st.checkbox("¿Siente dolor en el pecho?")
        nivel_dolor = st.slider("Indique su nivel de dolor general", min_value=1, max_value=10, value=1)
        
        btn_calcular = st.form_submit_button("Generar Auto-Triage")

    if btn_calcular:
        if not nombre_paciente:
            st.error("Ingrese su nombre para generar su registro.")
        else:
            # Reutilizamos nuestra función puente
            resultado = procesar_datos_y_evaluar(fiebre_input, dificultad_respirar, tiene_dolor_pecho, nivel_dolor, tiempo_sintomas)
            nivel_corto = resultado.split(":")[0]
            
            # Reutilizamos el cálculo de tiempo
            tiempo_estimado, tiempo_base, carga = calcular_tiempo_estimado(resultado)
            
            # Guardamos por defecto como "Auto-Triage"
            guardar_nuevo_paciente(nombre_paciente, nivel_corto, tiempo_estimado)
            
            st.markdown("---")
            st.subheader("Resultado de la Evaluación:")
            if "Nivel 1" in resultado or "Nivel 2" in resultado: st.error(resultado)
            elif "Nivel 3" in resultado: st.warning(resultado)
            else: st.success(resultado)
                
            if tiempo_base > 0:
                st.metric(label="Tiempo Estimado de Espera", value=f"{tiempo_estimado} min")
            else:
                st.metric(label="Tiempo Estimado de Espera", value="Inmediato")
            
            st.markdown("### 📱 Tu Código QR de Pre-Ingreso")
            qr_data = f"Paciente: {nombre_paciente}\nPrioridad: {nivel_corto}\nMinutos Espera: {tiempo_estimado}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1E1E1E", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            st.image(buf, width=250)

def mostrar_vista_medica():
    st.title("🩺 Panel de Control Médico")
    
    df = cargar_datos()
    df_espera = df[df["Estado"] == "Auto-Triage"]
    df_atendidos = df[df["Estado"] == "Atendido"]
    
    col1, col2 = st.columns(2)
    with col1: st.metric(label="✅ Pacientes Atendidos", value=len(df_atendidos))
    with col2: st.metric(label="⏳ En Sala de Espera", value=len(df_espera))
    st.markdown("---")
    
    # st.tabs nos permite crear navegación por pestañas dentro de la misma página
    tab_espera, tab_manual = st.tabs(["📋 Pacientes en Espera", "➕ Nuevo Triage Manual"])
    
    # --- PESTAÑA 1: LISTA DE ESPERA ---
    with tab_espera:
        st.subheader("Validar Sala de Espera (Pre-Triage)")
        if df_espera.empty:
            st.success("No hay pacientes esperando de la app móvil.")
        else:
            st.dataframe(df_espera, use_container_width=True, hide_index=True)
            st.markdown("#### Validar Signos Vitales y Atender")
            opciones = {f"{row['Usuario']} - {row['Nivel_ESI']}": index for index, row in df_espera.iterrows()}
            paciente_seleccionado = st.selectbox("Seleccione al paciente:", list(opciones.keys()))
            indice_real = opciones[paciente_seleccionado]
            nivel_original_str = df.at[indice_real, "Nivel_ESI"]
            nivel_original_num = int(nivel_original_str[6])
            
            with st.form("form_signos_vitales"):
                colA, colB, colC = st.columns(3)
                with colA: sistolica = st.number_input("Presión Sistólica", 0, 300, 120)
                with colB: spo2 = st.number_input("Saturación O2", 0, 100, 98)
                with colC: hr = st.number_input("Frec. Cardíaca", 0, 300, 75)
                btn_validar = st.form_submit_button("Validar Signos y Marcar como 'Atendido'")
                
            if btn_validar:
                if spo2 < 90 or sistolica > 200 or sistolica < 80 or hr > 130 or hr < 40: nuevo_nivel = 1
                elif spo2 < 94 or sistolica > 160 or sistolica < 90 or hr > 110 or hr < 50: nuevo_nivel = 2
                else: nuevo_nivel = 3
                    
                if nuevo_nivel < nivel_original_num:
                    st.error(f"🚨 PRIORIDAD AJUSTADA. Nivel {nivel_original_num} ➡️ Nivel {nuevo_nivel}.")
                    df_temp = cargar_datos()
                    df_temp.at[indice_real, "Nivel_ESI"] = f"Nivel {nuevo_nivel} - Ajustado"
                    df_temp.to_csv(ARCHIVO_CSV, index=False)
                
                actualizar_estado(indice_real)
                st.rerun()

    # --- PESTAÑA 2: TRIAGE MANUAL ---
    with tab_manual:
        st.subheader("Ingreso Manual por Personal Médico")
        st.info("Utilice este formulario para pacientes que llegan directo a ventanilla sin usar la App móvil.")
        
        with st.form("form_triage_manual"):
            nombre_manual = st.text_input("Nombre del Paciente:")
            
            # Mismas preguntas que el paciente, para poder reutilizar evaluar_triage
            st.markdown("**1. Cuestionario de Síntomas:**")
            colX, colY = st.columns(2)
            with colX:
                sintoma = st.selectbox("Síntoma principal", ["Fiebre", "Tos", "Dolor", "Herida", "Otro"])
                fiebre_m = st.number_input("Temperatura (°C)", 35.0, 42.0, 37.0)
                dias_m = st.number_input("Días con síntomas", 0, 30, 1)
            with colY:
                dif_res_m = st.radio("Dificultad respiratoria", ["No", "Sí"])
                dolor_p_m = st.checkbox("Dolor en el pecho")
                nivel_d_m = st.slider("Nivel de dolor (1-10)", 1, 10, 1)
                
            st.markdown("**2. Signos Vitales Medidos:**")
            colA2, colB2, colC2 = st.columns(3)
            with colA2: sis_m = st.number_input("Sistólica", 0, 300, 120, key="s2")
            with colB2: spo2_m = st.number_input("Saturación O2", 0, 100, 98, key="o2")
            with colC2: hr_m = st.number_input("Frec. Cardíaca", 0, 300, 75, key="h2")
            
            btn_manual = st.form_submit_button("Registrar, Evaluar y Enviar a Box")
            
        if btn_manual:
            if not nombre_manual:
                st.error("Ingrese el nombre del paciente.")
            else:
                # 1. Obtenemos nivel base por cuestionario (Reutilizando código!)
                res_cuestionario = procesar_datos_y_evaluar(fiebre_m, dif_res_m, dolor_p_m, nivel_d_m, dias_m)
                nivel_cuestionario = int(res_cuestionario.split(":")[0][6])
                
                # 2. Obtenemos nivel por signos vitales
                if spo2_m < 90 or sis_m > 200 or sis_m < 80 or hr_m > 130 or hr_m < 40: nivel_signos = 1
                elif spo2_m < 94 or sis_m > 160 or sis_m < 90 or hr_m > 110 or hr_m < 50: nivel_signos = 2
                else: nivel_signos = 3
                
                # 3. Nos quedamos con el nivel MÁS GRAVE (el número más bajo)
                nivel_final = min(nivel_cuestionario, nivel_signos)
                etiqueta_nivel = f"Nivel {nivel_final} - Triage Presencial"
                
                # 4. Guardamos DIRECTO como 'Atendido'
                guardar_nuevo_paciente(nombre_manual, etiqueta_nivel, "0 (Ya en centro)", estado="Atendido")
                st.success(f"Paciente {nombre_manual} ingresado exitosamente como {etiqueta_nivel}.")
                st.rerun()

    st.markdown("---")
    st.subheader("Historial de Pacientes Atendidos")
    if not df_atendidos.empty:
        st.dataframe(df_atendidos, use_container_width=True, hide_index=True)


# ==========================================
# 4. ENRUTADOR PRINCIPAL (START)
# ==========================================
inicializar_csv()

st.sidebar.title("🏥 Menú del Hospital")
perfil = st.sidebar.radio("Seleccione su perfil de usuario:", ["Paciente", "Personal Médico"])

if perfil == "Paciente":
    mostrar_vista_paciente()
elif perfil == "Personal Médico":
    mostrar_vista_medica()
