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

Autor: [Tu nombre]
Fecha: [Fecha de última modificación]
"""

import zmq  # Para comunicación distribuida
import json  # Para serialización de datos
import logging  # Para registro de eventos
from datetime import datetime
import csv  # Para manejo de archivos de datos
from dataclasses import dataclass
from enum import Enum
import os
import select
import sys
from config import DTI_URL, AULAS_REGISTRO_FILE, ASIGNACIONES_LOG_FILE

# =============================================================================
# Definiciones de clases y enumeraciones
# =============================================================================

class TipoAula(Enum):
    """
    Define los tipos de aulas disponibles en el sistema.
    
    Valores:
        SALON: Aula regular para clases teóricas
        LABORATORIO: Espacio equipado para prácticas
        AULA_MOVIL: Salón convertible en laboratorio
    """
    SALON = "salón"
    LABORATORIO = "laboratorio"
    AULA_MOVIL = "aula móvil"

class EstadoAula(Enum):
    """
    Define los estados posibles de un aula.
    
    Valores:
        DISPONIBLE: Aula libre para asignación
        ASIGNADA: Aula ocupada por una facultad/programa
    """
    DISPONIBLE = "disponible"
    ASIGNADA = "asignada"

@dataclass
class Aula:
    """
    Representa un aula en el sistema con sus atributos.
    
    Atributos:
        id (str): Identificador único del aula
        tipo (TipoAula): Tipo de aula (salón/laboratorio/móvil)
        estado (EstadoAula): Estado actual del aula
        capacidad (int): Número de estudiantes que puede albergar
        facultad (str): Facultad a la que está asignada (si aplica)
        programa (str): Programa académico asignado (si aplica)
        fecha_solicitud (str): Fecha de la solicitud de asignación
        fecha_asignacion (str): Fecha en que se realizó la asignación
    """
    id: str
    tipo: TipoAula
    estado: EstadoAula
    capacidad: int
    facultad: str = ""
    programa: str = ""
    fecha_solicitud: str = ""
    fecha_asignacion: str = ""

class ServidorDTI:
    """
    Clase principal que implementa la lógica del servidor DTI.
    
    Esta clase maneja:
    - Carga y guardado de datos de aulas
    - Procesamiento de solicitudes de asignación
    - Generación de estadísticas
    - Registro de operaciones
    """

    def __init__(self):
        """
        Inicializa el servidor DTI, cargando la configuración inicial
        y los datos de las aulas desde el archivo de registro.
        """
        self.aulas = {}
        self.configurar_registro()
        self.cargar_aulas()

    def configurar_registro(self):
        """
        Configura el sistema de registro de eventos.
        
        Establece el formato de log, nivel de detalle y archivo de salida
        para el seguimiento de operaciones del sistema.
        """
        logging.basicConfig(
            filename=ASIGNACIONES_LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def cargar_aulas(self):
        """
        Carga los datos de las aulas desde el archivo CSV de registro.
        
        Lee el archivo AULAS_REGISTRO_FILE y crea objetos Aula
        para cada registro encontrado.
        
        Raises:
            Exception: Si hay error al leer o procesar el archivo
        """
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
        """
        Procesa una solicitud de asignación de aulas.
        
        Args:
            solicitud (dict): Diccionario con los datos de la solicitud:
                - facultad: nombre de la facultad solicitante
                - programa: nombre del programa académico
                - salones: número de salones requeridos
                - laboratorios: número de laboratorios requeridos
                - semestre: semestre para el que se solicita
        
        Returns:
            dict: Respuesta con las asignaciones realizadas:
                - salones_asignados: lista de IDs de salones asignados
                - laboratorios_asignados: lista de IDs de laboratorios asignados
                - notificacion: mensaje sobre aulas móviles (si aplica)
        """
        try:
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
        """
        Genera un reporte de estadísticas del uso de aulas.
        
        Returns:
            dict: Estadísticas actuales del sistema:
                - total_salones: número total de salones
                - total_laboratorios: número total de laboratorios
                - total_aulas_moviles: número de aulas móviles
                - salones_disponibles: salones sin asignar
                - laboratorios_disponibles: laboratorios sin asignar
                - aulas_moviles_en_uso: aulas móviles asignadas
        """
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

def limpiar_sistema(servidor: ServidorDTI):
    """
    Reinicia el sistema a su estado inicial.
    
    Esta función:
    1. Libera todas las aulas asignadas
    2. Convierte aulas móviles de vuelta a salones
    3. Limpia el archivo de logs
    4. Muestra estadísticas actualizadas
    
    Args:
        servidor (ServidorDTI): Instancia del servidor a limpiar
    """
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
    """
    Punto de entrada principal del servidor DTI.
    
    Implementa el bucle principal del servidor que:
    1. Inicializa el socket ZMQ para comunicación
    2. Procesa solicitudes de facultades
    3. Maneja el comando de limpieza
    4. Mantiene estadísticas actualizadas
    
    El servidor puede detenerse con Ctrl+C.
    """
    print("✅ Iniciando Servidor Central (DTI)...")
    
    contexto = zmq.Context()
    servidor = ServidorDTI()
    
    # Socket para recibir solicitudes de las facultades
    socket = contexto.socket(zmq.REP)
    socket.bind(DTI_URL)
    
    print(f"📡 Escuchando solicitudes en {DTI_URL}")
    print("✨ Servidor DTI listo para procesar solicitudes")
    print("💡 Escriba 'limpiar' para reiniciar el sistema")
    
    try:
        while True:
            # Verificar si hay comando en la entrada estándar
            if select.select([sys.stdin], [], [], 0.0)[0]:
                comando = input().strip().lower()
                if comando == "limpiar":
                    limpiar_sistema(servidor)
                    continue

            try:
                # Esperar mensaje con timeout para poder revisar la entrada estándar
                if socket.poll(100) == zmq.POLLIN:
                    mensaje = socket.recv_string()
                    solicitud = json.loads(mensaje)
                    
                    logging.info(f"Solicitud recibida de facultad: {solicitud.get('facultad')}")
                    
                    # Procesar solicitud
                    respuesta = servidor.asignar_aulas(solicitud)
                    
                    # Enviar respuesta
                    socket.send_string(json.dumps(respuesta))
                    
                    # Mostrar estadísticas
                    estadisticas = servidor.obtener_estadisticas()
                    print("\nEstadísticas actuales:")
                    print(json.dumps(estadisticas, indent=2))
                    
                    logging.info(f"Respuesta enviada a facultad: {solicitud.get('facultad')}")
            
            except Exception as e:
                logging.error(f"Error procesando solicitud: {e}")
                if socket.poll(100) == zmq.POLLIN:
                    socket.send_string(json.dumps({"error": str(e)}))
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor DTI...")
    finally:
        socket.close()
        contexto.term()


if __name__ == "__main__":
    main()