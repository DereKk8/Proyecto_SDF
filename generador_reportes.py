"""
generador_reportes.py - Generador de Reportes de Métricas

Este módulo se encarga de generar y guardar los reportes de métricas
en los archivos de texto con el formato específico requerido.

Genera dos tipos de reportes:
1. metricas_sistema.txt - Métricas del servidor hacia facultades
2. metricas_por_programa.txt - Métricas específicas por programa académico
"""

import os
from datetime import datetime
from typing import Dict, Any
from recolector_metricas import recolector_global

class GeneradorReportes:
    """Clase para generar reportes de métricas en archivos de texto."""
    
    def __init__(self):
        self.archivo_sistema = "metricas_sistema.txt"
        self.archivo_programas = "metricas_por_programa.txt"
    
    def generar_reporte_sistema(self):
        """
        Genera el reporte de métricas del sistema (servidor → facultades)
        y lo guarda en metricas_sistema.txt
        """
        estadisticas = recolector_global.obtener_estadisticas_servidor()
        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Formatear el reporte
        reporte = self._formatear_reporte_sistema(estadisticas, marca_tiempo)
        
        # Guardar en archivo
        self._escribir_archivo(self.archivo_sistema, reporte)
    
    def generar_reporte_programas(self):
        """
        Genera el reporte de métricas por programa académico
        y lo guarda en metricas_por_programa.txt
        """
        metricas_programas = recolector_global.obtener_metricas_programas()
        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Formatear el reporte
        reporte = self._formatear_reporte_programas(metricas_programas, marca_tiempo)
        
        # Guardar en archivo
        self._escribir_archivo(self.archivo_programas, reporte)
    
    def _formatear_reporte_sistema(self, estadisticas: Dict, marca_tiempo: str) -> str:
        """
        Formatea el reporte de métricas del sistema según el formato especificado.
        
        Args:
            estadisticas: Diccionario con las estadísticas del servidor
            marca_tiempo: Timestamp del reporte
            
        Returns:
            String con el reporte formateado
        """
        tiempo_promedio = estadisticas.get("tiempo_promedio", 0.0)
        tiempo_minimo = estadisticas.get("tiempo_minimo", 0.0)
        tiempo_maximo = estadisticas.get("tiempo_maximo", 0.0)
        total_mediciones = estadisticas.get("total_mediciones", 0)
        total_solicitudes = estadisticas.get("total_solicitudes", 0)
        
        reporte = f"""--- REPORTE SERVIDOR-FACULTAD - {marca_tiempo} ---

1. MÉTRICAS SERVIDOR → FACULTADES:
   • Tiempo promedio de respuesta: {tiempo_promedio:.4f} segundos
   • Tiempo mínimo de respuesta: {tiempo_minimo:.4f} segundos
   • Tiempo máximo de respuesta: {tiempo_maximo:.4f} segundos
   • Total de mediciones: {total_mediciones}
   • Total solicitudes procesadas: {total_solicitudes}

======================================================================

"""
        return reporte
    
    def _formatear_reporte_programas(self, metricas_programas: Dict, marca_tiempo: str) -> str:
        """
        Formatea el reporte de métricas por programa según el formato especificado.
        
        Args:
            metricas_programas: Diccionario con las métricas de programas
            marca_tiempo: Timestamp del reporte
            
        Returns:
            String con el reporte formateado
        """
        if not metricas_programas:
            return f"""--- REPORTE POR PROGRAMA - {marca_tiempo} ---

3. MÉTRICAS POR PROGRAMA:

   No hay métricas de programas disponibles.

======================================================================

"""
        
        reporte = f"""--- REPORTE POR PROGRAMA - {marca_tiempo} ---

3. MÉTRICAS POR PROGRAMA:

"""
        
        # Agrupar programas por facultad
        facultades_programas = {}
        for clave, metrica in metricas_programas.items():
            facultad = metrica["facultad"]
            if facultad not in facultades_programas:
                facultades_programas[facultad] = []
            facultades_programas[facultad].append(metrica)
        
        # Generar reporte por facultad
        for facultad, programas in facultades_programas.items():
            reporte += f"""   📚 FACULTAD: {facultad}
   --------------------------------------------------
"""
            
            for programa in programas:
                reporte += f"""   🎓 Programa: {programa["programa"]}
      • Requerimientos atendidos satisfactoriamente: {programa["requerimientos_exitosos"]}
      • Requerimientos rechazados por facultad: {programa["requerimientos_rechazados_facultad"]}
      • Requerimientos rechazados por servidor: {programa["requerimientos_rechazados_servidor"]}
      • Errores de comunicación: {programa["errores_comunicacion"]}
      • Total de requerimientos: {programa["total_requerimientos"]}
      • Porcentaje de éxito: {programa["porcentaje_exito"]:.1f}%
      • Porcentaje rechazo facultad: {programa["porcentaje_rechazo_facultad"]:.1f}%
      • Porcentaje rechazo servidor: {programa["porcentaje_rechazo_servidor"]:.1f}%
      • Porcentaje errores: {programa["porcentaje_errores"]:.1f}%
      • Último registro: {programa["ultimo_registro"]}
      ······························

"""
        
        reporte += """======================================================================

"""
        return reporte
    
    def _escribir_archivo(self, nombre_archivo: str, contenido: str):
        """
        Escribe el contenido en el archivo especificado, agregando al final.
        
        Args:
            nombre_archivo: Nombre del archivo donde escribir
            contenido: Contenido a escribir
        """
        try:
            with open(nombre_archivo, 'a', encoding='utf-8') as archivo:
                archivo.write(contenido)
            # Removed print statement to avoid user output
        except Exception as e:
            # Only log errors, don't show to user
            pass
    
    def limpiar_archivos(self):
        """Limpia los archivos de reporte, eliminando su contenido."""
        archivos = [self.archivo_sistema, self.archivo_programas]
        
        for archivo in archivos:
            try:
                with open(archivo, 'w', encoding='utf-8') as f:
                    f.write("")  # Escribir archivo vacío
                # Removed print statement to avoid user output
            except Exception as e:
                # Only log errors, don't show to user
                pass
    
    def generar_reportes_completos(self):
        """Genera ambos reportes de métricas."""
        # Removed print statements to avoid user output
        self.generar_reporte_sistema()
        self.generar_reporte_programas()
        # Reports generated silently

# Instancia global del generador de reportes
generador_global = GeneradorReportes()
