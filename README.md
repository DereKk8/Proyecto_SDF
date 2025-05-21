# Sistema Distribuido de Asignación de Aulas 🎓🏫

Sistema distribuido para asignación de aulas y laboratorios implementado con Python y ZeroMQ. Utiliza un patrón de comunicación distribuido para ofrecer alta disponibilidad, tolerancia a fallos y balanceo de carga.

## 📋 TODOs y Plan de Desarrollo

A continuación se presenta la lista de tareas completadas y pendientes para el desarrollo incremental del sistema:

### Fase 1: Funcionalidad Base y Simulación ✅

- [x] **Módulo del cliente con solicitudes "mock"**
  - [x] Implementar generador de solicitudes aleatorias
  - [x] Crear cliente de prueba para simulación de carga
  - [x] Añadir parámetros configurables (frecuencia, volumen, tipos)

- [x] **Hilos para manejo de concurrencia**
  - [x] Refactorizar DTI para procesar múltiples solicitudes simultáneas
  - [x] Crear mecanismo de timeout para solicitudes bloqueadas
  - [x] Resolver condiciones de carrera con locks apropiados


### Fase 2: Mejoras de Arquitectura ✅

- [x] **Implementación del patrón "Load Balancing Broker" ZeroMQ**
  - [x] Desarrollar intermediario con balanceo de carga
  - [x] Implementar un broker centralizado que distribuye trabajo entre los trabajadores
  - [x] Convertir DTI_servidor en un trabajador (worker)
  - [x] Convertir facultad en un cliente del broker
  - [x] Implementar seguimiento de solicitudes pendientes

- [x] **Tolerancia a fallos del Servidor Central**
  - [x] Implementar mecanismo de heartbeat para detección de fallos
  - [x] Desarrollar proceso de recuperación automática
  - [x] Crear sistema de respaldo y sincronización de estado

### Fase 3: Monitoreo y Optimización (Pendiente)

- [ ] **Health check en un nodo adicional**
  - [ ] Desarrollar nodo de monitoreo independiente
  - [ ] Implementar verificación periódica de todos los componentes
  - [ ] Crear panel de estado del sistema en tiempo real
  - [ ] Añadir sistema de alertas para problemas detectados

- [ ] **Métricas de desempeño**
  - [ ] Desarrollar sistema completo de recolección de métricas:
    - [ ] Tiempo de respuesta promedio (del servidor a las Facultades)
    - [ ] Tiempo de respuesta mínimo y máximo (del servidor a las Facultades)
    - [ ] Tiempo promedio desde que los programas hacen los requerimientos hasta que son atendidos
    - [ ] Por Programa: número de requerimientos atendidos satisfactoriamente
    - [ ] Por Programa: número de requerimientos rechazados por la Facultad
    - [ ] Throughput del sistema (solicitudes/segundo)
    - [ ] Tasas de utilización de recursos por nodo
    - [ ] Tiempo de recuperación ante fallos
  - [ ] Implementar visualización de métricas históricas
  - [ ] Crear reportes automáticos de rendimiento

## 📌 Arquitectura del Sistema

### Componentes Principales

1. **Programa Académico (`programa_academico.py`)**

   - Cliente que genera y envía solicitudes
   - Implementa patrón ZMQ REQ
   - Maneja interfaz de usuario y validaciones
   - Conecta con servidores de facultad mediante Round-Robin

2. **Facultad (`facultad.py`)**

   - Servidor intermediario
   - Recibe solicitudes de programas académicos (ZMQ REP)
   - Reenvía solicitudes al DTI (ZMQ REQ)
   - Valida facultades y programas

3. **DTI (`DTI_servidor.py` y `DTI_servidor_backup.py`)**
   - Servidor central de asignación y su respaldo
   - Gestiona base de datos de aulas
   - Procesa solicitudes de asignación con control de concurrencia
   - Implementa semáforos y locks para limitar solicitudes paralelas
   - Mantiene registro de operaciones
   - Permite limpieza del sistema
   - Sistema de heartbeat para tolerancia a fallos

## 📌 Configuración del Sistema

El archivo `config.py` centraliza todas las configuraciones:

```python
# IP y puerto del Servidor DTI (Central)
DTI_IP = "127.0.0.1"
DTI_PUERTO = "5570"
DTI_URL = f"tcp://{DTI_IP}:{DTI_PUERTO}"

# Servidores de Facultad
FACULTAD_1_URL = "tcp://127.0.0.1:5555"
FACULTAD_2_URL = "tcp://127.0.0.1:5556"

# Lista de URLs de facultades
FACULTAD_SERVERS = [FACULTAD_1_URL, FACULTAD_2_URL]

# URLs para el broker
BROKER_FRONTEND_URL = "tcp://127.0.0.1:5559"  # Broker hacia clientes (facultades)
BROKER_BACKEND_URL = "tcp://127.0.0.1:5560"   # Broker hacia workers (DTI)

# URLs para el sistema de heartbeat y sincronización
HEARTBEAT_URL = "tcp://127.0.0.1:5561"        # Para latidos del servidor principal
SYNC_URL = "tcp://127.0.0.1:5562"             # Para sincronización de estado

# Archivos del sistema
FACULTADES_FILE = "facultades.txt"
AULAS_REGISTRO_FILE = "aulas_registro.txt"
ASIGNACIONES_LOG_FILE = "asignaciones_log.txt"
RESPALDO_ESTADO_ARCHIVO = "estado_respaldo.txt"
```

### Estructura de Archivos

1. **`facultades.txt`**

   ```
   Facultad1, Programa1, Programa2, Programa3
   Facultad2, Programa1, Programa2
   ```

2. **`aulas_registro.txt`**

   ```csv
   id,tipo,estado,capacidad,facultad,programa,fecha_solicitud,fecha_asignacion
   S001,salón,disponible,40,,,,
   L001,laboratorio,disponible,30,,,,
   ```

3. **`asignaciones_log.txt`**
   ```
   2024-03-14 10:30:00 - INFO - Asignación exitosa: Facultad X, Programa Y
   ```

4. **`broker.log`**
   ```
   2025-05-20 15:30:00 - INFO - Nuevo trabajador registrado: a1b2c3d4
   2025-05-20 15:31:02 - INFO - Solicitud recibida de: Facultad de Ingeniería - Sistemas
   ```

5. **`servidor_respaldo.log`**
   ```
   2025-05-20 15:30:00 - INFO - Servidor de respaldo iniciado - v1.1
   2025-05-20 15:30:10 - INFO - Latido del servidor principal recibido
   2025-05-20 15:40:00 - WARNING - No se detectaron latidos en 10 segundos, activando servidor
   ```

6. **`estado_respaldo.txt`**
   ```csv
   id,tipo,estado,capacidad,facultad,programa,fecha_solicitud,fecha_asignacion
   S001,salón,disponible,40,,,,
   L001,laboratorio,ocupado,30,Ingeniería,Sistemas,2025-05-20 14:30:00,2025-05-20 14:30:05
   ```

## 📌 Funcionalidades Detalladas

### 1. Gestión de Aulas

```python
@dataclass
class Aula:
    id: str
    tipo: TipoAula
    estado: EstadoAula
    capacidad: int
    facultad: str = ""
    programa: str = ""
    fecha_solicitud: str = ""
    fecha_asignacion: str = ""
```

### 2. Estructura de Solicitudes

```python
# Solicitud de Programa Académico
solicitud = {
    "facultad": str,
    "programa": str,
    "semestre": int,
    "salones": int,
    "laboratorios": int,
    "capacidad_min": int
}

# Respuesta del DTI
respuesta = {
    "facultad": str,
    "programa": str,
    "semestre": int,
    "salones_asignados": list,
    "laboratorios_asignados": list,
    "notificacion": str  # opcional
}
```

### 3. Comando de Limpieza (DTI)

- Escribir "limpiar" en la consola del DTI para:
  - Reiniciar estado de todas las aulas
  - Borrar registros de asignaciones
  - Limpiar logs
  - Reconvertir aulas móviles a salones

## 📌 Instalación y Ejecución

### Requisitos

- Python 3.8+
- ZeroMQ

```bash
pip install pyzmq
```

### Pasos de Ejecución

1. **Iniciar Servidor DTI**

```bash
python3 DTI_servidor.py
```

2. **Iniciar Servidores de Facultad**

```bash
python3 facultad.py 1  # Primera facultad
python3 facultad.py 2  # Segunda facultad
```

3. **Ejecutar Programa Académico**

```bash
python3 programa_academico.py
```

+### Ejecución de la Simulación Mock (Modo Autónomo)

- +El sistema permite simular solicitudes concurrentes de programas académicos de manera autónoma, sin interacción manual, usando hilos para simular concurrencia realista.
- +Para ejecutar la simulación, usa:
- +`bash
+python3 programa_academico.py --simulacion A
+`
  +o +`bash
+python3 programa_academico.py --simulacion B
+`
- +**¿Qué hace cada modo?**
- +- `--simulacion A`: Selecciona 5 facultades aleatorias y, para cada programa académico de esas facultades, genera una solicitud mock de 7 salones y 2 laboratorios. Cada solicitud se envía desde un hilo independiente, con un retardo aleatorio entre 0.1 y 2 segundos.
  +- `--simulacion B`: Igual que el modo A, pero cada solicitud pide 10 salones y 4 laboratorios.
- +Cada hilo imprime en consola la respuesta recibida para su solicitud, permitiendo observar el comportamiento concurrente y la asignación de recursos en el sistema.
- +Si no se pasa el argumento `--simulacion`, el programa funciona en modo interactivo tradicional.

## 📌 Flujo de Comunicación

1. **Programa Académico → Facultad**

   - Conexión REQ-REP
   - Balanceo Round-Robin entre facultades
   - Validación de entrada de usuario

2. **Facultad → DTI**

   - Validación de facultad y programas
   - Reenvío de solicitud al DTI
   - Espera de respuesta

3. **DTI → Facultad → Programa**
   - Procesamiento de solicitud
   - Asignación de aulas
   - Actualización de registros
   - Respuesta en cascada

## 📌 Manejo de Errores

### Niveles de Error

1. **Validación de Entrada**

   ```python
   def solicitar_numero(mensaje, minimo=1, maximo=None):
       while True:
           try:
               valor = int(input(mensaje))
               if maximo and (valor < minimo or valor > maximo):
                   print(f"\n❌ Error: Ingrese un número entre {minimo} y {maximo}.")
               else:
                   return valor
           except ValueError:
               print("\n❌ Error: Debe ingresar un número válido.")
   ```

2. **Comunicación ZMQ**

   ```python
   try:
       socket.send_string(json.dumps(solicitud))
       respuesta = socket.recv_string()
   except zmq.ZMQError:
       print("\n❌ Error: Fallo en la comunicación con el servidor.")
   ```

3. **Procesamiento de Datos**
   ```python
   try:
       asignacion = json.loads(respuesta)
   except json.JSONDecodeError:
       print("\n❌ Error: Respuesta malformada del servidor.")
   ```

## 📌 Características Avanzadas

### 1. Aulas Móviles

- Conversión automática de salones a laboratorios
- Notificación al usuario
- Registro en logs

### 2. Estadísticas en Tiempo Real

- Total de aulas por tipo
- Estado de ocupación
- Uso de aulas móviles

### 3. Persistencia de Datos

- Registro continuo de asignaciones
- Archivo de logs detallado
- Base de datos de aulas actualizada

## 📌 Notas de Desarrollo

- Uso de dataclasses para estructuras de datos
- Implementación de enumeraciones para tipos y estados
- Manejo de concurrencia en DTI
- Sistema de logging estructurado

## 📌 Contribuciones y Mejoras Futuras

- Implementación de GUI
- Soporte para más tipos de aulas
- Sistema de reservas anticipadas
- Estadísticas avanzadas

## 🔄 Implementación del Load Balancing Broker

El sistema ahora implementa el patrón Load Balancing Broker de ZeroMQ, que permite distribuir eficientemente el trabajo entre múltiples trabajadores (instancias DTI).

### Componentes del patrón

1. **Load Balancer Broker (`load_balancer_broker.py`)**
   - Componente central que conecta clientes y trabajadores
   - Distribuye las solicitudes entre los trabajadores disponibles
   - Mantiene un registro de trabajadores activos
   - Muestra estadísticas en tiempo real sobre el estado del sistema

2. **Clientes (`facultad.py`)**
   - Se registran con el broker usando un identificador único
   - Envían solicitudes al broker junto con información de "distancia" para simulación
   - Reciben respuestas de los trabajadores a través del broker

3. **Trabajadores (`DTI_servidor.py`)**
   - Se registran con el broker como trabajadores disponibles
   - Procesan las solicitudes asignadas por el broker
   - Envían respuestas de vuelta al broker para ser entregadas a los clientes

### Arquitectura del Sistema

```
                   +----------------+
                   |  Programas     |
                   |  Académicos    |
                   +-------+--------+
                           |
                           v
            +-------------+-------------+
            |                           |
+-----------+  Facultad 1    Facultad 2 +-----------+
|           |  (Cliente)     (Cliente)  |           |
|           +-------------+-------------+           |
|                         |                         |
|                         v                         |
|           +-------------+-------------+           |
|           |                           |           |
|           |    Load Balancer Broker   |           |
|           |                           |           |
|           +-------------+-------------+           |
|                         |                         |
|                         v                         |
|           +-------------+-------------+           |
|           |                           |           |
+-----------+  DTI 1        DTI 2       +-----------+
            |  (Worker)     (Worker)    |
            +---------------------------+
```

### Cómo Ejecutar el Sistema con Load Balancing

1. Inicie el broker:
```
python load_balancer_broker.py
```

2. Inicie uno o más servidores DTI (trabajadores):
```
python DTI_servidor.py
```

3. Inicie las instancias de facultad (clientes):
```
python facultad.py 1
python facultad.py 2
```

4. Ejecute el programa académico para realizar solicitudes:

Para ejecutar la simulación automática:
```
python programa_academico.py --simulacion A
```

### Características del Load Balancing Broker

- **Balanceo de carga**: Distribución equitativa de solicitudes entre trabajadores disponibles
- **Identificación de clientes**: Cada instancia de facultad se identifica de forma única
- **Seguimiento de solicitudes**: Monitoreo en tiempo real del número de solicitudes pendientes
- **Simulación de distancia**: Simulación de distancias físicas para ayudar en la distribución de carga

## 🛡️ Sistema de Tolerancia a Fallos

El sistema implementa un mecanismo completo de tolerancia a fallos que permite mantener la disponibilidad del servicio incluso cuando uno de los servidores DTI falla.

### Componentes del Sistema de Tolerancia a Fallos

1. **Servidor de Respaldo (`DTI_servidor_backup.py`)**
   - Monitorea el estado del servidor principal mediante heartbeats
   - Se activa automáticamente cuando detecta que el servidor principal ha fallado
   - Sincroniza el estado con el servidor principal de forma periódica
   - Registra eventos de fallo y recuperación en logs detallados

2. **Mecanismo de Heartbeat**
   - Latidos periódicos entre el servidor principal y de respaldo
   - Detección rápida de fallos basada en timeout
   - Protocolo de comunicación robusto para evitar falsos positivos

3. **Sincronización de Estado**
   - Persistencia de estado en formato CSV para recuperación rápida
   - Transferencia incremental de cambios para eficiencia
   - Protocolo de sincronización bidireccional

### Arquitectura de Alta Disponibilidad

```
                +-------------------+
                |  Load Balancer    |
                |  Broker           |
                +--------+----------+
                         |
            +------------+------------+
            |                         |
     +------+-------+         +-------+------+
     |  DTI Primario |<------->| DTI Respaldo |
     | (activo)      |         | (standby)    |
     +--------------+          +--------------+
           ^                          ^
           |                          |
           v                          v
     +--------------+          +--------------+
     |   Estado     |          |   Estado     |
     |  Persistente |          |   Respaldo   |
     +--------------+          +--------------+
```

### Resolución de Problemas de Comunicación

Se han implementado mejoras significativas para resolver los problemas de comunicación:

1. **Registro de Workers Mejorado**
   - Se corrigió el problema de registros duplicados de workers en el broker
   - Implementación de formato correcto para mensajes READY (ahora usando `send_multipart([b"READY"])`)
   - Detección y eliminación automática de workers fantasma

2. **Gestión de Solicitudes Robusta**
   - Implementación de identificadores únicos para cada solicitud
   - Rastreo completo del ciclo de vida de las solicitudes
   - Semáforos para controlar el número máximo de solicitudes concurrentes

3. **Timeout y Recuperación**
   - Configuración de timeout para operaciones de envío/recepción
   - Mecanismos de reintento con backoff exponencial
   - Recuperación automática de conexiones perdidas

### Cómo Ejecutar el Sistema con Tolerancia a Fallos

Para aprovechar las capacidades de tolerancia a fallos:

1. Inicie el broker:
```
python load_balancer_broker.py
```

2. Inicie el servidor DTI principal:
```
python DTI_servidor.py
```

3. Inicie el servidor DTI de respaldo:
```
python DTI_servidor_backup.py
```

4. Inicie las instancias de facultad:
```
python facultad.py 1
python facultad.py 2
```

5. Ejecute el programa académico:
```
python programa_academico.py --simulacion A | B
```

Para probar la tolerancia a fallos, puede detener el servidor DTI principal en cualquier momento y observar cómo el servidor de respaldo se activa automáticamente para mantener el servicio sin interrupción.

## 🔍 Monitoreo y Diagnóstico

El sistema incluye herramientas completas para monitorear su funcionamiento y diagnosticar problemas.

### Archivos de Log

- **broker.log**: Registro de actividades del broker, conexiones y distribución de solicitudes
- **servidor_respaldo.log**: Eventos del servidor de respaldo, detección de fallos y sincronización
- **programa_academico.log**: Registro de solicitudes de los programas académicos
- **asignaciones_log.txt**: Historial detallado de asignaciones de aulas

### Comandos de Diagnóstico

Cada componente del sistema acepta comandos de diagnóstico:

1. **En el broker (`load_balancer_broker.py`)**
   - `status`: Muestra estado actual del broker y estadísticas
   - `limpiar`: Elimina registros de workers duplicados
   - `salir`: Detiene el broker de forma controlada

2. **En el servidor DTI (`DTI_servidor.py` y `DTI_servidor_backup.py`)**
   - `status`: Muestra estadísticas del servidor
   - `limpiar`: Reinicia el estado de todas las aulas
   - `salir`: Detiene el servidor de forma controlada

### Resolución de Problemas Comunes

| Problema | Posible Causa | Solución |
|----------|---------------|----------|
| Solicitudes no procesadas | Workers no registrados correctamente | Reiniciar los servidores DTI y verificar logs |
| Errores de comunicación | Timeout en conexiones | Aumentar timeouts en config.py e intentar nuevamente |
| Activación errónea del respaldo | Falsos positivos en detección de fallos | Ajustar INTERVALO_LATIDO y TIMEOUT_LATIDO en DTI_servidor_backup.py |
| Duplicación de workers | Reconexiones incorrectas | Ejecutar comando `limpiar` en el broker |
