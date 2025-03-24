import zmq
import json
import random
import time
from config import FACULTAD_SERVERS, FACULTADES_FILE

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

def main():
    # Cargar las facultades y programas académicos
    facultades = cargar_facultades()
    
    # Seleccionar aleatoriamente una facultad y un programa académico
    facultad = random.choice(list(facultades.keys()))
    programa = random.choice(facultades[facultad])

    context = zmq.Context()
    
    # Alternar entre servidores de facultad
    server_index = random.randint(0, 1)
    socket = context.socket(zmq.REQ)
    socket.connect(FACULTAD_SERVERS[server_index])

    # Generar una solicitud aleatoria
    solicitud = {
        "facultad": facultad,
        "programa": programa,
        "semestre": random.randint(1, 10),
        "salones": random.randint(7, 10),
        "laboratorios": random.randint(2, 4)
    }

    print(f"[Programa Académico] Enviando solicitud a {FACULTAD_SERVERS[server_index]}: {solicitud}")

    # Enviar solicitud a la facultad
    socket.send_string(json.dumps(solicitud))

    # Esperar respuesta de la facultad
    respuesta = socket.recv_string()
    asignacion = json.loads(respuesta)

    print(f"[Programa Académico] Respuesta recibida: {asignacion}")

if __name__ == "__main__":
    main()