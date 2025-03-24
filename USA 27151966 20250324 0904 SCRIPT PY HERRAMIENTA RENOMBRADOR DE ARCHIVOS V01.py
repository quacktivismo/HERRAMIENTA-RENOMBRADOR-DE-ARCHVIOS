import os
import time
import subprocess
import sys
import platform
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict
import pywintypes
import win32file
import win32con


# Default folder (Downloads)
carpeta_por_defecto = Path.home() / "Downloads"
ventana_principal = None  # Main window variable


# Check and install pywin32 on Windows
def verificar_instalacion_pywin32():
    try:
        import win32file
        import win32con
        return True
    except ImportError:
        respuesta = messagebox.askyesno(
            "Instalación Requerida", 
            "El módulo pywin32 no está instalado. ¿Deseas instalarlo ahora?"
        )
        if respuesta:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
            return True
        else:
            return False


# Change creation and modification date in Windows
def cambiar_fecha_archivo_win(file_path, new_creation_time):
    new_creation_time_win = pywintypes.Time(new_creation_time)
    new_modification_time = new_creation_time_win

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
        win32file.SetFileTime(handle, new_creation_time_win, new_modification_time, new_modification_time)
        handle.close()
    except Exception as e:
        print(f"Error al cambiar la fecha de archivo {file_path}: {e}")


# Change date in macOS
def cambiar_fecha_archivo_mac(file_path, new_creation_time):
    os.utime(file_path, (new_creation_time, new_creation_time))


# Get formatted date
def obtener_fecha(formato, creation_time, increment=0):
    base_time = time.strftime('%Y%m%d %H%M%S', time.localtime(creation_time + increment))
    return base_time if formato == "AAAAMMDD HHMMSS" else base_time[:-2]


# Function to rename files
def renombrar_archivos(formato, carpeta):
    fecha_dict = defaultdict(list)
    
    # Show progress window
    progress_window = tk.Toplevel(ventana_principal)
    progress_window.title("Procesando archivos")
    progress_window.geometry("400x150")
    progress_window.resizable(False, False)
    progress_window.configure(bg="#1E1E1E")
    
    # Center the progress window
    center_window(progress_window)
    
    # Make the progress window modal
    progress_window.transient(ventana_principal)
    progress_window.grab_set()
    
    # Add progress label
    progress_label = tk.Label(progress_window, text="Iniciando proceso...", font=("SF Pro", 12), bg="#1E1E1E", fg="white")
    progress_label.pack(pady=(20, 10))
    
    # Add progress bar
    progress_bar = ttk.Progressbar(progress_window, mode="indeterminate", length=300)
    progress_bar.pack(pady=10)
    progress_bar.start(10)
    
    # Process files
    ventana_principal.update()
    
    # Collect all files first
    all_files = [f for f in Path(carpeta).iterdir() if f.is_file()]
    
    # Group files by creation time
    for i, file_path in enumerate(all_files):
        progress_label.config(text=f"Analizando archivo {i+1} de {len(all_files)}")
        ventana_principal.update()
        
        creation_time = file_path.stat().st_ctime
        formatted_time = obtener_fecha(formato, creation_time)
        fecha_dict[formatted_time].append(file_path)
    
    total_files = sum(len(files) for files in fecha_dict.values())
    processed = 0
    
    # Switch to determinate mode
    progress_bar.stop()
    progress_bar.config(mode="determinate", maximum=total_files, value=0)
    
    # Rename files
    for fecha, archivos in fecha_dict.items():
        for i, file_path in enumerate(archivos):
            creation_time = file_path.stat().st_ctime
            formatted_time = obtener_fecha(formato, creation_time, i)

            file_extension = file_path.suffix
            new_name = f"{formatted_time}{file_extension}"
            new_file_path = file_path.parent / new_name

            counter = 1
            while new_file_path.exists():
                formatted_time = obtener_fecha(formato, creation_time, i + counter)
                new_name = f"{formatted_time}{file_extension}"
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
                print(f"Error: El archivo {file_path} está en uso.")
            except FileExistsError:
                print(f"Error: El archivo {new_file_path} ya existe.")
    
    progress_window.destroy()
    
    # Show success message
    messagebox.showinfo("Proceso Completado", f"Se han renombrado {processed} archivos correctamente.")


# Function to center a window on the screen
def center_window(window):
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


# Set the dark theme for the application
def set_dark_theme():
    # Define colors for dark theme
    background_color = "#1E1E1E"
    button_color = "#444444"
    text_color = "white"
    accent_color = "#666666"
    
    return {
        "bg": background_color,
        "fg": text_color,
        "button_bg": button_color,
        "button_active_bg": "#555555",
        "frame_bg": "#252525",
        "accent_bg": accent_color
    }


# Function to select a folder for one-time use
def seleccionar_carpeta_puntual():
    carpeta = filedialog.askdirectory(title="Seleccionar Carpeta")
    if carpeta:
        actualizar_carpeta_seleccionada(Path(carpeta))


# Function to change the default folder
def cambiar_carpeta_por_defecto():
    global carpeta_por_defecto
    nueva_carpeta = filedialog.askdirectory(title="Seleccionar Carpeta Predeterminada")
    if nueva_carpeta:
        carpeta_por_defecto = Path(nueva_carpeta)
        actualizar_carpeta_seleccionada(carpeta_por_defecto, is_default=True)


# Update the displayed selected folder
def actualizar_carpeta_seleccionada(carpeta, is_default=False):
    folder_name = carpeta.name
    folder_path = str(carpeta)
    
    # Update folder label with shortened path if too long
    if len(folder_path) > 40:
        display_path = f"...{folder_path[-40:]}"
    else:
        display_path = folder_path
    
    if is_default:
        etiqueta_carpeta.config(text=f"Carpeta predeterminada: {display_path}")
    else:
        etiqueta_carpeta.config(text=f"Carpeta seleccionada: {display_path}")
    
    # Store the actual path for later use
    etiqueta_carpeta.carpeta_actual = carpeta


# Function to show legal notice with justified text
def mostrar_avisolegal(): 
    mensaje = """Queda terminantemente prohibida la modificación, distribución o cualquier otro uso no autorizado del código fuente, incluyendo a título enunciativo y no limitativo, su descarga, su descompilación, su tratamiento informático, su almacenamiento introducción en cualquier sistema de repositorio y recuperación, en cualquier forma o por cualquier medio ya sea electrónico, mecánico, conocido o por inventar, sin el permiso expreso de ANDREY JAMES BERGERT. 
 
El incumplimiento de esta prohibición podrá dar lugar a que sean ejercidas las acciones legales correspondientes por parte del titular de los derechos de autor de este código incluyendo aquellas de naturaleza penal previstas en los artículos 270 y siguientes del Código Penal español. 
 
Para autorizaciones o cualquier consulta relativa a los derechos de uso, podrá dirigirse al titular de estos derechos a través del siguiente correo electrónico: andreybergert@outlook.es""" 
     
    # Create legal notice window 
    ventana_legal = tk.Toplevel(ventana_principal) 
    ventana_legal.title("Aviso Legal") 
    ventana_legal.geometry("550x450") 
    ventana_legal.resizable(False, False) 
    ventana_legal.configure(bg="#1E1E1E") 
     
    # Center the window 
    center_window(ventana_legal) 
     
    # Make the window modal 
    ventana_legal.transient(ventana_principal) 
    ventana_legal.grab_set() 
     
    # Frame for content with dark color 
    frame_contenido = tk.Frame(ventana_legal, bg="#1E1E1E", padx=20, pady=20) 
    frame_contenido.pack(fill="both", expand=True) 
     
    # Create title for the legal notice window 
    titulo_aviso = tk.Label(frame_contenido, text="Aviso Legal", font=("SF Pro", 12, "bold"), 
                          bg="#1E1E1E", fg="white") 
    titulo_aviso.pack(pady=(0, 20)) 
     
    # Create a text widget with justified text 
    texto_legal = tk.Text(frame_contenido, wrap="word", height=15, bg="#252525", fg="white", 
                        font=("SF Pro", 10), bd=0, padx=15, pady=15, 
                        relief="flat", highlightthickness=0) 
    texto_legal.pack(fill="both", expand=True) 
     
    # Insert the message 
    texto_legal.insert("1.0", mensaje) 
     
    # Apply justified alignment - changed from "fill" to "left"
    texto_legal.tag_configure("justified", justify="left") 
    texto_legal.tag_add("justified", "1.0", "end") 
     
    # Make the text read-only 
    texto_legal.config(state="disabled") 
     
    # Close button with better visibility 
    boton_cerrar = tk.Button(ventana_legal, text="Cerrar", command=ventana_legal.destroy,  
                          bg="#444444", fg="white", font=("SF Pro", 11, "bold"), 
                          relief="flat", padx=15, pady=5, activebackground="#555555", 
                          activeforeground="white", width=10, height=1) 
    boton_cerrar.pack(pady=15)

# Function to create the main application interface
def crear_interfaz_principal():
    global ventana_principal, etiqueta_carpeta, theme
    
    ventana_principal = tk.Tk()
    ventana_principal.title("Renombrador de Archivos")
    # Increase height to ensure all elements are visible
    ventana_principal.geometry("500x500")
    ventana_principal.resizable(False, False)
    
    # Set theme
    theme = set_dark_theme()
    ventana_principal.configure(bg=theme["bg"])
    
    # Main container
    contenedor_principal = tk.Frame(ventana_principal, bg=theme["bg"], padx=20, pady=20)
    contenedor_principal.pack(fill="both", expand=True)
    
    # Header with app title
    titulo_app = tk.Label(contenedor_principal, text="Renombrador de Archivos", 
                        font=("SF Pro Display", 18, "bold"), bg=theme["bg"], fg=theme["fg"])
    titulo_app.pack(pady=(0, 5))
    
    # Add developer credit line
    credito_desarrollador = tk.Label(contenedor_principal, text="Herramienta desarrollada por Andrey Bergert",
                                  font=("SF Pro", 11), bg=theme["bg"], fg="#BBBBBB")
    credito_desarrollador.pack(pady=(0, 20))
    
    # Section 1: Folder Selection
    seccion_carpeta = tk.LabelFrame(contenedor_principal, text="Selección de Carpeta", 
                                  bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11),
                                  padx=15, pady=15)
    seccion_carpeta.pack(fill="x", pady=10)
    
    etiqueta_carpeta = tk.Label(seccion_carpeta, text=f"Carpeta predeterminada: {carpeta_por_defecto}",
                              bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11))
    etiqueta_carpeta.pack(anchor="w", pady=5)
    etiqueta_carpeta.carpeta_actual = carpeta_por_defecto  # Store actual path
    
    frame_botones_carpeta = tk.Frame(seccion_carpeta, bg=theme["bg"])
    frame_botones_carpeta.pack(fill="x", pady=5)
    
    boton_carpeta_default = tk.Button(frame_botones_carpeta, text="Cambiar carpeta predeterminada", 
                                    bg=theme["button_bg"], fg=theme["fg"], font=("SF Pro", 11),
                                    relief="flat", padx=10, pady=5, activebackground=theme["button_active_bg"],
                                    activeforeground=theme["fg"], command=cambiar_carpeta_por_defecto)
    boton_carpeta_default.pack(side="left", padx=5)
    
    boton_carpeta_puntual = tk.Button(frame_botones_carpeta, text="Seleccionar otra carpeta", 
                                    bg=theme["button_bg"], fg=theme["fg"], font=("SF Pro", 11),
                                    relief="flat", padx=10, pady=5, activebackground=theme["button_active_bg"],
                                    activeforeground=theme["fg"], command=seleccionar_carpeta_puntual)
    boton_carpeta_puntual.pack(side="left", padx=5)
    
    # Section 2: Format Selection
    seccion_formato = tk.LabelFrame(contenedor_principal, text="Formato de Renombrado",
                                  bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11),
                                  padx=15, pady=15)
    seccion_formato.pack(fill="x", pady=10)
    
    etiqueta_formato = tk.Label(seccion_formato, text="Seleccione el formato de fecha para los archivos:",
                              bg=theme["bg"], fg=theme["fg"], font=("SF Pro", 11))
    etiqueta_formato.pack(anchor="w", pady=5)
    
    frame_botones_formato = tk.Frame(seccion_formato, bg=theme["bg"])
    frame_botones_formato.pack(fill="x", pady=10)
    
    # Function to handle the renaming with the selected folder
    def iniciar_renombrado(formato):
        carpeta = etiqueta_carpeta.carpeta_actual
        renombrar_archivos(formato, carpeta)
    
    # Create button with big size (filling the entire area as in the image)
    boton_formato1 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMM", 
                             bg=theme["accent_bg"], fg=theme["fg"], font=("SF Pro", 12),
                             relief="flat", padx=10, pady=10, activebackground=theme["button_active_bg"],
                             activeforeground=theme["fg"], 
                             command=lambda: iniciar_renombrado("AAAAMMDD HHMM"))
    boton_formato1.pack(side="left", padx=5, expand=True, fill="x")
    
    boton_formato2 = tk.Button(frame_botones_formato, text="YYYYMMDD HHMMSS", 
                             bg=theme["accent_bg"], fg=theme["fg"], font=("SF Pro", 12),
                             relief="flat", padx=10, pady=10, activebackground=theme["button_active_bg"],
                             activeforeground=theme["fg"],
                             command=lambda: iniciar_renombrado("AAAAMMDD HHMMSS"))
    boton_formato2.pack(side="left", padx=5, expand=True, fill="x")
    
    # Add a visible and much larger Aviso Legal button
    aviso_legal_frame = tk.Frame(contenedor_principal, bg=theme["bg"])
    aviso_legal_frame.pack(fill="x", pady=11)
    
    # Create a much bigger and more prominent Aviso Legal button
    aviso_legal_button = tk.Button(aviso_legal_frame, text="AVISO LEGAL", 
                                bg="#555555", fg="white", font=("SF Pro", 10, "bold"),
                                relief="flat", padx=20, pady=12,
                                activebackground="#555555", activeforeground="white",
                                width=20, height=2, command=mostrar_avisolegal)
    aviso_legal_button.pack(pady=5, fill="x")
    
    # Footer with version info
    frame_footer = tk.Frame(contenedor_principal, bg=theme["bg"])
    frame_footer.pack(fill="x", pady=(5, 0), side="bottom")
    
    # Version info
    version_label = tk.Label(frame_footer, text="v2.0", bg=theme["bg"], fg="#8a8a8d", font=("SF Pro", 10))
    version_label.pack(side="left")
    
    # Center the window on the screen
    center_window(ventana_principal)
    
    return ventana_principal


# Verify if pywin32 is installed on Windows
if platform.system() == "Windows":
    if not verificar_instalacion_pywin32():
        sys.exit("No se puede continuar sin pywin32. Asegúrate de instalarlo para poder manipular las fechas en Windows.")

# Create and start the application
ventana_principal = crear_interfaz_principal()
ventana_principal.mainloop()