# =============================================================================
# Configuración del Sistema de Asignación de Aulas
# =============================================================================

# IP y puerto del Servidor DTI (Central)
DTI_IP = "127.0.0.1"
DTI_PUERTO = "5570"
DTI_URL = f"tcp://{DTI_IP}:{DTI_PUERTO}"

# Servidores de Facultad
FACULTAD_1_URL = "tcp://127.0.0.1:5555"
FACULTAD_2_URL = "tcp://127.0.0.1:5558"

# Lista de URLs de facultades
FACULTAD_SERVERS = [FACULTAD_1_URL, FACULTAD_2_URL]

# Archivos del sistema
FACULTADES_FILE = "facultades.txt"
AULAS_REGISTRO_FILE = "aulas_registro.txt"
ASIGNACIONES_LOG_FILE = "asignaciones_log.txt"