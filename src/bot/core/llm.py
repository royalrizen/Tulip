from pathlib import Path
import ctypes

BASE = Path(__file__).resolve().parent.parent
LIBRARY = BASE / "llm" / "libtuliplm.so"

model = ctypes.CDLL(str(LIBRARY))

model.init_model()

model.learn.argtypes = [ctypes.c_char_p]
model.save_model.argtypes = [ctypes.c_char_p]
model.load_model.argtypes = [ctypes.c_char_p]
