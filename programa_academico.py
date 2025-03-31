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

def seleccionar_facultades_y_programas(facultades):
    """Permite seleccionar una o más facultades y sus programas."""
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

def mostrar_asignacion(asignacion):
    """Muestra la asignación de aulas."""
    if "error" in asignacion:
        print("\n❌ Error en la asignación:", asignacion["error"])
        return
    
    print("\n" + "#" * 50)
    print(f"✅ Programa: {asignacion['programa']}")
    print(f"📌 Facultad: {asignacion['facultad']}")
    print(f"📚 Semestre: {asignacion['semestre']}")
    print(f"🏫 Salones asignados: {asignacion['salones_asignados']}")
    print(f"🔬 Laboratorios asignados: {asignacion['laboratorios_asignados']}")
    print("#" * 50)

def main():
    facultades = cargar_facultades()
    context = zmq.Context()
    sockets = [context.socket(zmq.REQ) for _ in FACULTAD_SERVERS]
    for i, socket in enumerate(sockets):
        socket.connect(FACULTAD_SERVERS[i])

    while True:
        solicitud_colectiva = input("\n¿Desea realizar una solicitud colectiva? (s/n): ").strip().lower() == 's'
        
        if solicitud_colectiva:
            seleccionadas = seleccionar_facultades_y_programas(facultades)
            if not seleccionadas:
                continue
            salones = solicitar_numero("Ingrese el número de salones: ", 1)
            laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0)
            solicitudes = []
            for facultad, programas in seleccionadas:
                for programa in programas:
                    solicitudes.append({
                        "facultad": facultad,
                        "programa": programa,
                        "semestre": 2,
                        "salones": salones,
                        "laboratorios": laboratorios
                    })
        else:
            seleccionadas = seleccionar_facultades_y_programas(facultades)
            if not seleccionadas:
                continue
            solicitudes = []
            for facultad, programas in seleccionadas:
                for programa in programas:
                    print("\n" + "-" * 50)
                    print(f"Ingresando datos para el programa: {programa}")
                    print("-" * 50)
                    semestre = solicitar_numero("Ingrese el semestre: ", 1, 10)
                    salones = solicitar_numero("Ingrese el número de salones: ", 1)
                    laboratorios = solicitar_numero("Ingrese el número de laboratorios: ", 0)
                    solicitudes.append({
                        "facultad": facultad,
                        "programa": programa,
                        "semestre": semestre,
                        "salones": salones,
                        "laboratorios": laboratorios
                    })

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

        if input("\n¿Desea realizar otra solicitud? (s/n): ").strip().lower() != 's':
            break

if __name__ == "__main__":
    main()
