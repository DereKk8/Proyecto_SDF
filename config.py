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

# Load Balancer Broker URLs
BROKER_IP = "127.0.0.1"
BROKER_FRONTEND_PORT = "5571"  # Port for clients (facultad)
BROKER_BACKEND_PORT = "5572"   # Port for workers (DTI)
BROKER_FRONTEND_URL = f"tcp://{BROKER_IP}:{BROKER_FRONTEND_PORT}"
BROKER_BACKEND_URL = f"tcp://{BROKER_IP}:{BROKER_BACKEND_PORT}"

# Puertos para el sistema de tolerancia a fallos
HEARTBEAT_PORT = "5573"  # Puerto para heartbeat
SYNC_PORT = "5574"       # Puerto para sincronización
HEARTBEAT_URL = f"tcp://{BROKER_IP}:{HEARTBEAT_PORT}"
SYNC_URL = f"tcp://{BROKER_IP}:{SYNC_PORT}"

# Archivos del sistema
FACULTADES_FILE = "facultades.txt"
AULAS_REGISTRO_FILE = "aulas_registro.txt"
ASIGNACIONES_LOG_FILE = "asignaciones_log.txt"
RESPALDO_ESTADO_ARCHIVO = "estado_respaldo.txt"