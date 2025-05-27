import zmq
import json
import os
from config import FACULTAD_SERVERS, FACULTADES_FILE
import logging
import argparse
import random
import time
import threading

# Importar sistema de métricas
from decoradores_metricas import medir_tiempo_respuesta_completo
from recolector_metricas import recolector_global
from generador_reportes import generador_global

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
            print(f"\n⚠️ Número inválido: {i}")
    
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

@medir_tiempo_respuesta_completo
def enviar_solicitudes(solicitudes, sockets):
    """
    Envía las solicitudes a los servidores y procesa las respuestas.
    
    Args:
        solicitudes (list): Lista de solicitudes a procesar
        sockets (list): Lista de sockets ZMQ conectados
    """
    server_index = 0
    for solicitud in solicitudes:
        socket = sockets[server_index]
        try:
            # Configurar timeout para la comunicación
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 segundos de timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 segundos de timeout
            
            # Intentar enviar la solicitud
            socket.send_string(json.dumps(solicitud))
            
            # Esperar respuesta
            respuesta = socket.recv_string()
            
            try:
                asignacion = json.loads(respuesta)
                if "error" in asignacion:
                    # Si el servidor de facultad reporta un error interno
                    logging.error(f"Error del servidor: {asignacion['error']}")
                    mostrar_error_amigable(CodigosError.FALLO_COMUNICACION_FACULTAD)
                else:
                    mostrar_asignacion(asignacion)
            except json.JSONDecodeError:
                # Error al decodificar la respuesta
                logging.error(f"Respuesta malformada: {respuesta}")
                mostrar_error_amigable(CodigosError.RESPUESTA_INVALIDA)
                
        except zmq.ZMQError as e:
            # Error de comunicación con el servidor
            logging.error(f"Error de comunicación ZMQ: {str(e)}")
            mostrar_error_amigable(CodigosError.FALLO_COMUNICACION_FACULTAD)
            
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

@medir_tiempo_respuesta_completo
def enviar_solicitud_simulacion(solicitud):
    """
    Función específica para envío de solicitudes en simulación.
    Usa los decoradores de métricas y maneja su propia conexión ZMQ.
    """
    context = zmq.Context()
    server_url = random.choice(FACULTAD_SERVERS)
    socket = context.socket(zmq.REQ)
    
    tiempo_inicio = time.time()
    
    try:
        socket.connect(server_url)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        socket.setsockopt(zmq.SNDTIMEO, 5000)
        
        # Enviar solicitud y medir tiempo
        socket.send_string(json.dumps(solicitud))
        respuesta = socket.recv_string()
        
        tiempo_respuesta = time.time() - tiempo_inicio
        
        # Registrar métricas manualmente en el recolector global
        recolector_global.estadisticas_servidor.agregar_metrica(tiempo_respuesta, True)
        
        # Registrar métrica por programa
        facultad = solicitud['facultad']
        programa = solicitud['programa']
        
        try:
            asignacion = json.loads(respuesta)
            if "error" in asignacion:
                resultado = "rechazado_servidor"
                logging.error(f"Error del servidor: {asignacion['error']}")
                print(f"\n❌ Error en la solicitud para {programa}")
            elif "noDisponible" in asignacion:
                resultado = "rechazado_servidor"
                print(f"\n⚠️ No hay aulas disponibles para {programa}")
            else:
                resultado = "exitoso"
                mostrar_asignacion(asignacion)
                
            # Registrar métrica por programa
            recolector_global.registrar_solicitud_programa(facultad, programa, resultado)
            
        except json.JSONDecodeError:
            resultado = "error_comunicacion"
            recolector_global.registrar_solicitud_programa(facultad, programa, resultado)
            print(f"\n❌ Error de comunicación con {programa}")
            
    except zmq.ZMQError as e:
        tiempo_respuesta = time.time() - tiempo_inicio
        recolector_global.estadisticas_servidor.agregar_metrica(tiempo_respuesta, False)
        recolector_global.registrar_solicitud_programa(
            solicitud['facultad'], solicitud['programa'], "error_comunicacion", str(e)
        )
        print(f"\n❌ Error de comunicación para {solicitud['programa']}")
    finally:
        socket.close()
        context.term()

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

    def proceso_programa_individual(solicitud):
        """Procesa una solicitud individual usando la función decorada."""
        # Retardo aleatorio entre 0.1 y 2 segundos
        time.sleep(random.uniform(0.1, 2.0))
        
        # Usar la función decorada específica para simulación
        # Esto asegura que las métricas se registren correctamente
        enviar_solicitud_simulacion(solicitud)

    # Ejecutar simulación con hilos para simular concurrencia
    hilos = []
    for solicitud in solicitudes:
        t = threading.Thread(target=proceso_programa_individual, args=(solicitud,))
        t.start()
        hilos.append(t)
    
    # Esperar a que todos los hilos terminen
    for t in hilos:
        t.join()
    
    print("\n🎯 Simulación completada.")
    # Esperar un momento para que todas las métricas se registren
    time.sleep(1)
    
    # Generar reportes de métricas (sin mostrar mensaje al usuario)
    generador_global.generar_reportes_completos()

def main():
    """Función principal que coordina el flujo del programa."""
    parser = argparse.ArgumentParser(description="Simulador de Programa Académico")
    parser.add_argument('--simulacion', choices=['A', 'B'], help='Ejecutar simulación mock con patrón A o B')
    args = parser.parse_args()

    if args.simulacion:
        simulacion_mock(args.simulacion)
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
        # Generar reportes finales de métricas (sin mostrar mensaje al usuario)
        generador_global.generar_reportes_completos()
        
        # Cerrar todas las conexiones
        for socket in sockets:
            socket.close()
        context.term()

if __name__ == "__main__":
    main()
