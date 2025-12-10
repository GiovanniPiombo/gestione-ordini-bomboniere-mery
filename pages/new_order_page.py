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
# Queste classi servono a migliorare l'UX e correggere comportamenti di default.
# ============================================================================

class NoWheelDateEdit(QDateEdit):
    """
    DateEdit che ignora la rotella del mouse per evitare cambi data accidentali
    durante lo scroll della pagina. Apre il calendario al click.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.lineEdit().setReadOnly(True) # Impedisce scrittura manuale
        self.lineEdit().setCursor(Qt.ArrowCursor)
        self.lineEdit().installEventFilter(self)
    
    def wheelEvent(self, event):
        """Blocca l'evento scroll."""
        event.ignore()

    def eventFilter(self, obj, event):
        """Intercetta il click per aprire il calendario manualmente."""
        if self.isReadOnly(): return super().eventFilter(obj, event)
        if obj == self.lineEdit() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.open_popup()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if not self.isReadOnly() and event.button() == Qt.LeftButton:
            self.open_popup()
        else:
            super().mousePressEvent(event)

    def open_popup(self):
        """Simula il click sulla freccetta per aprire il popup calendario."""
        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        rect = self.style().subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, self)
        super().mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, rect.center(), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))

class NoWheelComboBox(QComboBox):
    """ComboBox che ignora lo scroll del mouse per evitare cambi involontari."""
    def wheelEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.showPopup()
        else: super().mousePressEvent(event)

class CheckableComboBox(QComboBox):
    """
    ComboBox che permette selezioni multiple (es. più gusti confetti).
    Include un FIX CRITICO per Windows 11.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.model = QStandardItemModel(self)
        self.setModel(self.model)
        self.lineEdit().installEventFilter(self)
        self.view().viewport().installEventFilter(self)

    def wheelEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        # Apre il menu al click sulla casella di testo
        if obj == self.lineEdit() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.showPopup()
                return True
        
        # --- FIX WINDOWS 11 ---
        # Intercetta il rilascio del mouse sugli elementi della lista.
        # Invece di far chiudere il menu (comportamento standard), inverte lo stato
        # della checkbox e consuma l'evento (return True), mantenendo il menu aperto.
        if obj == self.view().viewport() and event.type() == QEvent.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            item = self.model.itemFromIndex(index)
            if item and item.isEnabled():
                new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                item.setCheckState(new_state)
                self.update_display_text()
                return True 
        return super().eventFilter(obj, event)

    def update_display_text(self):
        """Aggiorna il testo visibile separando le scelte con virgole."""
        checked_items = [self.model.item(i).text() for i in range(self.model.rowCount()) 
                         if self.model.item(i).checkState() == Qt.Checked]
        self.lineEdit().setText(", ".join(checked_items))

    def addItem(self, text, data=None):
        """Aggiunge un elemento con checkbox."""
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model.appendRow(item)

    def set_checked_items_from_string(self, text_string):
        """Ripristina lo stato delle checkbox partendo da una stringa salvata (CSV)."""
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
            self.lineEdit().setText(text_string)

# ============================================================================
# --- SEZIONE 2: PAGINA PRINCIPALE ---
# ============================================================================

class NewOrderPage(QWidget):
    
    def __init__(self, on_back):
        super().__init__()
        self.current_file_path = None
        self.setup_ui(on_back)
        self.prepare_new_order()

    def setup_ui(self, on_back):
        """Costruisce l'interfaccia grafica usando un Layout a scorrimento."""
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget) 

        # --- A. GRUPPO INFORMAZIONI GENERALI ---
        form_layout = QFormLayout()
        
        self.order_date_picker = NoWheelDateEdit()
        self.order_date_picker.setReadOnly(True) 
        self.order_date_picker.setButtonSymbols(QAbstractSpinBox.NoButtons)
        
        title = QLabel("<h2>Informazioni Ordine</h2>")
        title.setObjectName("titleLabel")
        form_layout.addRow(title)
        form_layout.addRow("Data Ordine:", self.order_date_picker)
        
        self.operator_combo = NoWheelComboBox()
        self.operator_combo.addItems(["Ketty", "Valentina"])
        form_layout.addRow("Ordine Di:", self.operator_combo)
        
        self.date_picker = NoWheelDateEdit()
        form_layout.addRow("Data Cerimonia:", self.date_picker)
        
        self.delivery_date_picker = NoWheelDateEdit()
        form_layout.addRow("Data Consegna:", self.delivery_date_picker)
        
        self.ceremony_combo = NoWheelComboBox()
        self.ceremony_combo.addItems(["Nascita","Battesimo","Comunione","Cresima","Laurea","Matrimonio","25 Anni","50 Anni","60 Anni","Anniversario","Compleanno","Pensione"])
        form_layout.addRow("Tipo Cerimonia:", self.ceremony_combo)
        
        self.ribbon_color = QLineEdit()
        form_layout.addRow("Colore Nastri:", self.ribbon_color)
        
        self.confetti_combo = CheckableComboBox()
        for i in ["Mandorla", "Cioccolato", "Ciocopassion", "Snob", "Stella"]: 
            self.confetti_combo.addItem(i)
        form_layout.addRow("Tipo Confetti:", self.confetti_combo)
        
        self.confetti_color_combo = NoWheelComboBox()
        self.confetti_color_combo.addItems(["Bianco", "Rosa", "Azzurro", "Rosso", "Oro", "Argento"])
        form_layout.addRow("Colore Confetti:", self.confetti_color_combo)
        
        self.packaging = QLineEdit()
        form_layout.addRow("Confezione:", self.packaging)
        
        # Gestione dinamica pagamento (mostra/nasconde acconti)
        self.payment_type = NoWheelComboBox()
        self.payment_type.addItems(["Acconto", "Consegna", "Giorno Prima Della Cerimonia", "Altro"])
        self.payment_type.currentTextChanged.connect(self.toggle_acconto_fields)
        form_layout.addRow("Pagamento:", self.payment_type)

        self.label_acc1 = QLabel("Tipo Acconto 1:")
        self.acc1_tipo = NoWheelComboBox()
        self.acc1_tipo.addItems(["", "Contanti", "Bancomat", "Bonifico"])
        self.label_acc1_val = QLabel("Importo Acconto 1:")
        self.acc1_val = QLineEdit()
        form_layout.addRow(self.label_acc1, self.acc1_tipo)
        form_layout.addRow(self.label_acc1_val, self.acc1_val)

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

        # --- B. TABELLA ARTICOLI ---
        layout.addWidget(QLabel("<b>Dettagli Ordine</b>"))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Ditta", "Codice", "Descrizione", "Quantità", "Prezzo Unitario", "Totale"])
        self.table.itemChanged.connect(self.update_totals) # Callback calcoli
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 560)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 140)
        self.table.setMinimumHeight(300)
        
        layout.addWidget(self.table)
        
        tbl_btns = QHBoxLayout()
        btn_add = QPushButton("➕ Aggiungi Riga")
        btn_add.clicked.connect(self.add_row)
        btn_del = QPushButton("🗑️ Rimuovi Riga")
        btn_del.clicked.connect(self.remove_selected_row)
        tbl_btns.addWidget(btn_add)
        tbl_btns.addWidget(btn_del)
        tbl_btns.addStretch()
        layout.addLayout(tbl_btns)
        
        # --- C. DATI CLIENTE ---
        form_cli = QFormLayout()
        form_cli.addRow(QLabel("<h2>Dati Cliente</h2>"))
        self.customer_name = QLineEdit()
        form_cli.addRow("Nome Cliente:", self.customer_name)
        self.customer_number = QLineEdit()
        form_cli.addRow("Telefono Cliente:", self.customer_number)
        layout.addLayout(form_cli)

        # --- D. BOTTONI AZIONE ---
        btm_btns = QHBoxLayout()
        btn_menu = QPushButton("⬅️ Menu")
        btn_menu.clicked.connect(on_back)
        
        # Gruppo Ordini
        self.btn_save_ord = QPushButton("💾 Salva Ordine")
        self.btn_save_ord.clicked.connect(lambda: self.save_process(is_quote=False, print_after=False))
        
        self.btn_prt_ord = QPushButton("📄 Stampa Ordine")
        self.btn_prt_ord.clicked.connect(lambda: self.save_process(is_quote=False, print_after=True))

        # Gruppo Preventivi
        self.btn_save_qt = QPushButton("💾 Salva Preventivo")
        self.btn_save_qt.clicked.connect(lambda: self.save_process(is_quote=True, print_after=False))
        
        self.btn_prt_qt = QPushButton("📄 Stampa Prev.")
        self.btn_prt_qt.clicked.connect(lambda: self.save_process(is_quote=True, print_after=True))

        # Bottone Converti
        self.btn_convert = QPushButton("✅ Converti in Ordine")
        self.btn_convert.clicked.connect(self.convert_quote_to_order)
        self.btn_convert.setStyleSheet("background-color: #d1e7dd; border: 1px solid #badbcc; color: #0f5132; font-weight: bold;")

        btm_btns.addWidget(btn_menu)
        btm_btns.addStretch()
        # Aggiungo i widget al layout (la visibilità sarà gestita da update_button_states)
        btm_btns.addWidget(self.btn_save_qt)
        btm_btns.addWidget(self.btn_prt_qt)
        btm_btns.addSpacing(15)
        btm_btns.addWidget(self.btn_convert)
        btm_btns.addSpacing(15)
        btm_btns.addWidget(self.btn_save_ord)
        btm_btns.addWidget(self.btn_prt_ord)
        
        layout.addLayout(btm_btns)
        layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    # ============================================================================
    # --- SEZIONE 3: LOGICA UI E INTERAZIONE ---
    # ============================================================================

    def toggle_acconto_fields(self, text):
        """Nasconde/Mostra i campi Acconto se la selezione è diversa da 'Acconto'."""
        is_visible = (text == "Acconto")
        widgets = [self.label_acc1, self.acc1_tipo, self.label_acc1_val, self.acc1_val,
                   self.label_acc2, self.acc2_tipo, self.label_acc2_val, self.acc2_val]
        for w in widgets:
            w.setVisible(is_visible)

    def update_button_states(self, mode="NEW"):
        """
        Gestisce la VISIBILITÀ dei bottoni in base al contesto.
        mode:
          - "NEW": Nuovo foglio. Vedo tutti i salvataggi (Ordine e Prev). Nascondo converti.
          - "ORDER": Ordine esistente. NASCONDO tutto ciò che riguarda i Preventivi.
          - "QUOTE": Preventivo esistente. NASCONDO salvataggio diretto Ordine (serve Converti).
        """
        # 1. Nascondo tutto preventivamente per pulizia
        self.btn_save_ord.setVisible(False)
        self.btn_prt_ord.setVisible(False)
        self.btn_save_qt.setVisible(False)
        self.btn_prt_qt.setVisible(False)
        self.btn_convert.setVisible(False)

        if mode == "NEW":
            # Pagina pulita: posso creare sia Ordine che Preventivo
            self.btn_save_ord.setVisible(True)
            self.btn_prt_ord.setVisible(True)
            self.btn_save_qt.setVisible(True)
            self.btn_prt_qt.setVisible(True)
            
        elif mode == "ORDER":
            # Sto modificando un Ordine: posso solo aggiornare/stampare l'ordine
            self.btn_save_ord.setVisible(True)
            self.btn_prt_ord.setVisible(True)
            
        elif mode == "QUOTE":
            # Sto modificando un Preventivo: posso aggiornare/stampare preventivo o CONVERTIRE
            self.btn_save_qt.setVisible(True)
            self.btn_prt_qt.setVisible(True)
            self.btn_convert.setVisible(True)

    def prepare_new_order(self):
        """RESET TOTALE del form. Usato all'avvio o dopo un salvataggio."""
        self.current_file_path = None
        
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
        
        # Reset Combo
        self.confetti_combo.set_checked_items_from_string("")
        self.confetti_color_combo.setCurrentIndex(0)
        self.payment_type.setCurrentIndex(0)
        self.acc1_tipo.setCurrentIndex(0)
        self.acc2_tipo.setCurrentIndex(0)
        
        # Reset Tabella (rigenera 6 righe vuote)
        self.table.setRowCount(0)
        for _ in range(6): self.add_row()
        
        self.toggle_acconto_fields(self.payment_type.currentText())
        
        # Imposta stato bottoni su NUOVO (Vedi tutto tranne converti)
        self.update_button_states("NEW")

    def load_order(self, file_path):
        """Carica dati da file JSON distinguendo se Ordine o Preventivo."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.current_file_path = file_path
            
            # Controlla se il file si trova nella cartella Preventivi
            is_quote = (os.path.abspath(QUOTES_DIR) in os.path.abspath(file_path))
            
            # AGGIORNAMENTO VISIBILITÀ BOTTONI
            if is_quote:
                self.update_button_states("QUOTE")
            else:
                self.update_button_states("ORDER")
            
            info = data.get("info_ordine", {})
            cust = data.get("dati_cliente", {})
            
            # LOGICA DATE: Se è un preventivo, metti data ordine a OGGI (rinnovo).
            if is_quote: 
                self.order_date_picker.setDate(QDate.currentDate())
            else: 
                self.order_date_picker.setDate(QDate.fromString(info.get("data_ordine"), Qt.ISODate))
            
            self.date_picker.setDate(QDate.fromString(info.get("data_cerimonia"), Qt.ISODate))
            
            del_date = info.get("data_consegna")
            self.delivery_date_picker.setDate(QDate.fromString(del_date, Qt.ISODate) if del_date else QDate.currentDate())
            
            self.operator_combo.setCurrentText(info.get("operatore", ""))
            self.ceremony_combo.setCurrentText(info.get("tipo_cerimonia", ""))
            self.ribbon_color.setText(info.get("colore_nastri", ""))
            
            self.confetti_combo.set_checked_items_from_string(info.get("tipo_confetti", ""))
            self.confetti_color_combo.setCurrentText(info.get("colore_confetti", ""))
            
            self.packaging.setText(info.get("confezione", ""))
            self.payment_type.setCurrentText(info.get("pagamento", ""))
            self.extra.setText(info.get("altro", ""))
            
            self.acc1_tipo.setCurrentText(info.get("acconto1_tipo", ""))
            self.acc1_val.setText(info.get("acconto1_importo", ""))
            self.acc2_tipo.setCurrentText(info.get("acconto2_tipo", ""))
            self.acc2_val.setText(info.get("acconto2_importo", ""))

            self.customer_name.setText(cust.get("nome_cliente", ""))
            self.customer_number.setText(cust.get("telefono_cliente", ""))
            
            # Popolamento Tabella
            self.table.setRowCount(0)
            for item in data.get("dettagli_ordine", []): 
                self.add_row_with_data(item)
            
            # Mantiene estetica: minimo 6 righe
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
        """Aggiunge una riga vuota, con limite massimo di 13 per layout stampa."""
        if self.table.rowCount() >= 13:
            QMessageBox.warning(self, "Limite", "Massimo 13 articoli consentiti per layout di stampa.")
            return
        self.add_row_with_data({})

    def add_row_with_data(self, data):
        """Crea fisicamente la riga e i suoi widget."""
        r = self.table.rowCount()
        self.table.insertRow(r)
        
        cb = NoWheelComboBox()
        cb.addItems(["","BAGUTTA","BIPAPER","CLARALUNA","CUOREMATTO","DIMAR","DOLCICOSE","HERVIT","EMMEBI","ETM","FAMA","FANTIN","FOGAL","FRANCESCO","LAGUNA","MAS","NEGO","PABEN","QUADRIFOGLIO","TABOR"])
        cb.setCurrentText(data.get("ditta", ""))
        self.table.setCellWidget(r, 0, cb)
        
        self.table.setItem(r, 1, QTableWidgetItem(data.get("codice", "")))
        self.table.setItem(r, 2, QTableWidgetItem(data.get("descrizione", "")))
        self.table.setItem(r, 3, QTableWidgetItem(str(data.get("quantita", ""))))
        self.table.setItem(r, 4, QTableWidgetItem(str(data.get("prezzo_unitario", ""))))
        
        # Colonna Totale: Read Only
        tot = QTableWidgetItem(str(data.get("prezzo_totale", "0.00")))
        tot.setFlags(tot.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(r, 5, tot)

        self.table.resizeRowToContents(r)

    def remove_selected_row(self):
        if self.table.currentRow() >= 0: 
            self.table.removeRow(self.table.currentRow())

    def update_totals(self, item):
        """
        Calcola automaticamente il Totale Riga (Qt * Prezzo).
        Scatta al cambio di valore in tabella.
        """
        # Agisce solo se modifico Qt (col 3) o Prezzo (col 4)
        if item.column() not in [3, 4]: return
        
        r = item.row()
        qty_item = self.table.item(r, 3)
        price_item = self.table.item(r, 4)
        total_item = self.table.item(r, 5)

        if qty_item is None or price_item is None or total_item is None:
            return

        try:
            q_text = qty_item.text().replace(',', '.')
            p_text = price_item.text().replace(',', '.')
            q = float(q_text or 0)
            p = float(p_text or 0)
        except ValueError:
            q, p = 0.0, 0.0
            
        # IMPORTANTE: Blocca i segnali prima di scrivere il totale.
        # Altrimenti scrivere il totale scatenerebbe un nuovo evento 'itemChanged'
        # creando un loop infinito.
        self.table.blockSignals(True)
        total_item.setText(f"{q*p:.2f}")
        self.table.blockSignals(False)

    # ============================================================================
    # --- SEZIONE 5: LOGICA DI SALVATAGGIO E CONVERSIONE ---
    # ============================================================================

    def convert_quote_to_order(self):
        """
        Logica di conversione:
        1. Conferma utente.
        2. Salva un NUOVO file ordine (con data oggi).
        3. Cancella il VECCHIO file preventivo.
        """
        old_path = self.current_file_path
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Conferma Conversione")
        msg.setText("Convertire preventivo in ordine?\nLa data ordine verrà aggiornata ad OGGI e il preventivo eliminato.")
        msg.setIcon(QMessageBox.Question)
        
        btn_si = msg.addButton("Sì", QMessageBox.YesRole)
        btn_no = msg.addButton("No", QMessageBox.NoRole)
        
        msg.exec()
        
        if msg.clickedButton() != btn_si:
            return
        
        # Aggiorna data a oggi per il nuovo ordine
        self.order_date_picker.setDate(QDate.currentDate())
        
        # Salva come ORDINE (is_quote=False)
        data, path = self.perform_save(is_quote=False)
        
        if data and path and old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
                QMessageBox.information(self, "Info", "Conversione riuscita.")
                self.prepare_new_order()
            except Exception as e:
                QMessageBox.warning(self, "Attenzione", f"Ordine creato, ma impossibile eliminare vecchio preventivo: {e}")

    def save_process(self, is_quote, print_after):
        """Wrapper per salvare e opzionalmente stampare."""
        data, path = self.perform_save(is_quote)
        
        if not data: return
        
        doc_type = "Preventivo" if is_quote else "Ordine"
        QMessageBox.information(self, "Salvataggio", f"{doc_type} salvato con successo:\n{os.path.basename(path)}")
        
        if print_after:
            generate_and_print_order(data, os.path.basename(path))
        
        self.prepare_new_order()

    def perform_save(self, is_quote=False):
        """Scrive fisicamente il file JSON su disco."""
        if not self.customer_name.text().strip():
            QMessageBox.warning(self, "Errore", "Inserire almeno il Nome Cliente.")
            return None, None

        # 1. Raccolta dati dal form
        info = {
            "data_ordine": self.order_date_picker.date().toString(Qt.ISODate),
            "operatore": self.operator_combo.currentText(),
            "data_cerimonia": self.date_picker.date().toString(Qt.ISODate),
            "data_consegna": self.delivery_date_picker.date().toString(Qt.ISODate),
            "tipo_cerimonia": self.ceremony_combo.currentText(),
            "colore_nastri": self.ribbon_color.text(),
            "tipo_confetti": self.confetti_combo.lineEdit().text(),
            "colore_confetti": self.confetti_color_combo.currentText(),
            "confezione": self.packaging.text(),
            "pagamento": self.payment_type.currentText(),
            "altro": self.extra.text(),
            "tipo_documento": "preventivo" if is_quote else "ordine",
            "acconto1_tipo": self.acc1_tipo.currentText(), 
            "acconto1_importo": self.acc1_val.text(),
            "acconto2_tipo": self.acc2_tipo.currentText(), 
            "acconto2_importo": self.acc2_val.text()
        }
        
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
            # Salva solo righe non vuote
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

        # 2. Determinazione percorso e nome file
        target_dir = QUOTES_DIR if is_quote else ORDERS_DIR
        os.makedirs(target_dir, exist_ok=True)
        
        # Se stiamo sovrascrivendo un file esistente nella cartella corretta, usa quel percorso
        if self.current_file_path and os.path.dirname(self.current_file_path) == os.path.abspath(target_dir):
            path = self.current_file_path
        else:
            # Creazione nuovo file: Sanificazione nome cliente (via caratteri speciali)
            safe_name = re.sub(r'[\\/*?:"<>|]', "", self.customer_name.text()).replace(" ", "_")
            prefix = 'Preventivo' if is_quote else 'Ordine'
            base_filename = f"{prefix}_{safe_name}_{info['data_cerimonia']}"
            
            path = os.path.join(target_dir, f"{base_filename}.json")
            
            # Gestione duplicati: aggiunge _1, _2 se il file esiste già
            counter = 1
            while os.path.exists(path):
                path = os.path.join(target_dir, f"{base_filename}_{counter}.json")
                counter += 1

        try:
            with open(path, 'w', encoding='utf-8') as f: 
                json.dump(full_data, f, indent=4, ensure_ascii=False)
            
            self.current_file_path = path
            return full_data, path
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Critico", f"Salvataggio fallito: {e}")
            return None, None