import zmq
import json
import os
from config import FACULTAD_SERVERS, FACULTADES_FILE

def cargar_facultades():
    """Carga las facultades y programas académicos desde el archivo de texto con validaciones."""
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

def solicitar_numero(mensaje, minimo=1, maximo=None):
    """Solicita un número al usuario, asegurando que sea válido."""
    while True:
        try:
            valor = int(input(mensaje))
            if maximo and (valor < minimo or valor > maximo):
                print(f"\n❌ Error: Ingrese un número entre {minimo} y {maximo}.")
            else:
                return valor
        except ValueError:
            print("\n❌ Error: Debe ingresar un número válido.")

def seleccionar_facultad_y_programas(facultades):
    """Permite al usuario seleccionar una facultad y uno o más programas académicos con validación de entrada."""
    if not facultades:
        print("\n❌ No hay facultades disponibles para seleccionar.")
        return None, None

    print("\n" + "=" * 50)
    print("Facultades disponibles:")
    print("=" * 50)
    for i, facultad in enumerate(facultades.keys(), 1):
        print(f"{i}. {facultad}")

    facultad_index = solicitar_numero("\nIngrese el número de la facultad: ", 1, len(facultades)) - 1
    facultad_seleccionada = list(facultades.keys())[facultad_index]

    print("\n" + "=" * 50)
    print(f"Programas académicos en {facultad_seleccionada}:")
    print("=" * 50)
    programas = facultades[facultad_seleccionada]
    for i, programa in enumerate(programas, 1):
        print(f"{i}. {programa}")

    while True:
        try:
            programa_indices = input("\nIngrese los números de los programas académicos separados por comas: ")
            programas_seleccionados = [programas[int(i) - 1] for i in programa_indices.split(",") if i.strip().isdigit()]
            if programas_seleccionados:
                break
            else:
                print("\n❌ Error: Debe ingresar al menos un programa válido.")
        except (ValueError, IndexError):
            print("\n❌ Error: Debe ingresar números válidos de la lista.")

    return facultad_seleccionada, programas_seleccionados

def mostrar_asignacion(asignacion):
    """Muestra la asignación de aulas de forma más legible."""
    if "error" in asignacion:
        print("\n❌ Error en la asignación:", asignacion["error"])
        return
    
    print("\n" + "#" * 50)
    print(f"✅ Solicitud procesada para el programa: {asignacion['programa']}")
    print(f"📌 Facultad: {asignacion['facultad']}")
    print(f"📚 Semestre: {asignacion['semestre']}")
    print(f"🏫 Salones asignados: {asignacion['salones_asignados']}")
    print(f"🔬 Laboratorios asignados: {asignacion['laboratorios_asignados']}")
    print("#" * 50)

def main():
    facultades = cargar_facultades()
    context = zmq.Context()
    
    # Inicializamos los sockets para los dos servidores
    sockets = [context.socket(zmq.REQ) for _ in FACULTAD_SERVERS]
    for i, socket in enumerate(sockets):
        socket.connect(FACULTAD_SERVERS[i])

    server_index = 0  # Alternar servidores

    while True:
        facultad, programas = seleccionar_facultad_y_programas(facultades)
        if facultad is None:
            break  # No hay facultades disponibles

        solicitudes = []
        for programa in programas:
            print("\n" + "-" * 50)
            print(f"Ingresando datos para el programa: {programa}")
            print("-" * 50)
            semestre = solicitar_numero("Ingrese el semestre: ", 1, 10)
            salones = solicitar_numero("Ingrese el número de salones: ", 1)
            laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0)

            solicitud = {
                "facultad": facultad,
                "programa": programa,
                "semestre": semestre,
                "salones": salones,
                "laboratorios": laboratorios
            }
            solicitudes.append(solicitud)

        for solicitud in solicitudes:
            socket = sockets[server_index]  # Alternar servidores
            try:
                socket.send_string(json.dumps(solicitud))
                respuesta = socket.recv_string()
                asignacion = json.loads(respuesta)
                mostrar_asignacion(asignacion)  # Mostrar asignación con formato legible
            except json.JSONDecodeError:
                print("\n❌ Error: Respuesta malformada del servidor.")
                continue
            except zmq.ZMQError:
                print("\n❌ Error: Fallo en la comunicación con el servidor.")
                continue

            server_index = (server_index + 1) % len(sockets)  # Cambiar al siguiente servidor

        continuar = input("\n¿Desea realizar otra solicitud? (s/n): ").strip().lower()
        if continuar != 's':
            break

if __name__ == "__main__":
    main()