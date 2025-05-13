# Sistema Distribuido de Asignación de Aulas 🎓🏫

Sistema distribuido para asignación de aulas y laboratorios implementado con Python y ZeroMQ. Utiliza un patrón de comunicación Request-Reply entre tres componentes principales: Programas Académicos (clientes), Facultades (intermediarios) y DTI (servidor central).

## 📋 TODOs y Plan de Desarrollo

A continuación se presenta la lista de tareas pendientes ordenadas por prioridad para el desarrollo incremental del sistema:

### Fase 1: Funcionalidad Base y Simulación

- [x] **Módulo del cliente con solicitudes "mock"**

  - [x] Implementar generador de solicitudes aleatorias
  - [x] Crear cliente de prueba para simulación de carga
  - [x] Añadir parámetros configurables (frecuencia, volumen, tipos)

- [x] **Hilos para manejo de concurrencia**
  - [x] Refactorizar DTI para procesar múltiples solicitudes simultáneas
  - [x] Crear mecanismo de timeout para solicitudes bloqueadas
  - ** Bug
      Mirar como se estan realizando las solicitudes de los programas y porque no hay condiciones de carrera (sin Locks)?


### Fase 2: Mejoras de Arquitectura

- [ ] **Implementación del patrón "Load Balancing Broker" ZeroMQ**

  - [ ] Desarrollar intermediario con balanceo de carga
  - [ ] Permitir selección de modelo de comunicación en tiempo de ejecución:
    - [ ] Modelo actual (REQ - REPLY)
    - [ ] Modelo broker centralizado
  - [ ] Añadir interfaz para selección de modelo de comunicación

- [ ] **Tolerancia a fallos del Servidor Central (Nodo 5)**
  - [ ] Implementar mecanismo de heartbeat para detección de fallos
  - [ ] Desarrollar proceso de recuperación automática
  - [ ] Crear sistema de respaldo y sincronización de estado

### Fase 3: Monitoreo y Optimización

- [ ] **Health check en un nodo adicional (Nodo 5)**

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
  - [ ] Añadir detección de cuellos de botella

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

3. **DTI (`DTI_servidor.py`)**
   - Servidor central de asignación
   - Gestiona base de datos de aulas
   - Procesa solicitudes de asignación
   - Mantiene registro de operaciones
   - Permite limpieza del sistema

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

# Archivos del sistema
FACULTADES_FILE = "facultades.txt"
AULAS_REGISTRO_FILE = "aulas_registro.txt"
ASIGNACIONES_LOG_FILE = "asignaciones_log.txt"
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
