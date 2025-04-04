# Sistema Distribuido de Asignación de Aulas 🎓🏫

Sistema distribuido para asignación de aulas y laboratorios implementado con Python y ZeroMQ. Utiliza un patrón de comunicación Request-Reply entre tres componentes principales: Programas Académicos (clientes), Facultades (intermediarios) y DTI (servidor central).

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
python DTI_servidor.py
```

2. **Iniciar Servidores de Facultad**
```bash
python facultad.py 1  # Primera facultad
python facultad.py 2  # Segunda facultad
```

3. **Ejecutar Programa Académico**
```bash
python programa_academico.py
```

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
