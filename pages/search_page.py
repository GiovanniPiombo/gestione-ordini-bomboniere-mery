import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem,
    QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

from paths import ORDERS_DIR

class SearchPage(QWidget):
    """
    Pagina di ricerca che carica, visualizza, ordina e filtra 
    i file JSON degli ordini dalla cartella 'orders'.
    """

    def __init__(self, on_back, on_load_order, on_print_order):
        super().__init__()
        
        self.on_load_order = on_load_order
        self.on_print_order = on_print_order
        
        # Lista interna per memorizzare i dati degli ordini caricati
        self.all_orders = []

        layout = QVBoxLayout()
        title = QLabel("<h2>Lista Ordini</h2>")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Barra di ricerca
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca per nome cliente...")
        self.search_bar.textChanged.connect(self.filter_orders)
        layout.addWidget(self.search_bar)

        # Lista per visualizzare gli ordini
        self.order_list_widget = QListWidget()
        self.order_list_widget.itemDoubleClicked.connect(self.handle_double_click)
        layout.addWidget(self.order_list_widget)

        # Layout per i bottoni
        button_layout = QHBoxLayout()

        btn_back = QPushButton("⬅️ Torna al Menu")
        btn_back.clicked.connect(on_back)
        
        btn_print = QPushButton("📄 Stampa Selezionato")
        btn_print.clicked.connect(self.handle_print_click)
        
        button_layout.addWidget(btn_back)
        button_layout.addWidget(btn_print)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def handle_double_click(self, item):
        """
        Chiamato al doppio clic su un item della lista.
        Recupera il percorso del file e chiama il callback 'on_load_order'.
        """
        file_path = item.data(Qt.UserRole)
        if file_path and self.on_load_order:
            self.on_load_order(file_path)

    def handle_print_click(self):
        """
        Chiamato al clic sul pulsante Stampa.
        Recupera il percorso del file selezionato e chiama il callback 'on_print_order'.
        """
        selected_item = self.order_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un ordine da stampare.")
            return

        file_path = selected_item.data(Qt.UserRole) # Recupera il percorso salvato
        if file_path and self.on_print_order:
            self.on_print_order(file_path)

    def showEvent(self, event):
        """
        Override: Chiamato da Qt ogni volta che la pagina viene mostrata.
        Usato per ricaricare gli ordini.
        """
        self.load_orders()
        super().showEvent(event)

    def load_orders(self):
        """
        Carica tutti i file .json dalla cartella ORDERS_DIR,
        li analizza e li ordina per data cerimonia.
        """
        self.all_orders = []

        # ORDERS_DIR è ora la costante importata
        if not os.path.exists(ORDERS_DIR): 
            self.order_list_widget.clear()
            self.order_list_widget.addItem(f"Errore: Cartella '{ORDERS_DIR}' non trovata.")
            return

        for filename in os.listdir(ORDERS_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(ORDERS_DIR, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    customer_name = data.get("dati_cliente", {}).get("nome_cliente", "Sconosciuto")
                    ceremony_date_str = data.get("info_ordine", {}).get("data_cerimonia", "")
                    
                    try:
                        ceremony_date = datetime.fromisoformat(ceremony_date_str)
                    except (ValueError, TypeError):
                        ceremony_date = datetime.min # Fallback per date non valide o mancanti

                    self.all_orders.append({
                        'filename': filename,
                        'customer_name': customer_name,
                        'ceremony_date': ceremony_date,
                        'full_path': file_path
                    })
                
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Errore durante la lettura di {filename}: {e}")
                    pass
        
        # Ordina la lista di ordini per data cerimonia (dalla più vecchia alla più recente)
        self.all_orders.sort(key=lambda x: x['ceremony_date'])
        
        self.update_list_widget()

    def update_list_widget(self, orders_to_display=None):
        """
        Popola la QListWidget con la lista di ordini fornita.
        """
        self.order_list_widget.clear()
        
        if orders_to_display is None:
            orders_to_display = self.all_orders

        if not orders_to_display:
            if not self.all_orders:
                self.order_list_widget.addItem("Nessun ordine trovato.")
            else:
                self.order_list_widget.addItem("Nessun ordine corrisponde alla ricerca.")
            return

        for order in orders_to_display:
            if order['ceremony_date'] == datetime.min:
                date_str = "N.D."
            else:
                date_str = order['ceremony_date'].strftime('%d/%m/%Y')

            display_text = f"{order['customer_name']}  (Cerimonia: {date_str})"
            
            list_item = QListWidgetItem(display_text)
            
            # Salva il percorso completo (non visibile) dentro l'item
            list_item.setData(Qt.UserRole, order['full_path']) 
            
            self.order_list_widget.addItem(list_item)

    def filter_orders(self):
        """
        Filtra la lista 'self.all_orders' in base al testo nella barra di ricerca.
        """
        search_text = self.search_bar.text().lower().strip()

        if not search_text:
            self.update_list_widget(self.all_orders)
            return

        filtered_list = [
            order for order in self.all_orders 
            if search_text in order['customer_name'].lower()
        ]
        
        self.update_list_widget(filtered_list)