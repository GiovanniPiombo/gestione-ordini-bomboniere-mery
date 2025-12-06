import os
import sys

def get_app_dir():
    """ 
    Ottiene la directory dell'eseguibile (.exe) o dello script (.py).
    Usato SOLO per trovare l'eseguibile.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.dirname(__file__))

def get_resource_dir():
    """
    Ottiene la directory delle risorse interne (style.qss, template.ods, icon.png).
    Punta a _MEIPASS (es. _internal) se "congelati".
    """
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.dirname(__file__))

def get_data_dir():
    """
    Ottiene la directory "sicura" per i dati utente (JSON, PDF, ODS).
    Usa C:/Users/TuoNome/AppData/Local/BomboniereMery
    """
    # 'LOCALAPPDATA' è il percorso standard per i dati delle app
    path = os.path.join(os.environ['LOCALAPPDATA'], 'BomboniereMery')
    
    # Crea la cartella se non esiste
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        print(f"ATTENZIONE: Impossibile creare la cartella dati: {e}")
    
    return path


# Directory per le risorse interne (dentro _internal)
RESOURCE_DIR = get_resource_dir()
# Directory per i dati utente (in AppData)
DATA_DIR = get_data_dir()


# Percorsi assoluti dei file risorsa (cercati in _internal)
STYLE_PATH = os.path.join(RESOURCE_DIR, "style.qss")
TEMPLATE_PATH = os.path.join(RESOURCE_DIR, "template.ods")
ICON_PATH = os.path.join(RESOURCE_DIR, "icon.png")

# Percorsi delle cartelle dati (ora in AppData)
ORDERS_DIR = os.path.join(DATA_DIR, "orders")
QUOTES_DIR = os.path.join(DATA_DIR, "quotes")
OUTPUT_DIR = os.path.join(DATA_DIR, "ordini_stampati")