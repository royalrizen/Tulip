from pathlib import Path
import ctypes

LIBRARY = Path(__file__).resolve().parent / "libtuliplm.so"
_model = ctypes.CDLL(str(LIBRARY))
_model.init_model()
_model.learn.argtypes = [ctypes.c_char_p]
_model.save_model.argtypes = [ctypes.c_char_p]
_model.load_model.argtypes = [ctypes.c_char_p]

def learn(text: str):
    _model.learn(text.encode("utf-8"))
def save(filename: str):
    _model.save_model(filename.encode("utf-8"))
def load(filename: str):
    _model.load_model(filename.encode("utf-8"))
