import zmq
import json
import sys
import os
from config import FACULTAD_1_URL, FACULTAD_2_URL, FACULTADES_FILE, DTI_URL
from datetime import datetime

def cargar_facultades():
    """Carga las facultades y programas académicos desde el archivo de texto con validación."""
    facultades = {}
    if not os.path.exists(FACULTADES_FILE):
        print(f"\n❌ Error: No se encontró el archivo '{FACULTADES_FILE}'. El servidor continuará sin datos.")
        return facultades

    try:
        with open(FACULTADES_FILE, "r", encoding="utf-8") as file:
            for line in file:
                data = line.strip().split(", ")
                if len(data) < 2:
                    print(f"\n⚠️ Advertencia: Línea mal formada en '{FACULTADES_FILE}': {line.strip()}")
                    continue
                facultad = data[0]
                programas = data[1:]
                facultades[facultad] = programas
    except Exception as e:
        print(f"\n❌ Error al leer el archivo '{FACULTADES_FILE}': {e}")

    return facultades

def procesar_solicitud(solicitud, facultades):
    """Procesa la solicitud y la reenvía al DTI."""
    try:
        if not isinstance(solicitud, dict):
            return {"error": "Solicitud malformada"}

        # Validar que la facultad existe
        facultad = solicitud.get("facultad")
        if facultad not in facultades:
            return {"error": f"La facultad '{facultad}' no existe"}

        # Preparar solicitud para DTI
        solicitud_dti = {
            "tipo_solicitud": "ASIGNACION",
            **solicitud,
            "fecha_solicitud": datetime.now().isoformat()
        }

        # Enviar al DTI y esperar respuesta
        contexto = zmq.Context()
        socket_dti = contexto.socket(zmq.REQ)
        socket_dti.connect(DTI_URL)
        
        try:
            socket_dti.send_string(json.dumps(solicitud_dti))
            respuesta = socket_dti.recv_string()
            return json.loads(respuesta)
        except Exception as e:
            return {"error": f"Error en comunicación con DTI: {str(e)}"}
        finally:
            socket_dti.close()
            contexto.term()

    except Exception as e:
        return {"error": f"Error en procesamiento: {str(e)}"}

def main(endpoint):
    facultades = cargar_facultades()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    try:
        socket.bind(endpoint)
    except zmq.ZMQError as e:
        print(f"\n❌ Error: No se pudo iniciar el servidor en {endpoint}. Detalles: {e}")
        return
    
    print(f"\n✅ [Facultad] Servidor iniciado en {endpoint}. Esperando solicitudes...")

    while True:
        try:
            mensaje = socket.recv_string()
            solicitud = json.loads(mensaje)

            print("\n" + "=" * 50)
            print(f"[Facultad] Solicitud recibida:")
            print(json.dumps(solicitud, indent=2))
            print("=" * 50)

            respuesta = procesar_solicitud(solicitud, facultades)
            socket.send_string(json.dumps(respuesta))

            print("\n" + "#" * 50)
            print(f"[Facultad] Respuesta enviada:")
            print(json.dumps(respuesta, indent=2))
            print("#" * 50)

        except json.JSONDecodeError:
            print("\n❌ Error: Se recibió una solicitud con formato incorrecto.")
            socket.send_string(json.dumps({"error": "Solicitud en formato incorrecto."}))
        except zmq.ZMQError:
            print("\n❌ Error en la comunicación con el cliente.")
        except Exception as e:
            print(f"\n❌ Error inesperado en el servidor: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 facultad.py <1|2>")
        sys.exit(1)

    facultad_id = sys.argv[1]
    endpoint = FACULTAD_1_URL if facultad_id == "1" else FACULTAD_2_URL
    main(endpoint)