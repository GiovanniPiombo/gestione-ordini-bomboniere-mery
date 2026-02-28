import os
import json
import re
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem,
    QHBoxLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt

# Importiamo le cartelle dove cercare i file
from paths import ORDERS_DIR, QUOTES_DIR

class SearchPage(QWidget):
    """
    Pagina di Ricerca e Gestione Liste.
    
    Funzionalità principali:
    1. Visualizzare l'elenco di Ordini o Preventivi (switch tramite menu a tendina).
    2. Filtrare l'elenco in tempo reale digitando il nome.
    3. Aprire un file per la modifica (doppio click).
    4. Convertire un Preventivo in Ordine (tasto "Conferma").
    5. Stampare direttamente un documento selezionato.
    6. Eliminare definitivamente un Ordine o Preventivo.
    """

    def __init__(self, on_back, on_load_order, on_print_order):
        super().__init__()
        
        # Callback ricevute dalla MainWindow per navigare o stampare
        self.on_load_order = on_load_order
        self.on_print_order = on_print_order
        
        # Lista interna per memorizzare i dati caricati (per il filtro)
        self.all_orders = []

        layout = QVBoxLayout()
        title = QLabel("<h2>Lista Ordini e Preventivi</h2>")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # --- SELETTORE MODALITÀ (Ordini vs Preventivi) ---
        self.type_selector = QComboBox()
        self.type_selector.addItems(["📂 Ordini", "📝 Preventivi"])
        # Quando cambia l'indice (0 o 1), ricarichiamo la lista corretta
        self.type_selector.currentIndexChanged.connect(self.on_type_changed) 
        layout.addWidget(self.type_selector)

        # --- BARRA DI RICERCA ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca per nome cliente...")
        # Ad ogni carattere digitato, filtriamo la lista visibile
        self.search_bar.textChanged.connect(self.filter_orders)
        layout.addWidget(self.search_bar)

        # --- LISTA VISUALE ---
        self.order_list_widget = QListWidget()
        # Il doppio click su una riga apre l'editor
        self.order_list_widget.itemDoubleClicked.connect(self.handle_double_click)
        layout.addWidget(self.order_list_widget)

        # --- BOTTONI AZIONE ---
        button_layout = QHBoxLayout()

        btn_back = QPushButton("⬅️ Torna al Menu")
        btn_back.clicked.connect(on_back)
        
        # Bottone "Elimina"
        self.btn_delete = QPushButton("🗑️ Elimina Selezionato")
        self.btn_delete.setStyleSheet("background-color: #f8d7da; border: 1px solid #f5c2c7; color: #842029; font-weight: bold;")
        self.btn_delete.clicked.connect(self.delete_selected_item)

        # Bottone "Conferma": visibile SOLO se siamo in modalità Preventivi
        self.btn_confirm = QPushButton("✅ Conferma Preventivo")
        self.btn_confirm.clicked.connect(self.confirm_selected_quote)
        self.btn_confirm.setVisible(False) # Nascosto di default
        
        btn_print = QPushButton("📄 Stampa Selezionato")
        btn_print.clicked.connect(self.handle_print_click)
        
        button_layout.addWidget(btn_back)
        button_layout.addStretch() # Spinge i bottoni successivi a destra
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_confirm)
        button_layout.addWidget(btn_print)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    # ============================================================================
    # --- LOGICA INTERFACCIA ---
    # ============================================================================

    def on_type_changed(self):
        """Gestisce il cambio di selezione (Ordini/Preventivi) e aggiorna la UI."""
        # Se l'indice è 1, siamo su "Preventivi"
        is_quote_mode = (self.type_selector.currentIndex() == 1)
        
        # Mostra il tasto "Conferma" solo se stiamo guardando i preventivi
        self.btn_confirm.setVisible(is_quote_mode)
        
        # Ricarica i dati dalla cartella giusta
        self.load_orders()

    def handle_double_click(self, item):
        """Gestisce l'apertura del file quando si clicca due volte sulla lista."""
        # Recuperiamo il percorso completo nascosto nell'item (UserRole)
        file_path = item.data(Qt.UserRole)
        if file_path and self.on_load_order:
            # Chiama la funzione della MainWindow per cambiare pagina e caricare i dati
            self.on_load_order(file_path)

    def handle_print_click(self):
        """Stampa l'elemento selezionato senza aprirlo."""
        selected_item = self.order_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un elemento da stampare.")
            return

        file_path = selected_item.data(Qt.UserRole)
        if file_path and self.on_print_order:
            self.on_print_order(file_path)

    # ============================================================================
    # --- LOGICA CORE: ELIMINAZIONE E CONVERSIONE ---
    # ============================================================================

    def delete_selected_item(self):
        """Elimina fisicamente il file dell'ordine o preventivo selezionato."""
        selected_item = self.order_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un elemento da eliminare.")
            return

        file_path = selected_item.data(Qt.UserRole)
        is_quote_mode = (self.type_selector.currentIndex() == 1)
        doc_type = "preventivo" if is_quote_mode else "ordine"

        # Finestra di conferma critica
        msg = QMessageBox(self)
        msg.setWindowTitle(f"Conferma Eliminazione {doc_type.capitalize()}")
        msg.setText(f"Sei sicuro di voler eliminare definitivamente questo {doc_type}?\n\nQuesta azione NON può essere annullata.")
        msg.setIcon(QMessageBox.Warning)

        btn_si = msg.addButton("Sì, Elimina", QMessageBox.DestructiveRole)
        btn_no = msg.addButton("Annulla", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() == btn_si:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    QMessageBox.information(self, "Successo", f"{doc_type.capitalize()} eliminato correttamente.")
                    self.load_orders() # Aggiorna la lista rimuovendo il file cancellato
                else:
                    QMessageBox.warning(self, "Errore", "Il file non esiste o è già stato eliminato.")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile eliminare il file:\n{e}")

    def confirm_selected_quote(self):
        """
        Logica per trasformare un preventivo in un ordine effettivo.
        Include conferma con tasti personalizzati "Sì/No".
        """
        selected_item = self.order_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Attenzione", "Seleziona un preventivo da confermare.")
            return

        old_path = selected_item.data(Qt.UserRole)
        
        # --- COSTRUZIONE MESSAGGIO CUSTOM ---
        msg = QMessageBox(self)
        msg.setWindowTitle("Conferma Preventivo")
        msg.setText(f"Vuoi trasformare questo preventivo in un ORDINE effettivo?\nLa data dell'ordine verrà aggiornata ad OGGI.")
        msg.setIcon(QMessageBox.Question)
        
        btn_si = msg.addButton("Sì", QMessageBox.YesRole)
        btn_no = msg.addButton("No", QMessageBox.NoRole)
        
        msg.exec()

        if msg.clickedButton() != btn_si:
            return

        try:
            # 1. Leggi i dati originali
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 2. Modifica i metadati
            if "info_ordine" not in data: data["info_ordine"] = {}
            data["info_ordine"]["tipo_documento"] = "ordine"
            data["info_ordine"]["data_ordine"] = datetime.now().date().isoformat()

            # 3. Genera il nuovo percorso file
            cust_name = data.get("dati_cliente", {}).get("nome_cliente", "Cliente").strip()
            cer_date = data.get("info_ordine", {}).get("data_cerimonia", "")
            
            safe_cust_name = re.sub(r'[\\/*?:"<>|]', "", cust_name)
            safe_cust_name = re.sub(r'\s+', '_', safe_cust_name).strip('_')

            base_filename = f"Ordine_{safe_cust_name}_{cer_date}"
            target_filename = base_filename + ".json"
            target_path = os.path.join(ORDERS_DIR, target_filename)

            # Gestione duplicati
            counter = 1
            while os.path.exists(target_path):
                target_filename = f"{base_filename}_{counter}.json"
                target_path = os.path.join(ORDERS_DIR, target_filename)
                counter += 1

            # 4. Scrivi il nuovo file
            if not os.path.exists(ORDERS_DIR):
                os.makedirs(ORDERS_DIR)
                
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # 5. Rimuovi il vecchio file
            os.remove(old_path)

            QMessageBox.information(self, "Successo", "Preventivo trasformato in Ordine!\nData aggiornata ad oggi.")
            
            self.load_orders() 

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile convertire il file:\n{e}")

    # ============================================================================
    # --- CARICAMENTO E FILTRAGGIO DATI ---
    # ============================================================================
            
    def showEvent(self, event):
        """Metodo chiamato automaticamente ogni volta che la pagina diventa visibile."""
        self.load_orders()
        super().showEvent(event)

    def load_orders(self):
        """Scansiona la cartella (Orders o Quotes) e carica i file in memoria."""
        self.all_orders = []

        is_quote_mode = (self.type_selector.currentIndex() == 1)
        target_dir = QUOTES_DIR if is_quote_mode else ORDERS_DIR
        
        # Aggiorna visibilità bottone conferma (ridondante ma sicuro)
        self.btn_confirm.setVisible(is_quote_mode)

        if not os.path.exists(target_dir): 
            if is_quote_mode:
                self.update_list_widget()
                return
            self.order_list_widget.clear()
            self.order_list_widget.addItem(f"Cartella non trovata: {target_dir}")
            return

        # Scansione directory
        for filename in os.listdir(target_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(target_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Estrazione dati minimi per la lista
                    customer_name = data.get("dati_cliente", {}).get("nome_cliente", "Sconosciuto")
                    ceremony_date_str = data.get("info_ordine", {}).get("data_cerimonia", "")
                    
                    try:
                        ceremony_date = datetime.fromisoformat(ceremony_date_str)
                    except (ValueError, TypeError):
                        ceremony_date = datetime.min 

                    # Aggiunge alla lista interna (non ancora visibile)
                    self.all_orders.append({
                        'filename': filename,
                        'customer_name': customer_name,
                        'ceremony_date': ceremony_date,
                        'full_path': file_path
                    })
                except (json.JSONDecodeError, IOError):
                    pass # Ignora file corrotti
        
        # Ordina per data cerimonia (dal più vecchio al più recente)
        self.all_orders.sort(key=lambda x: x['ceremony_date'])
        
        # Aggiorna la lista visibile a schermo
        self.update_list_widget()

    def update_list_widget(self, orders_to_display=None):
        """Disegna gli elementi nella QListWidget."""
        self.order_list_widget.clear()
        
        # Se non passiamo una lista filtrata, usa tutto
        if orders_to_display is None:
            orders_to_display = self.all_orders

        if not orders_to_display:
            msg = "Nessun preventivo trovato." if self.type_selector.currentIndex() == 1 else "Nessun ordine trovato."
            if self.search_bar.text(): msg = "Nessun risultato per la ricerca."
            self.order_list_widget.addItem(msg)
            return

        for order in orders_to_display:
            # Formattazione Data
            if order['ceremony_date'] == datetime.min:
                date_str = "N.D."
            else:
                date_str = order['ceremony_date'].strftime('%d/%m/%Y')
            
            # Icona visiva nel testo (Emoji)
            prefix = "📝" if self.type_selector.currentIndex() == 1 else "🧾"
            display_text = f"{prefix} {order['customer_name']}  (Cerimonia: {date_str})"
            
            list_item = QListWidgetItem(display_text)
            # Salviamo il percorso completo nel dato "nascosto" dell'item
            list_item.setData(Qt.UserRole, order['full_path']) 
            self.order_list_widget.addItem(list_item)

    def filter_orders(self):
        """Filtra la lista in base al testo digitato nella barra di ricerca."""
        search_text = self.search_bar.text().lower().strip()
        
        if not search_text:
            self.update_list_widget(self.all_orders)
            return
            
        # List Comprehension per filtrare
        filtered_list = [o for o in self.all_orders if search_text in o['customer_name'].lower()]
        self.update_list_widget(filtered_list)