import zmq
import json
import os
from config import FACULTAD_SERVERS, FACULTADES_FILE
import logging
import argparse
import random
import time
import threading
import uuid
from monitor_metricas import obtener_monitor
from monitor_metricas_programa import obtener_monitor_programa

# =============================================================================
# Funciones de carga y validación de datos
# =============================================================================

def cargar_facultades():
    """
    Carga las facultades y programas académicos desde el archivo de texto.
    
    Returns:
        dict: Diccionario con las facultades y sus programas académicos.
    """
    facultades = {}
    if not os.path.exists(FACULTADES_FILE):
        print(f"\n❌ Error: No se encontró el archivo '{FACULTADES_FILE}'.")
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

# =============================================================================
# Funciones de interacción con el usuario
# =============================================================================

def solicitar_numero(mensaje, minimo=1, maximo=None):
    """
    Solicita un número al usuario con validación de rango.
    
    Args:
        mensaje (str): Mensaje a mostrar al usuario
        minimo (int): Valor mínimo permitido
        maximo (int, optional): Valor máximo permitido
    
    Returns:
        int: Número válido ingresado por el usuario
    """
    while True:
        try:
            valor = int(input(mensaje))
            if maximo and (valor < minimo or valor > maximo):
                print(f"\n❌ Error: Ingrese un número entre {minimo} y {maximo}.")
            else:
                return valor
        except ValueError:
            print("\n❌ Error: Debe ingresar un número válido.")

def seleccionar_facultades_y_programas(facultades):
    """
    Permite al usuario seleccionar facultades y programas.
    
    Args:
        facultades (dict): Diccionario de facultades y programas
    
    Returns:
        list: Lista de tuplas (facultad, programas) seleccionadas
    """
    if not facultades:
        print("\n❌ No hay facultades disponibles.")
        return []

    print("\n" + "=" * 50)
    print("Facultades disponibles:")
    print("=" * 50)
    for i, facultad in enumerate(facultades.keys(), 1):
        print(f"{i}. {facultad}")

    indices = input("\nIngrese los números de las facultades separados por comas: ").split(",")
    seleccionadas = []
    for i in indices:
        try:
            facultad = list(facultades.keys())[int(i) - 1]
            seleccionadas.append((facultad, facultades[facultad]))
        except (ValueError, IndexError):
            print(f"\n⚠️ Advertencia: Número inválido ({i}).")
    
    return seleccionadas

# =============================================================================
# Funciones de visualización
# =============================================================================

def mostrar_asignacion(asignacion):
    """
    Muestra la asignación de aulas de manera formateada.
    
    Args:
        asignacion (dict): Diccionario con la información de asignación
    """
    if "error" in asignacion:
        print("\n❌ Error en la asignación:", asignacion["error"])
        return

    if "noDisponible" in asignacion:
        print("\n⚠️ No hay disponibilidad para la solicitud:", asignacion["noDisponible"])
        return
    
    print("\n" + "#" * 50)
    print(f"✅ Programa: {asignacion['programa']}")
    print(f"📌 Facultad: {asignacion['facultad']}")
    print(f"📚 Semestre: {asignacion['semestre']}")
    print(f"🏫 Salones asignados: {asignacion['salones_asignados']}")
    print(f"🔬 Laboratorios asignados: {asignacion['laboratorios_asignados']}")
    if "notificacion" in asignacion:
        print(f"\n⚠️ {asignacion['notificacion']}")
    print("#" * 50)

# =============================================================================
# Funciones de procesamiento de solicitudes
# =============================================================================

def crear_solicitud(facultad, programa, semestre, salones, laboratorios):
    """Crea una solicitud con los nuevos campos requeridos."""
    return {
        "facultad": facultad,
        "programa": programa,
        "semestre": semestre,
        "salones": salones,
        "laboratorios": laboratorios,
        "capacidad_min": 30  # Valor por defecto o solicitado al usuario
    }

def procesar_solicitud_colectiva(seleccionadas):
    """
    Procesa una solicitud colectiva para múltiples programas.
    
    Args:
        seleccionadas (list): Lista de tuplas (facultad, programas) seleccionadas
    
    Returns:
        list: Lista de solicitudes procesadas
    """
    semestre = solicitar_numero("Ingrese el semestre: ", 1, 10)
    salones = solicitar_numero("Ingrese el número de salones: ", 1)
    laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0)
    
    solicitudes = []
    for facultad, programas in seleccionadas:
        for programa in programas:
            solicitudes.append(crear_solicitud(facultad, programa, semestre, salones, laboratorios))
    return solicitudes

def procesar_solicitud_individual(seleccionadas):
    """
    Procesa solicitudes individuales para cada programa.
    
    Args:
        seleccionadas (list): Lista de tuplas (facultad, programas) seleccionadas
    
    Returns:
        list: Lista de solicitudes procesadas
    """
    solicitudes = []
    for facultad, programas in seleccionadas:
        for programa in programas:
            print("\n" + "-" * 50)
            print(f"Ingresando datos para el programa: {programa}")
            print("-" * 50)
            semestre = solicitar_numero("Ingrese el semestre: ", 1, 10)
            salones = solicitar_numero("Ingrese el número de salones: ", 1, 30)
            laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0, 10)
            solicitudes.append(crear_solicitud(facultad, programa, semestre, salones, laboratorios))
    return solicitudes

# =============================================================================
# Función principal
# =============================================================================

class CodigosError:
    """Códigos de error del sistema"""
    FALLO_COMUNICACION_FACULTAD = "F001"
    RESPUESTA_INVALIDA = "F002"
    SERVIDOR_NO_DISPONIBLE = "F003"

def mostrar_error_amigable(codigo_error):
    """
    Muestra un mensaje de error amigable al usuario según el código.
    
    Args:
        codigo_error (str): Código del error ocurrido
    """
    mensajes = {
        CodigosError.FALLO_COMUNICACION_FACULTAD: "No se pudo procesar su solicitud en este momento F001 ",
        CodigosError.RESPUESTA_INVALIDA: "No se pudo procesar la respuesta del servidor F002",
        CodigosError.SERVIDOR_NO_DISPONIBLE: "El servicio no está disponible en este momento F003"
    }
    print(f"\n❌ {mensajes.get(codigo_error, 'Error desconocido')}")

def enviar_solicitudes(solicitudes, sockets):
    """
    Envía las solicitudes a los servidores y procesa las respuestas.
    
    Args:
        solicitudes (list): Lista de solicitudes a procesar
        sockets (list): Lista de sockets ZMQ conectados
    """
    # Obtener monitor de métricas
    monitor = obtener_monitor()
    
    # Contador de solicitudes pendientes con lock para sincronización
    pending_count = [threading.Lock(), 0]
    
    server_index = 0
    for solicitud in solicitudes:
        socket = sockets[server_index]
        
        # Generar ID único para la solicitud y registrar inicio
        id_solicitud = str(uuid.uuid4())
        facultad = solicitud.get("facultad", "Desconocida")
        programa = solicitud.get("programa", "Desconocido")
        
        monitor.registrar_inicio_solicitud_programa(id_solicitud, facultad, programa)
        
        try:
            # Configurar timeout para la comunicación
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 segundos de timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 segundos de timeout
            
            # Incrementar contador
            with pending_count[0]:
                pending_count[1] += 1
            
            # Intentar enviar la solicitud
            socket.send_string(json.dumps(solicitud))
            
            # Esperar respuesta
            respuesta = socket.recv_string()
            
            # Decrementar contador
            with pending_count[0]:
                pending_count[1] -= 1
            
            try:
                asignacion = json.loads(respuesta)
                if "error" in asignacion:
                    # Si el servidor de facultad reporta un error interno
                    logging.error(f"Error del servidor: {asignacion['error']}")
                    mostrar_error_amigable(CodigosError.FALLO_COMUNICACION_FACULTAD)
                else:
                    mostrar_asignacion(asignacion)
                
                # Registrar fin de solicitud exitosa
                monitor.registrar_fin_solicitud_programa(id_solicitud)
                    
            except json.JSONDecodeError:
                # Error al decodificar la respuesta
                logging.error(f"Respuesta malformada: {respuesta}")
                mostrar_error_amigable(CodigosError.RESPUESTA_INVALIDA)
                # Registrar fin incluso en caso de error
                monitor.registrar_fin_solicitud_programa(id_solicitud)
                
        except zmq.ZMQError as e:
            # Error de comunicación con el servidor
            logging.error(f"Error de comunicación ZMQ: {str(e)}")
            mostrar_error_amigable(CodigosError.FALLO_COMUNICACION_FACULTAD)
            
            # Registrar fin incluso en caso de error de comunicación
            monitor.registrar_fin_solicitud_programa(id_solicitud)
            
            # Decrementar contador en caso de error
            with pending_count[0]:
                pending_count[1] -= 1
            
            # Intentar reconectar el socket
            try:
                socket.close()
                socket = context.socket(zmq.REQ) # type: ignore
                socket.connect(FACULTAD_SERVERS[server_index])
                sockets[server_index] = socket
            except:
                mostrar_error_amigable(CodigosError.SERVIDOR_NO_DISPONIBLE)
        
        # Rotar al siguiente servidor
        server_index = (server_index + 1) % len(sockets)
        
    # Esperar a que todas las solicitudes se completen
    time.sleep(0.5)  # Dar tiempo para que el contador se actualice
    print("\r", end="")

def simulacion_mock(patron):
    """
    Ejecuta la simulación mock según el patrón A o B.
    """
    facultades_dict = cargar_facultades()
    if len(facultades_dict) < 5:
        print("\n❌ Se requieren al menos 5 facultades para la simulación.")
        return
    

    # Seleccionar 5 facultades aleatoriamente
    facultades_seleccionadas = random.sample(list(facultades_dict.keys()), 5)
    solicitudes = []
    for facultad in facultades_seleccionadas:
        for programa in facultades_dict[facultad]:
            if patron == 'A':
                salones, laboratorios = 7, 2
            else:
                salones, laboratorios = 10, 4
            solicitudes.append({
                'facultad': facultad,
                'programa': programa,
                'semestre': random.randint(1, 10),
                'salones': salones,
                'laboratorios': laboratorios,
                'capacidad_min': 30
            })

    def proceso_programa(solicitud, pending_count):
        # Obtener monitor de métricas y generar ID único
        monitor = obtener_monitor()
        id_solicitud = str(uuid.uuid4())
        facultad = solicitud.get("facultad", "Desconocida")
        programa = solicitud.get("programa", "Desconocido")
        
        # Registrar inicio de solicitud
        monitor.registrar_inicio_solicitud_programa(id_solicitud, facultad, programa)
        
        # Retardo aleatorio entre 0.1 y 2 segundos
        time.sleep(random.uniform(0.1, 2.0))
        context = zmq.Context()
        
        # Seleccionar servidor de facultad - intentar ambos si es necesario
        servers_to_try = list(FACULTAD_SERVERS)  # Hacer una copia para poder reordenar
        random.shuffle(servers_to_try)  # Aleatorizar el orden
        
        # Incrementar el contador de solicitudes pendientes
        with pending_count[0]:
            pending_count[1] += 1
        
        success = False
        error_message = "No hay servidores de facultad disponibles"
        
        # Intentar enviar a los servidores disponibles
        for server_url in servers_to_try:
            try:
                socket = context.socket(zmq.REQ)
                # Configurar timeouts más adecuados
                socket.setsockopt(zmq.RCVTIMEO, 15000)  # 15 segundos para recibir
                socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 segundos para enviar
                socket.setsockopt(zmq.LINGER, 1000)     # Esperar max 1 segundo al cerrar
                
                socket.connect(server_url)
                
                socket.send_string(json.dumps(solicitud))
                
                # Recibir con tiempo de espera
                respuesta = socket.recv_string()
                
                try:
                    asignacion = json.loads(respuesta)
                    mostrar_asignacion(asignacion)
                    
                    # Registrar métricas por programa según el resultado
                    monitor_programa = obtener_monitor_programa()
                    if "error" in asignacion:
                        monitor_programa.registrar_error_comunicacion_programa(facultad, programa, "error_servidor")
                    elif "noDisponible" in asignacion:
                        monitor_programa.registrar_requerimiento_rechazado_por_servidor(facultad, programa, "no_disponible")
                    else:
                        monitor_programa.registrar_requerimiento_atendido_satisfactoriamente(facultad, programa)
                    
                    success = True
                    
                    # Registrar fin de solicitud exitosa
                    monitor.registrar_fin_solicitud_programa(id_solicitud)
                    
                    break  # Salir del bucle si tuvo éxito
                except json.JSONDecodeError:
                    error_message = f"Respuesta malformada: {respuesta[:100]}..."
                    print(f"\n❌ {error_message}")
                finally:
                    socket.close()
                    
            except zmq.ZMQError as e:
                error_message = f"Error de comunicación: {str(e)}"
                print(f"\n❌ {error_message} con {server_url}")
                # Registrar error de comunicación por programa
                monitor_programa = obtener_monitor_programa()
                monitor_programa.registrar_error_comunicacion_programa(facultad, programa, "zmq_error")
                if socket:
                    socket.close()
                    
        # Decrementar el contador cuando la solicitud se completa (éxito o error)
        with pending_count[0]:
            pending_count[1] -= 1
            
        if not success:
            print(f"\n❌ Todos los intentos fallaron para {solicitud['facultad']} - {solicitud['programa']}: {error_message}")
            # Registrar fin incluso en caso de fallo total
            monitor.registrar_fin_solicitud_programa(id_solicitud)
            
        context.term()

    # Crear un contador compartido con un lock para evitar condiciones de carrera
    # [lock, counter]
    pending_count = [threading.Lock(), 0]

    hilos = []
    for solicitud in solicitudes:
        t = threading.Thread(target=proceso_programa, args=(solicitud, pending_count))
        t.start()
        hilos.append(t)
    
    print("🚀 Iniciando simulación...")
    
    for t in hilos:
        t.join()
    
    print("✅ Simulación completada")

def generar_reportes_periodicos():
    """
    Función para generar reportes periódicos de métricas programa-atención en segundo plano.
    """
    monitor = obtener_monitor()
    monitor_programa = obtener_monitor_programa()
    
    while True:
        try:
            time.sleep(300)  # Generar reporte cada 5 minutos
            
            # Reporte programa-atención (sin mostrar en consola)
            monitor.generar_reporte_programa_atencion()
            
            # Reporte por programa (archivo separado, sin mostrar en consola)
            monitor_programa.guardar_reporte_por_programa()
            
        except Exception as e:
            # Solo registrar errores en log, no mostrar en consola
            logging.error(f"Error generando reporte periódico: {e}")

def main():
    """Función principal que coordina el flujo del programa."""
    parser = argparse.ArgumentParser(description="Simulador de Programa Académico")
    parser.add_argument('--simulacion', choices=['A', 'B'], help='Ejecutar simulación mock con patrón A o B')
    args = parser.parse_args()

    # Iniciar hilo de reportes periódicos (silencioso)
    hilo_reportes = threading.Thread(target=generar_reportes_periodicos, daemon=True)
    hilo_reportes.start()

    if args.simulacion:
        simulacion_mock(args.simulacion)
        
        # Generar reportes después de la simulación (silencioso)
        monitor = obtener_monitor()
        monitor.generar_reporte_programa_atencion()
        
        monitor_programa = obtener_monitor_programa()
        monitor_programa.guardar_reporte_por_programa()
        
        return

    # Configurar logging
    logging.basicConfig(
        filename='programa_academico.log',
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    facultades = cargar_facultades()
    context = zmq.Context()
    sockets = []
    
    # Inicializar conexiones con manejo de errores
    for server_url in FACULTAD_SERVERS:
        try:
            socket = context.socket(zmq.REQ)
            socket.connect(server_url)
            sockets.append(socket)
        except zmq.ZMQError:
            logging.error(f"No se pudo conectar a {server_url}")
            mostrar_error_amigable(CodigosError.SERVIDOR_NO_DISPONIBLE)
            return

    try:
        while True:
            solicitud_colectiva = input("\n¿Desea realizar una solicitud colectiva? (s/n): ").strip().lower() == 's'
            seleccionadas = seleccionar_facultades_y_programas(facultades)
            
            if not seleccionadas:
                continue
                
            solicitudes = (procesar_solicitud_colectiva(seleccionadas) 
                          if solicitud_colectiva 
                          else procesar_solicitud_individual(seleccionadas))
            
            enviar_solicitudes(solicitudes, sockets)

            if input("\n¿Desea realizar otra solicitud? (s/n): ").strip().lower() != 's':
                break
    
    finally:
        # Cerrar todas las conexiones
        for socket in sockets:
            socket.close()
        context.term()

if __name__ == "__main__":
    main()
