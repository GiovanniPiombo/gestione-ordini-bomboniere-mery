import json
import os 
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtGui import QIcon # Importa QIcon
from pages.menu_page import MenuPage
from pages.search_page import SearchPage
from pages.new_order_page import NewOrderPage
from pages.settings_page import SettingsPage 

# Importa la funzione di stampa
from core.print_order import generate_and_print_order
# Importa il percorso dell'icona
from paths import ICON_PATH 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bomboniere Mery")
        self.resize(1280, 720)
        
        # --- BLOCCO ICONA ---
        try:
            if os.path.exists(ICON_PATH):
                self.setWindowIcon(QIcon(ICON_PATH))
            else:
                print(f"Attenzione: Icona non trovata in {ICON_PATH}")
        except Exception as e:
            print(f"!!! ERRORE DURANTE IL CARICAMENTO DELL'ICONA: {e}")
            print("L'app si avvierà senza icona.")
        # ---------------------------------------------

        # Stacked widget per contenere tutte le pagine
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Creazione delle pagine
        self.menu_page = MenuPage(
            on_search=lambda: self.show_page(self.search_page),
            on_new_order=self.prepare_and_show_new_order,
            on_settings=lambda: self.show_page(self.settings_page)
        )
        
        self.search_page = SearchPage(
            on_back=lambda: self.show_page(self.menu_page),
            on_load_order=self.open_order_for_editing,
            on_print_order=self.print_existing_order 
        )
        
        self.new_order_page = NewOrderPage(
            on_back=lambda: self.show_page(self.menu_page)
        )
        
        # --- INIZIALIZZAZIONE NUOVA PAGINA IMPOSTAZIONI ---
        self.settings_page = SettingsPage(
            on_back=lambda: self.show_page(self.menu_page)
        )

        # Aggiunta delle pagine allo stack
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.search_page)
        self.stack.addWidget(self.new_order_page)
        self.stack.addWidget(self.settings_page) 

        # Mostra il menu principale all'avvio
        self.show_page(self.menu_page)

    def show_page(self, page):
        """Cambia la pagina visibile."""
        self.stack.setCurrentWidget(page)

    def prepare_and_show_new_order(self):
        """Prepara la pagina NewOrder per un inserimento pulito."""
        self.new_order_page.prepare_new_order() 
        self.show_page(self.new_order_page)

    def open_order_for_editing(self, file_path):
        """Carica un ordine esistente nella pagina NewOrder."""
        self.new_order_page.load_order(file_path) 
        self.show_page(self.new_order_page)

    def print_existing_order(self, file_path):
        """
        Carica i dati JSON da un file e chiama la funzione di stampa.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                order_data = json.load(f)
            
            base_filename = os.path.basename(file_path)
            
            # Chiama la funzione di stampa importata
            generate_and_print_order(order_data, base_filename)
            
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.critical(
                self, 
                "Errore di Caricamento", 
                f"Impossibile leggere il file dell'ordine per la stampa:\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Errore di Stampa", 
                f"Si è verificato un errore imprevisto durante la stampa:\n{e}"
            )