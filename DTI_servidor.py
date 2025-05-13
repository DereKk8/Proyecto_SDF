"""
DTI_servidor.py - Servidor Central del Sistema de Asignación de Aulas

Este módulo implementa el servidor central (DTI) del sistema de asignación de aulas.
Gestiona la asignación de salones y laboratorios, manteniendo un registro de su estado
y procesando solicitudes de las facultades.

Características principales:
- Gestión de aulas (salones, laboratorios y aulas móviles)
- Procesamiento de solicitudes de asignación
- Sistema de logging para seguimiento de operaciones
- Persistencia de datos en archivos CSV
- Comando de limpieza del sistema
- Estadísticas en tiempo real

"""

import zmq  # Para comunicación distribuida
import json  # Para serialización de datos
import logging  # Para registro de eventos
from datetime import datetime
import csv
from dataclasses import dataclass
from enum import Enum
import os
from config import DTI_URL, AULAS_REGISTRO_FILE, ASIGNACIONES_LOG_FILE
import select
import sys
import threading

# =============================================================================
# Definiciones de clases y enumeraciones
# =============================================================================

class TipoAula(Enum):
    SALON = "salón"
    LABORATORIO = "laboratorio"
    AULA_MOVIL = "aula móvil"

class EstadoAula(Enum):
    DISPONIBLE = "disponible"
    ASIGNADA = "asignada"

@dataclass
class Aula:
    id: str
    tipo: TipoAula
    estado: EstadoAula
    capacidad: int
    facultad: str = ""
    programa: str = ""
    fecha_solicitud: str = ""
    fecha_asignacion: str = ""

class ServidorDTI:
    def __init__(self):
        self.aulas = {}
        self.configurar_registro()
        self.cargar_aulas()
        self.lock = threading.Lock()  # Para proteger recursos compartidos

    def configurar_registro(self):
        """Configura el sistema de registro de eventos."""
        logging.basicConfig(
            filename=ASIGNACIONES_LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def cargar_aulas(self):
        """Carga las aulas desde el archivo de registro."""
        try:
            with open(AULAS_REGISTRO_FILE, 'r', encoding='utf-8') as archivo:
                lector = csv.DictReader(archivo)
                for fila in lector:
                    self.aulas[fila['id']] = Aula(
                        id=fila['id'],
                        tipo=TipoAula(fila['tipo']),
                        estado=EstadoAula(fila['estado']),
                        capacidad=int(fila['capacidad']),
                        facultad=fila['facultad'],
                        programa=fila['programa'],
                        fecha_solicitud=fila['fecha_solicitud'],
                        fecha_asignacion=fila['fecha_asignacion']
                    )
            logging.info(f"Aulas cargadas exitosamente: {len(self.aulas)} aulas en total")
        except Exception as e:
            logging.error(f"Error al cargar aulas: {e}")
            raise

    def guardar_aulas(self):
        """Guarda el estado actual de las aulas en el archivo."""
        try:
            with self.lock:
                with open(AULAS_REGISTRO_FILE, 'w', newline='', encoding='utf-8') as archivo:
                    escritor = csv.writer(archivo)
                    escritor.writerow(['id', 'tipo', 'estado', 'capacidad', 'facultad', 
                                   'programa', 'fecha_solicitud', 'fecha_asignacion'])
                    for aula in self.aulas.values():
                        escritor.writerow([
                            aula.id, aula.tipo.value, aula.estado.value, aula.capacidad,
                            aula.facultad, aula.programa, aula.fecha_solicitud, 
                            aula.fecha_asignacion
                        ])
            logging.info("Base de datos de aulas actualizada")
        except Exception as e:
            logging.error(f"Error al guardar aulas: {e}")
            raise

    def asignar_aulas(self, solicitud: dict) -> dict:
        """Procesa una solicitud de asignación de aulas."""
        try:
            with self.lock:
                facultad = solicitud["facultad"]
                programa = solicitud["programa"]
                num_salones = solicitud["salones"]
                num_laboratorios = solicitud["laboratorios"]
                marca_tiempo = datetime.now().isoformat()

                # Buscar salones disponibles
                salones_asignados = []
                for aula in self.aulas.values():
                    if (len(salones_asignados) < num_salones and 
                        aula.tipo == TipoAula.SALON and 
                        aula.estado == EstadoAula.DISPONIBLE):
                        aula.estado = EstadoAula.ASIGNADA
                        aula.facultad = facultad
                        aula.programa = programa
                        aula.fecha_solicitud = marca_tiempo
                        aula.fecha_asignacion = marca_tiempo
                        salones_asignados.append(aula.id)

                # Buscar laboratorios disponibles
                laboratorios_asignados = []
                laboratorios_disponibles = [a for a in self.aulas.values() 
                                          if a.tipo == TipoAula.LABORATORIO and 
                                          a.estado == EstadoAula.DISPONIBLE]

                for aula in laboratorios_disponibles[:num_laboratorios]:
                    aula.estado = EstadoAula.ASIGNADA
                    aula.facultad = facultad
                    aula.programa = programa
                    aula.fecha_solicitud = marca_tiempo
                    aula.fecha_asignacion = marca_tiempo
                    laboratorios_asignados.append(aula.id)

                # Convertir salones en aulas móviles si es necesario
                aulas_moviles = []
                if len(laboratorios_asignados) < num_laboratorios:
                    labs_faltantes = num_laboratorios - len(laboratorios_asignados)
                    salones_disponibles = [a for a in self.aulas.values() 
                                         if a.tipo == TipoAula.SALON and 
                                         a.estado == EstadoAula.DISPONIBLE and 
                                         a.id not in salones_asignados]

                    for aula in salones_disponibles[:labs_faltantes]:
                        aula.tipo = TipoAula.AULA_MOVIL
                        aula.estado = EstadoAula.ASIGNADA
                        aula.facultad = facultad
                        aula.programa = programa
                        aula.fecha_solicitud = marca_tiempo
                        aula.fecha_asignacion = marca_tiempo
                        aulas_moviles.append(aula.id)
                        logging.info(f"Salón {aula.id} convertido en aula móvil")

                # Guardar cambios
                self.guardar_aulas()
                
                respuesta = {
                    "facultad": facultad,
                    "programa": programa,
                    "semestre": solicitud["semestre"],
                    "salones_asignados": salones_asignados,
                    "laboratorios_asignados": laboratorios_asignados + aulas_moviles
                }

                if aulas_moviles:
                    respuesta["notificacion"] = (
                        f"Se han convertido {len(aulas_moviles)} salones en aulas móviles "
                        f"por falta de laboratorios disponibles."
                    )

                logging.info(
                    f"Asignación exitosa:\n"
                    f"Facultad: {facultad}\n"
                    f"Programa: {programa}\n"
                    f"Salones: {salones_asignados}\n"
                    f"Laboratorios: {laboratorios_asignados}\n"
                    f"Aulas móviles: {aulas_moviles}"
                )

                return respuesta

        except Exception as e:
            mensaje_error = f"Error en la asignación: {str(e)}"
            logging.error(mensaje_error)
            return {"error": mensaje_error}

    def obtener_estadisticas(self) -> dict:
        """Genera estadísticas de uso de aulas."""
        estadisticas = {
            "total_salones": 0,
            "total_laboratorios": 0,
            "total_aulas_moviles": 0,
            "salones_disponibles": 0,
            "laboratorios_disponibles": 0,
            "aulas_moviles_en_uso": 0
        }

        for aula in self.aulas.values():
            if aula.tipo == TipoAula.SALON:
                estadisticas["total_salones"] += 1
                if aula.estado == EstadoAula.DISPONIBLE:
                    estadisticas["salones_disponibles"] += 1
            elif aula.tipo == TipoAula.LABORATORIO:
                estadisticas["total_laboratorios"] += 1
                if aula.estado == EstadoAula.DISPONIBLE:
                    estadisticas["laboratorios_disponibles"] += 1
            elif aula.tipo == TipoAula.AULA_MOVIL:
                estadisticas["total_aulas_moviles"] += 1
                if aula.estado == EstadoAula.ASIGNADA:
                    estadisticas["aulas_moviles_en_uso"] += 1

        return estadisticas

def limpiar_sistema(servidor):
    """Limpia todas las asignaciones y registros del sistema."""
    try:
        # Reiniciar estado de todas las aulas
        for aula in servidor.aulas.values():
            aula.estado = EstadoAula.DISPONIBLE
            aula.facultad = ""
            aula.programa = ""
            aula.fecha_solicitud = ""
            aula.fecha_asignacion = ""
            # Si era un aula móvil, volverla a convertir en salón
            if aula.tipo == TipoAula.AULA_MOVIL:
                aula.tipo = TipoAula.SALON

        # Guardar el estado limpio en el archivo
        servidor.guardar_aulas()

        # Limpiar archivo de logs
        open(ASIGNACIONES_LOG_FILE, 'w').close()
        
        # Reiniciar el sistema de logging
        servidor.configurar_registro()
        logging.info("Sistema limpiado completamente")
        
        print("\n✨ Sistema limpiado exitosamente")
        print("📋 Todas las asignaciones han sido borradas")
        print("📝 Registros de logs reiniciados")
        
        # Mostrar estadísticas después de la limpieza
        estadisticas = servidor.obtener_estadisticas()
        print("\nEstadísticas actuales:")
        print(json.dumps(estadisticas, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error al limpiar el sistema: {str(e)}")
        logging.error(f"Error durante la limpieza del sistema: {str(e)}")

def main():
    """Función principal del servidor DTI."""
    print("✅ Iniciando Servidor Central (DTI)...")
    
    contexto = zmq.Context()
    servidor = ServidorDTI()
    
    # Socket para recibir solicitudes de las facultades
    socket = contexto.socket(zmq.REP)
    socket.bind(DTI_URL)
    
    print(f"📡 Escuchando solicitudes en {DTI_URL}")
    print("✨ Servidor DTI listo para procesar solicitudes")
    print("💡 Escriba 'limpiar' para reiniciar el sistema")
    
    def atender_solicitud(mensaje):
        try:
            solicitud = json.loads(mensaje)
            logging.info(f"Solicitud recibida de facultad: {solicitud.get('facultad')}")
            respuesta = servidor.asignar_aulas(solicitud)
            socket.send_string(json.dumps(respuesta))
            estadisticas = servidor.obtener_estadisticas()
            print("\nEstadísticas actuales:")
            print(json.dumps(estadisticas, indent=2))
            logging.info(f"Respuesta enviada a facultad: {solicitud.get('facultad')}")
        except Exception as e:
            logging.error(f"Error procesando solicitud: {e}")
            socket.send_string(json.dumps({"error": str(e)}))

    try:
        while True:
            # Verificar si hay comando en la entrada estándar
            if select.select([sys.stdin], [], [], 0.0)[0]:
                comando = input().strip().lower()
                if comando == "limpiar":
                    limpiar_sistema(servidor)
                    continue

            # Esperar mensaje con timeout para poder revisar la entrada estándar
            if socket.poll(100) == zmq.POLLIN:
                mensaje = socket.recv_string()
                # Lanzar un hilo para procesar la solicitud y responder
                t = threading.Thread(target=atender_solicitud, args=(mensaje,))
                t.start()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor DTI...")
    finally:
        socket.close()
        contexto.term()


if __name__ == "__main__":
    main()
