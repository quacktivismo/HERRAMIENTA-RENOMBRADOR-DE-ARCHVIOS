import os
import time
import subprocess
import sys
import platform
import json
import random
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict
import pywintypes
import win32file
import win32con

# Variables globales
carpeta_por_defecto = Path.home() / "Downloads"
config_file = Path.home() / ".renombrador_config.json"
texto_prefijo = ""
texto_sufijo = ""
formato_seleccionado = None
textos_frecuentes = []
# Variables para reemplazo de texto
texto_buscar = ""
texto_reemplazar = ""
# Variables para tipo de fecha: "original", "fija" o "aleatoria"
tipo_fecha = "original"
fecha_fija = ""  # Debe estar en formato "YYYYMMDD HHMMSS"

# Cargar y guardar textos frecuentes
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

textos_frecuentes = cargar_textos_frecuentes()

# Verificar instalación de pywin32 en Windows
def verificar_instalacion_pywin32():
    try:
        import win32file, win32con
        return True
    except ImportError:
        if messagebox.askyesno("Instalación Requerida", "El módulo pywin32 no está instalado. ¿Deseas instalarlo ahora?"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            return True
        return False

# Funciones para ajustar la fecha de creación del archivo según el sistema
def cambiar_fecha_archivo_win(file_path, new_creation_time):
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
    os.utime(file_path, (new_creation_time, new_creation_time))

# Función para obtener la fecha formateada
def obtener_fecha(formato, creation_time, increment=0):
    t = time.localtime(creation_time + increment)
    base_time = time.strftime('%Y%m%d %H%M%S', t)
    return base_time if formato == "AAAAMMDD HHMMSS" else base_time[:-2]

# Función para renombrar archivos
def renombrar_archivos(formato, carpeta, texto_prefijo="", texto_sufijo="", mantener_original=False):
    global tipo_fecha, fecha_fija, texto_buscar, texto_reemplazar
    fecha_dict = defaultdict(list)
    progress_window = tk.Toplevel(ventana_principal)
    progress_window.title("Procesando archivos")
    progress_window.geometry("800x150")
    progress_window.resizable(False, False)
    progress_window.configure(bg="#1E1E1E")
    center_window(progress_window)
    progress_window.transient(ventana_principal)
    progress_window.grab_set()

    progress_label = tk.Label(progress_window, text="Iniciando proceso...", font=("SF Pro", 12),
                                bg="#1E1E1E", fg="white")
    progress_label.pack(pady=(20, 10))
    progress_bar = ttk.Progressbar(progress_window, mode="indeterminate", length=300)
    progress_bar.pack(pady=10)
    progress_bar.start(10)
    ventana_principal.update()

    # Obtener todos los archivos de la carpeta
    all_files = [f for f in Path(carpeta).iterdir() if f.is_file()]
    for i, file_path in enumerate(all_files):
        progress_label.config(text=f"Analizando archivo {i+1} de {len(all_files)}")
        ventana_principal.update()
        # Seleccionar fecha según el tipo elegido
        if tipo_fecha == "original":
            creation_time = file_path.stat().st_ctime
        elif tipo_fecha == "fija":
            try:
                creation_time = time.mktime(time.strptime(fecha_fija, '%Y%m%d %H%M%S'))
            except Exception:
                creation_time = file_path.stat().st_ctime
        elif tipo_fecha == "aleatoria":
            start = time.mktime(time.strptime("20000101 000000", "%Y%m%d %H%M%S"))
            end = time.mktime(time.strptime("20301231 235959", "%Y%m%d %H%M%S"))
            creation_time = random.randint(int(start), int(end))
        formatted_time = obtener_fecha(formato, creation_time)
        fecha_dict[formatted_time].append(file_path)

    total_files = sum(len(v) for v in fecha_dict.values())
    processed = 0
    progress_bar.stop()
    progress_bar.config(mode="determinate", maximum=total_files, value=0)

    for fecha, archivos in fecha_dict.items():
        for i, file_path in enumerate(archivos):
            # Seleccionar la fecha para cada archivo según el tipo
            if tipo_fecha == "original":
                creation_time = file_path.stat().st_ctime
            elif tipo_fecha == "fija":
                try:
                    creation_time = time.mktime(time.strptime(fecha_fija, '%Y%m%d %H%M%S'))
                except Exception:
                    creation_time = file_path.stat().st_ctime
            elif tipo_fecha == "aleatoria":
                start = time.mktime(time.strptime("20000101 000000", "%Y%m%d %H%M%S"))
                end = time.mktime(time.strptime("20301231 235959", "%Y%m%d %H%M%S"))
                creation_time = random.randint(int(start), int(end))
            formatted_time = obtener_fecha(formato, creation_time, i)
            file_extension = file_path.suffix
            original_part = f" {file_path.stem.upper()}" if mantener_original else ""
            new_name = (f"{texto_prefijo} " if texto_prefijo else "") + \
                       formatted_time + \
                       (f" {texto_sufijo}" if texto_sufijo else "") + \
                       original_part + file_extension
            # Aplicar reemplazo de texto si se definió
            if texto_buscar and texto_buscar in new_name:
                new_name = new_name.replace(texto_buscar, texto_reemplazar)
            new_file_path = file_path.parent / new_name

            counter = 1
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

# Alternar pantalla completa
def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    ventana_principal.attributes("-fullscreen", fullscreen)

# Función para centrar una ventana
def center_window(window):
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

# Función para alternar pantalla completa (F11)
def toggle_fullscreen(event=None):
    is_full = ventana_principal.attributes("-fullscreen")
    ventana_principal.attributes("-fullscreen", not is_full)

# Tema oscuro para la interfaz
def set_dark_theme():
    return {
        "bg": "#1E1E1E",
        "fg": "white",
        "button_bg": "#444444",
        "button_active_bg": "#555555",
        "frame_bg": "#252525",
        "accent_bg": "#666666"
    }

# Ventana para personalizar textos y gestionar favoritos, ahora con campos para reemplazo de texto
def personalizar_texto():
    global textos_frecuentes, texto_prefijo, texto_sufijo, texto_buscar, texto_reemplazar
    ventana_texto = tk.Toplevel(ventana_principal)
    ventana_texto.title("Personalizar Texto")
    ventana_texto.geometry("900x900")
    ventana_texto.resizable(False, False)
    ventana_texto.configure(bg="#1E1E1E")
    center_window(ventana_texto)
    ventana_texto.transient(ventana_principal)
    ventana_texto.grab_set()

    frame_contenido = tk.Frame(ventana_texto, bg="#1E1E1E", padx=20, pady=20)
    frame_contenido.pack(fill="both", expand=True)
    tk.Label(frame_contenido, text="Personalizar Texto para Archivos", 
             font=("SF Pro", 12, "bold"), bg="#1E1E1E", fg="white").pack(pady=(0, 20))

    # Campo para texto (prefijo)
    frame_prefijo = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_prefijo.pack(fill="x", pady=5)
    tk.Label(frame_prefijo, text="Texto a añadir ANTES de la fecha:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).pack(anchor="w", pady=5)
    entrada_prefijo = tk.Entry(frame_prefijo, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_prefijo.pack(fill="x", pady=5)
    entrada_prefijo.insert(0, texto_prefijo)

    # Campo para texto (sufijo)
    frame_sufijo = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_sufijo.pack(fill="x", pady=5)
    tk.Label(frame_sufijo, text="Texto a añadir DESPUÉS de la fecha:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).pack(anchor="w", pady=5)
    entrada_sufijo = tk.Entry(frame_sufijo, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_sufijo.pack(fill="x", pady=5)
    entrada_sufijo.insert(0, texto_sufijo)

    # Campos para reemplazo de texto
    frame_reemplazo = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_reemplazo.pack(fill="x", pady=5)
    tk.Label(frame_reemplazo, text="Texto a buscar (para reemplazar):", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).pack(anchor="w", pady=5)
    entrada_buscar = tk.Entry(frame_reemplazo, font=("SF Pro", 11), bg="#252525", fg="white",
                              insertbackground="white", relief="flat", borderwidth=3)
    entrada_buscar.pack(fill="x", pady=5)
    tk.Label(frame_reemplazo, text="Texto de reemplazo:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).pack(anchor="w", pady=5)
    entrada_reemplazar = tk.Entry(frame_reemplazo, font=("SF Pro", 11), bg="#252525", fg="white",
                                  insertbackground="white", relief="flat", borderwidth=3)
    entrada_reemplazar.pack(fill="x", pady=5)

    # Sección de textos frecuentes
    frame_frecuentes = tk.Frame(frame_contenido, bg="#1E1E1E")
    frame_frecuentes.pack(fill="both", expand=True, pady=10)
    tk.Label(frame_frecuentes, text="Textos frecuentes:", bg="#1E1E1E",
             fg="white", font=("SF Pro", 11)).pack(anchor="w", pady=5)
    frame_lista = tk.Frame(frame_frecuentes, bg="#1E1E1E")
    frame_lista.pack(fill="both", expand=True)
    scrollbar = tk.Scrollbar(frame_lista)
    scrollbar.pack(side="right", fill="y")
    lista_textos = tk.Listbox(frame_lista, font=("SF Pro", 11), bg="#252525", fg="white",
                              relief="flat", borderwidth=0, selectbackground="#555555",
                              yscrollcommand=scrollbar.set, height=5)
    lista_textos.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=lista_textos.yview)
    for texto in textos_frecuentes:
        lista_textos.insert(tk.END, texto)

    frame_botones_lista = tk.Frame(frame_frecuentes, bg="#1E1E1E")
    frame_botones_lista.pack(fill="x", pady=5)
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
    tk.Button(frame_botones_lista, text="Usar Seleccionado", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=seleccionar_texto).pack(side="left", padx=5)
    tk.Button(frame_botones_lista, text="Añadir a Favoritos", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=añadir_texto).pack(side="left", padx=5)
    tk.Button(frame_botones_lista, text="Eliminar", bg="#444444", fg="white", font=("SF Pro", 11),
              relief="flat", padx=5, activebackground="#555555", activeforeground="white", command=eliminar_texto).pack(side="left", padx=5)

    frame_acciones = tk.Frame(ventana_texto, bg="#1E1E1E")
    frame_acciones.pack(fill="x", padx=20, pady=10)
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

# Aviso Legal
def mostrar_avisolegal():
    mensaje = ("Queda terminantemente prohibida la modificación, distribución o cualquier otro uso no autorizado "
               "del código fuente, incluyendo su descarga, descompilación, almacenamiento o introducción en "
               "cualquier sistema sin el permiso expreso de ANDREY JAMES BERGERT. "
               "\n\nPara autorizaciones o consultas, dirigirse a andreybergert@outlook.es")
    ventana_legal = tk.Toplevel(ventana_principal)
    ventana_legal.title("Aviso Legal")
    ventana_legal.geometry("550x450")
    ventana_legal.resizable(False, False)
    ventana_legal.configure(bg="#1E1E1E")
    center_window(ventana_legal)
    ventana_legal.transient(ventana_principal)
    ventana_legal.grab_set()
    frame_contenido = tk.Frame(ventana_legal, bg="#1E1E1E", padx=20, pady=20)
    frame_contenido.pack(fill="both", expand=True)
    tk.Label(frame_contenido, text="Aviso Legal", font=("SF Pro", 12, "bold"),
             bg="#1E1E1E", fg="white").pack(pady=(0, 20))
    texto_legal = tk.Text(frame_contenido, wrap="word", height=15, bg="#252525", fg="white",
                          font=("SF Pro", 10), bd=0, padx=15, pady=15, relief="flat", highlightthickness=0)
    texto_legal.pack(fill="both", expand=True)
    texto_legal.insert("1.0", mensaje)
    texto_legal.tag_configure("justified", justify="left")
    texto_legal.tag_add("justified", "1.0", "end")
    texto_legal.config(state="disabled")
    tk.Button(ventana_legal, text="Cerrar", command=ventana_legal.destroy,
              bg="#444444", fg="white", font=("SF Pro", 11, "bold"), relief="flat",
              padx=15, pady=5, activebackground="#555555", activeforeground="white", width=10, height=1).pack(pady=15)

# Funciones de selección de carpeta
def cambiar_carpeta_por_defecto():
    global carpeta_por_defecto
    nueva = filedialog.askdirectory(title="Seleccionar Carpeta Predeterminada")
    if nueva:
        carpeta_por_defecto = Path(nueva)
        actualizar_carpeta_seleccionada(carpeta_por_defecto, default=True)

def seleccionar_carpeta_puntual():
    nueva = filedialog.askdirectory(title="Seleccionar Carpeta")
    if nueva:
        actualizar_carpeta_seleccionada(Path(nueva))

def actualizar_carpeta_seleccionada(carpeta, default=False):
    folder_path = str(carpeta)
    display_path = f"...{folder_path[-40:]}" if len(folder_path) > 40 else folder_path
    if default:
        etiqueta_carpeta.config(text=f"Carpeta predeterminada: {display_path}")
    else:
        etiqueta_carpeta.config(text=f"Carpeta seleccionada: {display_path}")
    etiqueta_carpeta.carpeta_actual = carpeta

# Interfaz principal
def crear_interfaz_principal():
    global ventana_principal, etiqueta_carpeta, formato_seleccionado, texto_prefijo, texto_sufijo
    global boton_formato1, boton_formato2, tipo_fecha, fecha_fija
    ventana = tk.Tk()
    ventana.title("Renombrador de Archivos")
    ventana.geometry("800x800")
    ventana.resizable(False, False)
    theme = set_dark_theme()
    ventana.configure(bg=theme["bg"])
    
    # Asignar tecla F11 para pantalla completa
    ventana.bind("<F11>", toggle_fullscreen)
    
    contenedor = tk.Frame(ventana, bg=theme["bg"], padx=20, pady=20)
    contenedor.pack(fill="both", expand=True)
    tk.Label(contenedor, text="Renombrador de Archivos", font=("SF Pro Display", 18, "bold"),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=(0, 5))
    tk.Label(contenedor, text="Herramienta desarrollada por Andrey Bergert", font=("SF Pro", 11),
             bg=theme["bg"], fg="#BBBBBB").pack(pady=(0, 20))
    
    # Sección de carpeta
    seccion_carpeta = tk.LabelFrame(contenedor, text="Selección de Carpeta", bg=theme["bg"],
                                    fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_carpeta.pack(fill="x", pady=10)
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
              command=cambiar_carpeta_por_defecto).pack(side="left", padx=5)
    tk.Button(frame_botones_carpeta, text="Seleccionar otra carpeta", bg=theme["button_bg"],
              fg=theme["fg"], font=("SF Pro", 11), relief="flat", padx=10, pady=5,
              activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
              command=seleccionar_carpeta_puntual).pack(side="left", padx=5)
    
    # Sección de formato
    seccion_formato = tk.LabelFrame(contenedor, text="Formato de Renombrado", bg=theme["bg"],
                                    fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_formato.pack(fill="x", pady=10)
    tk.Label(seccion_formato, text="Seleccione el formato de fecha:", bg=theme["bg"],
             fg=theme["fg"], font=("SF Pro", 11)).pack(anchor="w", pady=5)
    frame_botones_formato = tk.Frame(seccion_formato, bg=theme["bg"])
    frame_botones_formato.pack(fill="x", pady=10)
    # Botones de formato (se usa la función seleccionar_formato para resaltar la opción elegida)
    boton_formato1 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMM", bg=theme["accent_bg"],
                               fg=theme["fg"], font=("SF Pro", 12), relief="flat", padx=10, pady=10,
                               activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
                               command=lambda: seleccionar_formato("AAAAMMDD HHMM"))
    boton_formato1.pack(side="left", padx=5, expand=True, fill="x")
    boton_formato2 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMMSS", bg=theme["accent_bg"],
                               fg=theme["fg"], font=("SF Pro", 12), relief="flat", padx=10, pady=10,
                               activebackground=theme["button_active_bg"], activeforeground=theme["fg"],
                               command=lambda: seleccionar_formato("AAAAMMDD HHMMSS"))
    boton_formato2.pack(side="left", padx=5, expand=True, fill="x")
    
    # Nueva sección para seleccionar el tipo de fecha a asignar
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
    
    # Sección de personalización de texto
    seccion_texto = tk.LabelFrame(contenedor, text="Personalización de Texto", bg=theme["bg"],
                                  fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_texto.pack(fill="x", pady=10)
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
    # Opción para mantener el nombre original en mayúsculas
    mantener_original = tk.BooleanVar(value=False)
    tk.Checkbutton(seccion_texto, text="Mantener nombre original (mayúsculas)", variable=mantener_original,
                   bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11), selectcolor="#252525",
                   activebackground=theme["bg"], activeforeground=theme["fg"]).pack(anchor="w", pady=5)
    
    # Sección de ejecución
    seccion_ejecutar = tk.LabelFrame(contenedor, text="Ejecutar", bg=theme["bg"],
                                     fg=theme["fg"], font=("SF Pro", 11), padx=15, pady=15)
    seccion_ejecutar.pack(fill="x", pady=10)
    def ejecutar_renombrado():
        global tipo_fecha, fecha_fija
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
    
    # Botón de AVISO LEGAL
    aviso_legal_frame = tk.Frame(contenedor, bg=theme["bg"])
    aviso_legal_frame.pack(fill="x", pady=11)
    aviso_legal_button = tk.Button(aviso_legal_frame, text="AVISO LEGAL", 
                                   bg="#555555", fg="white", font=("SF Pro", 10, "bold"),
                                   relief="flat", padx=20, pady=12, activebackground="#555555",
                                   activeforeground="white", width=20, height=2, command=mostrar_avisolegal)
    aviso_legal_button.pack(pady=5, fill="x")
    
    # Footer
    tk.Label(contenedor, text="v2.0", bg=theme["bg"], fg="#8a8a8d", font=("SF Pro", 10)).pack(side="left", pady=(5, 0))
    
    center_window(ventana)
    return ventana

def seleccionar_formato(formato):
    global formato_seleccionado
    formato_seleccionado = formato
    # Resaltar la opción seleccionada
    theme = set_dark_theme()
    if formato == "AAAAMMDD HHMM":
        boton_formato1.config(bg="#666666", relief="sunken")
        boton_formato2.config(bg=theme["accent_bg"], relief="flat")
    else:  # Se asume que el otro formato es "AAAAMMDD HHMMSS"
        boton_formato1.config(bg=theme["accent_bg"], relief="flat")
        boton_formato2.config(bg="#666666", relief="sunken")

# Inicio del programa
if platform.system() == "Windows":
    if not verificar_instalacion_pywin32():
        sys.exit("No se puede continuar sin pywin32. Asegúrate de instalarlo.")

ventana_principal = crear_interfaz_principal()
ventana_principal.mainloop()