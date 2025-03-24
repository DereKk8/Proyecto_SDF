# Sistema Distribuido de Asignación de Aulas 🎓🏫

Este sistema implementa un **Sistema Distribuido de Asignación de Aulas y Laboratorios** utilizando **Python** y **ZeroMQ**.  
Permite que **programas académicos** envíen solicitudes a **servidores de facultad**, los cuales procesan las solicitudes y asignan aulas de manera equitativa.  

---

## **📌 Características del sistema**
✅ **Comunicación Distribuida:** Implementa **Request-Reply Síncrono** con **ZeroMQ**.  
✅ **Balanceo de Carga:** Distribuye solicitudes entre **dos servidores de facultad** usando **Round-Robin**.  
✅ **Gestión de Errores:** Manejo de errores en **entrada de usuario**, **conexiones** y **formatos de datos**.  
✅ **Interfaz de Consola Intuitiva:** **Menús interactivos**, validaciones y formato claro de respuestas.  

---

## **📌 Requisitos**
Antes de ejecutar el sistema, asegúrate de tener instalado:

- **Python 3.8+**
- **ZeroMQ** (`pyzmq`)
- **Archivos de configuración (`config.py` y `facultades.txt`) correctamente configurados**

### **📌 Instalación de Dependencias**
Ejecuta el siguiente comando para instalar **ZeroMQ**:
```bash
pip install pyzmq
```

## **📌 Estructura del Proyecto**

📂 Proyecto_SDF/
├── programa_academico.py  ➝ Cliente (envía solicitudes de asignación)
├── facultad.py  ➝ Servidor (procesa solicitudes y asigna aulas)
├── config.py  ➝ Configuraciones generales (puertos, IPs, archivos)
├── facultades.txt  ➝ Base de datos con facultades y programas académicos
├── README.md  ➝ Este archivo con documentación del sistema

## **📌 Configuración**

Antes de ejecutar el sistema, verifica que el archivo `config.py` esté correctamente configurado:

```python
# Rutas de los servidores de facultad
ZMQ_FACULTAD_1 = "tcp://127.0.0.1:5555"
ZMQ_FACULTAD_2 = "tcp://127.0.0.1:5556"

# Lista de servidores de facultad para balanceo de carga
FACULTAD_SERVERS = [ZMQ_FACULTAD_1, ZMQ_FACULTAD_2]

# Archivo con las facultades y programas académicos
FACULTADES_FILE = "facultades.txt"
```

## **📌 Cómo Ejecutar el Sistema**

### 1. Iniciar los Servidores de Facultad

Cada servidor se ejecuta en una terminal separada:

```bash
python facultad.py 1
python facultad.py 2
```

Salida esperada:
```
✅ [Facultad] Servidor iniciado en tcp://127.0.0.1:5555. Esperando solicitudes...
✅ [Facultad] Servidor iniciado en tcp://127.0.0.1:5556. Esperando solicitudes...
```

### 2. Ejecutar un Programa Académico

Desde otra terminal, ejecuta el cliente:

```bash
python programa_academico.py
```

## **📌 Flujo de Solicitudes**

### Selección de Facultad y Programas

El usuario selecciona una facultad y uno o más programas académicos.

### Ingreso de Datos de Solicitud

Para cada programa académico, el usuario ingresa:
- Semestre
- Número de salones
- Número de laboratorios

## **📌 Manejo de Errores**

El sistema maneja diferentes tipos de errores:

| Error | Mensaje en pantalla |
|-------|---------------------|
| Archivo facultades.txt no encontrado | ❌ Error: No se encontró el archivo 'facultades.txt'. |
| Entrada inválida (texto en vez de número) | ❌ Error: Debe ingresar un número válido. |
| Facultad o programa inexistente | ❌ Error: Debe ingresar un número dentro del rango. |
| Respuesta malformada del servidor | ❌ Error: Respuesta malformada del servidor. |
| Servidor de facultad no disponible | ❌ Error: Fallo en la comunicación con el servidor. |

## **📌 Ejemplo Completo**

```
==================================================
Facultades disponibles:
==================================================
1. Facultad de Ingeniería
2. Facultad de Medicina
Ingrese el número de la facultad: 1

==================================================
Programas académicos en Facultad de Ingeniería:
==================================================
1. Ingeniería Civil
2. Ingeniería de Sistemas
Ingrese los números de los programas académicos separados por comas: 2

--------------------------------------------------
Ingresando datos para el programa: Ingeniería de Sistemas
--------------------------------------------------
Ingrese el semestre: 5
Ingrese el número de salones: 8
Ingrese el número de laboratorios: 3

##################################################
✅ Solicitud procesada para el programa: Ingeniería de Sistemas
📌 Facultad: Facultad de Ingeniería
📚 Semestre: 5
🏫 Salones asignados: 8
🔬 Laboratorios asignados: 3
##################################################
```

## **📌 Contribuciones**

Si deseas contribuir al proyecto, puedes hacer un fork del repositorio, realizar cambios y enviar un pull request.

## **📌 Notas Finales**

📌 **Tecnologías usadas:** Python, ZeroMQ.
📌 **Sistema distribuido:** 2 servidores de facultad, múltiples clientes.
📌 **Escalabilidad:** Se pueden agregar más servidores si es necesario.

🚀 ¡Listo! Ahora el sistema está funcionando correctamente.

## **📌 ¿Qué incluye este README?**
✅ **Explicación del sistema y tecnologías utilizadas**  
✅ **Instrucciones de instalación y ejecución**  
✅ **Ejemplo detallado de uso**  
✅ **Manejo de errores y flujo de solicitudes**  

Si tienes dudas o sugerencias, ¡házmelo saber! 😃