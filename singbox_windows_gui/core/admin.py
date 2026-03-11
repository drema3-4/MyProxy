import ctypes
import sys
import os

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join(sys.argv[1:])
    executable = sys.executable

    # Если мы запущены из обычного интерпретатора (python.exe), пробуем использовать pythonw.exe
    if executable.lower().endswith('python.exe'):
        pythonw = executable[:-4] + 'w.exe'
        if os.path.exists(pythonw):
            executable = pythonw

    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, f'"{script}" {params}', None, 1
    )
    sys.exit(0)