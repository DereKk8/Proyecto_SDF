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
- Sistema de métricas de tiempo de respuesta

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

# Importar sistema de métricas
from decoradores_metricas import medir_tiempo_servidor
from recolector_metricas import recolector_global
from generador_reportes import generador_global

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
        thread_id = threading.get_ident()
        try:
           
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

    @medir_tiempo_servidor
    def asignar_aulas(self, solicitud: dict) -> dict:
        """Procesa una solicitud de asignación de aulas."""
        thread_id = threading.get_ident()
        
        
        try:
                facultad = solicitud["facultad"]
                programa = solicitud["programa"]
                num_salones = solicitud["salones"]
                num_laboratorios = solicitud["laboratorios"]
                marca_tiempo = datetime.now().isoformat()

                # Verificar disponibilidad antes de asignar
                salones_disponibles = [a for a in self.aulas.values() 
                                     if a.tipo == TipoAula.SALON and 
                                     a.estado == EstadoAula.DISPONIBLE]
                
                if len(salones_disponibles) < num_salones:
                    return {
                        "noDisponible": True,
                        "noDisponible": f"No hay suficientes salones disponibles. Solicitados: {num_salones}, Disponibles: {len(salones_disponibles)}"
                    }

                # Buscar salones disponibles
                salones_asignados = []
                for aula in salones_disponibles[:num_salones]:
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

                # Verificar si hay suficientes laboratorios o salones convertibles
                salones_convertibles = [a for a in self.aulas.values() 
                                      if a.tipo == TipoAula.SALON and 
                                      a.estado == EstadoAula.DISPONIBLE and 
                                      a.id not in salones_asignados]
                
                total_disponible = len(laboratorios_disponibles) + len(salones_convertibles)
                if total_disponible < num_laboratorios:
                    return {
                        "noDisponible": True,
                        "noDisponible": f"No hay suficientes laboratorios o salones convertibles. Solicitados: {num_laboratorios}, Disponibles: {total_disponible} (Labs: {len(laboratorios_disponibles)}, Convertibles: {len(salones_convertibles)})"
                    }

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
                    f"ASIGNACION EXITOSA - "
                    f"Facultad: {facultad} | "
                    f"Programa: {programa} | "
                    f"Salones: {len(salones_asignados)} | "
                    f"Laboratorios: {len(laboratorios_asignados)} | "
                    f"Aulas moviles: {len(aulas_moviles)}"
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
        
        # Limpiar métricas acumuladas
        recolector_global.limpiar_metricas()
        generador_global.limpiar_archivos()
        
        print("\n" + "=" * 60)
        print("| SISTEMA LIMPIADO EXITOSAMENTE")
        print("=" * 60)
        print("| Operacion                    | Estado")
        print("-" * 60)
        print("| Asignaciones borradas        | Completado")
        print("| Registros de logs            | Reiniciados")
        print("| Metricas y reportes          | Limpiados")
        print("=" * 60)
        
        # Mostrar estadísticas después de la limpieza
        estadisticas = servidor.obtener_estadisticas()
        print("\n" + "-" * 60)
        print("| ESTADISTICAS DESPUES DE LIMPIEZA")
        print("-" * 60)
        print("| Tipo de Aula      | Total | Disponibles | En Uso")
        print("-" * 60)
        print("| Salones           | {:5} | {:11} | {:6}".format(
            estadisticas["total_salones"], 
            estadisticas["salones_disponibles"],
            estadisticas["total_salones"] - estadisticas["salones_disponibles"]
        ))
        print("| Laboratorios      | {:5} | {:11} | {:6}".format(
            estadisticas["total_laboratorios"], 
            estadisticas["laboratorios_disponibles"],
            estadisticas["total_laboratorios"] - estadisticas["laboratorios_disponibles"]
        ))
        print("| Aulas Moviles     | {:5} | {:11} | {:6}".format(
            estadisticas["total_aulas_moviles"], 
            estadisticas["total_aulas_moviles"] - estadisticas["aulas_moviles_en_uso"],
            estadisticas["aulas_moviles_en_uso"]
        ))
        print("-" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("| ERROR AL LIMPIAR EL SISTEMA")
        print("=" * 60)
        print("| Error: {}".format(str(e)))
        print("=" * 60)
        logging.error(f"Error durante la limpieza del sistema: {str(e)}")

def main():
    """Función principal del servidor DTI."""
    # Mostrar información del servidor en formato tabla
    print("\n" + "=" * 80)
    print("| SERVIDOR CENTRAL DTI - SISTEMA DE ASIGNACION DE AULAS")
    print("=" * 80)
    print("| Estado            | Iniciando Servidor Central (DTI)")
    print("| URL               | {}".format(DTI_URL))
    print("| Estado Conexion   | Escuchando solicitudes")
    print("| Servidor          | DTI listo para procesar solicitudes")
    print("-" * 80)
    print("| COMANDOS DISPONIBLES")
    print("-" * 80)
    print("| Comando           | Descripcion")
    print("-" * 80)
    print("| limpiar           | Reinicia el sistema")
    print("| generar           | Genera reportes de metricas")
    print("=" * 80)
    
    contexto = zmq.Context()
    servidor = ServidorDTI()
    
    # Socket para recibir solicitudes de las facultades
    socket = contexto.socket(zmq.REP)
    socket.bind(DTI_URL)
    
    
    def atender_solicitud(mensaje):
        thread_id = threading.get_ident()
        try:
            
            solicitud = json.loads(mensaje)

            respuesta = servidor.asignar_aulas(solicitud)
            socket.send_string(json.dumps(respuesta))
            estadisticas = servidor.obtener_estadisticas()
            print("\n" + "-" * 60)
            print("| ESTADISTICAS ACTUALES DEL SISTEMA")
            print("-" * 60)
            print("| Tipo de Aula      | Total | Disponibles | En Uso")
            print("-" * 60)
            print("| Salones           | {:5} | {:11} | {:6}".format(
                estadisticas["total_salones"], 
                estadisticas["salones_disponibles"],
                estadisticas["total_salones"] - estadisticas["salones_disponibles"]
            ))
            print("| Laboratorios      | {:5} | {:11} | {:6}".format(
                estadisticas["total_laboratorios"], 
                estadisticas["laboratorios_disponibles"],
                estadisticas["total_laboratorios"] - estadisticas["laboratorios_disponibles"]
            ))
            print("| Aulas Moviles     | {:5} | {:11} | {:6}".format(
                estadisticas["total_aulas_moviles"], 
                estadisticas["total_aulas_moviles"] - estadisticas["aulas_moviles_en_uso"],
                estadisticas["aulas_moviles_en_uso"]
            ))
            print("-" * 60)
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
                elif comando == "generar":
                    print("\n" + "-" * 60)
                    print("| GENERANDO REPORTES DE METRICAS")
                    print("-" * 60)
                    generador_global.generar_reportes_completos()
                    print("| Reportes generados exitosamente")
                    print("-" * 60)
                    continue

            # Esperar mensaje con timeout para poder revisar la entrada estándar
            if socket.poll(100) == zmq.POLLIN:
                mensaje = socket.recv_string()
                print("\n" + "-" * 60)
                print("| SOLICITUD RECIBIDA")
                print("-" * 60)
                print("| Contenido: {}".format(mensaje))
                print("-" * 60)
                # Lanzar un hilo para procesar la solicitud y responder
                t = threading.Thread(target=atender_solicitud, args=(mensaje,))
                t.start()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("| DETENIENDO SERVIDOR DTI")
        print("=" * 60)
        print("| Estado: Cerrando conexiones...")
        print("=" * 60)
    finally:
        socket.close()
        contexto.term()


if __name__ == "__main__":
    main()