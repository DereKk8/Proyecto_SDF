"""
recolector_metricas.py - Módulo de Recolección de Métricas de Tiempo de Respuesta

Este módulo implementa la recolección de métricas de tiempo de respuesta del sistema:
- Tiempo de respuesta entre DTI y Facultades
- Tiempo de respuesta completo desde programa académico
- Estadísticas de solicitudes procesadas

Todas las variables, funciones y comentarios están en español.
"""

import time
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json

@dataclass
class MetricaTiempo:
    """Clase para almacenar métricas de tiempo de una solicitud."""
    tiempo_inicio: float
    tiempo_fin: float
    tiempo_respuesta: float
    facultad: str
    programa: str
    exitosa: bool
    tipo_error: str = ""

@dataclass
class EstadisticasServidor:
    """Estadísticas acumuladas del servidor hacia facultades."""
    tiempos_respuesta: List[float] = field(default_factory=list)
    total_solicitudes: int = 0
    solicitudes_exitosas: int = 0
    solicitudes_fallidas: int = 0
    
    def agregar_metrica(self, tiempo_respuesta: float, exitosa: bool):
        """Agrega una nueva métrica al conjunto de estadísticas."""
        self.tiempos_respuesta.append(tiempo_respuesta)
        self.total_solicitudes += 1
        if exitosa:
            self.solicitudes_exitosas += 1
        else:
            self.solicitudes_fallidas += 1
    
    def obtener_estadisticas(self) -> Dict:
        """Retorna un diccionario con las estadísticas calculadas."""
        if not self.tiempos_respuesta:
            return {
                "tiempo_promedio": 0.0,
                "tiempo_minimo": 0.0,
                "tiempo_maximo": 0.0,
                "total_mediciones": 0,
                "total_solicitudes": 0,
                "solicitudes_exitosas": 0,
                "solicitudes_fallidas": 0
            }
        
        return {
            "tiempo_promedio": sum(self.tiempos_respuesta) / len(self.tiempos_respuesta),
            "tiempo_minimo": min(self.tiempos_respuesta),
            "tiempo_maximo": max(self.tiempos_respuesta),
            "total_mediciones": len(self.tiempos_respuesta),
            "total_solicitudes": self.total_solicitudes,
            "solicitudes_exitosas": self.solicitudes_exitosas,
            "solicitudes_fallidas": self.solicitudes_fallidas
        }

@dataclass
class MetricaPrograma:
    """Métricas específicas de un programa académico."""
    facultad: str
    programa: str
    requerimientos_exitosos: int = 0
    requerimientos_rechazados_facultad: int = 0
    requerimientos_rechazados_servidor: int = 0
    errores_comunicacion: int = 0
    ultimo_registro: str = ""
    
    def obtener_total_requerimientos(self) -> int:
        """Calcula el total de requerimientos procesados."""
        return (self.requerimientos_exitosos + 
                self.requerimientos_rechazados_facultad + 
                self.requerimientos_rechazados_servidor + 
                self.errores_comunicacion)
    
    def obtener_estadisticas(self) -> Dict:
        """Retorna estadísticas porcentuales del programa."""
        total = self.obtener_total_requerimientos()
        if total == 0:
            return {
                "porcentaje_exito": 0.0,
                "porcentaje_rechazo_facultad": 0.0,
                "porcentaje_rechazo_servidor": 0.0,
                "porcentaje_errores": 0.0
            }
        
        return {
            "porcentaje_exito": (self.requerimientos_exitosos / total) * 100,
            "porcentaje_rechazo_facultad": (self.requerimientos_rechazados_facultad / total) * 100,
            "porcentaje_rechazo_servidor": (self.requerimientos_rechazados_servidor / total) * 100,
            "porcentaje_errores": (self.errores_comunicacion / total) * 100
        }

class RecolectorMetricas:
    """
    Clase principal para recolectar y gestionar métricas del sistema.
    Thread-safe para uso concurrente.
    """
    
    def __init__(self):
        self.estadisticas_servidor = EstadisticasServidor()
        self.metricas_programas: Dict[str, MetricaPrograma] = {}
        self.mutex = threading.Lock()
        
    def iniciar_medicion_servidor(self) -> float:
        """Inicia la medición de tiempo para una solicitud del servidor."""
        return time.time()
    
    def finalizar_medicion_servidor(self, tiempo_inicio: float, exitosa: bool) -> float:
        """
        Finaliza la medición de tiempo del servidor y registra la métrica.
        
        Args:
            tiempo_inicio: Timestamp de inicio de la medición
            exitosa: Si la solicitud fue exitosa o no
            
        Returns:
            Tiempo de respuesta en segundos
        """
        tiempo_fin = time.time()
        tiempo_respuesta = tiempo_fin - tiempo_inicio
        
        with self.mutex:
            self.estadisticas_servidor.agregar_metrica(tiempo_respuesta, exitosa)
        
        return tiempo_respuesta
    
    def registrar_solicitud_programa(self, facultad: str, programa: str, 
                                   resultado: str, mensaje_error: str = ""):
        """
        Registra el resultado de una solicitud de programa académico.
        
        Args:
            facultad: Nombre de la facultad
            programa: Nombre del programa académico
            resultado: 'exitoso', 'rechazado_facultad', 'rechazado_servidor', 'error_comunicacion'
            mensaje_error: Mensaje de error si aplica
        """
        clave_programa = f"{facultad}|{programa}"
        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with self.mutex:
            if clave_programa not in self.metricas_programas:
                self.metricas_programas[clave_programa] = MetricaPrograma(
                    facultad=facultad,
                    programa=programa
                )
            
            programa_metrica = self.metricas_programas[clave_programa]
            programa_metrica.ultimo_registro = marca_tiempo
            
            if resultado == "exitoso":
                programa_metrica.requerimientos_exitosos += 1
            elif resultado == "rechazado_facultad":
                programa_metrica.requerimientos_rechazados_facultad += 1
            elif resultado == "rechazado_servidor":
                programa_metrica.requerimientos_rechazados_servidor += 1
            elif resultado == "error_comunicacion":
                programa_metrica.errores_comunicacion += 1
    
    def obtener_estadisticas_servidor(self) -> Dict:
        """Obtiene las estadísticas actuales del servidor."""
        with self.mutex:
            return self.estadisticas_servidor.obtener_estadisticas()
    
    def obtener_metricas_programas(self) -> Dict[str, Dict]:
        """Obtiene las métricas de todos los programas académicos."""
        with self.mutex:
            resultado = {}
            for clave, metrica in self.metricas_programas.items():
                estadisticas = metrica.obtener_estadisticas()
                resultado[clave] = {
                    "facultad": metrica.facultad,
                    "programa": metrica.programa,
                    "requerimientos_exitosos": metrica.requerimientos_exitosos,
                    "requerimientos_rechazados_facultad": metrica.requerimientos_rechazados_facultad,
                    "requerimientos_rechazados_servidor": metrica.requerimientos_rechazados_servidor,
                    "errores_comunicacion": metrica.errores_comunicacion,
                    "total_requerimientos": metrica.obtener_total_requerimientos(),
                    "ultimo_registro": metrica.ultimo_registro,
                    **estadisticas
                }
            return resultado
    
    def limpiar_metricas(self):
        """Limpia todas las métricas acumuladas."""
        with self.mutex:
            self.estadisticas_servidor = EstadisticasServidor()
            self.metricas_programas.clear()

# Instancia global del recolector de métricas
recolector_global = RecolectorMetricas()
