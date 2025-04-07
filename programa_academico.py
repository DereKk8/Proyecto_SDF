import zmq
import json
import os
from config import FACULTAD_SERVERS, FACULTADES_FILE
import logging

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
                socket = context.socket(zmq.REQ)
                socket.connect(FACULTAD_SERVERS[server_index])
                sockets[server_index] = socket
            except:
                mostrar_error_amigable(CodigosError.SERVIDOR_NO_DISPONIBLE)
        
        # Rotar al siguiente servidor
        server_index = (server_index + 1) % len(sockets)

def main():
    """Función principal que coordina el flujo del programa."""
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
