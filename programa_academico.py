import zmq
import json
import os
from config import FACULTAD_SERVERS, FACULTADES_FILE

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
            salones = solicitar_numero("Ingrese el número de salones: ", 1)
            laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0)
            solicitudes.append(crear_solicitud(facultad, programa, semestre, salones, laboratorios))
    return solicitudes

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
            socket.send_string(json.dumps(solicitud))
            respuesta = socket.recv_string()
            asignacion = json.loads(respuesta)
            mostrar_asignacion(asignacion)
        except json.JSONDecodeError:
            print("\n❌ Error: Respuesta malformada del servidor.")
        except zmq.ZMQError:
            print("\n❌ Error: Fallo en la comunicación con el servidor.")
        
        server_index = (server_index + 1) % len(sockets)

# =============================================================================
# Función principal
# =============================================================================

def main():
    """Función principal que coordina el flujo del programa."""
    facultades = cargar_facultades()
    context = zmq.Context()
    sockets = [context.socket(zmq.REQ) for _ in FACULTAD_SERVERS]
    for i, socket in enumerate(sockets):
        socket.connect(FACULTAD_SERVERS[i])

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

if __name__ == "__main__":
    main()
