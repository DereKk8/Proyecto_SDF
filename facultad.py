"""
facultad.py - Servidor de Facultad Simplificado

Este módulo implementa un servidor intermediario que:
1. Recibe solicitudes de asignación de aulas de los programas académicos
2. Valida que la facultad solicitante exista
3. Reenvía las solicitudes válidas al servidor DTI
4. Retorna las respuestas del DTI a los programas

Uso básico:
    python facultad.py 1  # Inicia el primer servidor de facultad
    python facultad.py 2  # Inicia el segundo servidor de facultad

Archivos necesarios:
    - config.py: Contiene las URLs y configuraciones
    - facultades.txt: Lista de facultades y sus programas

"""

import zmq      # Para comunicación entre procesos
import json     # Para serialización de mensajes
import sys      # Para argumentos de línea de comandos
from config import FACULTAD_1_URL, FACULTAD_2_URL, FACULTADES_FILE, DTI_URL

def leer_facultades():
    """
    Lee el archivo de facultades y crea un diccionario de facultades y sus programas.

    Formato del archivo facultades.txt:
        Facultad1, Programa1, Programa2, Programa3
        Facultad2, Programa1, Programa2

    Returns:
        dict: Diccionario con facultades como claves y lista de programas como valores
        Ejemplo:
        {
            "Facultad de Ingeniería": ["Sistemas", "Civil", "Electrónica"],
            "Facultad de Medicina": ["Medicina", "Enfermería"]
        }
    """
    try:
        with open(FACULTADES_FILE, "r", encoding="utf-8") as archivo:
            facultades = {}
            for linea in archivo:
                partes = linea.strip().split(", ")
                if len(partes) >= 2:
                    facultades[partes[0]] = partes[1:]
            return facultades
    except Exception as e:
        print(f"Error al leer facultades: {e}")
        return {}

def enviar_a_dti(solicitud):
    """
    Envía una solicitud al servidor DTI y espera su respuesta.

    Args:
        solicitud (dict): Diccionario con los datos de la solicitud
            Ejemplo:
            {
                "facultad": "Facultad de Ingeniería",
                "programa": "Sistemas",
                "salones": 2,
                "laboratorios": 1,
                "semestre": 1
            }

    Returns:
        dict: Respuesta del servidor DTI o mensaje de error
            Éxito ejemplo:
            {
                "salones_asignados": ["S001", "S002"],
                "laboratorios_asignados": ["L001"]
            }
            Error ejemplo:
            {
                "error": "Mensaje de error"
            }
    """
    contexto = zmq.Context()
    socket = contexto.socket(zmq.REQ)
    socket.connect(DTI_URL)
    
    try:
        socket.send_string(json.dumps(solicitud))
        return json.loads(socket.recv_string())
    except Exception as e:
        return {"error": f"Error de comunicación con DTI: {e}"}
    finally:
        socket.close()
        contexto.term()

def iniciar_servidor(url_servidor):
    """
    Inicia el servidor de facultad y procesa solicitudes en un bucle infinito.

    Args:
        url_servidor (str): URL donde escuchará el servidor (ej: "tcp://127.0.0.1:5555")

    Flujo de operación:
        1. Carga la lista de facultades válidas
        2. Configura el socket ZMQ en modo REP (reply)
        3. Espera y procesa solicitudes en bucle:
            - Recibe solicitud JSON
            - Valida que la facultad exista
            - Reenvía solicitud válida al DTI
            - Retorna respuesta al programa solicitante

    Manejo de errores:
        - Validación de formato JSON
        - Verificación de facultad existente
        - Errores de comunicación con DTI
        - Errores inesperados
    """
    # Cargar datos de facultades
    facultades = leer_facultades()
    if not facultades:
        print("⚠️ Advertencia: No hay facultades configuradas")
    
    # Configurar socket
    contexto = zmq.Context()
    socket = contexto.socket(zmq.REP)
    
    try:
        socket.bind(url_servidor)
        print(f"✅ Servidor de facultad iniciado en {url_servidor}")
        
        # Bucle principal
        while True:
            try:
                # Recibir solicitud
                solicitud = json.loads(socket.recv_string())
                print(f"\nSolicitud recibida: {solicitud}")
                
                # Validar facultad
                if solicitud.get("facultad") not in facultades:
                    respuesta = {"error": "Facultad no válida"}
                else:
                    # Reenviar a DTI
                    respuesta = enviar_a_dti(solicitud)
                
                # Enviar respuesta
                socket.send_string(json.dumps(respuesta))
                print(f"Respuesta enviada: {respuesta}")
                
            except json.JSONDecodeError:
                socket.send_string(json.dumps({"error": "Formato de solicitud inválido"}))
            except Exception as e:
                socket.send_string(json.dumps({"error": f"Error: {str(e)}"}))
                
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        socket.close()
        contexto.term()

if __name__ == "__main__":
    """
    Punto de entrada del script.
    
    Valida los argumentos de línea de comandos y inicia el servidor
    correspondiente según el número proporcionado (1 o 2).
    
    Uso:
        python facultad.py 1  # Inicia el primer servidor
        python facultad.py 2  # Inicia el segundo servidor
    """
    # Validar argumentos
    if len(sys.argv) != 2 or sys.argv[1] not in ["1", "2"]:
        print("Uso: python facultad.py <1|2>")
        sys.exit(1)
    
    # Seleccionar URL según el número de servidor
    url = FACULTAD_1_URL if sys.argv[1] == "1" else FACULTAD_2_URL
    
    # Iniciar servidor
    iniciar_servidor(url)