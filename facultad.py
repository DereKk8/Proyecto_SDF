import zmq
import json
import sys
from config import ZMQ_FACULTAD_1, ZMQ_FACULTAD_2

def procesar_solicitud(solicitud):
    """Simula la asignación de aulas en función de la disponibilidad."""
    max_salones = 10
    max_laboratorios = 4

    salones_asignados = min(solicitud["salones"], max_salones)
    laboratorios_asignados = min(solicitud["laboratorios"], max_laboratorios)

    return {
        "programa": solicitud["programa"],
        "semestre": solicitud["semestre"],
        "salones_asignados": salones_asignados,
        "laboratorios_asignados": laboratorios_asignados
    }

def main(endpoint):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(endpoint)
    
    print(f"[Facultad] Servidor iniciado en {endpoint}. Esperando solicitudes...")

    while True:
        # Recibir solicitud de un programa académico
        mensaje = socket.recv_string()
        solicitud = json.loads(mensaje)
        
        print(f"[Facultad] Solicitud recibida: {solicitud}")

        # Procesar la solicitud y asignar aulas
        respuesta = procesar_solicitud(solicitud)
        
        # Enviar la respuesta al programa académico
        socket.send_string(json.dumps(respuesta))
        print(f"[Facultad] Respuesta enviada: {respuesta}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 facultad.py <1|2>")
        sys.exit(1)

    facultad_id = sys.argv[1]
    endpoint = ZMQ_FACULTAD_1 if facultad_id == "1" else ZMQ_FACULTAD_2
    main(endpoint)