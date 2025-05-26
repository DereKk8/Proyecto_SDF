"""
monitor_metricas_programa.py - Sistema de Métricas por Programa Académico

Este módulo maneja específicamente las métricas desglosadas por programa académico:
- Requerimientos atendidos satisfactoriamente
- Requerimientos rechazados por facultad
- Requerimientos rechazados por servidor
- Errores de comunicación

Genera reportes en archivo separado: metricas_por_programa.txt
"""

import threading
import time
from datetime import datetime
from collections import defaultdict

class MonitorMetricasPrograma:
    """
    Monitor específico para métricas por programa académico.
    Thread-safe para uso en entornos concurrentes.
    """
    
    def __init__(self, archivo_metricas="metricas_por_programa.txt"):
        """
        Inicializa el monitor de métricas por programa.
        
        Args:
            archivo_metricas (str): Nombre del archivo donde guardar las métricas
        """
        self.archivo_metricas = archivo_metricas
        self.lock = threading.Lock()
        
        # Estructura de datos para métricas por programa
        # Formato: {clave_programa: {datos_del_programa}}
        self.requerimientos_por_programa = defaultdict(lambda: {
            'atendidos_satisfactoriamente': 0,
            'rechazados_por_facultad': 0,
            'rechazados_por_servidor': 0,
            'errores_comunicacion': 0,
            'facultad': '',
            'ultimo_timestamp': ''
        })
    
    def _generar_clave_programa(self, facultad, programa):
        """
        Genera una clave única para identificar un programa específico.
        
        Args:
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
            
        Returns:
            str: Clave única en formato "facultad|programa"
        """
        return f"{facultad}|{programa}"
    
    def registrar_requerimiento_atendido_satisfactoriamente(self, facultad, programa):
        """
        Registra un requerimiento que fue atendido satisfactoriamente.
        
        Args:
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
        """
        with self.lock:
            clave = self._generar_clave_programa(facultad, programa)
            self.requerimientos_por_programa[clave]['atendidos_satisfactoriamente'] += 1
            self.requerimientos_por_programa[clave]['facultad'] = facultad
            self.requerimientos_por_programa[clave]['ultimo_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def registrar_requerimiento_rechazado_por_facultad(self, facultad, programa, motivo=""):
        """
        Registra un requerimiento rechazado por la facultad.
        
        Args:
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
            motivo (str): Motivo del rechazo (opcional)
        """
        with self.lock:
            clave = self._generar_clave_programa(facultad, programa)
            self.requerimientos_por_programa[clave]['rechazados_por_facultad'] += 1
            self.requerimientos_por_programa[clave]['facultad'] = facultad
            self.requerimientos_por_programa[clave]['ultimo_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def registrar_requerimiento_rechazado_por_servidor(self, facultad, programa, motivo=""):
        """
        Registra un requerimiento rechazado por el servidor DTI.
        
        Args:
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
            motivo (str): Motivo del rechazo (opcional)
        """
        with self.lock:
            clave = self._generar_clave_programa(facultad, programa)
            self.requerimientos_por_programa[clave]['rechazados_por_servidor'] += 1
            self.requerimientos_por_programa[clave]['facultad'] = facultad
            self.requerimientos_por_programa[clave]['ultimo_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def registrar_error_comunicacion_programa(self, facultad, programa, tipo_error=""):
        """
        Registra un error de comunicación para un programa específico.
        
        Args:
            facultad (str): Nombre de la facultad
            programa (str): Nombre del programa académico
            tipo_error (str): Tipo de error ocurrido (opcional)
        """
        with self.lock:
            clave = self._generar_clave_programa(facultad, programa)
            self.requerimientos_por_programa[clave]['errores_comunicacion'] += 1
            self.requerimientos_por_programa[clave]['facultad'] = facultad
            self.requerimientos_por_programa[clave]['ultimo_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def calcular_metricas_por_programa(self):
        """
        Calcula métricas agregadas por programa.
        
        Returns:
            dict: Diccionario con métricas calculadas por programa
        """
        with self.lock:
            metricas_calculadas = {}
            
            for clave, datos in self.requerimientos_por_programa.items():
                facultad, programa = clave.split('|', 1)
                
                total_requerimientos = (
                    datos['atendidos_satisfactoriamente'] +
                    datos['rechazados_por_facultad'] +
                    datos['rechazados_por_servidor'] +
                    datos['errores_comunicacion']
                )
                
                if total_requerimientos > 0:
                    porcentaje_exito = (datos['atendidos_satisfactoriamente'] / total_requerimientos) * 100
                    porcentaje_rechazo_facultad = (datos['rechazados_por_facultad'] / total_requerimientos) * 100
                    porcentaje_rechazo_servidor = (datos['rechazados_por_servidor'] / total_requerimientos) * 100
                    porcentaje_errores = (datos['errores_comunicacion'] / total_requerimientos) * 100
                else:
                    porcentaje_exito = porcentaje_rechazo_facultad = porcentaje_rechazo_servidor = porcentaje_errores = 0
                
                metricas_calculadas[clave] = {
                    'facultad': facultad,
                    'programa': programa,
                    'atendidos_satisfactoriamente': datos['atendidos_satisfactoriamente'],
                    'rechazados_por_facultad': datos['rechazados_por_facultad'],
                    'rechazados_por_servidor': datos['rechazados_por_servidor'],
                    'errores_comunicacion': datos['errores_comunicacion'],
                    'total_requerimientos': total_requerimientos,
                    'porcentaje_exito': porcentaje_exito,
                    'porcentaje_rechazo_facultad': porcentaje_rechazo_facultad,
                    'porcentaje_rechazo_servidor': porcentaje_rechazo_servidor,
                    'porcentaje_errores': porcentaje_errores,
                    'ultimo_timestamp': datos['ultimo_timestamp']
                }
            
            return metricas_calculadas
    
    def generar_reporte_por_programa(self):
        """
        Genera un reporte completo de métricas por programa.
        
        Returns:
            str: Reporte formateado como string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metricas = self.calcular_metricas_por_programa()
        
        if not metricas:
            return f"--- REPORTE POR PROGRAMA - {timestamp} ---\n\n3. MÉTRICAS POR PROGRAMA:\n\n   📊 No hay datos de programas registrados aún.\n\n"
        
        # Agrupar por facultad
        facultades = defaultdict(list)
        for clave, datos in metricas.items():
            facultades[datos['facultad']].append(datos)
        
        # Generar reporte
        reporte = f"--- REPORTE POR PROGRAMA - {timestamp} ---\n\n"
        reporte += "3. MÉTRICAS POR PROGRAMA:\n\n"
        
        for facultad, programas in facultades.items():
            reporte += f"   📚 FACULTAD: {facultad}\n"
            reporte += "   " + "-" * 50 + "\n"
            
            for programa_data in programas:
                reporte += f"   🎓 Programa: {programa_data['programa']}\n"
                reporte += f"      • Requerimientos atendidos satisfactoriamente: {programa_data['atendidos_satisfactoriamente']}\n"
                reporte += f"      • Requerimientos rechazados por facultad: {programa_data['rechazados_por_facultad']}\n"
                reporte += f"      • Requerimientos rechazados por servidor: {programa_data['rechazados_por_servidor']}\n"
                reporte += f"      • Errores de comunicación: {programa_data['errores_comunicacion']}\n"
                reporte += f"      • Total de requerimientos: {programa_data['total_requerimientos']}\n"
                reporte += f"      • Porcentaje de éxito: {programa_data['porcentaje_exito']:.1f}%\n"
                reporte += f"      • Porcentaje rechazo facultad: {programa_data['porcentaje_rechazo_facultad']:.1f}%\n"
                reporte += f"      • Porcentaje rechazo servidor: {programa_data['porcentaje_rechazo_servidor']:.1f}%\n"
                reporte += f"      • Porcentaje errores: {programa_data['porcentaje_errores']:.1f}%\n"
                reporte += f"      • Último registro: {programa_data['ultimo_timestamp']}\n\n"
        
        return reporte
    
    def _escribir_reporte_programa_archivo(self, reporte):
        """
        Escribe el reporte de métricas por programa al archivo.
        
        Args:
            reporte (str): Contenido del reporte a escribir
        """
        try:
            with open(self.archivo_metricas, "a", encoding="utf-8") as archivo:
                archivo.write(reporte)
                archivo.flush()
        except Exception as e:
            print(f"❌ Error al escribir reporte por programa: {e}")
    
    def guardar_reporte_por_programa(self):
        """
        Genera y guarda un reporte de métricas por programa en el archivo.
        """
        reporte = self.generar_reporte_por_programa()
        self._escribir_reporte_programa_archivo(reporte)
        print(f"📊 Reporte por programa guardado en {self.archivo_metricas}")

# Instancia global del monitor de métricas por programa
_monitor_programa_global = None
_lock_monitor_programa = threading.Lock()

def obtener_monitor_programa():
    """
    Obtiene la instancia global del monitor de métricas por programa.
    Implementa patrón Singleton thread-safe.
    
    Returns:
        MonitorMetricasPrograma: Instancia del monitor
    """
    global _monitor_programa_global
    
    if _monitor_programa_global is None:
        with _lock_monitor_programa:
            if _monitor_programa_global is None:
                _monitor_programa_global = MonitorMetricasPrograma()
    
    return _monitor_programa_global 