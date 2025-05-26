# Sistema de Métricas Integrado - Guía de Uso

## Descripción General

El sistema de monitoreo de métricas ha sido completamente integrado con el sistema de asignación de aulas existente. Ahora todas las comunicaciones y operaciones se registran automáticamente para análisis de desempeño.

## Métricas Recolectadas Automáticamente

### 1. Tiempo de Respuesta Servidor → Facultades

- **Qué mide**: Tiempo que toma el servidor DTI en procesar una solicitud de asignación
- **Cuándo se registra**: En cada operación de `asignar_aulas()` en `DTI_servidor.py`
- **Incluye**: Asignaciones exitosas, errores de disponibilidad, errores de procesamiento

### 2. Tiempo de Comunicación Facultad → Broker

- **Qué mide**: Tiempo de comunicación entre facultades y el broker
- **Cuándo se registra**: En cada llamada a `enviar_a_broker()` en `facultad.py`
- **Incluye**: Comunicaciones exitosas, timeouts, errores de red

### 3. Tiempo Programa → Atención Completa

- **Qué mide**: Tiempo total desde que un programa hace una solicitud hasta recibir respuesta
- **Cuándo se registra**: En cada solicitud en `programa_academico.py`
- **Incluye**: Todo el flujo: programa → facultad → broker → DTI → respuesta

## Archivos Modificados

### `DTI_servidor.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor

class ServidorDTI:
    def __init__(self):
        # ... código existente ...
        self.monitor_metricas = obtener_monitor()

    def asignar_aulas(self, solicitud: dict) -> dict:
        tiempo_inicio_servidor = time.time()
        # ... procesamiento ...
        tiempo_respuesta = time.time() - tiempo_inicio_servidor
        self.monitor_metricas.registrar_tiempo_respuesta_servidor(
            tiempo_respuesta, facultad, "asignacion_exitosa"
        )
```

### `facultad.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor

def enviar_a_broker(solicitud, client_id):
    monitor = obtener_monitor()
    tiempo_inicio_comunicacion = time.time()
    # ... comunicación ...
    tiempo_comunicacion = time.time() - tiempo_inicio_comunicacion
    monitor.registrar_tiempo_respuesta_servidor(
        tiempo_comunicacion, facultad, "comunicacion_broker_exitosa"
    )
```

### `programa_academico.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor

def enviar_solicitudes(solicitudes, sockets):
    monitor = obtener_monitor()
    for solicitud in solicitudes:
        id_solicitud = str(uuid.uuid4())
        monitor.registrar_inicio_solicitud_programa(id_solicitud, facultad, programa)
        # ... procesamiento ...
        tiempo_total = monitor.registrar_fin_solicitud_programa(id_solicitud)
```

## Cómo Usar el Sistema

### 1. Ejecución Normal

El sistema de métricas funciona automáticamente. Solo ejecuta los componentes como siempre:

```bash
# Terminal 1: Broker
python3 broker.py

# Terminal 2: Servidor DTI
python3 DTI_servidor.py

# Terminal 3: Facultad 1
python3 facultad.py 1

# Terminal 4: Facultad 2
python3 facultad.py 2

# Terminal 5: Programa académico
python3 programa_academico.py
```

### 2. Simulaciones con Métricas

```bash
# Simulación patrón A (7 salones, 2 laboratorios)
python3 programa_academico.py --simulacion A

# Simulación patrón B (10 salones, 4 laboratorios)
python3 programa_academico.py --simulacion B
```

### 3. Verificar Métricas

Las métricas se guardan automáticamente en `metricas_sistema.txt`:

## Archivo de Métricas (`metricas_sistema.txt`)

### Estructura del Archivo

```
=== SISTEMA DE MONITOREO DE MÉTRICAS DE TIEMPO DE RESPUESTA ===
Archivo creado: 2025-05-26 15:17:05
======================================================================

--- REPORTE DE MÉTRICAS - 2025-05-26 15:17:10 ---

1. MÉTRICAS SERVIDOR → FACULTADES:
   • Tiempo promedio de respuesta: 0.1050 segundos
   • Tiempo mínimo de respuesta: 0.1042 segundos
   • Tiempo máximo de respuesta: 0.1053 segundos
   • Total de mediciones: 16

2. MÉTRICAS PROGRAMA → ATENCIÓN:
   • Tiempo promedio solicitud-atención: 0.1051 segundos
   • Tiempo mínimo solicitud-atención: 0.1045 segundos
   • Tiempo máximo solicitud-atención: 0.1054 segundos
   • Total de mediciones: 8

3. ESTADÍSTICAS GENERALES:
   • Total solicitudes procesadas: 8
   • Total respuestas enviadas: 16
   • Solicitudes en progreso: 0
```

### Reportes Automáticos

- **Frecuencia**: Cada 5 minutos durante operación normal
- **Ubicación**: Se agregan al final del archivo `metricas_sistema.txt`
- **Persistencia**: Los datos se mantienen entre reinicios del sistema

## Interpretación de Métricas

### Métricas Servidor → Facultades

- **Tiempo promedio bajo (< 0.1s)**: Sistema funcionando eficientemente
- **Tiempo promedio alto (> 1s)**: Posible sobrecarga del servidor DTI
- **Gran diferencia min/max**: Variabilidad en la carga del sistema

### Métricas Programa → Atención

- **Tiempo total bajo (< 0.5s)**: Comunicación eficiente end-to-end
- **Tiempo total alto (> 5s)**: Posibles cuellos de botella en la red
- **Solicitudes en progreso altas**: Sistema saturado

## Casos de Uso para Análisis

### 1. Análisis de Rendimiento

```bash
# Ejecutar simulación y analizar resultados
python3 programa_academico.py --simulacion A
grep "Tiempo promedio" metricas_sistema.txt | tail -5
```

### 2. Detección de Problemas

```bash
# Buscar errores en las métricas
grep -i "error\|timeout\|fallo" metricas_sistema.txt
```

### 3. Comparación de Patrones

```bash
# Ejecutar ambos patrones y comparar
python3 programa_academico.py --simulacion A
python3 programa_academico.py --simulacion B
# Comparar los reportes generados
```

## Configuración Avanzada

### Cambiar Frecuencia de Reportes

En `programa_academico.py`, función `generar_reportes_periodicos()`:

```python
time.sleep(60)  # Cambiar a 300 para reportes cada 5 minutos
```

### Personalizar Archivo de Métricas

En `monitor_metricas.py`:

```python
monitor = MonitorMetricas("mi_archivo_metricas.txt")
```

## Solución de Problemas

### Problema: No se generan métricas

**Solución**: Verificar que `monitor_metricas.py` esté en el directorio correcto

### Problema: Archivo de métricas no se actualiza

**Solución**: Verificar permisos de escritura en el directorio

### Problema: Métricas inconsistentes

**Solución**: Reiniciar todos los componentes del sistema

## Beneficios del Sistema Integrado

1. **Monitoreo Automático**: No requiere intervención manual
2. **Análisis Histórico**: Datos persistentes para análisis temporal
3. **Detección de Problemas**: Identificación automática de cuellos de botella
4. **Optimización**: Datos para mejorar el rendimiento del sistema
5. **Transparencia**: Visibilidad completa del flujo de solicitudes

## Próximos Pasos

1. **Alertas Automáticas**: Implementar notificaciones cuando las métricas excedan umbrales
2. **Dashboard Web**: Crear interfaz gráfica para visualizar métricas en tiempo real
3. **Análisis Predictivo**: Usar datos históricos para predecir carga del sistema
4. **Métricas Adicionales**: Agregar métricas de uso de memoria y CPU
