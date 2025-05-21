"""
DTI_servidor_backup.py - Servidor de Respaldo del Sistema de Asignación de Aulas

Este módulo implementa un servidor de respaldo para el sistema de asignación de aulas.
Monitorea el servidor central (DTI) mediante un mecanismo de latidos (heartbeats) y asume su
rol automáticamente en caso de detectar un fallo.

Características principales:
- Monitoreo continuo del servidor central mediante latidos
- Detección de fallos y activación automática como servidor principal
- Sincronización de estado con el servidor principal
- Registro en el Load Balancing Broker al activarse
- Persistencia de datos sincronizados en formato CSV

"""

import zmq
import json
import logging
import threading
import time
import uuid
import os
import sys
import select
from datetime import datetime
import csv
from dataclasses import dataclass, asdict
from enum import Enum

# Importar las mismas definiciones que el servidor principal
from DTI_servidor import Aula, TipoAula, EstadoAula, ServidorDTI, limpiar_sistema
from config import BROKER_BACKEND_URL, AULAS_REGISTRO_FILE, ASIGNACIONES_LOG_FILE
from config import HEARTBEAT_URL, SYNC_URL, RESPALDO_ESTADO_ARCHIVO

# Configuración para el latido y sincronización
INTERVALO_LATIDO = 2.0    # segundos entre cada latido (heartbeat)
TIMEOUT_LATIDO = 5.0      # tiempo máximo de espera antes de asumir fallo
INTERVALO_SINC = 10.0     # intervalo de sincronización de estado

class ServidorDTIRespaldo:
    """Implementación del servidor de respaldo para el DTI."""
    
    def __init__(self):
        """Inicializa el servidor de respaldo."""
        self.contexto = zmq.Context()
        self.servidor_activo = False  # Inicialmente no está activo
        self.servidor_principal_vivo = True
        self.ultimo_latido = time.time()
        self.servidor = None  # Instancia de ServidorDTI cuando se active
        
        # Control de peticiones concurrentes
        self.active_requests = 0  # Contador de solicitudes activas
        self.active_requests_lock = threading.Lock()  # Lock para modificar el contador
        self.max_concurrent_requests = 10  # Máximo número de solicitudes concurrentes
        self.request_semaphore = threading.Semaphore(self.max_concurrent_requests)  # Semáforo para limitar solicitudes
        
        # Configurar logging
        self.configurar_registro()
        
        # Cargar el estado persistente si existe
        self.cargar_estado_respaldo()
        
    def configurar_registro(self):
        """Configura el sistema de registro para el servidor de respaldo."""
        logging.basicConfig(
            filename="servidor_respaldo.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Mostrar logs tanto en archivo como en consola para facilitar la depuración
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)  # Solo advertencias y errores en consola
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        logging.info("Servidor de respaldo iniciado - v1.1")
        logging.info(f"URLs configuradas - Heartbeat: {HEARTBEAT_URL}, Sync: {SYNC_URL}, Broker: {BROKER_BACKEND_URL}")
        
    def cargar_estado_respaldo(self):
        """Carga el estado desde el archivo de respaldo si existe."""
        try:
            self.estado_respaldo = {"aulas": {}}
            
            if os.path.exists(RESPALDO_ESTADO_ARCHIVO):
                with open(RESPALDO_ESTADO_ARCHIVO, 'r', encoding='utf-8') as archivo:
                    lector = csv.reader(archivo)
                    encabezados = next(lector, None)  # Leer encabezados
                    
                    if encabezados and len(encabezados) >= 8:  # Verificar que hay suficientes columnas
                        for fila in lector:
                            if len(fila) >= 8:
                                aula_id = fila[0]
                                self.estado_respaldo["aulas"][aula_id] = {
                                    "id": fila[0],
                                    "tipo": fila[1],
                                    "estado": fila[2],
                                    "capacidad": int(fila[3]) if fila[3].isdigit() else 0,
                                    "facultad": fila[4],
                                    "programa": fila[5],
                                    "fecha_solicitud": fila[6],
                                    "fecha_asignacion": fila[7]
                                }
                
                logging.info(f"Estado de respaldo cargado: {len(self.estado_respaldo['aulas'])} aulas")
            else:
                logging.info("No se encontró archivo de estado de respaldo, se inicializó uno nuevo")
        except Exception as e:
            logging.error(f"Error al cargar estado de respaldo: {e}")
            self.estado_respaldo = {"aulas": {}}
            
    def guardar_estado_respaldo(self):
        """Guarda el estado actual en el archivo de respaldo."""
        try:
            if self.servidor:
                with open(RESPALDO_ESTADO_ARCHIVO, 'w', newline='', encoding='utf-8') as archivo:
                    escritor = csv.writer(archivo)
                    escritor.writerow(['id', 'tipo', 'estado', 'capacidad', 'facultad', 
                                       'programa', 'fecha_solicitud', 'fecha_asignacion'])
                    
                    for aula_id, aula in self.servidor.aulas.items():
                        escritor.writerow([
                            aula.id, aula.tipo.value, aula.estado.value, aula.capacidad,
                            aula.facultad, aula.programa, aula.fecha_solicitud, 
                            aula.fecha_asignacion
                        ])
                        
                logging.info("Estado de respaldo guardado")
        except Exception as e:
            logging.error(f"Error al guardar estado de respaldo: {e}")
    
    def iniciar_monitor_latidos(self):
        """Inicia el monitoreo de latidos (heartbeat) del servidor principal."""
        socket = self.contexto.socket(zmq.SUB)
        socket.connect(HEARTBEAT_URL)
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        logging.info(f"Monitoreo de latidos iniciado en {HEARTBEAT_URL}")
        print(f"📡 Monitoreo de latidos iniciado en {HEARTBEAT_URL}")
        
        while True:
            try:
                # Verificar si hay un latido con timeout
                if socket.poll(int(TIMEOUT_LATIDO * 1000)) == zmq.POLLIN:
                    mensaje = socket.recv_string()
                    self.ultimo_latido = time.time()
                    if not self.servidor_principal_vivo:
                        logging.info("Servidor principal restaurado")
                        print("✅ Servidor principal restaurado")
                        self.servidor_principal_vivo = True
                else:
                    # No se recibió latido dentro del tiempo de espera
                    if self.servidor_principal_vivo:
                        logging.warning("Servidor principal no responde")
                        print("❌ Servidor principal no responde")
                        self.servidor_principal_vivo = False
                        # Activar este servidor como principal
                        if not self.servidor_activo:
                            self.activar_servidor()
            except Exception as e:
                logging.error(f"Error en monitor de latidos: {e}")
                time.sleep(1)  # Evitar bucle rápido en caso de error
    
    def iniciar_receptor_sincronizacion(self):
        """Inicia el receptor para sincronización de estado desde el servidor principal."""
        socket = self.contexto.socket(zmq.SUB)
        socket.connect(SYNC_URL)
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        logging.info(f"Receptor de sincronización iniciado en {SYNC_URL}")
        print(f"📡 Receptor de sincronización iniciado en {SYNC_URL}")
        
        while True:
            try:
                if socket.poll(1000) == zmq.POLLIN:
                    mensaje = socket.recv_string()
                    # Procesar el mensaje de sincronización
                    self.procesar_mensaje_sinc(mensaje)
            except Exception as e:
                logging.error(f"Error en receptor de sincronización: {e}")
                time.sleep(1)
    
    def procesar_mensaje_sinc(self, mensaje):
        """Procesa un mensaje de sincronización del servidor principal."""
        try:
            datos_sinc = json.loads(mensaje)
            self.estado_respaldo = datos_sinc
            logging.info("Estado sincronizado con servidor principal")
            
            # Si estamos activos, actualizar el estado del servidor
            if self.servidor_activo and self.servidor:
                self.actualizar_estado_servidor()
                
            # Guardar el estado sincronizado como CSV
            self.guardar_estado_respaldo_desde_json()
        except Exception as e:
            logging.error(f"Error procesando mensaje de sincronización: {e}")
    
    def guardar_estado_respaldo_desde_json(self):
        """Guarda el estado recibido en JSON como archivo CSV."""
        try:
            if 'aulas' in self.estado_respaldo:
                with open(RESPALDO_ESTADO_ARCHIVO, 'w', newline='', encoding='utf-8') as archivo:
                    escritor = csv.writer(archivo)
                    escritor.writerow(['id', 'tipo', 'estado', 'capacidad', 'facultad', 
                                      'programa', 'fecha_solicitud', 'fecha_asignacion'])
                    
                    for aula_id, aula_dict in self.estado_respaldo['aulas'].items():
                        escritor.writerow([
                            aula_dict['id'], 
                            aula_dict['tipo'], 
                            aula_dict['estado'],
                            aula_dict['capacidad'],
                            aula_dict['facultad'],
                            aula_dict['programa'],
                            aula_dict['fecha_solicitud'],
                            aula_dict['fecha_asignacion']
                        ])
        except Exception as e:
            logging.error(f"Error guardando estado JSON como CSV: {e}")
    
    def actualizar_estado_servidor(self):
        """Actualiza el estado del servidor con los datos sincronizados."""
        try:
            if not self.servidor or not self.servidor_activo:
                return
                
            # Actualizar aulas desde el estado sincronizado
            if 'aulas' in self.estado_respaldo:
                for aula_id, aula_dict in self.estado_respaldo['aulas'].items():
                    if aula_id in self.servidor.aulas:
                        # Actualizar aula existente
                        aula = self.servidor.aulas[aula_id]
                        aula.tipo = TipoAula(aula_dict['tipo'])
                        aula.estado = EstadoAula(aula_dict['estado'])
                        aula.capacidad = aula_dict['capacidad']
                        aula.facultad = aula_dict['facultad']
                        aula.programa = aula_dict['programa']
                        aula.fecha_solicitud = aula_dict['fecha_solicitud']
                        aula.fecha_asignacion = aula_dict['fecha_asignacion']
                    else:
                        # Crear nueva aula
                        self.servidor.aulas[aula_id] = Aula(
                            id=aula_dict['id'],
                            tipo=TipoAula(aula_dict['tipo']),
                            estado=EstadoAula(aula_dict['estado']),
                            capacidad=aula_dict['capacidad'],
                            facultad=aula_dict['facultad'],
                            programa=aula_dict['programa'],
                            fecha_solicitud=aula_dict['fecha_solicitud'],
                            fecha_asignacion=aula_dict['fecha_asignacion']
                        )
                        
            # Guardar el estado actualizado
            self.servidor.guardar_aulas()
            logging.info("Estado del servidor actualizado con datos sincronizados")
        except Exception as e:
            logging.error(f"Error actualizando estado del servidor: {e}")
    
    def activar_servidor(self):
        """Activa este servidor como principal en caso de fallo."""
        try:
            logging.info("¡ACTIVANDO SERVIDOR DE RESPALDO!")
            print("\n⚠️ ¡ALERTA! Servidor principal caído. Activando servidor de respaldo...")
            
            # Crear la instancia de ServidorDTI
            self.servidor = ServidorDTI()
            
            # Actualizar con el estado sincronizado si está disponible
            self.actualizar_estado_servidor()
            
            # Activar el servidor para recibir solicitudes
            self.servidor_activo = True
            
            # Registrarse como worker en el broker - esto es crítico para la tolerancia a fallos
            logging.info("Registrando servidor de respaldo en el broker")
            print("🔄 Registrando servidor de respaldo en el broker...")
            self.registrar_en_broker()
            print("✅ Servidor de respaldo completamente activado y operativo")
            logging.info("Servidor de respaldo activado correctamente")
            print("✅ Servidor de respaldo activado correctamente")
        except Exception as e:
            logging.error(f"Error activando servidor de respaldo: {e}")
            print(f"❌ Error activando servidor de respaldo: {e}")
    
    def registrar_en_broker(self):
        """Registra este servidor como worker en el Load Balancing Broker."""
        try:
            socket = self.contexto.socket(zmq.DEALER)
            # Crear una identidad única para este worker
            id_worker = str(uuid.uuid4()).encode()
            socket.setsockopt(zmq.IDENTITY, id_worker)
            
            # Conectar con el broker (backend)
            socket.connect(BROKER_BACKEND_URL)
            
            logging.info(f"Conectando al broker como worker en {BROKER_BACKEND_URL}")
            print(f"📡 Conectando al broker como worker en {BROKER_BACKEND_URL}")
            print(f"🆔 ID del Worker (respaldo): {id_worker.decode()}")
            
            # Ya no enviamos el READY aquí, lo haremos en el hilo worker
            # para asegurarnos de que el hilo esté listo para recibir respuestas
            
            # Iniciar hilo para procesar solicitudes
            threading.Thread(target=self.hilo_worker, args=(socket,), daemon=True).start()
            
            logging.info(f"Registrado correctamente en el broker con ID: {id_worker.decode()}")
            print("✅ Registrado correctamente en el broker")
        except Exception as e:
            logging.error(f"Error registrando en broker: {e}")
            print(f"❌ Error registrando en broker: {e}")
    
    def hilo_worker(self, socket):
        """Hilo dedicado a procesar solicitudes como worker."""
        try:
            logging.info("Hilo worker iniciado")
            
            # Enviar mensaje inicial READY para registrarse con el broker
            socket.send(b"READY")
            logging.info("Enviado mensaje READY inicial al broker (registro)")
            print("📡 Worker de respaldo listo para recibir solicitudes")
            
            # Lista para hacer seguimiento a hilos activos
            processing_threads = []
            last_status_report = time.time()
            status_report_interval = 5  # Segundos entre reportes de estado

            while self.servidor_activo:
                try:
                    # Solo aceptar nuevas solicitudes si hay un semáforo disponible
                    can_accept_more = self.request_semaphore.acquire(blocking=False)
                    
                    # Verificar si hay mensajes del broker solo si podemos aceptar más
                    if can_accept_more and socket.poll(100) == zmq.POLLIN:
                        # Recibir mensaje del broker
                        frames = socket.recv_multipart()
                        if len(frames) >= 4:
                            vacio = frames[0]      # Should be empty
                            id_cliente = frames[1]  # ID of client
                            delimitador = frames[2]  # Should be empty
                            peticion = frames[3]    # Request data
                            
                            # Incrementar contador de solicitudes activas
                            with self.active_requests_lock:
                                self.active_requests += 1
                                
                            logging.info(f"Recibida solicitud, tamaño de frames: {len(frames)}")
                            logging.info(f"Solicitudes activas: {self.active_requests}")
                            
                            # Procesar solicitud en un nuevo hilo
                            t = threading.Thread(
                                target=self.procesar_solicitud_con_tracking, 
                                args=(socket, id_cliente, peticion.decode("utf-8"))
                            )
                            t.daemon = True
                            t.start()
                            
                            # Limpiar la lista de hilos terminados
                            processing_threads = [thread for thread in processing_threads if thread.is_alive()]
                            processing_threads.append(t)
                        else:
                            # Recibimos un mensaje que no entendemos
                            logging.warning(f"Recibido mensaje con formato inválido, frames: {len(frames)}")
                except zmq.ZMQError as e:
                    logging.error(f"Error ZMQ en hilo worker: {e}")
                    time.sleep(0.1)  # Pequeña pausa
                
                # Verificar comandos de consola
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    comando = input().strip().lower()
                    if comando == "limpiar" and self.servidor:
                        limpiar_sistema(self.servidor)
                        self.guardar_estado_respaldo()
                    elif comando == "salir":
                        break
                    elif comando == "status" or comando == "estado":
                        print(f"ℹ️ Servidor de respaldo - Solicitudes activas: {self.active_requests}")
                
                # Si hemos adquirido un semáforo pero no había mensajes, liberarlo
                if can_accept_more and not socket.poll(0) == zmq.POLLIN:
                    self.request_semaphore.release()
                
                # Mostrar estado periódicamente en el log
                if time.time() - last_status_report > status_report_interval:
                    with self.active_requests_lock:
                        logging.info(f"Estado del servidor: {self.active_requests} solicitudes activas, " + 
                                    f"{len(processing_threads)} hilos de procesamiento")
                    last_status_report = time.time()
                
                # Small sleep to prevent tight loop
                time.sleep(0.01)
                        
            # Actualizar estado de respaldo antes de salir
            if self.servidor:
                self.guardar_estado_respaldo()
                    
        except Exception as e:
            logging.error(f"Error en hilo worker: {e}")
    
    def procesar_solicitud_con_tracking(self, socket, id_cliente, mensaje):
        """Procesa una solicitud con seguimiento del estado."""
        request_id = str(uuid.uuid4())[:8]  # ID corto para seguimiento
        logging.info(f"Iniciando procesamiento de solicitud {request_id}")
        try:
            self.procesar_solicitud(socket, id_cliente, mensaje, request_id)
        except Exception as e:
            logging.error(f"Error no capturado en solicitud {request_id}: {e}")
            # Intentar enviar error al cliente
            try:
                self._enviar_error(socket, id_cliente, f"Error interno: {str(e)}")
            except:
                logging.error(f"No se pudo enviar mensaje de error para solicitud {request_id}")
        finally:
            # Siempre liberar recursos cuando terminamos
            with self.active_requests_lock:
                self.active_requests -= 1
                logging.info(f"Solicitud {request_id} completada. Solicitudes activas restantes: {self.active_requests}")
            
            # Liberar el semáforo
            self.request_semaphore.release()
    
    def procesar_solicitud(self, socket, id_cliente, mensaje, request_id=''):
        """Procesa una solicitud y envía la respuesta de vuelta al broker."""
        if not self.servidor_activo or not self.servidor:
            logging.warning(f"[{request_id}] Intento de procesar solicitud con servidor inactivo")
            return
            
        try:
            solicitud = json.loads(mensaje)
            facultad = solicitud.get('facultad', 'desconocido')
            programa = solicitud.get('programa', 'desconocido')
            
            logging.info(f"[{request_id}] Procesando solicitud de {facultad} - {programa}")
            print(f"\n📩 Solicitud [{request_id}] de {facultad} - {programa}")
            
            # Medir el tiempo de procesamiento
            inicio = time.time()
            
            # Procesar la solicitud con tiempo límite (evitar procesamiento infinito)
            respuesta = self.servidor.asignar_aulas(solicitud)
            
            # Calcular tiempo de procesamiento
            tiempo_proc = time.time() - inicio
            
            # Mostrar estadísticas
            estadisticas = self.servidor.obtener_estadisticas()
            print(f"\n📊 Estadísticas [{request_id}] tras asignar aulas a {facultad} - {programa}")
            print(json.dumps(estadisticas, indent=2))
            
            # Enviar respuesta al broker
            socket.send_multipart([
                b"",              # Empty frame
                id_cliente,        # Client ID
                b"",              # Empty delimiter
                json.dumps(respuesta).encode("utf-8")  # Response
            ])
            
            logging.info(f"[{request_id}] Respuesta enviada a {facultad} - {programa} (procesado en {tiempo_proc:.2f}s)")
            print(f"✅ Respuesta [{request_id}] enviada a {facultad} - {programa}")
            
            # Guardar el estado actualizado
            self.guardar_estado_respaldo()
            
            # Enviar READY para indicar que estamos listos para una nueva solicitud
            socket.send_multipart([b"READY"])
            logging.info("Solicitud procesada completamente. Enviado mensaje READY al broker.")
            
        except json.JSONDecodeError:
            logging.error(f"[{request_id}] Error al decodificar JSON de la solicitud")
            self._enviar_error(socket, id_cliente, "Formato de solicitud inválido", request_id)
        except KeyError as e:
            logging.error(f"[{request_id}] Falta campo requerido en la solicitud: {e}")
            self._enviar_error(socket, id_cliente, f"Falta campo requerido: {e}", request_id)
        except Exception as e:
            mensaje_error = f"Error procesando solicitud: {str(e)}"
            logging.error(f"[{request_id}] {mensaje_error}")
            self._enviar_error(socket, id_cliente, mensaje_error, request_id)
            
    def _enviar_error(self, socket, id_cliente, mensaje_error, request_id=''):
        """Envía un mensaje de error al cliente y marca el worker como disponible."""
        try:
            # Enviar mensaje de error
            socket.send_multipart([
                b"",              # Empty frame
                id_cliente,        # Client ID
                b"",              # Empty delimiter
                json.dumps({"error": mensaje_error}).encode("utf-8")
            ])
            logging.info(f"[{request_id}] Mensaje de error enviado al cliente: {mensaje_error}")
            
            # Enviar READY para seguir recibiendo solicitudes
            socket.send_multipart([b"READY"])
            logging.info(f"[{request_id}] Error manejado. Enviado mensaje READY al broker.")
        except Exception as e:
            logging.error(f"[{request_id}] Error al enviar mensaje de error: {e}")
            # Último intento de enviar READY
            try:
                socket.send_multipart([b"READY"])
            except:
                logging.error(f"[{request_id}] No se pudo enviar READY después de error")
                
    def reportar_estado(self):
        """Genera un reporte del estado actual del servidor."""
        if not self.servidor_activo:
            estado = "inactivo (en espera)"
        else:
            estado = "activo"
            
        with self.active_requests_lock:
            solicitudes = self.active_requests
            
        reporte = {
            "estado": estado,
            "solicitudes_activas": solicitudes,
            "semaforo_disponible": self.request_semaphore._value,
            "capacidad_maxima": self.max_concurrent_requests,
            "ultimo_latido": time.time() - self.ultimo_latido
        }
        
        return reporte
    
    def iniciar(self):
        """Inicia el servidor de respaldo."""
        print("✅ Iniciando Servidor de Respaldo DTI...")
        print("📡 Modo escucha: esperando señales del servidor principal")
        
        # Iniciar el hilo de monitoreo de latidos
        threading.Thread(target=self.iniciar_monitor_latidos, daemon=True).start()
        
        # Iniciar el hilo de sincronización
        threading.Thread(target=self.iniciar_receptor_sincronizacion, daemon=True).start()
        
        print("💡 Servidor de respaldo listo y monitoreando servidor principal")
        print("💡 Estado: En espera (se activará automáticamente si falla el servidor principal)")
        print("💡 Escriba 'limpiar' para reiniciar el sistema o 'salir' para terminar")
        
        # Loop principal para comandos
        try:
            while True:
                comando = input().strip().lower()
                if comando == "salir":
                    break
                elif comando == "limpiar" and self.servidor_activo and self.servidor:
                    limpiar_sistema(self.servidor)
                    self.guardar_estado_respaldo()
                elif comando == "status" or comando == "estado":
                    estado = self.reportar_estado()
                    print("\n📊 Estado del servidor de respaldo:")
                    print(json.dumps(estado, indent=2))
                    print(f"Servidor {'✅ ACTIVO' if self.servidor_activo else '⏸️ EN ESPERA'}")
                    if self.servidor_activo:
                        print(f"Solicitudes activas: {estado['solicitudes_activas']}/{estado['capacidad_maxima']}")
                        print(f"Semáforo disponible: {estado['semaforo_disponible']}")
                    print(f"Último latido hace: {estado['ultimo_latido']:.1f} segundos")
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servidor de respaldo...")
        finally:
            self.contexto.term()
            logging.info("Servidor de respaldo detenido")


if __name__ == "__main__":
    servidor_respaldo = ServidorDTIRespaldo()
    servidor_respaldo.iniciar()
