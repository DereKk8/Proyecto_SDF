# Sistema de Métricas Integrado - Guía de Uso

## Descripción General

El sistema de monitoreo de métricas ha sido completamente integrado con el sistema de asignación de aulas. Recolecta automáticamente métricas de tiempo de respuesta y contadores por programa para análisis de desempeño completo.

**IMPORTANTE**: Las métricas ahora se guardan en **dos archivos separados**:

- `metricas_sistema.txt`: Métricas de tiempo de respuesta (servidor-facultad y programa-atención)
- `metricas_por_programa.txt`: Métricas desglosadas por programa académico

## Métricas Recolectadas Automáticamente

### 1. Tiempo de Respuesta Servidor → Facultades

- **Qué mide**: Tiempo total de respuesta desde facultad hasta DTI (incluye broker + DTI)
- **Cuándo se registra**: En cada comunicación completa en `facultad.py`
- **Incluye**: Respuestas exitosas, respuestas inválidas, errores ZMQ, errores generales

### 2. Tiempo Programa → Atención Completa

- **Qué mide**: Tiempo total desde que un programa hace una solicitud hasta recibir respuesta
- **Cuándo se registra**: En cada solicitud en `programa_academico.py`
- **Incluye**: Todo el flujo: programa → facultad → broker → DTI → respuesta

### 3. Métricas por Programa

- **Requerimientos atendidos satisfactoriamente**: Solicitudes exitosas con asignación de aulas
- **Requerimientos rechazados por facultad**: Rechazos por facultad inválida
- **Requerimientos rechazados por servidor**: Rechazos por falta de disponibilidad
- **Errores de comunicación**: Fallos de red o comunicación

## Archivos Modificados

### `facultad.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor
from monitor_metricas_programa import obtener_monitor_programa

def enviar_a_broker(solicitud, client_id):
    monitor = obtener_monitor()
    tiempo_inicio_comunicacion = time.time()
    # ... comunicación completa (broker + DTI) ...
    tiempo_respuesta_total = time.time() - tiempo_inicio_comunicacion
    monitor.registrar_tiempo_respuesta_servidor(
        tiempo_respuesta_total,
        solicitud.get("facultad", "Desconocida"),
        "respuesta_exitosa"  # o "respuesta_invalida", "error_zmq", "error_general"
    )

# Registro de rechazos por facultad inválida (archivo separado)
if solicitud.get("facultad") not in facultades:
    monitor_programa = obtener_monitor_programa()
    monitor_programa.registrar_requerimiento_rechazado_por_facultad(
        solicitud.get("facultad", "Desconocida"),
        solicitud.get("programa", "Desconocido"),
        "facultad_invalida"
    )
```

### `programa_academico.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor
from monitor_metricas_programa import obtener_monitor_programa

def proceso_programa(solicitud, pending_count):
    monitor = obtener_monitor()
    monitor_programa = obtener_monitor_programa()
    id_solicitud = str(uuid.uuid4())
    facultad = solicitud.get("facultad", "Desconocida")
    programa = solicitud.get("programa", "Desconocido")

    # Registrar inicio de solicitud (tiempo de respuesta)
    monitor.registrar_inicio_solicitud_programa(id_solicitud, facultad, programa)

    # ... procesamiento ...

    # Registrar métricas por programa según el resultado (archivo separado)
    if "error" in asignacion:
        monitor_programa.registrar_error_comunicacion_programa(facultad, programa, "error_servidor")
    elif "noDisponible" in asignacion:
        monitor_programa.registrar_requerimiento_rechazado_por_servidor(facultad, programa, "no_disponible")
    else:
        monitor_programa.registrar_requerimiento_atendido_satisfactoriamente(facultad, programa)

    # Registrar fin de solicitud (tiempo de respuesta)
    tiempo_total = monitor.registrar_fin_solicitud_programa(id_solicitud)
```

### `load_balancer_broker.py`

```python
# Integración agregada:
from monitor_metricas import obtener_monitor

class LoadBalancerBroker:
    def __init__(self):
        # ... código existente ...
        self.monitor_metricas = obtener_monitor()
        self.total_solicitudes_procesadas_broker = 0

    # Genera reportes periódicos de métricas servidor-facultad
    def generar_reportes_periodicos(self):
        while self.running:
            time.sleep(300)  # Cada 5 minutos
            reporte = self.monitor_metricas.generar_reporte_servidor_facultad(
                self.total_solicitudes_procesadas_broker
            )
```

## Cómo Usar el Sistema

### 1. Ejecución Normal

El sistema de métricas funciona automáticamente. Solo ejecuta los componentes como siempre:

```bash
# Terminal 1: Broker
python3 load_balancer_broker.py

# Terminal 2: Servidor DTI
python3 DTI_servidor.py

# Terminal 3: Facultad 1
python3 facultad.py 1

# Terminal 4: Facultad 2
python3 facultad.py 2

# Terminal 5: Programa académico
python3 programa_academico.py
```

**Nota importante**: En el broker puedes usar comandos interactivos:

- `metricas` o `metrics`: Genera reporte servidor-facultad inmediato
- `status` o `estado`: Muestra estado actual del broker
- `salir`: Termina el broker

### 2. Simulaciones con Métricas

```bash
# Simulación patrón A (7 salones, 2 laboratorios)
python3 programa_academico.py --simulacion A

# Simulación patrón B (10 salones, 4 laboratorios)
python3 programa_academico.py --simulacion B
```

### 3. Verificar Métricas

Las métricas se guardan automáticamente en `metricas_sistema.txt`:

## Archivos de Métricas

### Estructura de Archivos

El sistema genera reportes en **dos archivos separados**:

### 1. `metricas_sistema.txt` - Métricas de Tiempo de Respuesta

Contiene métricas de tiempo de respuesta del sistema:

#### 1. Reporte Programa-Atención (generado por `programa_academico.py`)

```
--- REPORTE PROGRAMA-ATENCIÓN - 2025-05-26 16:28:01 ---

2. MÉTRICAS PROGRAMA → ATENCIÓN:
   • Tiempo promedio solicitud-atención: 0.1051 segundos
   • Tiempo mínimo solicitud-atención: 0.1045 segundos
   • Tiempo máximo solicitud-atención: 0.1054 segundos
   • Total de mediciones: 8
   • Total respuestas enviadas: 16
```

#### 2. Reporte Servidor-Facultad (generado por `load_balancer_broker.py`)

```
--- REPORTE SERVIDOR-FACULTAD - 2025-05-26 16:28:01 ---

1. MÉTRICAS SERVIDOR → FACULTADES:
   • Tiempo promedio de respuesta: 0.1050 segundos
   • Tiempo mínimo de respuesta: 0.1042 segundos
   • Tiempo máximo de respuesta: 0.1053 segundos
   • Total de mediciones: 16
   • Total solicitudes procesadas: 25
```

### 2. `metricas_por_programa.txt` - Métricas por Programa Académico

Contiene métricas desglosadas por programa académico:

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
```

### Reportes Automáticos

- **`programa_academico.py`**: Cada 5 minutos genera:
  - Reportes programa-atención → `metricas_sistema.txt`
  - Reportes por programa → `metricas_por_programa.txt`
- **`load_balancer_broker.py`**: Cada 5 minutos genera reportes servidor-facultad → `metricas_sistema.txt`
- **Persistencia**: Los datos se mantienen entre reinicios del sistema

### Reportes Manuales

Para generar reportes servidor-facultad manualmente desde el broker:

```bash
# En la consola del broker, escribir:
metricas
# o
metrics
```

Esto generará inmediatamente un reporte de métricas servidor-facultad con las estadísticas actuales.

## Interpretación de Métricas

### Métricas Servidor → Facultades

- **Tiempo promedio bajo (< 0.5s)**: Sistema funcionando eficientemente
- **Tiempo promedio alto (> 2s)**: Posible sobrecarga del broker o DTI
- **Gran diferencia min/max**: Variabilidad en la carga del sistema
- **Tipos de operación**: "respuesta_exitosa", "respuesta_invalida", "error_zmq", "error_general"

### Métricas Programa → Atención

- **Tiempo total bajo (< 1s)**: Comunicación eficiente end-to-end
- **Tiempo total alto (> 5s)**: Posibles cuellos de botella en la red
- **Total respuestas enviadas**: Contador de solicitudes completadas

### Métricas Por Programa

- **Porcentaje de éxito alto (> 80%)**: Programa funcionando bien
- **Rechazos por facultad**: Problemas de configuración o datos inválidos
- **Rechazos por servidor**: Problemas de disponibilidad de aulas
- **Errores de comunicación**: Problemas de red o infraestructura

````

## Configuración Avanzada

### Cambiar Frecuencia de Reportes

En `programa_academico.py`, función `generar_reportes_periodicos()`:

```python
time.sleep(300)  # Cambiar a 60 para reportes cada minuto
````

En `load_balancer_broker.py`, función `generar_reportes_periodicos()`:

```python
time.sleep(300)  # Cambiar a 60 para reportes cada minuto
```

### Personalizar Archivos de Métricas

En `monitor_metricas.py`:

```python
monitor = MonitorMetricas("mi_archivo_metricas.txt")
```

En `monitor_metricas_programa.py`:

```python
monitor_programa = MonitorMetricasPrograma("mi_archivo_programas.txt")
```

### Generar Reportes Manuales

#### Desde el Broker (Recomendado para servidor-facultad)

```bash
# En la consola del broker ejecutándose:
metricas    # Genera reporte servidor-facultad inmediato
status      # Muestra estado actual del sistema
```

#### Desde Código Python

```python
from monitor_metricas import obtener_monitor
from monitor_metricas_programa import obtener_monitor_programa

monitor = obtener_monitor()
monitor_programa = obtener_monitor_programa()

# Reporte programa-atención → metricas_sistema.txt
reporte_programa = monitor.generar_reporte_programa_atencion()

# Reporte servidor-facultad → metricas_sistema.txt
reporte_servidor = monitor.generar_reporte_servidor_facultad(total_solicitudes_broker)

# Reporte por programa → metricas_por_programa.txt
monitor_programa.guardar_reporte_por_programa()
```

## Tipos de Métricas Disponibles

### Métricas de Tiempo

- Tiempo de respuesta servidor → facultades
- Tiempo programa → atención completa

### Métricas de Contadores

- Requerimientos atendidos satisfactoriamente
- Requerimientos rechazados por facultad
- Requerimientos rechazados por servidor
- Errores de comunicación

### Métricas Calculadas

- Porcentajes de éxito/fallo
- Estadísticas por facultad y programa
- Totales de solicitudes procesadas
