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

# =============================================================================
# VARIABLES GLOBALES Y CONFIGURACIÓN INICIAL
# =============================================================================
carpeta_por_defecto = Path.home() / "Downloads"
config_file = Path.home() / ".renombrador_config.json"
texto_prefijo = ""
texto_sufijo = ""
formato_seleccionado = None  # Formato de fecha: "AAAAMMDD HHMM" o "AAAAMMDD HHMMSS"
textos_frecuentes = []
# Variables para reemplazo de texto
texto_buscar = ""
texto_reemplazar = ""
# Variables para la selección del tipo de fecha: "original", "fija" o "aleatoria"
tipo_fecha = "original"
fecha_fija = ""  # Formato: "YYYYMMDD HHMMSS"

# Variables para configuración de aleatorización parcial de fecha (en modo 'aleatoria')
# Si random_completo está marcado, se ignoran los demás.
random_completo = False  
random_md = False        # Aleatorizar Mes y Día
random_hm = False        # Aleatorizar Hora y Minuto
random_s = False         # Aleatorizar Segundos

# =============================================================================
# VERIFICACIÓN DE INSTALACIÓN DEL MÓDULO PYWIN32 (SO WINDOWS)
# =============================================================================
def verificar_instalacion_pywin32():
    # Se encarga de verificar si el módulo pywin32 está instalado; de lo contrario, ofrece instalarlo.
    try:
        import win32file, win32con
        return True
    except ImportError:
        if messagebox.askyesno("Instalación Requerida", "El módulo pywin32 no está instalado. ¿Deseas instalarlo ahora?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            return True
        return False

# =============================================================================
# FUNCIONES PARA MODIFICAR LAS FECHAS DE LOS ARCHIVOS (WIN Y MAC)
# =============================================================================
def cambiar_fecha_archivo_win(file_path, new_creation_time):
    # Cambia la fecha de creación, modificación y acceso de un archivo en Windows.
    new_time = pywintypes.Time(new_creation_time)
    try:
        handle = win32file.CreateFile(
            str(file_path),
            win32con.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None
        )
        win32file.SetFileTime(handle, new_time, new_time, new_time)
        handle.close()
    except Exception as e:
        print(f"Error al cambiar la fecha de {file_path}: {e}")

def cambiar_fecha_archivo_mac(file_path, new_creation_time):
    # Cambia la fecha de modificación de un archivo en macOS.
    os.utime(file_path, (new_creation_time, new_creation_time))

# =============================================================================
# CREACIÓN DE LA INTERFAZ PRINCIPAL
# =============================================================================
def crear_interfaz_principal():
    global ventana_principal, etiqueta_carpeta, formato_seleccionado, texto_prefijo, texto_sufijo
    global boton_formato1, boton_formato2, tipo_fecha, fecha_fija, random_frame

    ventana = tk.Tk()
    ventana_principal = ventana
    ventana.title("Renombrador de Archivos")
    ventana.geometry("800x800")
    ventana.minsize(600, 600)
    ventana.resizable(True, True)
    theme = set_dark_theme()
    ventana.configure(bg=theme["bg"])

    # Vincular eventos
    ventana.bind("<Configure>", on_resize)
    ventana.bind("<F11>", toggle_fullscreen)

    # Configuración del grid en la ventana principal
    ventana.grid_rowconfigure(0, weight=1)
    ventana.grid_columnconfigure(0, weight=1)

    # --- CONFIGURACIÓN DEL SCROLL ---
    # Se crea un frame contenedor para el canvas y la scrollbar
    contenedor_canvas = tk.Frame(ventana, bg=theme["bg"])
    contenedor_canvas.grid(row=0, column=0, sticky="nsew")

    # Canvas que contendrá el frame con el contenido
    canvas = tk.Canvas(contenedor_canvas, bg=theme["bg"], highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    # Barra de desplazamiento vertical
    scrollbar = tk.Scrollbar(contenedor_canvas, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Configuración del canvas para el scroll
    canvas.configure(yscrollcommand=scrollbar.set)

    # Frame donde se agregará el contenido (todos los widgets originales)
    contenedor = tk.Frame(canvas, bg=theme["bg"], padx=20, pady=20)
    # Se inserta el frame en el canvas
    canvas.create_window((0, 0), window=contenedor, anchor="nw")

    # Actualizar la región de scroll cuando el tamaño del contenedor cambie
    contenedor.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Opcional: Permitir el scroll con la rueda del mouse en el canvas
    def _on_mousewheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # --- CONTENIDO ORIGINAL ---
    # Encabezado
    header_frame = tk.Frame(contenedor, bg=theme["bg"])
    header_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
    tk.Label(header_frame, text="Renombrador de Archivos", font=("SF Pro Display", 18, "bold"),
             bg=theme["bg"], fg=theme["fg"]).pack(anchor="w")
    tk.Label(header_frame, text="Herramienta desarrollada por Andrey Bergert", font=("SF Pro", 11),
             bg=theme["bg"], fg="#BBBBBB").pack(anchor="w")

    # Sección de selección de carpeta
    seccion_carpeta = tk.LabelFrame(contenedor, text="Selección de Carpeta", bg=theme["bg"],
                                    fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_carpeta.grid(row=1, column=0, sticky="ew", pady=10)
    global etiqueta_carpeta
    etiqueta_carpeta = tk.Label(seccion_carpeta, text=f"Carpeta predeterminada: {carpeta_por_defecto}",
                                bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11))
    etiqueta_carpeta.pack(anchor="w", pady=5)
    etiqueta_carpeta.carpeta_actual = carpeta_por_defecto
    frame_botones_carpeta = tk.Frame(seccion_carpeta, bg=theme["bg"])
    frame_botones_carpeta.pack(fill="x", pady=5)
    tk.Button(frame_botones_carpeta, text="Cambiar carpeta predeterminada", bg=theme["button_bg"],
              fg=theme["fg"], font=("SF Pro", 11), relief="flat", padx=10, pady=5,
              activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
              command=cambiar_carpeta_por_defecto).pack(side="left", padx=5, expand=True, fill="x")
    tk.Button(frame_botones_carpeta, text="Seleccionar otra carpeta", bg=theme["button_bg"],
              fg=theme["fg"], font=("SF Pro", 11), relief="flat", padx=10, pady=5,
              activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
              command=seleccionar_carpeta_puntual).pack(side="left", padx=5, expand=True, fill="x")

    # Sección de formato de renombrado
    seccion_formato = tk.LabelFrame(contenedor, text="Formato de Renombrado", bg=theme["bg"],
                                    fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_formato.grid(row=2, column=0, sticky="ew", pady=10)
    tk.Label(seccion_formato, text="Seleccione el formato de fecha:", bg=theme["bg"],
             fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w", pady=5)
    frame_botones_formato = tk.Frame(seccion_formato, bg=theme["bg"])
    frame_botones_formato.pack(fill="x", pady=10)
    boton_formato1 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMM", bg=theme["accent_bg"],
                               fg=theme["fg"], font=("SF Pro", 12), relief="flat", padx=10, pady=10,
                               activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
                               command=lambda: seleccionar_formato("AAAAMMDD HHMM"))
    boton_formato1.pack(side="left", padx=5, expand=True, fill="both")
    boton_formato2 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMMSS", bg=theme["accent_bg"],
                               fg=theme["fg"], font=("SF Pro", 12), relief="flat", padx=10, pady=10,
                               activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
                               command=lambda: seleccionar_formato("AAAAMMDD HHMMSS"))
    boton_formato2.pack(side="left", padx=5, expand=True, fill="both")

    # Sección para definir el tipo de fecha a asignar
    frame_tipo_fecha = tk.LabelFrame(seccion_formato, text="Tipo de Fecha a Asignar", bg=theme["bg"],
                                     fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=10)
    frame_tipo_fecha.pack(fill="x", pady=10)
    tipo_fecha_var = tk.StringVar(value="original")
    tk.Radiobutton(frame_tipo_fecha, text="Usar fecha original", variable=tipo_fecha_var, value="original",
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w")
    tk.Radiobutton(frame_tipo_fecha, text="Usar fecha fija", variable=tipo_fecha_var, value="fija",
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w")
    entry_fecha_fija = tk.Entry(frame_tipo_fecha, font=("SF Pro", 11), bg="#252525", fg="white",
                                insertbackground="white", relief="flat", borderwidth=3)
    entry_fecha_fija.pack(fill="x", pady=5)
    tk.Label(frame_tipo_fecha, text="(Formato: YYYYMMDD HHMMSS)", bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 10)).pack(anchor="w")
    tk.Radiobutton(frame_tipo_fecha, text="Fecha y hora aleatoria", variable=tipo_fecha_var, value="aleatoria",
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w")

    # Frame adicional para opciones de aleatorización (visible solo si se selecciona "aleatoria")
    random_frame = tk.Frame(frame_tipo_fecha, bg=theme["bg"])
    random_frame.pack(fill="x", pady=5)
    global_var_completo = tk.BooleanVar(value=False)
    global_var_md = tk.BooleanVar(value=False)
    global_var_hm = tk.BooleanVar(value=False)
    global_var_s = tk.BooleanVar(value=False)
    tk.Checkbutton(random_frame, text="Aleatorización completa", variable=global_var_completo,
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 10)).grid(row=0, column=0, sticky="w", padx=5)
    tk.Checkbutton(random_frame, text="Aleatorizar Mes y Día", variable=global_var_md,
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 10)).grid(row=0, column=1, sticky="w", padx=5)
    tk.Checkbutton(random_frame, text="Aleatorizar Hora y Minuto", variable=global_var_hm,
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 10)).grid(row=0, column=2, sticky="w", padx=5)
    tk.Checkbutton(random_frame, text="Aleatorizar Segundos", variable=global_var_s,
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 10)).grid(row=0, column=3, sticky="w", padx=5)

    def actualizar_opciones_aleatorias():
        global random_completo, random_md, random_hm, random_s
        random_completo = global_var_completo.get()
        random_md = global_var_md.get()
        random_hm = global_var_hm.get()
        random_s = global_var_s.get()

    # Sección de personalización de texto
    seccion_texto = tk.LabelFrame(contenedor, text="Personalización de Texto", bg=theme["bg"],
                                  fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_texto.grid(row=3, column=0, sticky="ew", pady=10)
    tk.Label(seccion_texto, text="Texto personalizado (antes y después de la fecha):",
             bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w", pady=5)
    texto_actual = tk.Label(seccion_texto,
                            text=f"Antes: {'Ninguno' if not texto_prefijo else texto_prefijo}\nDespués: {'Ninguno' if not texto_sufijo else texto_sufijo}",
                            bg=theme["bg"], fg="#BBBBBB", font=("SF Pro", 11, "italic"))
    texto_actual.pack(anchor="w", pady=5)
    def actualizar_etiqueta_texto():
        texto_actual.config(text=f"Antes: {'Ninguno' if not texto_prefijo else texto_prefijo}\nDespués: {'Ninguno' if not texto_sufijo else texto_sufijo}")
    tk.Button(seccion_texto, text="Personalizar texto", bg=theme["button_bg"],
              fg=theme["fg"], font=("SF Pro", 11), relief="flat", padx=10, pady=5,
              activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
              command=lambda: [personalizar_texto(), actualizar_etiqueta_texto()]).pack(anchor="w", pady=5)
    mantener_original = tk.BooleanVar(value=False)
    tk.Checkbutton(seccion_texto, text="Mantener nombre original (solo letras y números)",
                   variable=mantener_original, bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11),
                   selectcolor="#252525", activebackground=theme["bg"], activeforeground=theme["fg"]).pack(anchor="w", pady=5)

    # Sección de ejecución
    seccion_ejecutar = tk.LabelFrame(contenedor, text="Ejecutar", bg=theme["bg"],
                                     fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_ejecutar.grid(row=4, column=0, sticky="ew", pady=10)
    def ejecutar_renombrado():
        global tipo_fecha, fecha_fija
        actualizar_opciones_aleatorias()
        tipo_fecha = tipo_fecha_var.get()
        if tipo_fecha == "fija":
            fecha_fija = entry_fecha_fija.get().strip()
        else:
            fecha_fija = ""
        if formato_seleccionado is None:
            messagebox.showerror("Error", "Debes seleccionar un formato de fecha primero.")
            return
        renombrar_archivos(formato_seleccionado, etiqueta_carpeta.carpeta_actual, texto_prefijo, texto_sufijo, mantener_original.get())
    tk.Button(seccion_ejecutar, text="RENOMBRAR ARCHIVOS", bg="#007BFF", fg="white",
              font=("SF Pro", 14, "bold"), relief="flat", padx=10, pady=15,
              activebackground="#0069D9", activeforeground="white", command=ejecutar_renombrado).pack(fill="x", pady=5)

    # Botón de aviso legal
    aviso_legal_frame = tk.Frame(contenedor, bg=theme["bg"])
    aviso_legal_frame.grid(row=5, column=0, sticky="ew", pady=10)
    tk.Button(aviso_legal_frame, text="AVISO LEGAL", 
               bg="#555555", fg="white", font=("SF Pro", 10, "bold"),
               relief="flat", padx=20, pady=12, activebackground="#555555",
               activeforeground="white", command=mostrar_avisolegal).pack(fill="x", pady=5)

    # Pie de página
    tk.Label(contenedor, text="3.0", bg=theme["bg"], fg="#8a8a8d", font=("SF Pro", 10)).grid(row=6, column=0, sticky="w", pady=(5, 0))

    center_window(ventana)
    return ventana

def seleccionar_formato(formato):
    global formato_seleccionado
    formato_seleccionado = formato
    theme = set_dark_theme()
    if formato == "AAAAMMDD HHMM":
        boton_formato1.config(bg="#666666", relief="sunken")
        boton_formato2.config(bg=theme["accent_bg"], relief="flat")
    else:  # "AAAAMMDD HHMMSS"
        boton_formato1.config(bg=theme["accent_bg"], relief="flat")
        boton_formato2.config(bg="#666666", relief="sunken")

# =============================================================================
# FUNCIONES PARA LA ESCALABILIDAD DINÁMICA DE LA INTERFAZ
# =============================================================================
def on_resize(event):
    # Función que recalcula el tamaño de fuente en función del ancho de la ventana.
    new_size = max(10, int(event.width / 80))
    new_font = ("SF Pro", new_size)
    # Se actualizan todos los widgets; se puede optimizar según necesidad.
    def update_widget_font(widget):
        try:
            current_font = widget.cget("font")
            widget.config(font=new_font)
        except:
            pass
        for child in widget.winfo_children():
            update_widget_font(child)
    update_widget_font(ventana_principal)

# =============================================================================
# FUNCIONES DE CONFIGURACIÓN DE TEXTOS FRECUENTES
# =============================================================================
def cargar_textos_frecuentes():
    # Carga la configuración de textos frecuentes desde un archivo JSON.
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('textos_frecuentes', [])
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    return []

def guardar_textos_frecuentes(textos):
    # Guarda los textos frecuentes en un archivo JSON.
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({'textos_frecuentes': textos}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")

textos_frecuentes = cargar_textos_frecuentes()

# =============================================================================
# FUNCIÓN DE LIMPIEZA DEL NOMBRE ORIGINAL
# =============================================================================
def limpiar_nombre_original(nombre):
    # Convierte el nombre a mayúsculas y elimina cualquier carácter que no sea A-Z o 0-9.
    nombre = nombre.upper()
    return re.sub(r'[^\w\s]', '', nombre)

# =============================================================================
# FUNCIONES PARA GENERAR FECHA ALEATORIA CON CONTROL PARCIAL
# =============================================================================
def generar_fecha_aleatoria(fecha_base, random_options):
    """
    Dada una fecha base (datetime), devuelve una nueva fecha en la que se aleatorizan
    determinados componentes según random_options, que es un diccionario con claves:
    'md' para Mes y Día, 'hm' para Hora y Minuto, 's' para Segundos.
    Si random_options['completo'] es True, se genera una fecha totalmente aleatoria.
    """
    if random_options.get('completo'):
        # Aleatorización completa, sin tomar la fecha base en cuenta.
        return datetime.datetime(
            random.randint(2000, 2030),
            random.randint(1, 12),
            random.randint(1, 28),  # Para evitar problemas con meses de 30 o 31 días.
            random.randint(0, 23),
            random.randint(0, 59),
            random.randint(0, 59)
        )
    # Se parte de la fecha base
    anio = fecha_base.year
    mes = fecha_base.month
    dia = fecha_base.day
    hora = fecha_base.hour
    minuto = fecha_base.minute
    segundo = fecha_base.second

    if random_options.get('md'):
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)  # Valor seguro para todos los meses.
    if random_options.get('hm'):
        hora = random.randint(0, 23)
        minuto = random.randint(0, 59)
    if random_options.get('s'):
        segundo = random.randint(0, 59)
    return datetime.datetime(anio, mes, dia, hora, minuto, segundo)

# =============================================================================
# FUNCIÓN PARA OBTENER LA FECHA FORMATEADA SEGÚN EL FORMATO SELECCIONADO
# =============================================================================
def obtener_fecha(formato, creation_time, incremento=0):
    # Convierte la marca de tiempo en una cadena formateada. Se puede aplicar un incremento para diferenciar archivos.
    t = time.localtime(creation_time + incremento)
    base_time = time.strftime('%Y%m%d %H%M%S', t)
    return base_time if formato == "AAAAMMDD HHMMSS" else base_time[:-2]

# =============================================================================
# FUNCIÓN PRINCIPAL DE RENOMBRADO DE ARCHIVOS
# =============================================================================
def renombrar_archivos(formato, carpeta, texto_prefijo="", texto_sufijo="", mantener_original=False):
    global tipo_fecha, fecha_fija, texto_buscar, texto_reemplazar, random_completo, random_md, random_hm, random_s
    fecha_dict = defaultdict(list)

    # Ventana de progreso con diseño adaptable
    progress_window = tk.Toplevel(ventana_principal)
    progress_window.title("Procesando archivos")
    progress_window.geometry("600x150")
    progress_window.minsize(400, 100)
    progress_window.configure(bg="#1E1E1E")
    progress_window.grid_rowconfigure(0, weight=1)
    progress_window.grid_columnconfigure(0, weight=1)
    progress_window.transient(ventana_principal)
    progress_window.grab_set()

    progress_frame = tk.Frame(progress_window, bg="#1E1E1E")
    progress_frame.grid(sticky="nsew", padx=10, pady=10)
    progress_label = tk.Label(progress_frame, text="Iniciando proceso...", font=("SF Pro", 12),
                                bg="#1E1E1E", fg="white")
    progress_label.grid(row=0, column=0, pady=(10, 5))
    progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate", length=300)
    progress_bar.grid(row=1, column=0, pady=5)
    progress_bar.start(10)
    ventana_principal.update()

    # Se obtienen todos los archivos de la carpeta seleccionada.
    all_files = [f for f in Path(carpeta).iterdir() if f.is_file()]
    for i, file_path in enumerate(all_files):
        progress_label.config(text=f"Analizando archivo {i+1} de {len(all_files)}")
        ventana_principal.update()
        # Selección de fecha según el tipo definido.
        if tipo_fecha == "original":
            creation_time = file_path.stat().st_ctime
        elif tipo_fecha == "fija":
            try:
                creation_time = time.mktime(time.strptime(fecha_fija, '%Y%m%d %H%M%S'))
            except Exception:
                creation_time = file_path.stat().st_ctime
        elif tipo_fecha == "aleatoria":
            # Si se está en modo aleatorio, usamos la fecha original como base para la aleatorización parcial.
            base_date = datetime.datetime.fromtimestamp(file_path.stat().st_ctime)
            options = {
                'completo': random_completo,
                'md': random_md,
                'hm': random_hm,
                's': random_s
            }
            nueva_fecha = generar_fecha_aleatoria(base_date, options)
            creation_time = time.mktime(nueva_fecha.timetuple())
        formatted_time = obtener_fecha(formato, creation_time)
        fecha_dict[formatted_time].append(file_path)

    total_files = sum(len(v) for v in fecha_dict.values())
    processed = 0
    progress_bar.stop()
    progress_bar.config(mode="determinate", maximum=total_files, value=0)

    for fecha, archivos in fecha_dict.items():
        for i, file_path in enumerate(archivos):
            # Repetimos el proceso de selección de fecha para cada archivo.
            if tipo_fecha == "original":
                creation_time = file_path.stat().st_ctime
            elif tipo_fecha == "fija":
                try:
                    creation_time = time.mktime(time.strptime(fecha_fija, '%Y%m%d %H%M%S'))
                except Exception:
                    creation_time = file_path.stat().st_ctime
            elif tipo_fecha == "aleatoria":
                base_date = datetime.datetime.fromtimestamp(file_path.stat().st_ctime)
                options = {
                    'completo': random_completo,
                    'md': random_md,
                    'hm': random_hm,
                    's': random_s
                }
                nueva_fecha = generar_fecha_aleatoria(base_date, options)
                creation_time = time.mktime(nueva_fecha.timetuple())
            formatted_time = obtener_fecha(formato, creation_time, i)
            file_extension = file_path.suffix
            # Si se mantiene el nombre original, se limpia para eliminar caracteres especiales.
            original_part = f" {limpiar_nombre_original(file_path.stem)}" if mantener_original else ""
            new_name = (f"{texto_prefijo} " if texto_prefijo else "") + \
           formatted_time + \
           (f" {texto_sufijo}" if texto_sufijo else "") + \
           original_part + file_extension
            # Aplicar reemplazo de texto si está definido.
            if texto_buscar and texto_buscar in new_name:
                new_name = new_name.replace(texto_buscar, texto_reemplazar)
            new_file_path = file_path.parent / new_name

            counter = 1
            # Evitar colisiones en nombres: si el nuevo nombre ya existe, se añade un incremento.
            while new_file_path.exists():
                formatted_time = obtener_fecha(formato, creation_time, i + counter)
                new_name = (f"{texto_prefijo} " if texto_prefijo else "") + \
                           formatted_time + \
                           (f" {texto_sufijo}" if texto_sufijo else "") + \
                           original_part + file_extension
                if texto_buscar and texto_buscar in new_name:
                    new_name = new_name.replace(texto_buscar, texto_reemplazar)
                new_file_path = file_path.parent / new_name
                counter += 1

            try:
                progress_label.config(text=f"Renombrando: {file_path.name} → {new_name}")
                ventana_principal.update()
                os.rename(file_path, new_file_path)
                # Se actualizan las fechas embebidas del archivo para que coincidan con el nombre asignado.
                new_creation_time = time.mktime(time.strptime(formatted_time, '%Y%m%d %H%M%S'))
                if platform.system() == "Windows":
                    cambiar_fecha_archivo_win(new_file_path, new_creation_time)
                elif platform.system() == "Darwin":
                    cambiar_fecha_archivo_mac(new_file_path, new_creation_time)
                processed += 1
                progress_bar["value"] = processed
                ventana_principal.update()
            except PermissionError:
                print(f"Error: {file_path} está en uso.")
            except FileExistsError:
                print(f"Error: {new_file_path} ya existe.")

    progress_window.destroy()
    messagebox.showinfo("Proceso Completado", f"Se han renombrado {processed} archivos correctamente.")

# =============================================================================
# FUNCIONES DE UTILIDAD PARA LA INTERFAZ (CENTRAR VENTANAS, TEMA OSCURO, ETC.)
# =============================================================================
def toggle_fullscreen(event=None):
    # Alterna entre pantalla completa y ventana normal.
    is_full = ventana_principal.attributes("-fullscreen")
    ventana_principal.attributes("-fullscreen", not is_full)

def center_window(window):
    # Centra una ventana en la pantalla.
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def set_dark_theme():
    # Define y retorna un diccionario con la configuración del tema oscuro.
    return {
        "bg": "#1E1E1E",
        "fg": "white",
        "button_bg": "#444444",
        "button_active_bg": "#555555",
        "frame_bg": "#252525",
        "accent_bg": "#666666"
    }

# =============================================================================
# FUNCIÓN PARA LA PERSONALIZACIÓN DE TEXTOS (ANTES/DESPUÉS, REEMPLAZO, FAVORITOS)
# =============================================================================
def personalizar_texto():
    global textos_frecuentes, texto_prefijo, texto_sufijo, texto_buscar, texto_reemplazar
    ventana_texto = tk.Toplevel(ventana_principal)
    ventana_texto.title("Personalizar Texto")
    ventana_texto.geometry("600x600")
    ventana_texto.minsize(400, 400)
    ventana_texto.configure(bg="#1E1E1E")
    ventana_texto.grid_rowconfigure(0, weight=1)
    ventana_texto.grid_columnconfigure(0, weight=1)
    center_window(ventana_texto)
    ventana_texto.transient(ventana_principal)
    ventana_texto.grab_set()

    frame_contenido = tk.Frame(ventana_texto, bg="#1E1E1E", padx=20, pady=20)
    frame_contenido.grid(sticky="nsew")
    
    tk.Label(frame_contenido, text="Personalizar Texto para Archivos", 
             font=("SF Pro", 12, "bold"), bg="#1E1E1E", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

    tk.Label(frame_contenido, text="Texto a añadir ANTES de la fecha:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).grid(row=1, column=0, sticky="w", pady=5)
    entrada_prefijo = tk.Entry(frame_contenido, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_prefijo.grid(row=1, column=1, sticky="ew", pady=5)
    entrada_prefijo.insert(0, texto_prefijo)

    tk.Label(frame_contenido, text="Texto a añadir DESPUÉS de la fecha:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).grid(row=2, column=0, sticky="w", pady=5)
    entrada_sufijo = tk.Entry(frame_contenido, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_sufijo.grid(row=2, column=1, sticky="ew", pady=5)
    entrada_sufijo.insert(0, texto_sufijo)

    tk.Label(frame_contenido, text="Texto a buscar (para reemplazar):", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).grid(row=3, column=0, sticky="w", pady=5)
    entrada_buscar = tk.Entry(frame_contenido, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_buscar.grid(row=3, column=1, sticky="ew", pady=5)
    tk.Label(frame_contenido, text="Texto de reemplazo:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).grid(row=4, column=0, sticky="w", pady=5)
    entrada_reemplazar = tk.Entry(frame_contenido, font=("SF Pro", 11), bg="#252525", fg="white",
                                  insertbackground="white", relief="flat", borderwidth=3)
    entrada_reemplazar.grid(row=4, column=1, sticky="ew", pady=5)

    tk.Label(frame_contenido, text="Textos frecuentes:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).grid(row=5, column=0, sticky="w", pady=5)
    frame_lista = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_lista.grid(row=5, column=1, sticky="nsew", pady=5)
    lista_textos = tk.Listbox(frame_lista, font=("SF Pro", 11), bg="#252525", fg="white",
                              relief="flat", borderwidth=0, selectbackground="#555555",
                              height=5)
    lista_textos.pack(side="left", fill="both", expand=True)
    scrollbar = tk.Scrollbar(frame_lista, command=lista_textos.yview)
    scrollbar.pack(side="right", fill="y")
    lista_textos.config(yscrollcommand=scrollbar.set)
    for texto in textos_frecuentes:
        lista_textos.insert(tk.END, texto)

    def seleccionar_texto():
        seleccion = lista_textos.curselection()
        if seleccion:
            txt = lista_textos.get(seleccion[0])
            entrada_prefijo.delete(0, tk.END)
            entrada_prefijo.insert(0, txt)
    def añadir_texto():
        nuevo = entrada_prefijo.get().strip()
        if nuevo and nuevo not in textos_frecuentes:
            textos_frecuentes.append(nuevo)
            lista_textos.insert(tk.END, nuevo)
            guardar_textos_frecuentes(textos_frecuentes)
    def eliminar_texto():
        seleccion = lista_textos.curselection()
        if seleccion:
            txt = lista_textos.get(seleccion[0])
            if txt in textos_frecuentes:
                textos_frecuentes.remove(txt)
                lista_textos.delete(seleccion[0])
                guardar_textos_frecuentes(textos_frecuentes)
                
    frame_botones_lista = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_botones_lista.grid(row=6, column=0, columnspan=2, pady=5)
    tk.Button(frame_botones_lista, text="Usar Seleccionado", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=seleccionar_texto).pack(side="left", padx=5)
    tk.Button(frame_botones_lista, text="Añadir a Favoritos", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=añadir_texto).pack(side="left", padx=5)
    tk.Button(frame_botones_lista, text="Eliminar", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=eliminar_texto).pack(side="left", padx=5)

    frame_acciones = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_acciones.grid(row=7, column=0, columnspan=2, pady=10, sticky="e")
    def aplicar_texto():
        global texto_prefijo, texto_sufijo, texto_buscar, texto_reemplazar
        texto_prefijo = entrada_prefijo.get().strip()
        texto_sufijo = entrada_sufijo.get().strip()
        texto_buscar = entrada_buscar.get().strip()
        texto_reemplazar = entrada_reemplazar.get().strip()
        ventana_texto.destroy()
    tk.Button(frame_acciones, text="Aplicar", bg="#444444", fg="white", font=("SF Pro", 11, "bold"),
              relief="flat", padx=15, pady=5, activebackground="#555555", activeforeground="white", command=aplicar_texto).pack(side="right", padx=5)
    tk.Button(frame_acciones, text="Cancelar", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=15, pady=5, activebackground="#555555", activeforeground="white", command=ventana_texto.destroy).pack(side="right", padx=5)
    frame_contenido.columnconfigure(1, weight=1)

# =============================================================================
# VENTANA DE AVISO LEGAL
# =============================================================================
def mostrar_avisolegal():
    mensaje = (""
    "Queda terminantemente prohibida la modificación,"
    "distribución o cualquier otro uso no autorizado del código fuente, incluyendo a"
    "título enunciativo y no limitativo, su descarga, su descompilación, su"
    "tratamiento informático, su almacenamiento introducción en cualquier sistema de"
    "repositorio y recuperación, en cualquier forma o por cualquier medio ya sea"
    "electrónico, mecánico, conocido o por inventar, sin el permiso expreso de"
    "ANDREY JAMES BERGERT "
    "\n\n El incumplimiento de esta prohibición podrá dar lugar a que"
    "sean ejercidas las acciones legales correspondientes por parte del titular de"
    "los derechos de autor de este código incluyendo aquellas de naturaleza penal"
    "previstas en los artículos 270 y siguientes del Código Penal español."
    "\n\n Para autorizaciones o cualquier consulta relativa a los"
    "derechos de uso, podrá dirigirse al titular de estos derechos a través del"
    "siguiente correo electrónico: andreybergert@outlook.es")
    ventana_legal = tk.Toplevel(ventana_principal)
    ventana_legal.title("Aviso Legal")
    ventana_legal.geometry("500x400")
    ventana_legal.minsize(400, 300)
    ventana_legal.configure(bg="#1E1E1E")
    center_window(ventana_legal)
    ventana_legal.transient(ventana_principal)
    ventana_legal.grab_set()
    frame_contenido = tk.Frame(ventana_legal, bg="#1E1E1E", padx=20, pady=20)
    frame_contenido.pack(fill="both", expand=True)
    tk.Label(frame_contenido, text="Aviso Legal", font=("SF Pro", 12, "bold"),
             bg="#1E1E1E", fg="white").pack(pady=(0, 20))
    texto_legal = tk.Text(frame_contenido, wrap="word", bg="#252525", fg="white",
                          font=("SF Pro", 10), bd=0, padx=15, pady=15, relief="flat", highlightthickness=0)
    texto_legal.pack(fill="both", expand=True)
    texto_legal.insert("1.0", mensaje)
    texto_legal.tag_configure("justified", justify="left")
    texto_legal.tag_add("justified", "1.0", "end")
    texto_legal.config(state="disabled")
    tk.Button(ventana_legal, text="Cerrar", command=ventana_legal.destroy,
              bg="#444444", fg="white", font=("SF Pro", 11, "bold"), relief="flat",
              padx=15, pady=5, activebackground="#555555", activeforeground="white").pack(pady=15)

# =============================================================================
# FUNCIONES PARA LA SELECCIÓN DE CARPETAS
# =============================================================================
def cambiar_carpeta_por_defecto():
    # Permite cambiar la carpeta predeterminada.
    global carpeta_por_defecto
    nueva = filedialog.askdirectory(title="Seleccionar Carpeta Predeterminada")
    if nueva:
        carpeta_por_defecto = Path(nueva)
        actualizar_carpeta_seleccionada(carpeta_por_defecto, default=True)

def seleccionar_carpeta_puntual():
    # Permite seleccionar otra carpeta de forma puntual.
    nueva = filedialog.askdirectory(title="Seleccionar Carpeta")
    if nueva:
        actualizar_carpeta_seleccionada(Path(nueva))

def actualizar_carpeta_seleccionada(carpeta, default=False):
    # Actualiza la etiqueta que muestra la carpeta seleccionada.
    folder_path = str(carpeta)
    display_path = f"...{folder_path[-40:]}" if len(folder_path) > 40 else folder_path
    if default:
        etiqueta_carpeta.config(text=f"Carpeta predeterminada: {display_path}")
    else:
        etiqueta_carpeta.config(text=f"Carpeta seleccionada: {display_path}")
    etiqueta_carpeta.carpeta_actual = carpeta

# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================
if platform.system() == "Windows":
    if not verificar_instalacion_pywin32():
        sys.exit("No se puede continuar sin pywin32. Asegúrate de instalarlo.")

ventana_principal = crear_interfaz_principal()
ventana_principal.mainloop()