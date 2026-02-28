import os
import sys
import json

def get_app_dir():
    """ 
    Ottiene la directory dell'eseguibile (.exe) o dello script (.py).
    Usato SOLO per trovare l'eseguibile e il file config.json.
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

def load_config():
    """Carica config.json. Se non esiste, lo crea con valori di default."""
    app_dir = get_app_dir()
    config_path = os.path.join(app_dir, "config.json")
    
    # Struttura di base del JSON
    default_config = {
        "custom_data_path": ""  # Se lasciato vuoto, userà AppData
    }

    # 1. Crea il file se non esiste al primo avvio
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            print(f"ATTENZIONE: Impossibile creare config.json: {e}")
        return default_config

    # 2. Leggi il file se esiste
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERRORE: Impossibile leggere config.json ({e}). Uso impostazioni di default.")
        return default_config

def get_data_dir():
    """
    Ottiene la directory "sicura" per i dati utente (JSON, PDF, ODS).
    Legge dal config.json, se è vuoto usa AppData come riserva.
    """
    config = load_config()
    custom_path = config.get("custom_data_path", "").strip()

    # Se c'è un percorso nel config usiamo quello, altrimenti il fallback originale
    if custom_path:
        path = custom_path
    else:
        path = os.path.join(os.environ['LOCALAPPDATA'], 'BomboniereMery')
    
    # Crea la cartella (e le sottocartelle necessarie) se non esiste
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        print(f"ATTENZIONE: Impossibile creare la cartella dati: {e}")
    
    return path


# --- INIZIALIZZAZIONE VARIABILI ESPORTATE ---

# Directory per le risorse interne (dentro _internal)
RESOURCE_DIR = get_resource_dir()
# Directory per i dati utente (Custom o AppData)
DATA_DIR = get_data_dir()

# Percorsi assoluti dei file risorsa (cercati in _internal)
STYLE_PATH = os.path.join(RESOURCE_DIR, "style.qss")
TEMPLATE_PATH = os.path.join(RESOURCE_DIR, "template.ods")
ICON_PATH = os.path.join(RESOURCE_DIR, "icon.png")

# Percorsi delle cartelle dati (create all'interno di DATA_DIR)
ORDERS_DIR = os.path.join(DATA_DIR, "orders")
QUOTES_DIR = os.path.join(DATA_DIR, "quotes")
OUTPUT_DIR = os.path.join(DATA_DIR, "ordini_stampati")