"""Lanzador de JC-POS como aplicación de escritorio.

Arranca el sistema Django completo de forma local (base de datos SQLite propia,
sin depender de internet ni de ningún servicio en la nube) y lo muestra en una
ventana de escritorio nativa. Pensado para empacarse con PyInstaller + Inno
Setup (ver desktop/jc-pos.spec y desktop/installer.iss).
"""

import json
import os
import secrets
import socket
import string
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_NAME = "JC-POS"
PREFERRED_PORT = 58327
CONFIG_FILENAME = "config.json"


def get_app_data_dir():
    """Carpeta donde vive la base de datos y la clave secreta de esta instalación."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_or_create_secret_key(data_dir):
    key_file = data_dir / "secret.key"
    if key_file.exists():
        existing = key_file.read_text().strip()
        if existing:
            return existing
    alphabet = string.ascii_letters + string.digits
    key = "".join(secrets.choice(alphabet) for _ in range(50))
    key_file.write_text(key)
    return key


def resource_base_dir():
    """Carpeta donde PyInstaller deja el proyecto (y, en desarrollo, la raíz del repo)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def is_port_open(host, port, timeout=0.3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_server(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open("127.0.0.1", port):
            return True
        time.sleep(0.2)
    return False


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_config(data_dir):
    config_path = data_dir / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_config(data_dir, config):
    try:
        (data_dir / CONFIG_FILENAME).write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError:
        pass


def show_message(title, message):
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo(title, message)
        root.destroy()
    except Exception:
        print(f"{title}\n{message}")


def ask_role_and_server(data_dir):
    """Pregunta, la primera vez que se abre la app en esta PC (o cuando se
    pide explícitamente con --configure), si esta computadora es la
    principal/servidor o si se va a conectar a una caja ya instalada en la
    red. Devuelve el dict de configuración guardado, o None si se canceló."""
    try:
        import tkinter
        from tkinter import messagebox, simpledialog
    except Exception:
        # Sin tkinter disponible (no debería pasar en el build de Windows):
        # por seguridad, asumimos que esta PC es el servidor.
        config = {"mode": "server"}
        save_config(data_dir, config)
        return config

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    is_server = messagebox.askyesno(
        f"{APP_NAME} · Configuración inicial",
        "¿Esta es la ÚNICA computadora del negocio, o la PRINCIPAL donde se "
        "guardan los datos?\n\n"
        "Elige 'Sí' en la mayoría de los casos (incluyendo si solo usas una caja).\n\n"
        "Elige 'No' solo si esta PC va a ser una caja adicional que se conecta "
        "a otra computadora donde JC-POS ya está instalado como principal.",
        parent=root,
    )

    if is_server:
        config = {"mode": "server"}
        save_config(data_dir, config)
        root.destroy()
        return config

    server_url = None
    while server_url is None:
        address = simpledialog.askstring(
            f"{APP_NAME} · Conectar a otra caja",
            "Escribe la dirección de red de la computadora principal\n"
            "(te la debe dar quien la instaló ahí), por ejemplo:\n\n"
            "192.168.1.50\n\n"
            "o el nombre de esa PC, por ejemplo:\nCAJA-PRINCIPAL",
            parent=root,
        )
        if address is None:
            root.destroy()
            return None
        address = address.strip()
        if not address:
            continue
        if address.startswith("http://") or address.startswith("https://"):
            server_url = address if address.endswith("/") else address + "/"
        else:
            address = address.split("/")[0]
            if ":" not in address:
                address = f"{address}:{PREFERRED_PORT}"
            server_url = f"http://{address}/"

    host_port = server_url.split("//", 1)[1].rstrip("/")
    host, _, port_str = host_port.partition(":")
    reachable = is_port_open(host, int(port_str) if port_str.isdigit() else PREFERRED_PORT, timeout=2)
    if not reachable:
        messagebox.showwarning(
            f"{APP_NAME} · Aviso",
            f"No se pudo conectar ahora mismo a {server_url}\n\n"
            "Puede que esa PC esté apagada, que el sistema no esté abierto ahí, "
            "o que la dirección esté mal escrita.\n\n"
            "Se guardó de todas formas — JC-POS intentará conectarse cada vez "
            "que lo abras. Si el problema sigue, usa 'Configurar conexión' "
            "desde el menú de inicio para corregir la dirección.",
            parent=root,
        )

    config = {"mode": "client", "server_url": server_url}
    save_config(data_dir, config)
    root.destroy()
    return config


def fix_streams(data_dir):
    """PyInstaller, empacado sin consola (console=False), deja sys.stdout y
    sys.stderr en None porque Windows no le asigna ninguna consola al proceso.
    Cualquier código que intente escribir ahí (incluyendo comandos de Django
    como 'migrate' o 'seed_groups') truena con 'NoneType' object has no
    attribute 'write'. Los redirigimos a un archivo de log para que nunca
    sean None, sin perder el detalle por si hay que diagnosticar algo."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_path = data_dir / "jc-pos.log"
    try:
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    except OSError:
        import io

        log_file = io.StringIO()
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def configure_django_environment(base_dir, data_dir):
    db_path = data_dir / "db.sqlite3"
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    os.environ.setdefault("DEBUG", "False")
    os.environ.setdefault("ALLOWED_HOSTS", "*")
    os.environ.setdefault("SECRET_KEY", get_or_create_secret_key(data_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(base_dir))
    os.chdir(base_dir)


def run_migrations():
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)
    call_command("seed_groups", verbosity=0)


def generate_password():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


def write_credentials_file(data_dir, password):
    """Respaldo en texto plano de la contraseña del administrador, por si se
    cierra o se pierde de vista la ventana emergente que solo la muestra una
    vez. Vive únicamente en esta PC, en la carpeta de datos de la app."""
    try:
        (data_dir / "admin-password.txt").write_text(
            "JC-POS - credenciales del administrador\n"
            "=========================================\n\n"
            f"Usuario: admin\n"
            f"Contraseña: {password}\n\n"
            f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Puedes cambiar esta contraseña luego desde Admin > Usuarios,\n"
            "y borrar este archivo una vez que la hayas anotado en un lugar seguro.\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def ensure_admin_user(data_dir):
    """Crea un usuario administrador la primera vez que se instala, para no
    depender de ninguna línea de comandos. Devuelve la contraseña generada,
    o None si ya existía un administrador de antes."""
    from django.contrib.auth.models import User

    if User.objects.filter(is_superuser=True).exists():
        return None
    password = generate_password()
    User.objects.create_superuser(username="admin", email="", password=password)
    write_credentials_file(data_dir, password)
    return password


def reset_admin_password(data_dir):
    """Restablece (o crea, si no existía) la contraseña del usuario 'admin'
    con una nueva generada al azar. Pensado para correrse desde línea de
    comandos (jc-pos.exe --reset-admin) cuando se perdió la contraseña
    original y no se pudo recuperar del archivo de respaldo."""
    from django.contrib.auth.models import User

    password = generate_password()
    user, _created = User.objects.get_or_create(
        username="admin", defaults={"is_superuser": True, "is_staff": True}
    )
    user.is_superuser = True
    user.is_staff = True
    user.set_password(password)
    user.save()
    write_credentials_file(data_dir, password)
    return password


def start_server(port):
    from waitress import serve

    from config.wsgi import application

    def _serve():
        serve(application, host="0.0.0.0", port=port, _quiet=True)

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    return thread


def show_first_run_message(password, lan_url, data_dir, title=f"{APP_NAME} · Primer uso"):
    message = (
        f"Usuario: admin\n"
        f"Contraseña: {password}\n\n"
        f"Guárdala en un lugar seguro — la puedes cambiar luego desde Admin > Usuarios.\n"
        f"También queda guardada en:\n{data_dir / 'admin-password.txt'}\n\n"
        f"Para conectar otras cajas a este mismo sistema, en esa PC elige "
        f"'Configurar conexión' y escribe esta dirección:\n{lan_url}"
    )
    show_message(title, message)


def open_window(url, check_reachable=False):
    if check_reachable:
        host_port = url.split("//", 1)[1].rstrip("/")
        host, _, port_str = host_port.partition(":")
        port = int(port_str) if port_str.isdigit() else PREFERRED_PORT
        if not any(is_port_open(host, port, timeout=1) for _ in range(3)):
            show_message(
                f"{APP_NAME} · No se pudo conectar",
                f"No se pudo conectar a la computadora principal ({url}).\n\n"
                "Verifica que esa PC esté encendida, que JC-POS esté abierto ahí, "
                "y que ambas estén en la misma red WiFi.\n\n"
                "Si la dirección cambió, usa 'Configurar conexión' desde el menú "
                "de inicio para corregirla.",
            )
            return
    try:
        import webview

        webview.create_window(APP_NAME, url, width=1300, height=820, min_size=(960, 620))
        webview.start()
    except Exception:
        webbrowser.open(url)
        try:
            input(f"{APP_NAME} está corriendo en {url}\nPresiona Enter aquí para cerrarlo...")
        except EOFError:
            while True:
                time.sleep(3600)


def run_as_server(base_dir, data_dir, reset_admin=False):
    configure_django_environment(base_dir, data_dir)
    port = PREFERRED_PORT
    already_running = is_port_open("127.0.0.1", port)

    if reset_admin:
        import django

        django.setup()
        run_migrations()
        password = reset_admin_password(data_dir)
        show_first_run_message(
            password, f"http://{get_lan_ip()}:{port}/", data_dir,
            title=f"{APP_NAME} · Contraseña restablecida",
        )
        return

    if not already_running:
        import django

        django.setup()
        run_migrations()
        admin_password = ensure_admin_user(data_dir)
        start_server(port)
        if not wait_for_server(port):
            raise RuntimeError("El servidor local de JC-POS no arrancó a tiempo.")
        if admin_password:
            show_first_run_message(admin_password, f"http://{get_lan_ip()}:{port}/", data_dir)

    open_window(f"http://127.0.0.1:{port}/")


def run_as_client(data_dir, config, reset_admin=False):
    if reset_admin:
        show_message(
            f"{APP_NAME} · Esta PC es una caja conectada",
            "Esta computadora está configurada como una caja que se conecta a "
            "otra PC principal — no tiene su propia base de datos.\n\n"
            "Restablece la contraseña del administrador desde 'Restablecer "
            "contraseña de administrador' en la computadora principal, no en esta.",
        )
        return
    open_window(config["server_url"], check_reachable=True)


def main():
    base_dir = resource_base_dir()
    data_dir = get_app_data_dir()
    fix_streams(data_dir)

    reset_admin = "--reset-admin" in sys.argv

    if "--configure" in sys.argv:
        ask_role_and_server(data_dir)
        return

    config = load_config(data_dir)
    if config is None:
        config = ask_role_and_server(data_dir)
        if config is None:
            return

    if config.get("mode") == "client":
        run_as_client(data_dir, config, reset_admin=reset_admin)
    else:
        run_as_server(base_dir, data_dir, reset_admin=reset_admin)


if __name__ == "__main__":
    main()
