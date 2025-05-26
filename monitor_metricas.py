"""
monitor_metricas.py - Sistema de Monitoreo de Métricas de Tiempo de Respuesta

Este módulo implementa la recolección y análisis de métricas de tiempo de respuesta
para el sistema de asignación de aulas. Registra todas las métricas en un archivo .txt
para análisis histórico.

Métricas recolectadas:
- Tiempo de respuesta promedio del servidor a las facultades
- Tiempo de respuesta mínimo y máximo del servidor a las facultades  
- Tiempo promedio desde solicitud hasta atención de programas académicos
"""

import time
import threading
from datetime import datetime
from collections import defaultdict, deque
import json
import os

class MonitorMetricas:
    def __init__(self, archivo_metricas="metricas_sistema.txt"):
        """
        Inicializa el monitor de métricas.
        
        Args:
            archivo_metricas (str): Nombre del archivo donde se guardarán las métricas
        """
        self.archivo_metricas = archivo_metricas
        self.lock = threading.Lock()
        
        # Almacenamiento de tiempos de respuesta servidor-facultad
        self.tiempos_servidor_facultad = deque(maxlen=1000)  # Últimas 1000 mediciones
        
        # Almacenamiento de tiempos programa-atención
        self.tiempos_programa_atencion = deque(maxlen=1000)  # Últimas 1000 mediciones
        
        # Diccionario para rastrear solicitudes en progreso
        self.solicitudes_en_progreso = {}
        
        # Contadores para estadísticas
        self.total_solicitudes_procesadas = 0
        self.total_respuestas_enviadas = 0
        
        # Inicializar archivo de métricas si no existe
        self._inicializar_archivo_metricas()
    
    def _inicializar_archivo_metricas(self):
        """Inicializa el archivo de métricas con encabezados si no existe."""
        if not os.path.exists(self.archivo_metricas):
            with open(self.archivo_metricas, 'w', encoding='utf-8') as archivo:
                archivo.write("=== SISTEMA DE MONITOREO DE MÉTRICAS DE TIEMPO DE RESPUESTA ===\n")
                archivo.write(f"Archivo creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                archivo.write("=" * 70 + "\n\n")
    
    def registrar_inicio_solicitud_programa(self, id_solicitud, facultad, programa):
        """
        Registra el inicio de una solicitud de programa académico.
        
        Args:
            id_solicitud (str): Identificador único de la solicitud
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
        """
        with self.lock:
            tiempo_inicio = time.time()
            self.solicitudes_en_progreso[id_solicitud] = {
                'tiempo_inicio': tiempo_inicio,
                'facultad': facultad,
                'programa': programa,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def registrar_fin_solicitud_programa(self, id_solicitud):
        """
        Registra el fin de una solicitud de programa académico y calcula el tiempo total.
        
        Args:
            id_solicitud (str): Identificador único de la solicitud
            
        Returns:
            float: Tiempo total de procesamiento en segundos, o None si no se encontró la solicitud
        """
        with self.lock:
            if id_solicitud in self.solicitudes_en_progreso:
                tiempo_fin = time.time()
                solicitud = self.solicitudes_en_progreso.pop(id_solicitud)
                tiempo_total = tiempo_fin - solicitud['tiempo_inicio']
                
                # Almacenar el tiempo de programa-atención
                self.tiempos_programa_atencion.append({
                    'tiempo': tiempo_total,
                    'facultad': solicitud['facultad'],
                    'programa': solicitud['programa'],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                self.total_solicitudes_procesadas += 1
                return tiempo_total
            return None
    
    def registrar_tiempo_respuesta_servidor(self, tiempo_respuesta, facultad, operacion="asignacion"):
        """
        Registra un tiempo de respuesta del servidor a una facultad.
        
        Args:
            tiempo_respuesta (float): Tiempo de respuesta en segundos
            facultad (str): Nombre de la facultad
            operacion (str): Tipo de operación realizada
        """
        with self.lock:
            self.tiempos_servidor_facultad.append({
                'tiempo': tiempo_respuesta,
                'facultad': facultad,
                'operacion': operacion,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            self.total_respuestas_enviadas += 1
    
    def calcular_metricas_servidor_facultad(self):
        """
        Calcula las métricas de tiempo de respuesta servidor-facultad.
        
        Returns:
            dict: Diccionario con tiempo promedio, mínimo y máximo
        """
        with self.lock:
            if not self.tiempos_servidor_facultad:
                return {
                    'tiempo_promedio': 0.0,
                    'tiempo_minimo': 0.0,
                    'tiempo_maximo': 0.0,
                    'total_mediciones': 0
                }
            
            tiempos = [medicion['tiempo'] for medicion in self.tiempos_servidor_facultad]
            
            return {
                'tiempo_promedio': sum(tiempos) / len(tiempos),
                'tiempo_minimo': min(tiempos),
                'tiempo_maximo': max(tiempos),
                'total_mediciones': len(tiempos)
            }
    
    def calcular_metricas_programa_atencion(self):
        """
        Calcula las métricas de tiempo programa-atención.
        
        Returns:
            dict: Diccionario con tiempo promedio y estadísticas adicionales
        """
        with self.lock:
            if not self.tiempos_programa_atencion:
                return {
                    'tiempo_promedio': 0.0,
                    'tiempo_minimo': 0.0,
                    'tiempo_maximo': 0.0,
                    'total_mediciones': 0
                }
            
            tiempos = [medicion['tiempo'] for medicion in self.tiempos_programa_atencion]
            
            return {
                'tiempo_promedio': sum(tiempos) / len(tiempos),
                'tiempo_minimo': min(tiempos),
                'tiempo_maximo': max(tiempos),
                'total_mediciones': len(tiempos)
            }
    
    def generar_reporte_metricas(self):
        """
        Genera un reporte completo de todas las métricas y lo guarda en el archivo.
        
        Returns:
            dict: Diccionario con todas las métricas calculadas
        """
        metricas_servidor = self.calcular_metricas_servidor_facultad()
        metricas_programa = self.calcular_metricas_programa_atencion()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        reporte = {
            'timestamp': timestamp,
            'metricas_servidor_facultad': metricas_servidor,
            'metricas_programa_atencion': metricas_programa,
            'estadisticas_generales': {
                'total_solicitudes_procesadas': self.total_solicitudes_procesadas,
                'total_respuestas_enviadas': self.total_respuestas_enviadas,
                'solicitudes_en_progreso': len(self.solicitudes_en_progreso)
            }
        }
        
        # Escribir reporte al archivo
        self._escribir_reporte_archivo(reporte)
        
        return reporte
    
    def generar_reporte_programa_atencion(self):
        """
        Genera solo el reporte de métricas programa-atención.
        
        Returns:
            dict: Diccionario con las métricas de programa-atención
        """
        metricas_programa = self.calcular_metricas_programa_atencion()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        reporte = {
            'timestamp': timestamp,
            'metricas_programa_atencion': metricas_programa,
            'total_respuestas_enviadas': self.total_respuestas_enviadas
        }
        
        # Escribir solo la sección de programa-atención
        self._escribir_reporte_programa_archivo(reporte)
        
        return reporte
    
    def generar_reporte_servidor_facultad(self, total_solicitudes_broker=None):
        """
        Genera solo el reporte de métricas servidor-facultad.
        
        Args:
            total_solicitudes_broker (int, optional): Total de solicitudes procesadas por el broker
        
        Returns:
            dict: Diccionario con las métricas servidor-facultad
        """
        metricas_servidor = self.calcular_metricas_servidor_facultad()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Usar el contador del broker si se proporciona, sino usar el contador local
        total_solicitudes = total_solicitudes_broker if total_solicitudes_broker is not None else self.total_solicitudes_procesadas
        
        reporte = {
            'timestamp': timestamp,
            'metricas_servidor_facultad': metricas_servidor,
            'total_solicitudes_procesadas': total_solicitudes
        }
        
        # Escribir solo la sección de servidor-facultad
        self._escribir_reporte_servidor_archivo(reporte)
        
        return reporte
    
    def _escribir_reporte_archivo(self, reporte):
        """
        Escribe el reporte de métricas al archivo de texto.
        
        Args:
            reporte (dict): Diccionario con las métricas a escribir
        """
        with open(self.archivo_metricas, 'a', encoding='utf-8') as archivo:
            archivo.write(f"\n--- REPORTE DE MÉTRICAS - {reporte['timestamp']} ---\n")
            
            # Métricas servidor-facultad
            servidor = reporte['metricas_servidor_facultad']
            archivo.write("\n1. MÉTRICAS SERVIDOR → FACULTADES:\n")
            archivo.write(f"   • Tiempo promedio de respuesta: {servidor['tiempo_promedio']:.4f} segundos\n")
            archivo.write(f"   • Tiempo mínimo de respuesta: {servidor['tiempo_minimo']:.4f} segundos\n")
            archivo.write(f"   • Tiempo máximo de respuesta: {servidor['tiempo_maximo']:.4f} segundos\n")
            archivo.write(f"   • Total de mediciones: {servidor['total_mediciones']}\n")
            
            # Métricas programa-atención
            programa = reporte['metricas_programa_atencion']
            archivo.write("\n2. MÉTRICAS PROGRAMA → ATENCIÓN:\n")
            archivo.write(f"   • Tiempo promedio solicitud-atención: {programa['tiempo_promedio']:.4f} segundos\n")
            archivo.write(f"   • Tiempo mínimo solicitud-atención: {programa['tiempo_minimo']:.4f} segundos\n")
            archivo.write(f"   • Tiempo máximo solicitud-atención: {programa['tiempo_maximo']:.4f} segundos\n")
            archivo.write(f"   • Total de mediciones: {programa['total_mediciones']}\n")
            
            # Estadísticas generales
            stats = reporte['estadisticas_generales']
            archivo.write("\n3. ESTADÍSTICAS GENERALES:\n")
            archivo.write(f"   • Total solicitudes procesadas: {stats['total_solicitudes_procesadas']}\n")
            archivo.write(f"   • Total respuestas enviadas: {stats['total_respuestas_enviadas']}\n")
            archivo.write(f"   • Solicitudes en progreso: {stats['solicitudes_en_progreso']}\n")
            
            archivo.write("\n" + "=" * 70 + "\n")
    
    def _escribir_reporte_programa_archivo(self, reporte):
        """
        Escribe solo el reporte de métricas programa-atención al archivo.
        
        Args:
            reporte (dict): Diccionario con las métricas de programa-atención
        """
        with open(self.archivo_metricas, 'a', encoding='utf-8') as archivo:
            archivo.write(f"\n--- REPORTE PROGRAMA-ATENCIÓN - {reporte['timestamp']} ---\n")
            
            # Métricas programa-atención
            programa = reporte['metricas_programa_atencion']
            archivo.write("\n2. MÉTRICAS PROGRAMA → ATENCIÓN:\n")
            archivo.write(f"   • Tiempo promedio solicitud-atención: {programa['tiempo_promedio']:.4f} segundos\n")
            archivo.write(f"   • Tiempo mínimo solicitud-atención: {programa['tiempo_minimo']:.4f} segundos\n")
            archivo.write(f"   • Tiempo máximo solicitud-atención: {programa['tiempo_maximo']:.4f} segundos\n")
            archivo.write(f"   • Total de mediciones: {programa['total_mediciones']}\n")
            archivo.write(f"   • Total respuestas enviadas: {reporte['total_respuestas_enviadas']}\n")
            
            archivo.write("\n" + "=" * 70 + "\n")
    
    def _escribir_reporte_servidor_archivo(self, reporte):
        """
        Escribe solo el reporte de métricas servidor-facultad al archivo.
        
        Args:
            reporte (dict): Diccionario con las métricas servidor-facultad
        """
        with open(self.archivo_metricas, 'a', encoding='utf-8') as archivo:
            archivo.write(f"\n--- REPORTE SERVIDOR-FACULTAD - {reporte['timestamp']} ---\n")
            
            # Métricas servidor-facultad
            servidor = reporte['metricas_servidor_facultad']
            archivo.write("\n1. MÉTRICAS SERVIDOR → FACULTADES:\n")
            archivo.write(f"   • Tiempo promedio de respuesta: {servidor['tiempo_promedio']:.4f} segundos\n")
            archivo.write(f"   • Tiempo mínimo de respuesta: {servidor['tiempo_minimo']:.4f} segundos\n")
            archivo.write(f"   • Tiempo máximo de respuesta: {servidor['tiempo_maximo']:.4f} segundos\n")
            archivo.write(f"   • Total de mediciones: {servidor['total_mediciones']}\n")
            archivo.write(f"   • Total solicitudes procesadas: {reporte['total_solicitudes_procesadas']}\n")
            
            archivo.write("\n" + "=" * 70 + "\n")
    
    def obtener_metricas_detalladas_por_facultad(self):
        """
        Obtiene métricas detalladas agrupadas por facultad.
        
        Returns:
            dict: Métricas organizadas por facultad
        """
        with self.lock:
            metricas_por_facultad = defaultdict(lambda: {
                'tiempos_servidor': [],
                'tiempos_programa': []
            })
            
            # Agrupar tiempos servidor-facultad
            for medicion in self.tiempos_servidor_facultad:
                facultad = medicion['facultad']
                metricas_por_facultad[facultad]['tiempos_servidor'].append(medicion['tiempo'])
            
            # Agrupar tiempos programa-atención
            for medicion in self.tiempos_programa_atencion:
                facultad = medicion['facultad']
                metricas_por_facultad[facultad]['tiempos_programa'].append(medicion['tiempo'])
            
            # Calcular estadísticas por facultad
            resultado = {}
            for facultad, datos in metricas_por_facultad.items():
                resultado[facultad] = {}
                
                if datos['tiempos_servidor']:
                    tiempos_srv = datos['tiempos_servidor']
                    resultado[facultad]['servidor'] = {
                        'promedio': sum(tiempos_srv) / len(tiempos_srv),
                        'minimo': min(tiempos_srv),
                        'maximo': max(tiempos_srv),
                        'mediciones': len(tiempos_srv)
                    }
                
                if datos['tiempos_programa']:
                    tiempos_prog = datos['tiempos_programa']
                    resultado[facultad]['programa'] = {
                        'promedio': sum(tiempos_prog) / len(tiempos_prog),
                        'minimo': min(tiempos_prog),
                        'maximo': max(tiempos_prog),
                        'mediciones': len(tiempos_prog)
                    }
            
            return resultado

# Instancia global del monitor (singleton)
monitor_global = MonitorMetricas()

def obtener_monitor():
    """
    Obtiene la instancia global del monitor de métricas.
    
    Returns:
        MonitorMetricas: Instancia del monitor
    """
    return monitor_global 