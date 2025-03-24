import zmq
import json
import sys
from config import ZMQ_FACULTAD_1, ZMQ_FACULTAD_2, FACULTADES_FILE

def cargar_facultades():
    """Carga las facultades y programas académicos desde el archivo de texto."""
    facultades = {}
    with open(FACULTADES_FILE, "r", encoding="utf-8") as file:
        for line in file:
            data = line.strip().split(", ")
            facultad = data[0]
            programas = data[1:]
            facultades[facultad] = programas
    return facultades

def procesar_solicitud(solicitud, facultades):
    """Simula la asignación de aulas en función de la disponibilidad y valida la facultad."""
    facultad = solicitud["facultad"]
    
    if facultad not in facultades:
        return {"error": f"La facultad '{facultad}' no existe en el sistema"}

    max_salones = 10
    max_laboratorios = 4

    salones_asignados = min(solicitud["salones"], max_salones)
    laboratorios_asignados = min(solicitud["laboratorios"], max_laboratorios)

    return {
        "facultad": facultad,
        "programa": solicitud["programa"],
        "semestre": solicitud["semestre"],
        "salones_asignados": salones_asignados,
        "laboratorios_asignados": laboratorios_asignados
    }

def main(endpoint):
    facultades = cargar_facultades()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(endpoint)
    
    print(f"[Facultad] Servidor iniciado en {endpoint}. Esperando solicitudes...")

    while True:
        mensaje = socket.recv_string()
        solicitud = json.loads(mensaje)
        
        print(f"[Facultad] Solicitud recibida: {solicitud}")

        respuesta = procesar_solicitud(solicitud, facultades)

        socket.send_string(json.dumps(respuesta))
        print(f"[Facultad] Respuesta enviada: {respuesta}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 facultad.py <1|2>")
        sys.exit(1)

    facultad_id = sys.argv[1]
    endpoint = ZMQ_FACULTAD_1 if facultad_id == "1" else ZMQ_FACULTAD_2
    main(endpoint)