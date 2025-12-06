import json
import re 
import os 
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFormLayout, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QAbstractSpinBox, QHBoxLayout, QMessageBox, QStyleOptionSpinBox, QStyle
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QMouseEvent, QCursor
from PySide6.QtCore import QDate, Qt, QEvent

# Importa la logica di stampa e i percorsi definiti nel progetto
from core.print_order import generate_and_print_order
from paths import ORDERS_DIR, QUOTES_DIR

# ============================================================================
# --- SEZIONE 1: WIDGET PERSONALIZZATI ---
# Queste classi estendono i widget base di Qt per migliorare l'esperienza utente
# e risolvere bug specifici (es. scroll involontario, comportamento su Windows 11).
# ============================================================================

class NoWheelDateEdit(QDateEdit):
    """
    Estensione di QDateEdit che IGNORA la rotella del mouse.
    Motivo: Evita che l'utente cambi data involontariamente scrollando la pagina.
    Inoltre, forza l'apertura del calendario al click sulla casella di testo.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True) # Usa il calendario popup invece delle frecce
        self.lineEdit().setReadOnly(True) # Impedisce la scrittura manuale (solo selezione)
        self.lineEdit().setCursor(Qt.ArrowCursor)
        self.lineEdit().installEventFilter(self) # Intercetta i click sulla casella
    
    def wheelEvent(self, event):
        """Blocca l'evento rotella."""
        event.ignore()

    def eventFilter(self, obj, event):
        """
        Intercetta il click sinistro sulla casella di testo (lineEdit)
        per aprire manualmente il calendario popup.
        """
        if self.isReadOnly(): return super().eventFilter(obj, event)
        if obj == self.lineEdit() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.open_popup()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Gestisce il click sul bottone laterale del widget."""
        if not self.isReadOnly() and event.button() == Qt.LeftButton:
            self.open_popup()
        else:
            super().mousePressEvent(event)

    def open_popup(self):
        """
        Simula un click sul bottone della freccia per aprire il calendario.
        Necessario perché abbiamo reso la lineEdit read-only.
        """
        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        rect = self.style().subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, self)
        # Invia un evento click falso al sistema
        super().mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, rect.center(), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))

class NoWheelComboBox(QComboBox):
    """
    Estensione di QComboBox che IGNORA la rotella del mouse.
    Motivo: Evita cambi accidentali di selezione mentre si scrolla il modulo.
    """
    def wheelEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        # Apre il menu a tendina solo con il tasto sinistro
        if event.button() == Qt.LeftButton: self.showPopup()
        else: super().mousePressEvent(event)

class CheckableComboBox(QComboBox):
    """
    ComboBox Avanzato con CHECKBOX MULTIPLE.
    Permette di selezionare più opzioni (es. più gusti di confetti) contemporaneamente.
    
    CRITICO: Include un fix specifico per WINDOWS 11 che impedisce la chiusura
    immediata del menu quando si clicca su un elemento.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True) # L'utente vede il testo ma non scrive direttamente
        
        # Usa un modello standard per gestire gli stati Check/Uncheck
        self.model = QStandardItemModel(self)
        self.setModel(self.model)
        
        # Installazione filtri eventi per gestire i click
        self.lineEdit().installEventFilter(self)
        self.view().viewport().installEventFilter(self)

    def wheelEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        """
        Cuore della logica Checkable.
        """
        # 1. Click sulla casella di testo -> Apre il menu
        if obj == self.lineEdit() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.showPopup()
                return True
        
        # 2. FIX WINDOWS 11: Click su un elemento della lista interna (viewport)
        if obj == self.view().viewport() and event.type() == QEvent.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            item = self.model.itemFromIndex(index)
            
            if item and item.isEnabled():
                # Inverte lo stato (Checked <-> Unchecked)
                new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                item.setCheckState(new_state)
                self.update_display_text()
                return True # "Mangia" l'evento: impedisce a Qt di chiudere il menu!
                
        return super().eventFilter(obj, event)

    def update_display_text(self):
        """Aggiorna il testo visibile concatenando gli elementi selezionati con virgole."""
        checked_items = [self.model.item(i).text() for i in range(self.model.rowCount()) 
                         if self.model.item(i).checkState() == Qt.Checked]
        self.lineEdit().setText(", ".join(checked_items))

    def addItem(self, text, data=None):
        """Aggiunge un elemento con checkbox al modello."""
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled) # Abilita la checkbox
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model.appendRow(item)

    def set_checked_items_from_string(self, text_string):
        """
        Prende una stringa CSV (es. "Cioccolato, Mandorla") e 
        seleziona le checkbox corrispondenti. Usato nel caricamento dati.
        """
        items_to_check = [x.strip() for x in (text_string or "").split(',')]
        found_any = False
        
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if item.text() in items_to_check:
                item.setCheckState(Qt.Checked)
                found_any = True
            else:
                item.setCheckState(Qt.Unchecked)
        
        if found_any:
            self.update_display_text()
        else:
            self.lineEdit().setText(text_string) # Fallback se nessun match

# ============================================================================
# --- SEZIONE 2: PAGINA PRINCIPALE (IL "BOSS FINALE") ---
# ============================================================================

class NewOrderPage(QWidget):
    """
    Pagina polifunzionale per:
    1. Creare Nuovi Ordini e Preventivi.
    2. Modificare esistenti.
    3. Convertire Preventivi in Ordini.
    4. Calcolare totali e salvare JSON.
    """
    
    def __init__(self, on_back):
        super().__init__()
        # Memorizza il percorso del file aperto (se siamo in modifica)
        self.current_file_path = None
        
        # Costruisce l'intera interfaccia grafica
        self.setup_ui(on_back)
        
        # Inizializza il form pulito
        self.prepare_new_order()

    def setup_ui(self, on_back):
        """
        Costruisce il layout. Usa QScrollArea perché il form è lungo e
        potrebbe non entrare in schermi piccoli.
        """
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # Adatta il contenuto alla finestra
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget) 

        # ---------------------------------------------------------
        # A. GRUPPO INFORMAZIONI GENERALI (Form Layout)
        # ---------------------------------------------------------
        form_layout = QFormLayout()
        
        # Data Ordine (spesso read-only o automatica)
        self.order_date_picker = NoWheelDateEdit()
        self.order_date_picker.setReadOnly(True) 
        self.order_date_picker.setButtonSymbols(QAbstractSpinBox.NoButtons)
        
        title = QLabel("<h2>Informazioni Ordine</h2>")
        title.setObjectName("titleLabel")
        form_layout.addRow(title)
        form_layout.addRow("Data Ordine:", self.order_date_picker)
        
        # Operatore
        self.operator_combo = NoWheelComboBox()
        self.operator_combo.addItems(["Ketty", "Valentina"])
        form_layout.addRow("Ordine Di:", self.operator_combo)
        
        # Date Evento
        self.date_picker = NoWheelDateEdit()
        form_layout.addRow("Data Cerimonia:", self.date_picker)
        
        self.delivery_date_picker = NoWheelDateEdit()
        form_layout.addRow("Data Consegna:", self.delivery_date_picker)
        
        # Dettagli Cerimonia
        self.ceremony_combo = NoWheelComboBox()
        self.ceremony_combo.addItems(["Nascita","Battesimo","Comunione","Cresima","Laurea","Matrimonio","25 Anni","50 Anni","60 Anni","Anniversario","Compleanno","Pensione"])
        form_layout.addRow("Tipo Cerimonia:", self.ceremony_combo)
        
        self.ribbon_color = QLineEdit()
        form_layout.addRow("Colore Nastri:", self.ribbon_color)
        
        # Confetti (Checkable Combo)
        self.confetti_combo = CheckableComboBox()
        for i in ["Mandorla", "Cioccolato", "Ciocopassion", "Snob", "Stella"]: 
            self.confetti_combo.addItem(i)
        form_layout.addRow("Tipo Confetti:", self.confetti_combo)
        
        self.confetti_color_combo = NoWheelComboBox()
        self.confetti_color_combo.addItems(["Bianco", "Rosa", "Azzurro", "Rosso", "Oro", "Argento"])
        form_layout.addRow("Colore Confetti:", self.confetti_color_combo)
        
        self.packaging = QLineEdit()
        form_layout.addRow("Confezione:", self.packaging)
        
        # Pagamento e Logica Dinamica Acconti
        self.payment_type = NoWheelComboBox()
        self.payment_type.addItems(["Acconto", "Consegna", "Giorno Prima Della Cerimonia", "Altro"])
        # Collega il segnale: se cambia il pagamento, mostra/nascondi campi acconto
        self.payment_type.currentTextChanged.connect(self.toggle_acconto_fields)
        form_layout.addRow("Pagamento:", self.payment_type)

        # Widget Acconto 1 (Nascosti di default se non "Acconto")
        self.label_acc1 = QLabel("Tipo Acconto 1:")
        self.acc1_tipo = NoWheelComboBox()
        self.acc1_tipo.addItems(["", "Contanti", "Bancomat", "Bonifico"])
        self.label_acc1_val = QLabel("Importo Acconto 1:")
        self.acc1_val = QLineEdit()
        form_layout.addRow(self.label_acc1, self.acc1_tipo)
        form_layout.addRow(self.label_acc1_val, self.acc1_val)

        # Widget Acconto 2
        self.label_acc2 = QLabel("Tipo Acconto 2:")
        self.acc2_tipo = NoWheelComboBox()
        self.acc2_tipo.addItems(["", "Contanti", "Bancomat", "Bonifico"])
        self.label_acc2_val = QLabel("Importo Acconto 2:")
        self.acc2_val = QLineEdit()
        form_layout.addRow(self.label_acc2, self.acc2_tipo)
        form_layout.addRow(self.label_acc2_val, self.acc2_val)

        self.extra = QLineEdit()
        form_layout.addRow("Altro:", self.extra)
        
        layout.addLayout(form_layout)

        # ---------------------------------------------------------
        # B. TABELLA ARTICOLI (Cuore Matematico)
        # ---------------------------------------------------------
        layout.addWidget(QLabel("<b>Dettagli Ordine</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Ditta", "Codice", "Descrizione", "Quantità", "Prezzo Unitario", "Totale"])
        
        # Connessione segnale: quando cambia una cella, ricalcola i totali
        self.table.itemChanged.connect(self.update_totals)
        
        # Configurazione Layout Tabella
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True) # L'ultima colonna riempie lo spazio
        self.table.setColumnWidth(0, 200) # Ditta più larga
        self.table.setColumnWidth(2, 500) # Descrizione molto larga
        self.table.setMinimumHeight(300)
        
        layout.addWidget(self.table)

        # --- FIX LARGHEZZE COLONNE ---
        # Impostiamo larghezze fisse per evitare che le scritte vengano schiacciate dal padding
        self.table.setColumnWidth(0, 180) # Ditta
        self.table.setColumnWidth(1, 90)  # Codice
        self.table.setColumnWidth(2, 560) # Descrizione (ridotta leggermente da 500 per dare spazio a Prezzo)
        self.table.setColumnWidth(3, 80)  # Quantità
        self.table.setColumnWidth(4, 140) # Prezzo Unitario (AUMENTATO: Ora il testo ci sta comodo)
        
        self.table.setMinimumHeight(300)
        
        # Bottoni gestione righe
        tbl_btns = QHBoxLayout()
        btn_add = QPushButton("➕ Aggiungi Riga")
        btn_add.clicked.connect(self.add_row)
        btn_del = QPushButton("🗑️ Rimuovi Riga")
        btn_del.clicked.connect(self.remove_selected_row)
        tbl_btns.addWidget(btn_add)
        tbl_btns.addWidget(btn_del)
        tbl_btns.addStretch()
        layout.addLayout(tbl_btns)
        
        # ---------------------------------------------------------
        # C. DATI CLIENTE
        # ---------------------------------------------------------
        form_cli = QFormLayout()
        form_cli.addRow(QLabel("<h2>Dati Cliente</h2>"))
        self.customer_name = QLineEdit()
        form_cli.addRow("Nome Cliente:", self.customer_name)
        self.customer_number = QLineEdit()
        form_cli.addRow("Telefono Cliente:", self.customer_number)
        layout.addLayout(form_cli)

        # ---------------------------------------------------------
        # D. BOTTONI AZIONE (Salva, Stampa, Converti, Esci)
        # ---------------------------------------------------------
        btm_btns = QHBoxLayout()
        btn_menu = QPushButton("⬅️ Menu")
        btn_menu.clicked.connect(on_back)
        
        # Gruppo Ordini
        btn_save_ord = QPushButton("💾 Salva Ordine")
        btn_save_ord.clicked.connect(lambda: self.save_process(is_quote=False, print_after=False))
        btn_prt_ord = QPushButton("📄 Stampa Ordine")
        btn_prt_ord.clicked.connect(lambda: self.save_process(is_quote=False, print_after=True))

        # Gruppo Preventivi
        self.btn_save_qt = QPushButton("💾 Salva Preventivo")
        self.btn_save_qt.clicked.connect(lambda: self.save_process(is_quote=True, print_after=False))
        self.btn_prt_qt = QPushButton("📄 Stampa Prev.")
        self.btn_prt_qt.clicked.connect(lambda: self.save_process(is_quote=True, print_after=True))

        # Bottone Speciale: Converti
        self.btn_convert = QPushButton("✅ Converti in Ordine")
        self.btn_convert.setVisible(False) # Visibile solo se carico un preventivo
        self.btn_convert.clicked.connect(self.convert_quote_to_order)
        # Stile verde per evidenziare l'azione positiva
        self.btn_convert.setStyleSheet("background-color: #d1e7dd; border: 1px solid #badbcc; color: #0f5132; font-weight: bold;")

        # Aggiunta al layout
        btm_btns.addWidget(btn_menu)
        btm_btns.addStretch()
        btm_btns.addWidget(self.btn_save_qt)
        btm_btns.addWidget(self.btn_prt_qt)
        btm_btns.addSpacing(15)
        btm_btns.addWidget(self.btn_convert)
        btm_btns.addSpacing(15)
        btm_btns.addWidget(btn_save_ord)
        btm_btns.addWidget(btn_prt_ord)
        
        layout.addLayout(btm_btns)
        layout.addStretch()
        
        # Finalizzazione Scroll Area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    # ============================================================================
    # --- SEZIONE 3: LOGICA UI E INTERAZIONE ---
    # ============================================================================

    def toggle_acconto_fields(self, text):
        """Nasconde o mostra i campi 'Acconto' in base alla scelta nel menu Pagamento."""
        is_visible = (text == "Acconto")
        # Lista dei widget da mostrare/nascondere
        widgets = [self.label_acc1, self.acc1_tipo, self.label_acc1_val, self.acc1_val,
                   self.label_acc2, self.acc2_tipo, self.label_acc2_val, self.acc2_val]
        for w in widgets:
            w.setVisible(is_visible)

    def prepare_new_order(self):
        """
        RESET TOTALE del form. Chiamato quando si clicca 'Nuovo Ordine'
        o dopo aver salvato con successo.
        """
        self.current_file_path = None
        self.btn_convert.setVisible(False)
        
        # Reset Date
        self.order_date_picker.setDate(QDate.currentDate())
        self.date_picker.setDate(QDate.currentDate())
        self.delivery_date_picker.setDate(QDate.currentDate())
        
        # Reset Campi Testo
        self.operator_combo.setCurrentIndex(0)
        self.ceremony_combo.setCurrentIndex(0)
        self.ribbon_color.clear()
        self.packaging.clear()
        self.extra.clear()
        self.customer_name.clear()
        self.customer_number.clear()
        self.acc1_val.clear()
        self.acc2_val.clear()
        
        # Reset Combo Complesse
        self.confetti_combo.set_checked_items_from_string("")
        self.confetti_color_combo.setCurrentIndex(0)
        self.payment_type.setCurrentIndex(0)
        self.acc1_tipo.setCurrentIndex(0)
        self.acc2_tipo.setCurrentIndex(0)
        
        # Reset Tabella (rigenera 6 righe vuote)
        self.table.setRowCount(0)
        for _ in range(6): self.add_row()
        
        # Aggiorna visibilità campi acconto
        self.toggle_acconto_fields(self.payment_type.currentText())

    def load_order(self, file_path):
        """
        Carica un file JSON e popola tutti i campi del form.
        Gestisce le differenze tra Ordini e Preventivi.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.current_file_path = file_path
            
            # Determina se è un preventivo guardando la cartella di provenienza
            is_quote = (os.path.abspath(QUOTES_DIR) in os.path.abspath(file_path))
            self.btn_convert.setVisible(is_quote)
            
            info = data.get("info_ordine", {})
            cust = data.get("dati_cliente", {})
            
            # Gestione Date: Se è un preventivo, data ordine diventa OGGI (per rinnovo)
            if is_quote: 
                self.order_date_picker.setDate(QDate.currentDate())
            else: 
                self.order_date_picker.setDate(QDate.fromString(info.get("data_ordine"), Qt.ISODate))
            
            self.date_picker.setDate(QDate.fromString(info.get("data_cerimonia"), Qt.ISODate))
            
            # Gestione Data Consegna (se manca, usa oggi)
            del_date = info.get("data_consegna")
            self.delivery_date_picker.setDate(QDate.fromString(del_date, Qt.ISODate) if del_date else QDate.currentDate())
            
            # Popolamento Campi
            self.operator_combo.setCurrentText(info.get("operatore", ""))
            self.ceremony_combo.setCurrentText(info.get("tipo_cerimonia", ""))
            self.ribbon_color.setText(info.get("colore_nastri", ""))
            
            # Popolamento Checkbox multiple (usa la stringa CSV salvata)
            self.confetti_combo.set_checked_items_from_string(info.get("tipo_confetti", ""))
            self.confetti_color_combo.setCurrentText(info.get("colore_confetti", ""))
            
            self.packaging.setText(info.get("confezione", ""))
            self.payment_type.setCurrentText(info.get("pagamento", ""))
            self.extra.setText(info.get("altro", ""))
            
            # Acconti
            self.acc1_tipo.setCurrentText(info.get("acconto1_tipo", ""))
            self.acc1_val.setText(info.get("acconto1_importo", ""))
            self.acc2_tipo.setCurrentText(info.get("acconto2_tipo", ""))
            self.acc2_val.setText(info.get("acconto2_importo", ""))

            # Cliente
            self.customer_name.setText(cust.get("nome_cliente", ""))
            self.customer_number.setText(cust.get("telefono_cliente", ""))
            
            # Popolamento Tabella
            self.table.setRowCount(0)
            for item in data.get("dettagli_ordine", []): 
                self.add_row_with_data(item)
            
            # Assicura che ci siano almeno 6 righe visibili (estetica)
            while self.table.rowCount() < 6: 
                self.add_row()
            
            self.toggle_acconto_fields(self.payment_type.currentText())

        except Exception as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile leggere il file:\n{e}")
            self.prepare_new_order()

    # ============================================================================
    # --- SEZIONE 4: LOGICA TABELLA (Righe, Calcoli) ---
    # ============================================================================

    def add_row(self):
        """Aggiunge una riga vuota. Limita a 13 righe per layout di stampa."""
        if self.table.rowCount() >= 13:
            QMessageBox.warning(self, "Limite", "Massimo 13 articoli consentiti per layout di stampa.")
            return
        self.add_row_with_data({})

    def add_row_with_data(self, data):
        """
        Crea una nuova riga e la riempie con i dati forniti (o vuoti).
        Imposta i widget specifici per ogni cella (ComboBox per ditta, ecc.)
        """
        r = self.table.rowCount()
        self.table.insertRow(r)
        
        # Colonna 0: ComboBox Ditte
        cb = NoWheelComboBox()
        cb.addItems(["","BAGUTTA","BIPAPER","CLARALUNA","CUOREMATTO","DIMAR","DOLCICOSE","HERVIT","EMMEBI","ETM","FAMA","FANTIN","FOGAL","FRANCESCO","LAGUNA","MAS","NEGO","PABEN","QUADRIFOGLIO","TABOR"])
        cb.setCurrentText(data.get("ditta", ""))
        self.table.setCellWidget(r, 0, cb)
        
        # Colonne 1-4: Testo Editabile
        self.table.setItem(r, 1, QTableWidgetItem(data.get("codice", "")))
        self.table.setItem(r, 2, QTableWidgetItem(data.get("descrizione", "")))
        self.table.setItem(r, 3, QTableWidgetItem(str(data.get("quantita", ""))))
        self.table.setItem(r, 4, QTableWidgetItem(str(data.get("prezzo_unitario", ""))))
        
        # Colonna 5: Totale (Non editabile, calcolato automaticamente)
        tot = QTableWidgetItem(str(data.get("prezzo_totale", "0.00")))
        tot.setFlags(tot.flags() & ~Qt.ItemIsEditable) # Rende la cella "Read Only"
        self.table.setItem(r, 5, tot)

        # --- FIX DIMENSIONI: Adatta l'altezza della riga al contenuto (CSS padding) ---
        self.table.resizeRowToContents(r)

    def remove_selected_row(self):
        """Rimuove la riga attualmente selezionata."""
        if self.table.currentRow() >= 0: 
            self.table.removeRow(self.table.currentRow())

    def update_totals(self, item):
        """
        Callback automatica: scatta quando una cella viene modificata.
        Se cambia Quantità o Prezzo Unitario, ricalcola il Totale della riga.
        """
        # Controlla che la modifica sia nelle colonne Quantità (3) o Prezzo (4)
        if item.column() not in [3, 4]: return
        
        r = item.row()
        
        # --- FIX CRASH: Recupera gli item in modo sicuro ---
        qty_item = self.table.item(r, 3)
        price_item = self.table.item(r, 4)
        total_item = self.table.item(r, 5)

        # Se uno degli item non esiste ancora (es. durante la creazione della riga),
        # interrompiamo la funzione per evitare l'errore 'NoneType'.
        if qty_item is None or price_item is None or total_item is None:
            return

        try:
            # Sostituisce la virgola con punto per conversione float
            q_text = qty_item.text().replace(',', '.')
            p_text = price_item.text().replace(',', '.')
            
            q = float(q_text or 0)
            p = float(p_text or 0)
        except ValueError:
            q, p = 0.0, 0.0
            
        # Blocca i segnali per evitare loop infiniti mentre aggiorno la cella totale
        self.table.blockSignals(True)
        total_item.setText(f"{q*p:.2f}")
        self.table.blockSignals(False)

    # ============================================================================
    # --- SEZIONE 5: LOGICA DI SALVATAGGIO E CONVERSIONE ---
    # ============================================================================

    def convert_quote_to_order(self):
        """
        Trasforma un Preventivo esistente in un Ordine.
        1. Chiede conferma (Sì/No).
        2. Salva i dati correnti come NUOVO Ordine (data oggi).
        3. Cancella il vecchio file Preventivo.
        """
        old_path = self.current_file_path
        
        # --- COSTRUZIONE MESSAGGIO CUSTOM (Per avere "Sì/No") ---
        msg = QMessageBox(self)
        msg.setWindowTitle("Conferma Conversione")
        msg.setText("Convertire preventivo in ordine?\nLa data ordine verrà aggiornata ad OGGI e il preventivo eliminato.")
        msg.setIcon(QMessageBox.Question)
        
        # Aggiungiamo i bottoni manualmente con il testo italiano
        btn_si = msg.addButton("Sì", QMessageBox.YesRole)
        btn_no = msg.addButton("No", QMessageBox.NoRole)
        
        msg.exec() # Mostra la finestra e aspetta il click
        
        # Se l'utente non ha cliccato "Sì", usciamo
        if msg.clickedButton() != btn_si:
            return
        
        # --- PROCEDURA DI CONVERSIONE ---
        
        # Forza data oggi per il nuovo ordine
        self.order_date_picker.setDate(QDate.currentDate())
        
        # Esegue salvataggio come ORDINE (is_quote=False)
        data, path = self.perform_save(is_quote=False)
        
        # Se salvataggio ok, elimina vecchio file
        if data and path and old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
                QMessageBox.information(self, "Info", "Conversione riuscita.")
                self.prepare_new_order()
            except Exception as e:
                QMessageBox.warning(self, "Attenzione", f"Ordine creato, ma impossibile eliminare vecchio preventivo: {e}")

    def save_process(self, is_quote, print_after):
        """
        Wrapper che gestisce il flusso completo: Salvataggio -> Messaggio -> Stampa (opzionale).
        """
        data, path = self.perform_save(is_quote)
        
        if not data: return # Salvataggio fallito o annullato
        
        doc_type = "Preventivo" if is_quote else "Ordine"
        QMessageBox.information(self, "Salvataggio", f"{doc_type} salvato con successo:\n{os.path.basename(path)}")
        
        if print_after:
            # Chiama la funzione di core che genera ODS -> PDF -> Stampa
            generate_and_print_order(data, os.path.basename(path))
        
        # Pulisce il form dopo l'operazione
        self.prepare_new_order()

    def perform_save(self, is_quote=False):
        """
        Logica Core di persistenza.
        1. Raccoglie dati dal form.
        2. Decide la cartella (Orders/Quotes).
        3. Genera nome file univoco.
        4. Scrive JSON su disco.
        """
        # Validazione minima
        if not self.customer_name.text().strip():
            QMessageBox.warning(self, "Errore", "Inserire almeno il Nome Cliente.")
            return None, None

        # 1. Raccolta Dati
        info = {
            "data_ordine": self.order_date_picker.date().toString(Qt.ISODate),
            "operatore": self.operator_combo.currentText(),
            "data_cerimonia": self.date_picker.date().toString(Qt.ISODate),
            "data_consegna": self.delivery_date_picker.date().toString(Qt.ISODate),
            "tipo_cerimonia": self.ceremony_combo.currentText(),
            "colore_nastri": self.ribbon_color.text(),
            "tipo_confetti": self.confetti_combo.lineEdit().text(), # Prende testo CSV
            "colore_confetti": self.confetti_color_combo.currentText(),
            "confezione": self.packaging.text(),
            "pagamento": self.payment_type.currentText(),
            "altro": self.extra.text(),
            "tipo_documento": "preventivo" if is_quote else "ordine",
            # Dati Acconto
            "acconto1_tipo": self.acc1_tipo.currentText(), 
            "acconto1_importo": self.acc1_val.text(),
            "acconto2_tipo": self.acc2_tipo.currentText(), 
            "acconto2_importo": self.acc2_val.text()
        }
        
        # Raccolta Tabella (salva solo righe non vuote)
        details = []
        for r in range(self.table.rowCount()):
            d = {
                "ditta": self.table.cellWidget(r, 0).currentText(),
                "codice": self.table.item(r, 1).text(),
                "descrizione": self.table.item(r, 2).text(),
                "quantita": self.table.item(r, 3).text(),
                "prezzo_unitario": self.table.item(r, 4).text(),
                "prezzo_totale": self.table.item(r, 5).text()
            }
            # Se almeno un campo (esclusi quelli numerici a 0) è pieno, salva la riga
            if any(v for k, v in d.items() if k not in ["prezzo_totale", "quantita", "prezzo_unitario"]):
                details.append(d)

        full_data = {
            "info_ordine": info, 
            "dati_cliente": {
                "nome_cliente": self.customer_name.text(), 
                "telefono_cliente": self.customer_number.text()
            }, 
            "dettagli_ordine": details
        }

        # 2. Gestione Percorso
        target_dir = QUOTES_DIR if is_quote else ORDERS_DIR
        os.makedirs(target_dir, exist_ok=True)
        
        # 3. Logica Nome File
        # Se stiamo modificando un file che è GIA' nella cartella giusta, sovrascriviamo
        if self.current_file_path and os.path.dirname(self.current_file_path) == os.path.abspath(target_dir):
            path = self.current_file_path
        else:
            # Creazione nuovo file: Sanificazione nome cliente
            safe_name = re.sub(r'[\\/*?:"<>|]', "", self.customer_name.text()).replace(" ", "_")
            prefix = 'Preventivo' if is_quote else 'Ordine'
            base_filename = f"{prefix}_{safe_name}_{info['data_cerimonia']}"
            
            path = os.path.join(target_dir, f"{base_filename}.json")
            
            # Evita sovrascritture accidentali aggiungendo _1, _2, ecc.
            counter = 1
            while os.path.exists(path):
                path = os.path.join(target_dir, f"{base_filename}_{counter}.json")
                counter += 1

        # 4. Scrittura su Disco
        try:
            with open(path, 'w', encoding='utf-8') as f: 
                json.dump(full_data, f, indent=4, ensure_ascii=False)
            
            # Aggiorna il puntatore al file corrente
            self.current_file_path = path
            return full_data, path
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Critico", f"Salvataggio fallito: {e}")
            return None, None