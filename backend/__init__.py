import sys
from os.path import abspath, dirname

# Добавляем папку backend в sys.path, чтобы абсолютные импорты работали
backend_path = dirname(abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)