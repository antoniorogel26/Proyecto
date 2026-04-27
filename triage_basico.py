# Definición de la función principal de triage
def evaluar_triage(fiebre, dificultad_respiratoria, dolor_de_pecho, tiempo_con_sintomas):
    # La función evalúa la gravedad de los síntomas y retorna un nivel de prioridad
    # Nivel 1: Emergencia (Riesgo de muerte inminente)
    # Nivel 2: Muy Urgente
    # Nivel 3: Urgente
    # Nivel 4: Menos Urgente
    # Nivel 5: No Urgente
    
    # Verificamos primero los síntomas más críticos (Nivel 1)
    if dificultad_respiratoria == "severa" or dolor_de_pecho == "severo":
        # Si hay dificultad respiratoria o dolor de pecho severo, es Nivel 1
        return "Nivel 1 - Emergencia: Requiere atención médica inmediata."
        
    # Si no es Nivel 1, verificamos condiciones de Nivel 2
    elif fiebre > 39.5 or dificultad_respiratoria == "moderada" or dolor_de_pecho == "moderado":
        # Fiebre muy alta o síntomas moderados en respiración/pecho indican Nivel 2
        return "Nivel 2 - Muy Urgente: Acuda a urgencias pronto, atención en menos de 15 minutos."
        
    # Si no es Nivel 1 ni 2, evaluamos para Nivel 3
    elif fiebre > 38.5 or tiempo_con_sintomas > 7:
        # Fiebre moderada o síntomas persistentes por más de una semana indican Nivel 3
        return "Nivel 3 - Urgente: Necesita evaluación médica, atención en menos de 60 minutos."
        
    # Si no cumple lo anterior, verificamos Nivel 4
    elif fiebre > 37.5 or tiempo_con_sintomas > 3:
        # Fiebre leve o síntomas de varios días indican Nivel 4
        return "Nivel 4 - Menos Urgente: Requiere evaluación, puede esperar hasta 2 horas."
        
    # Si no tiene ningún síntoma de gravedad o no cumple los criterios anteriores, es Nivel 5
    else:
        # Para síntomas leves y recientes, Nivel 5
        return "Nivel 5 - No Urgente: Puede ser atendido en consulta externa o esperar hasta 4 horas."

# Imprimimos el Disclaimer médico obligatorio
print("\n" + "="*50)
print("DISCLAIMER MÉDICO OBLIGATORIO")
print("="*50)
print("Esta aplicación de auto-triage es únicamente con fines informativos y educativos.")
print("NO constituye un diagnóstico médico, ni reemplaza el consejo, diagnóstico")
print("o tratamiento de un profesional de la salud calificado.")
print("Si usted cree que tiene una emergencia médica, llame a los servicios")
print("de emergencia de su localidad inmediatamente.")
print("="*50 + "\n")

# A continuación, unos ejemplos de uso de la función (para que puedas probar el script)
# Usamos 'if __name__ == "__main__":' para que este código de prueba SOLO se ejecute 
# cuando corremos este archivo directamente, y NO cuando lo importamos desde nuestra app de Streamlit.
if __name__ == "__main__":
    print("Ejemplo de evaluación 1 (Paciente con fiebre muy alta):")
    # Llamamos a la función con parámetros de ejemplo y guardamos el resultado
    resultado_1 = evaluar_triage(fiebre=39.8, dificultad_respiratoria="leve", dolor_de_pecho="leve", tiempo_con_sintomas=2)
    # Imprimimos el resultado
    print(resultado_1)

    print("\nEjemplo de evaluación 2 (Paciente sin síntomas graves):")
    # Llamamos a la función con otros parámetros
    resultado_2 = evaluar_triage(fiebre=36.5, dificultad_respiratoria="ninguna", dolor_de_pecho="ninguno", tiempo_con_sintomas=1)
    # Imprimimos el resultado
    print(resultado_2)
