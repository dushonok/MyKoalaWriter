import os
import shutil

# Import the version from ppa_settings or settings if available
try:
    from ppa_settings import APP_VERSION
except Exception:
    try:
        from settings import APP_VERSION
    except Exception:
        APP_VERSION = "0.0.0"

exe_name = f"MyKoalaWriter_{APP_VERSION}"

# Paths for config swapping
DEV_FILE = "..\\ConfigKeeper\\secret_env.py"
PROD_FILE = "..\\ConfigKeeperForApps\\secret_env_myKoalaWriter.py"
BACKUP_FILE = "..\\ConfigKeeper\\secret_env.py.bak"


def swap_in_prod():
    if not os.path.exists(PROD_FILE):
        print(f"Prod file not found: {PROD_FILE}. Skipping swap.")
        return
    # Backup the dev file if it exists
    if os.path.exists(DEV_FILE):
        shutil.copy(DEV_FILE, BACKUP_FILE)
    # Replace with prod file
    shutil.copy(PROD_FILE, DEV_FILE)
    print(f"✅ Swapped in prod config: {PROD_FILE} -> {DEV_FILE}")


def restore_dev():
    if os.path.exists(BACKUP_FILE):
        shutil.move(BACKUP_FILE, DEV_FILE)
        print(f"✅ Restored dev config: {BACKUP_FILE} -> {DEV_FILE}")


def build():
    cmd = (
        f'pyinstaller --onefile --name {exe_name} '
        "--paths=..\\ConfigKeeper "
        "--paths=..\\NotionAutomator "
        "--paths=..\\NotionUtils "
        "--paths=..\\WordPress "
        "--paths=..\\PixelCraft "
        "--paths=..\\CSVSliceMaster "
        "main.py"
    )

    print(f"Running: {cmd}")
    os.system(cmd)

    # Path to the generated exe
    exe_path = os.path.join('dist', f'{exe_name}.exe')
    dest_dir = r'D:\\\\Dropbox\\\\LivingOffCloud\\\\tools'
    dest_path = os.path.join(dest_dir, f'{exe_name}.exe')

    try:
        with open(exe_path, 'rb') as src_file:
            data = src_file.read()
        os.makedirs(dest_dir, exist_ok=True)
        with open(dest_path, 'wb') as dst_file:
            dst_file.write(data)
        print(f"Copied {exe_path} to {dest_path}")
    except Exception as e:
        print(f"Error copying file: {e}")


if __name__ == "__main__":
    env = os.getenv("APP_ENV", "prod")
    print(f"🔧 Building in {env.upper()} mode")
    try:
        if env == "prod":
            swap_in_prod()
        build()
    finally:
        if env == "prod":
            restore_dev()
