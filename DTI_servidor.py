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
- Arquitectura de trabajador ZeroMQ bajo el patrón Load Balancing Broker
- Heartbeat para sistema de tolerancia a fallos
- Sincronización de estado con servidor de respaldo

"""

import zmq  # Para comunicación distribuida
import json  # Para serialización de datos
import logging  # Para registro de eventos
from datetime import datetime
import csv
from dataclasses import dataclass
from enum import Enum
import os
from config import BROKER_BACKEND_URL, AULAS_REGISTRO_FILE, ASIGNACIONES_LOG_FILE, HEARTBEAT_URL, SYNC_URL
import select
import sys
import threading
import time
import uuid

# Configuración para el latido y sincronización
INTERVALO_LATIDO = 2.0  # segundos entre cada latido (heartbeat)
INTERVALO_SINC = 10.0   # intervalo de sincronización de estado


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
        self.detenido = False

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
    
    def enviar_estado_para_sincronizacion(self):
        """Prepara y envía el estado actual del servidor para sincronización con el backup."""
        try:
            # Convertir objetos Aula a diccionarios para poder serializarlos
            aulas_dict = {}
            for aula_id, aula in self.aulas.items():
                aulas_dict[aula_id] = {
                    "id": aula.id,
                    "tipo": aula.tipo.value,
                    "estado": aula.estado.value,
                    "capacidad": aula.capacidad,
                    "facultad": aula.facultad,
                    "programa": aula.programa,
                    "fecha_solicitud": aula.fecha_solicitud,
                    "fecha_asignacion": aula.fecha_asignacion
                }
            
            return {"aulas": aulas_dict}
        except Exception as e:
            logging.error(f"Error preparando estado para sincronización: {e}")
            return {"error": str(e)}

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

def iniciar_latidos(contexto):
    """Inicia el servicio de latidos (heartbeat) para indicar que el servidor está vivo."""
    try:
        socket = contexto.socket(zmq.PUB)
        socket.bind(HEARTBEAT_URL)
        
        logging.info(f"Servicio de latidos iniciado en {HEARTBEAT_URL}")
        print(f"💓 Servicio de latidos iniciado en {HEARTBEAT_URL}")
        
        # Enviar latidos periódicamente
        while True:
            socket.send_string(f"LATIDO {datetime.now().isoformat()}")
            time.sleep(INTERVALO_LATIDO)
    except Exception as e:
        logging.error(f"Error en servicio de latidos: {e}")

def iniciar_sincronizacion(contexto, servidor):
    """Inicia el servicio de sincronización de estado con el servidor de respaldo."""
    try:
        socket = contexto.socket(zmq.PUB)
        socket.bind(SYNC_URL)
        
        logging.info(f"Servicio de sincronización iniciado en {SYNC_URL}")
        print(f"🔄 Servicio de sincronización iniciado en {SYNC_URL}")
        
        # Enviar estado periódicamente
        while not servidor.detenido:
            estado = servidor.enviar_estado_para_sincronizacion()
            socket.send_string(json.dumps(estado))
            time.sleep(INTERVALO_SINC)
    except Exception as e:
        logging.error(f"Error en servicio de sincronización: {e}")

def main():
    """Función principal del servidor DTI - Implementado como Worker en el patrón Load Balancing Broker."""
    print("✅ Iniciando Servidor Central (DTI) como Worker...")
    
    contexto = zmq.Context()
    servidor = ServidorDTI()
    
    # Iniciar servicios de tolerancia a fallos
    threading.Thread(target=iniciar_latidos, args=(contexto,), daemon=True).start()
    threading.Thread(target=iniciar_sincronizacion, args=(contexto, servidor), daemon=True).start()
    
    # Socket para comunicarse con el broker
    socket = contexto.socket(zmq.DEALER)
    
    # Crear una identidad única para este worker
    worker_id = str(uuid.uuid4()).encode()
    socket.setsockopt(zmq.IDENTITY, worker_id)
    
    # Conectar con el broker (backend)
    socket.connect(BROKER_BACKEND_URL)
    
    print(f"📡 Conectado como Worker al broker en {BROKER_BACKEND_URL}")
    print(f"🆔 ID del Worker: {worker_id.decode()}")
    print("✨ Servidor DTI listo para procesar solicitudes")
    print("💡 Escriba 'limpiar' para reiniciar el sistema")
    
    # Enviar mensaje inicial para registrarse con el broker
    socket.send(b"READY")
    
    def procesar_solicitud(client_id, mensaje):
        """Procesa una solicitud y envía la respuesta de vuelta al broker."""
        try:
            solicitud = json.loads(mensaje)
            print(f"\nSolicitud recibida de {solicitud.get('facultad', 'desconocido')}: {mensaje}")
            
            # Procesar la solicitud
            respuesta = servidor.asignar_aulas(solicitud)
            
            # Mostrar estadísticas
            estadisticas = servidor.obtener_estadisticas()
            print("\nEstadísticas actuales:")
            print(json.dumps(estadisticas, indent=2))
            
            # Enviar respuesta al broker
            socket.send_multipart([
                b"",              # Empty frame
                client_id,        # Client ID
                b"",              # Empty delimiter
                json.dumps(respuesta).encode("utf-8")  # Response
            ])
            
            logging.info(f"Respuesta enviada a facultad: {solicitud.get('facultad')}")
            
        except Exception as e:
            error_msg = f"Error procesando solicitud: {e}"
            logging.error(error_msg)
            # Enviar mensaje de error
            socket.send_multipart([
                b"",              # Empty frame
                client_id,        # Client ID
                b"",              # Empty delimiter
                json.dumps({"error": str(e)}).encode("utf-8")
            ])
    
    try:
        while True:
            # Verificar si hay comando en la entrada estándar
            if select.select([sys.stdin], [], [], 0.0)[0]:
                comando = input().strip().lower()
                if comando == "limpiar":
                    limpiar_sistema(servidor)
                    continue
                elif comando == "salir":
                    break
            
            # Verificar si hay mensajes del broker con un timeout corto
            try:
                if socket.poll(100) == zmq.POLLIN:
                    # Recibir mensaje del broker
                    frames = socket.recv_multipart()
                    if len(frames) >= 4:
                        empty = frames[0]      # Should be empty
                        client_id = frames[1]  # ID of client
                        delimiter = frames[2]  # Should be empty
                        request = frames[3]    # Request data
                        
                        # Procesar en un hilo separado
                        t = threading.Thread(target=procesar_solicitud, args=(client_id, request.decode("utf-8")))
                        t.start()
                    else:
                        # Recibimos un mensaje que no entendemos, responder como READY
                        socket.send(b"READY")
            except zmq.ZMQError as e:
                logging.error(f"Error ZMQ: {e}")
                time.sleep(0.1)  # Pequeña pausa para evitar saturar la CPU
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor DTI...")
    finally:
        servidor.detenido = True
        socket.close()
        contexto.term()


if __name__ == "__main__":
    main()