"""
facultad.py - Cliente en el Sistema de Load Balancing Broker

Este módulo implementa un cliente en el patrón Load Balancing Broker que:
1. Recibe solicitudes de asignación de aulas de los programas académicos
2. Valida que la facultad solicitante exista
3. Reenvía las solicitudes válidas al broker
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
import uuid     # Para generar ID único de cliente
import time     # Para pausas y timeouts
from config import FACULTAD_1_URL, FACULTAD_2_URL, FACULTADES_FILE, BROKER_FRONTEND_URL
from monitor_metricas import obtener_monitor
from monitor_metricas_programa import obtener_monitor_programa

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

def enviar_a_broker(solicitud, client_id):
    """
    Envía una solicitud al broker y espera su respuesta.

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
        client_id (bytes): ID único del cliente para identificación

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
    # Obtener monitor de métricas
    monitor = obtener_monitor()
    tiempo_inicio_comunicacion = time.time()
    
    contexto = zmq.Context()
    socket = contexto.socket(zmq.DEALER)
    
    # Configurar identidad del cliente para el broker
    socket.setsockopt(zmq.IDENTITY, client_id)
    socket.connect(BROKER_FRONTEND_URL)
    
    # Configurar timeouts para evitar bloqueos
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 segundos de timeout para recepción
    socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 segundos de timeout para envío
    
    try:
        # Añadir distancia a la solicitud para simular carga
        solicitud['distance'] = sum(ord(c) for c in solicitud['facultad']) % 10 + 1
        
        # Enviar solicitud al broker
        socket.send_multipart([b"", json.dumps(solicitud).encode('utf-8')])
        
        # Recibir respuesta del broker (con timeout)
        response_frames = socket.recv_multipart()
        print(f"Frames recibidos: {len(response_frames)} - Contenido: {[f[:20] + b'...' if len(f) > 20 else f for f in response_frames]}")
        
        # En el patrón DEALER, la respuesta debe tener al menos un frame vacío seguido 
        # por el mensaje real (normalmente en la última posición)
        
        # Buscar el último frame no vacío que contenga datos JSON
        json_data = None
        for frame in reversed(response_frames):
            if frame:  # Si no está vacío
                try:
                    json_data = json.loads(frame.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue
        
        if json_data:
            # Registrar métricas de tiempo de respuesta del servidor (incluye broker + DTI)
            tiempo_respuesta_total = time.time() - tiempo_inicio_comunicacion
            monitor.registrar_tiempo_respuesta_servidor(
                tiempo_respuesta_total,
                solicitud.get("facultad", "Desconocida"),
                "respuesta_exitosa"
            )
            return json_data
        else:
            # Registrar métricas incluso para respuestas inválidas
            tiempo_respuesta_total = time.time() - tiempo_inicio_comunicacion
            monitor.registrar_tiempo_respuesta_servidor(
                tiempo_respuesta_total,
                solicitud.get("facultad", "Desconocida"),
                "respuesta_invalida"
            )
            print(f"ADVERTENCIA: No se encontró un JSON válido en la respuesta")
            return {"error": "No se pudo extraer datos JSON de la respuesta"}
    except zmq.ZMQError as e:
        # Registrar métricas de error de comunicación
        tiempo_respuesta_total = time.time() - tiempo_inicio_comunicacion
        monitor.registrar_tiempo_respuesta_servidor(
            tiempo_respuesta_total,
            solicitud.get("facultad", "Desconocida"),
            "error_zmq"
        )
        
        if e.errno == zmq.EAGAIN:
            print(f"TIMEOUT: Esperando respuesta del broker: {e}")
            return {"error": f"Timeout esperando respuesta del broker (posiblemente ocupado)"}
        else:
            print(f"ERROR ZMQ: Comunicación con el broker: {e}")
            return {"error": f"Error de comunicación ZMQ con el broker: {e}"}
    except Exception as e:
        # Registrar métricas de error general
        tiempo_respuesta_total = time.time() - tiempo_inicio_comunicacion
        monitor.registrar_tiempo_respuesta_servidor(
            tiempo_respuesta_total,
            solicitud.get("facultad", "Desconocida"),
            "error_general"
        )
        
        print(f"ERROR: Inesperado al comunicarse con el broker: {e}")
        return {"error": f"Error de comunicación con el broker: {e}"}
    finally:
        socket.close()
        contexto.term()

def iniciar_servidor(url_servidor):
    """
    Inicia el servidor de facultad y procesa solicitudes en un bucle infinito.
    Actúa como cliente en el patrón Load Balancing Broker.

    Args:
        url_servidor (str): URL donde escuchará el servidor (ej: "tcp://127.0.0.1:5555")

    Flujo de operación:
        1. Carga la lista de facultades válidas
        2. Configura el socket ZMQ en modo REP (reply)
        3. Espera y procesa solicitudes en bucle:
            - Recibe solicitud JSON
            - Valida que la facultad exista
            - Reenvía solicitud válida al broker
            - Retorna respuesta al programa solicitante

    Manejo de errores:
        - Validación de formato JSON
        - Verificación de facultad existente
        - Errores de comunicación con el broker
        - Errores inesperados
    """
    # Cargar datos de facultades
    facultades = leer_facultades()
    if not facultades:
        print("ADVERTENCIA: No hay facultades configuradas")
    
    # Crear ID único para este cliente (facultad)
    client_id = str(uuid.uuid4()).encode()
    instance_id = url_servidor.split(":")[-1]  # Extraer número de puerto para identificación
    
    # Configurar socket
    contexto = zmq.Context()
    socket = contexto.socket(zmq.REP)
    
    try:
        socket.bind(url_servidor)
        
        # Mostrar información en formato tabla
        print("\n" + "="*80)
        print("                    SERVIDOR DE FACULTAD - ESTADO INICIAL")
        print("="*80)
        print(f"| {'COMPONENTE':<25} | {'ESTADO':<15} | {'DETALLES':<30} |")
        print("-"*80)
        print(f"| {'Servidor Facultad':<25} | {'INICIADO':<15} | {'Cliente #{}'.format(instance_id):<30} |")
        print(f"| {'URL Servidor':<25} | {'ACTIVO':<15} | {url_servidor:<30} |")
        print(f"| {'Conexión Broker':<25} | {'CONECTADO':<15} | {BROKER_FRONTEND_URL:<30} |")
        print(f"| {'Cliente ID':<25} | {'ASIGNADO':<15} | {client_id.decode()[:30]:<30} |")
        print("-"*80)
        print("| ESTADO: Esperando solicitudes de programas académicos")
        print("="*80)
        
        # Variable para seguimiento de solicitudes
        solicitudes_procesadas = 0
        
        # Bucle principal
        while True:
            try:
                # Recibir solicitud con timeout para poder procesar interrupciones
                try:
                    mensaje = socket.recv_string(flags=zmq.NOBLOCK)
                    solicitud = json.loads(mensaje)
                    solicitudes_procesadas += 1
                    print(f"\nSolicitud #{solicitudes_procesadas} recibida: {solicitud}")
                    
                    # Validar facultad
                    if solicitud.get("facultad") not in facultades:
                        respuesta = {"error": "Facultad no válida"}
                        print(f"ADVERTENCIA: Facultad inválida: {solicitud.get('facultad')}")
                        
                        # Registrar rechazo por facultad inválida
                        monitor_programa = obtener_monitor_programa()
                        monitor_programa.registrar_requerimiento_rechazado_por_facultad(
                            solicitud.get("facultad", "Desconocida"), 
                            solicitud.get("programa", "Desconocido"), 
                            "facultad_invalida"
                        )
                    else:
                        # Añadir identificador de la instancia de facultad
                        solicitud["facultad_instance"] = instance_id
                        
                        # Reenviar al broker
                        print(f"ENVIANDO: Solicitud al broker: {solicitud.get('facultad')} - {solicitud.get('programa')}")
                        respuesta = enviar_a_broker(solicitud, client_id)
                        print(f"RECIBIDO: Respuesta del broker para: {solicitud.get('facultad')} - {solicitud.get('programa')}")
                    
                    # Enviar respuesta
                    socket.send_string(json.dumps(respuesta))
                    print(f"Respuesta enviada a programa: {respuesta}")
                except zmq.Again:
                    # No hay mensajes, esperar un poco y continuar
                    time.sleep(0.01)
                    continue
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Formato JSON inválido: {e}")
                socket.send_string(json.dumps({"error": "Formato de solicitud inválido"}))
            except zmq.ZMQError as e:
                print(f"ERROR ZMQ: {e}")
                if e.errno != zmq.ETERM:  # No es error de terminación
                    try:
                        socket.send_string(json.dumps({"error": f"Error de comunicación: {str(e)}"}))
                    except:
                        pass
            except Exception as e:
                print(f"ERROR: Inesperado: {e}")
                try:
                    socket.send_string(json.dumps({"error": f"Error: {str(e)}"}))
                except:
                    pass
                
    except Exception as e:
        print(f"ERROR FATAL: {e}")
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