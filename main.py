import sys
import os
import traceback
from PySide6.QtWidgets import QApplication

# Importa i nostri percorsi
from paths import STYLE_PATH, OUTPUT_DIR 

# --- Funzione di pulizia ---
def clean_output_directory(directory):
    if not os.path.exists(directory):
        return
    
    for filename in os.listdir(directory):
        if not (filename.endswith(".ods") or 
                filename.endswith(".pdf") or 
                filename.endswith(".bak")): 
            continue
            
        file_path = os.path.join(directory, filename)
        
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Attenzione: Impossibile eliminare {file_path}. Motivo: {e}")

# --- Funzione main ---
def main():
    # Esegui la pulizia all'avvio
    clean_output_directory(OUTPUT_DIR) 
    
    # Crea l'applicazione
    app = QApplication(sys.argv)

    # Carica il foglio di stile (style.qss)
    try:
        with open(STYLE_PATH, "r", encoding="utf-8") as f: 
            _style = f.read()
            app.setStyleSheet(_style)
    except FileNotFoundError:
        print(f"ATTENZIONE: file '{STYLE_PATH}' non trovato. L'app userà lo stile di default.")
    except Exception as e:
        print(f"!!! ERRORE nel caricamento dello stylesheet: {e}")

    # --- Importa la finestra DOPO aver creato l'app ---
    from main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    # Avvia l'applicazione
    sys.exit(app.exec())

# --- Blocco di avvio sicuro ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Se l'app crasha, questo lo cattura
        print("-------------------------------------------------")
        print("--- ERRORE ---")
        traceback.print_exc()
        print("-------------------------------------------------")
        input("PREMI INVIO PER CHIUDERE...")