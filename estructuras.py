# Estructura de solicitud del Programa Académico a Facultad
SOLICITUD_PROGRAMA = {
    "facultad": str,          # Nombre de la facultad
    "programa": str,          # Nombre del programa
    "semestre": int,          # Número de semestre
    "salones": int,          # Cantidad de salones requeridos
    "laboratorios": int,     # Cantidad de laboratorios requeridos
    "capacidad_min": int     # Capacidad mínima requerida por aula
}

# Estructura de solicitud de Facultad a DTI
SOLICITUD_FACULTAD = {
    "tipo_solicitud": "ASIGNACION",  # Tipo de operación
    "facultad": str,          # Nombre de la facultad
    "programa": str,          # Nombre del programa
    "semestre": int,          # Número de semestre
    "salones": int,          # Cantidad de salones requeridos
    "laboratorios": int,     # Cantidad de laboratorios requeridos
    "capacidad_min": int,    # Capacidad mínima requerida
    "fecha_solicitud": str   # Timestamp de la solicitud
}

# Estructura de respuesta del DTI
RESPUESTA_DTI = {
    "estado": str,           # "exitoso" o "error"
    "facultad": str,         # Facultad solicitante
    "programa": str,         # Programa solicitante
    "semestre": int,         # Semestre
    "salones_asignados": [   # Lista de salones asignados
        {
            "id": str,
            "tipo": str,
            "capacidad": int
        }
    ],
    "laboratorios_asignados": [  # Lista de laboratorios asignados
        {
            "id": str,
            "tipo": str,
            "capacidad": int
        }
    ],
    "notificacion": str,     # Mensajes adicionales (ej: aulas móviles)
    "error": str             # Mensaje de error (si aplica)
} 