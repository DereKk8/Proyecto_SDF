# Sistema de Métricas por Programa

## Descripción General

El sistema de métricas por programa permite recolectar y analizar estadísticas detalladas sobre el comportamiento de cada programa académico en el sistema de asignación de aulas. Este módulo registra y categoriza todos los requerimientos según su resultado final.

## Métricas Recolectadas

### Por Programa:

1. **Requerimientos atendidos satisfactoriamente**: Número de solicitudes que fueron procesadas exitosamente y resultaron en asignación de aulas
2. **Requerimientos rechazados por la Facultad**: Número de solicitudes rechazadas debido a facultad inválida o no reconocida
3. **Requerimientos rechazados por el Servidor**: Número de solicitudes rechazadas por el servidor DTI debido a falta de disponibilidad
4. **Errores de comunicación**: Número de solicitudes que fallaron debido a problemas de red o comunicación

## Estructura de Datos

### Variables en Español

```python
# Diccionario principal que almacena métricas por programa
requerimientos_por_programa = {
    'clave_programa': {
        'atendidos_satisfactoriamente': int,
        'rechazados_por_facultad': int,
        'rechazados_por_servidor': int,
        'errores_comunicacion': int,
        'facultad': str,
        'ultimo_timestamp': str
    }
}
```

### Clave de Programa

La clave del programa se forma como: `"{facultad}_{programa}"`

Ejemplo: `"Facultad de Ingeniería_Sistemas"`

## Funciones Principales

### 1. Registro de Métricas

#### `registrar_requerimiento_atendido_satisfactoriamente(facultad, programa)`

- **Propósito**: Registra un requerimiento exitoso
- **Cuándo usar**: Cuando el servidor DTI asigna aulas exitosamente
- **Ejemplo**:

```python
monitor.registrar_requerimiento_atendido_satisfactoriamente(
    "Facultad de Ingeniería",
    "Sistemas"
)
```

#### `registrar_requerimiento_rechazado_por_facultad(facultad, programa, motivo)`

- **Propósito**: Registra un rechazo por facultad inválida
- **Cuándo usar**: Cuando la facultad no existe en el sistema
- **Ejemplo**:

```python
monitor.registrar_requerimiento_rechazado_por_facultad(
    "Facultad Inexistente",
    "Programa",
    "facultad_invalida"
)
```

#### `registrar_requerimiento_rechazado_por_servidor(facultad, programa, motivo)`

- **Propósito**: Registra un rechazo por el servidor DTI
- **Cuándo usar**: Cuando no hay aulas disponibles
- **Ejemplo**:

```python
monitor.registrar_requerimiento_rechazado_por_servidor(
    "Facultad de Medicina",
    "Medicina",
    "no_disponible"
)
```

#### `registrar_error_comunicacion_programa(facultad, programa, tipo_error)`

- **Propósito**: Registra errores de comunicación
- **Cuándo usar**: Cuando hay problemas de red o ZMQ
- **Ejemplo**:

```python
monitor.registrar_error_comunicacion_programa(
    "Facultad de Derecho",
    "Derecho",
    "zmq_error"
)
```

### 2. Cálculo de Métricas

#### `calcular_metricas_por_programa()`

- **Propósito**: Calcula estadísticas completas por programa
- **Retorna**: Diccionario con métricas y porcentajes
- **Incluye**:
  - Contadores absolutos
  - Porcentajes de éxito/fallo
  - Total de requerimientos
  - Último timestamp

### 3. Generación de Reportes

#### `generar_reporte_por_programa()`

- **Propósito**: Genera y guarda reporte completo por programa
- **Archivo**: Escribe en `metricas_sistema.txt`
- **Formato**: Organizado por facultad y programa

## Integración en el Sistema

### En `programa_academico.py`

```python
# Al recibir respuesta exitosa
if "error" not in asignacion and "noDisponible" not in asignacion:
    monitor.registrar_requerimiento_atendido_satisfactoriamente(facultad, programa)

# Al recibir rechazo por no disponibilidad
elif "noDisponible" in asignacion:
    monitor.registrar_requerimiento_rechazado_por_servidor(facultad, programa, "no_disponible")

# Al recibir error del servidor
elif "error" in asignacion:
    monitor.registrar_error_comunicacion_programa(facultad, programa, "error_servidor")

# Al tener error de comunicación ZMQ
except zmq.ZMQError:
    monitor.registrar_error_comunicacion_programa(facultad, programa, "zmq_error")
```

### En `facultad.py`

```python
# Al validar facultad inválida
if solicitud.get("facultad") not in facultades:
    monitor.registrar_requerimiento_rechazado_por_facultad(
        solicitud.get("facultad", "Desconocida"),
        solicitud.get("programa", "Desconocido"),
        "facultad_invalida"
    )
```

## Formato del Archivo de Métricas

### Estructura del Reporte

```
--- REPORTE POR PROGRAMA - 2025-05-26 16:28:01 ---

3. MÉTRICAS POR PROGRAMA:

   📚 FACULTAD: Facultad de Ingeniería
   --------------------------------------------------
   🎓 Programa: Sistemas
      • Requerimientos atendidos satisfactoriamente: 3
      • Requerimientos rechazados por facultad: 1
      • Requerimientos rechazados por servidor: 0
      • Errores de comunicación: 0
      • Total de requerimientos: 4
      • Porcentaje de éxito: 75.0%
      • Porcentaje rechazo facultad: 25.0%
      • Porcentaje rechazo servidor: 0.0%
      • Porcentaje errores: 0.0%
      • Último registro: 2025-05-26 16:28:01
      ······························

======================================================================
```

## Casos de Uso

### 1. Análisis de Rendimiento por Programa

- Identificar programas con mayor tasa de éxito
- Detectar programas problemáticos
- Comparar rendimiento entre facultades

### 2. Diagnóstico de Problemas

- Identificar si los rechazos son por facultad inválida
- Detectar problemas de disponibilidad de aulas
- Monitorear errores de comunicación

### 3. Reportes Administrativos

- Generar estadísticas para administradores
- Crear reportes de uso del sistema
- Analizar patrones de demanda

## Ejemplo de Uso Completo

```python
from monitor_metricas import obtener_monitor

# Obtener instancia del monitor
monitor = obtener_monitor()

# Simular diferentes tipos de requerimientos
monitor.registrar_requerimiento_atendido_satisfactoriamente("Facultad de Ingeniería", "Sistemas")
monitor.registrar_requerimiento_rechazado_por_facultad("Facultad Inexistente", "Programa", "facultad_invalida")
monitor.registrar_requerimiento_rechazado_por_servidor("Facultad de Medicina", "Medicina", "no_disponible")
monitor.registrar_error_comunicacion_programa("Facultad de Derecho", "Derecho", "zmq_error")

# Generar reporte
reporte = monitor.generar_reporte_por_programa()
print(f"Reporte generado: {reporte['timestamp']}")
print(f"Programas con métricas: {len(reporte['metricas_por_programa'])}")
```

## Ventajas del Sistema

1. **Granularidad**: Métricas específicas por programa académico
2. **Categorización**: Diferentes tipos de fallos claramente identificados
3. **Porcentajes**: Cálculo automático de tasas de éxito/fallo
4. **Organización**: Reportes organizados por facultad
5. **Persistencia**: Almacenamiento en archivo de texto legible
6. **Thread-Safe**: Uso de locks para operaciones concurrentes

## Consideraciones de Rendimiento

- Uso de `defaultdict` para inicialización automática
- Locks para operaciones thread-safe
- Almacenamiento eficiente en memoria
- Escritura asíncrona al archivo

## Mantenimiento

- Los datos se mantienen en memoria durante la ejecución
- El archivo se actualiza con cada reporte generado
- No hay límite en el número de programas rastreados
- Los timestamps permiten análisis temporal
