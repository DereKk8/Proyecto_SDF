import zmq
import json
import random
import time
from config import FACULTAD_SERVERS

def main():
    context = zmq.Context()
    
    # Alternar entre servidores de facultad
    server_index = random.randint(0, 1)  # Elegimos aleatoriamente un servidor
    socket = context.socket(zmq.REQ)
    socket.connect(FACULTAD_SERVERS[server_index])

    # Generar una solicitud aleatoria
    solicitud = {
        "programa": "Ingeniería de Sistemas",
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