# HERRAMIENTA-RENOMBRADOR-DE-ARCHVIOS WINDOWS
Este script de Python proporciona una interfaz gráfica (GUI) construida con Tkinter para renombrar archivos en masa de forma estructurada, siguiendo convenciones de nombres basadas en fechas y opciones personalizadas.

🚀 Características principales

✅ Renombrado basado en fecha: Permite renombrar archivos usando la fecha de creación original, una fecha fija definida por el usuario o una fecha aleatoria generada dinámicamente.

✅ Generación de fecha aleatoria personalizada: Se puede aleatorizar solo ciertas partes de la fecha, como la hora y los minutos, el mes y el día, los segundos, o generar una fecha completamente aleatoria.

✅ Actualización automática de metadatos: Una vez renombrado, el archivo recibe una nueva fecha de creación y modificación que coincide con el nombre asignado.

✅ Limpieza del nombre original: Si se elige conservar el nombre original del archivo, este se limpia automáticamente, eliminando caracteres especiales y dejando solo letras mayúsculas (A-Z) y números (0-9).

✅ Compatibilidad con Windows: Se emplea pywin32 para modificar los metadatos en sistemas Windows

1️⃣ Configuración global y carga de datos
python
CopiarEditar
import os
import time
import subprocess
import sys
import platform
import json
import random
import datetime
import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict
import pywintypes
import win32file
import win32con

🔹 ¿Qué hace este bloque?

Carga todas las bibliotecas necesarias para el funcionamiento del script. Se incluyen:
Módulos estándar de Python: os, time, sys, json, random, datetime, re
Manejo de archivos y fechas: pathlib.Path, collections.defaultdict
Interfaz gráfica (GUI): tkinter, filedialog, messagebox, ttk
Gestión de fechas en archivos (Windows): pywintypes, win32file, win32con

2️⃣ Variables globales y configuración inicial

python
CopiarEditar
carpeta_por_defecto = Path.home() / "Downloads"
config_file = Path.home() / ".renombrador_config.json"
texto_prefijo = ""
texto_sufijo = ""
formato_seleccionado = None
textos_frecuentes = []
tipo_fecha = "original"
fecha_fija = ""

🔹 ¿Qué hace este bloque?

Define las variables que controlan el estado del programa:
carpeta_por_defecto → Directorio predeterminado donde se renombrarán los archivos.
config_file → Archivo JSON donde se guardan las configuraciones del usuario.
texto_prefijo / texto_sufijo → Textos opcionales que se pueden añadir antes o después del nombre del archivo.
formato_seleccionado → Define el formato de fecha usado en el renombrado.
textos_frecuentes → Lista de textos que el usuario usa con frecuencia para los nombres de archivos.
tipo_fecha → Controla si se usará la fecha original del archivo, una fecha fija o una aleatoria.
fecha_fija → Fecha específica que el usuario puede definir manualmente.

3️⃣ Cargar y guardar configuraciones

python
CopiarEditar
def cargar_textos_frecuentes():
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('textos_frecuentes', [])
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    return []

def guardar_textos_frecuentes(textos):
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({'textos_frecuentes': textos}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")

🔹 ¿Qué hace este bloque?

Gestiona la carga y el guardado de los textos frecuentes en un archivo JSON.
cargar_textos_frecuentes() → Carga los textos que el usuario ha guardado previamente. Si el archivo de configuración no existe, devuelve una lista vacía.
guardar_textos_frecuentes(textos) → Guarda los textos en el archivo JSON en un formato estructurado.

📌 ¿Por qué se usa JSON?

Es un formato ligero, estructurado y fácilmente editable, ideal para almacenar configuraciones sin necesidad de bases de datos.

4️⃣ Verificación de instalación de PyWin32 (Windows)

python
CopiarEditar
def verificar_instalacion_pywin32():
    try:
        import win32file, win32con
        return True
    except ImportError:
        if messagebox.askyesno("Instalación Requerida", "El módulo pywin32 no está instalado. ¿Deseas instalarlo ahora?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            return True
        return False

🔹 ¿Qué hace este bloque?

En Windows, este script necesita pywin32 para modificar los metadatos de los archivos.
Si pywin32 no está instalado, el script ofrece instalarlo automáticamente.
Usa subprocess para ejecutar pip install pywin32.

📌 ¿Por qué esto es útil?

Permite que usuarios sin conocimientos avanzados de Python puedan instalar automáticamente las dependencias necesarias sin abrir la terminal.
