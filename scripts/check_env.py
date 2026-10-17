"""Print platform + library info. Run on LinuxONE for 'proof of platform' screenshots."""
import importlib
import os
import platform
import sys

print("=== PlastiTrack environment check ===")
print("Machine     :", platform.machine())          # expect s390x
print("Byte order  :", sys.byteorder)                # expect big (IBM Z)
print("OS          :", platform.platform())
print("Python      :", sys.version.split()[0])
print("CPU count   :", os.cpu_count())

for name in ["numpy", "pandas", "sklearn", "xgboost", "llama_cpp", "streamlit"]:
    try:
        mod = importlib.import_module(name)
        print(f"{name:<12}:", getattr(mod, "__version__", "ok"))
    except ImportError:
        print(f"{name:<12}: not installed")
