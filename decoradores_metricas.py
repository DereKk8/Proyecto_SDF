"""
decoradores_metricas.py - Decoradores para Medición Automática de Métricas

Este módulo contiene decoradores que permiten medir automáticamente
los tiempos de respuesta y registrar métricas sin modificar 
significativamente el código existente.
"""

import functools
import time
from typing import Callable, Any
from recolector_metricas import recolector_global

def medir_tiempo_servidor(func: Callable) -> Callable:
    """
    Decorador para medir el tiempo de respuesta del servidor DTI.
    
    Args:
        func: Función a decorar (debe ser la función de procesamiento del DTI)
        
    Returns:
        Función decorada que mide automáticamente el tiempo de respuesta
    """
    @functools.wraps(func)
    def envolvente(*args, **kwargs):
        tiempo_inicio = recolector_global.iniciar_medicion_servidor()
        
        try:
            resultado = func(*args, **kwargs)
            # Determinar si la operación fue exitosa
            exitosa = not (isinstance(resultado, dict) and "error" in resultado)
            recolector_global.finalizar_medicion_servidor(tiempo_inicio, exitosa)
            return resultado
        except Exception as e:
            # En caso de excepción, marcar como no exitosa
            recolector_global.finalizar_medicion_servidor(tiempo_inicio, False)
            raise e
    
    return envolvente

def registrar_solicitud_programa(func: Callable) -> Callable:
    """
    Decorador para registrar automáticamente las métricas de solicitudes de programa.
    
    Args:
        func: Función que procesa solicitudes de programa académico
        
    Returns:
        Función decorada que registra automáticamente las métricas
    """
    @functools.wraps(func)
    def envolvente(solicitud, *args, **kwargs):
        facultad = solicitud.get("facultad", "Desconocida")
        programa = solicitud.get("programa", "Desconocido")
        
        try:
            resultado = func(solicitud, *args, **kwargs)
            
            # Determinar el tipo de resultado
            if isinstance(resultado, dict):
                if "error" in resultado:
                    error_msg = resultado["error"]
                    if "Facultad no válida" in error_msg:
                        tipo_resultado = "rechazado_facultad"
                    elif "comunicación" in error_msg.lower():
                        tipo_resultado = "error_comunicacion"
                    else:
                        tipo_resultado = "rechazado_servidor"
                else:
                    tipo_resultado = "exitoso"
            else:
                tipo_resultado = "exitoso"
            
            # Registrar la métrica
            recolector_global.registrar_solicitud_programa(
                facultad, programa, tipo_resultado
            )
            
            return resultado
            
        except Exception as e:
            # En caso de excepción, registrar como error de comunicación
            recolector_global.registrar_solicitud_programa(
                facultad, programa, "error_comunicacion", str(e)
            )
            raise e
    
    return envolvente

def medir_tiempo_respuesta_completo(func: Callable) -> Callable:
    """
    Decorador para medir el tiempo completo de respuesta desde el programa académico.
    
    Args:
        func: Función que envía solicitudes desde programa académico
        
    Returns:
        Función decorada que mide el tiempo completo de respuesta
    """
    @functools.wraps(func)
    def envolvente(*args, **kwargs):
        tiempo_inicio = time.time()
        
        try:
            resultado = func(*args, **kwargs)
            tiempo_total = time.time() - tiempo_inicio
            
            # Log del tiempo total (opcional para debugging)
            print(f"⏱️ Tiempo total de respuesta: {tiempo_total:.4f} segundos")
            
            return resultado
            
        except Exception as e:
            tiempo_total = time.time() - tiempo_inicio
            print(f"❌ Tiempo hasta error: {tiempo_total:.4f} segundos")
            raise e
    
    return envolvente
