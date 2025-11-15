import json
import re 
import os 
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFormLayout, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QAbstractSpinBox, QHBoxLayout, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt

# Importa la funzione di stampa dalla nuova posizione
from core.print_order import generate_and_print_order
from paths import ORDERS_DIR


class NewOrderPage(QWidget):
    """Pagina di nuovo ordine con contenuto scorrevole, tabella modificabile, totali automatici e rimozione righe."""
    def __init__(self, on_back):
        super().__init__()
        
        self.current_file_path = None

        main_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        page_content_layout = QVBoxLayout(content_widget) 

        form_layout_info = QFormLayout()
        
        self.order_date_picker = QDateEdit()
        self.order_date_picker.setDate(QDate.currentDate()) 
        self.order_date_picker.setReadOnly(True) # Impedisce la modifica manuale
        self.order_date_picker.setButtonSymbols(QAbstractSpinBox.NoButtons) # Nasconde i pulsanti su/giù
        title = QLabel("<h2>Informazioni Ordine</h2>")
        title.setObjectName("titleLabel") # ID usato dallo stylesheet (QSS)
        form_layout_info.addRow(title) 
        form_layout_info.addRow("Data Ordine:", self.order_date_picker) 
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["Ketty","Valentina"])
        form_layout_info.addRow("Ordine Di:", self.operator_combo) 
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        form_layout_info.addRow("Data Cerimonia:", self.date_picker)
        
        # --- NUOVO CAMPO: DATA CONSEGNA ---
        self.delivery_date_picker = QDateEdit()
        self.delivery_date_picker.setCalendarPopup(True)
        self.delivery_date_picker.setDate(QDate.currentDate())
        form_layout_info.addRow("Data Consegna:", self.delivery_date_picker)
        # ------------------------------------
        
        self.ceremony_combo = QComboBox()
        self.ceremony_combo.addItems(["Nascita","Battesimo","Comunione","Cresima","Laurea","Matrimonio","25 Anni","50 Anni","60 Anni","Anniversario","Compleanno","Pensione"])
        form_layout_info.addRow("Tipo Cerimonia:", self.ceremony_combo) 
        self.ribbon_color = QLineEdit()
        form_layout_info.addRow("Colore Nastri:", self.ribbon_color) 
        self.confetti_combo = QComboBox()
        self.confetti_combo.addItems(["Mandorla", "Cioccolato", "Ciocopassion", "Snob", "Stella"])
        form_layout_info.addRow("Tipo Confetti:", self.confetti_combo) 
        self.confetti_color_combo = QComboBox()
        self.confetti_color_combo.addItems(["Bianco", "Rosa", "Azzurro", "Rosso", "Oro", "Argento"])
        form_layout_info.addRow("Colore Confetti:", self.confetti_color_combo)
        self.packaging = QLineEdit()
        form_layout_info.addRow("Confezione:", self.packaging)
        
        # --- CAMPI PAGAMENTO E ACCONTO ---
        self.payment_type = QComboBox()
        self.payment_type.addItems(["Acconto","Consegna","Giorno Prima Della Cerimonia", "Altro"])
        form_layout_info.addRow("Pagamento:", self.payment_type)

        # Campi Acconto 1
        self.label_acconto1_tipo = QLabel("Tipo Acconto 1:")
        self.acconto1_tipo_combo = QComboBox()
        self.acconto1_tipo_combo.addItems(["", "Contanti", "Bancomat", "Bonifico"])
        self.label_acconto1_importo = QLabel("Importo Acconto 1:")
        self.acconto1_importo_input = QLineEdit()
        
        form_layout_info.addRow(self.label_acconto1_tipo, self.acconto1_tipo_combo)
        form_layout_info.addRow(self.label_acconto1_importo, self.acconto1_importo_input)

        # Campi Acconto 2
        self.label_acconto2_tipo = QLabel("Tipo Acconto 2:")
        self.acconto2_tipo_combo = QComboBox()
        self.acconto2_tipo_combo.addItems(["", "Contanti", "Bancomat", "Bonifico"])
        self.label_acconto2_importo = QLabel("Importo Acconto 2:")
        self.acconto2_importo_input = QLineEdit()
        
        form_layout_info.addRow(self.label_acconto2_tipo, self.acconto2_tipo_combo)
        form_layout_info.addRow(self.label_acconto2_importo, self.acconto2_importo_input)

        # Connetti il segnale per mostrare/nascondere i campi acconto
        self.payment_type.currentTextChanged.connect(self.toggle_acconto_fields)

        self.extra = QLineEdit()
        form_layout_info.addRow("Altro:", self.extra)
        page_content_layout.addLayout(form_layout_info)

        # --- Tabella Dettagli Ordine ---
        table_label = QLabel("<b>Dettagli Ordine</b>")
        page_content_layout.addWidget(table_label)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Ditta", "Codice", "Descrizione", "Prezzo Unitario", "Quantità", "Prezzo Totale"
        ])
        self.table.itemChanged.connect(self.update_totals)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 200) # Ditta
        self.table.setColumnWidth(1, 100) # Codice
        self.table.setColumnWidth(2, 500) # Descrizione
        self.table.setColumnWidth(3, 150) # Prezzo Unitario
        self.table.setColumnWidth(4, 80)  # Quantità
        self.table.setColumnWidth(5, 100) # Prezzo Totale
        
        # Permette la modifica al clic o con la tastiera
        self.table.setEditTriggers(
            QAbstractItemView.SelectedClicked | QAbstractItemView.AnyKeyPressed
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(300)
        page_content_layout.addWidget(self.table)
        
        table_button_layout = QHBoxLayout()
        btn_add_row = QPushButton("➕ Aggiungi Riga")
        btn_add_row.clicked.connect(self.add_row)
        btn_remove_row = QPushButton("🗑️ Rimuovi Riga")
        btn_remove_row.clicked.connect(self.remove_selected_row)
        table_button_layout.addWidget(btn_add_row)
        table_button_layout.addWidget(btn_remove_row)
        table_button_layout.addStretch() 
        page_content_layout.addLayout(table_button_layout)
        
        # --- Form Dati Cliente ---
        form_layout_customer = QFormLayout()
        form_layout_customer.addRow(QLabel("<h2>Dati Cliente</h2>"))
        self.customer_name = QLineEdit() 
        form_layout_customer.addRow("Nome Cliente:", self.customer_name)
        self.customer_number = QLineEdit() 
        form_layout_customer.addRow("Telefono Cliente:", self.customer_number)
        page_content_layout.addLayout(form_layout_customer)

        # --- Bottoni di fondo pagina ---
        bottom_button_layout = QHBoxLayout()
        btn_back = QPushButton("⬅️ Torna al Menu")
        btn_back.clicked.connect(on_back)
        btn_save = QPushButton("💾 Salva Ordine")
        btn_save.clicked.connect(self.save_order_and_close)
        btn_save_print = QPushButton("📄 Salva e Stampa")
        btn_save_print.clicked.connect(self.save_order_and_print)
        bottom_button_layout.addWidget(btn_back)
        bottom_button_layout.addWidget(btn_save)
        bottom_button_layout.addWidget(btn_save_print)
        bottom_button_layout.addStretch() 
        page_content_layout.addLayout(bottom_button_layout)
        
        page_content_layout.addStretch() 
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
        
        self.prepare_new_order()

    def toggle_acconto_fields(self, text):
        """Mostra o nasconde i campi acconto in base alla selezione."""
        is_acconto = (text == "Acconto")
        
        self.label_acconto1_tipo.setVisible(is_acconto)
        self.acconto1_tipo_combo.setVisible(is_acconto)
        self.label_acconto1_importo.setVisible(is_acconto)
        self.acconto1_importo_input.setVisible(is_acconto)
        
        self.label_acconto2_tipo.setVisible(is_acconto)
        self.acconto2_tipo_combo.setVisible(is_acconto)
        self.label_acconto2_importo.setVisible(is_acconto)
        self.acconto2_importo_input.setVisible(is_acconto)

    def prepare_new_order(self):
        """Resetta tutti i campi per un nuovo ordine."""
        self.current_file_path = None
        self.order_date_picker.setDate(QDate.currentDate())
        self.operator_combo.setCurrentIndex(0)
        self.date_picker.setDate(QDate.currentDate())
        self.delivery_date_picker.setDate(QDate.currentDate())
        self.ceremony_combo.setCurrentIndex(0)
        self.ribbon_color.setText("")
        self.confetti_combo.setCurrentIndex(0)
        self.confetti_color_combo.setCurrentIndex(0)
        self.packaging.setText("")
        self.payment_type.setCurrentIndex(0)
        
        self.acconto1_tipo_combo.setCurrentIndex(0)
        self.acconto1_importo_input.setText("")
        self.acconto2_tipo_combo.setCurrentIndex(0)
        self.acconto2_importo_input.setText("")
        
        self.extra.setText("")
        self.customer_name.setText("")
        self.customer_number.setText("")
        self.table.clearContents()
        self.table.setRowCount(0)
        
        for _ in range(6): # Aggiunge 6 righe vuote di default
            self.add_row()
            
        self.toggle_acconto_fields(self.payment_type.currentText())

    def load_order(self, file_path):
        """Carica i dati di un ordine JSON esistente nel form."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.table.clearContents()
            self.table.setRowCount(0)
            self.current_file_path = file_path
            
            info = data.get("info_ordine", {})
            self.order_date_picker.setDate(QDate.fromString(info.get("data_ordine"), Qt.ISODate))
            self.operator_combo.setCurrentText(info.get("operatore", ""))
            self.date_picker.setDate(QDate.fromString(info.get("data_cerimonia"), Qt.ISODate))
            
            # Gestisce la data consegna (nuovo campo)
            delivery_date_str = info.get("data_consegna")
            if delivery_date_str:
                self.delivery_date_picker.setDate(QDate.fromString(delivery_date_str, Qt.ISODate))
            else:
                self.delivery_date_picker.setDate(QDate.currentDate()) # Fallback
            
            self.ceremony_combo.setCurrentText(info.get("tipo_cerimonia", ""))
            self.ribbon_color.setText(info.get("colore_nastri", ""))
            self.confetti_combo.setCurrentText(info.get("tipo_confetti", ""))
            self.confetti_color_combo.setCurrentText(info.get("colore_confetti", ""))
            self.packaging.setText(info.get("confezione", ""))
            self.payment_type.setCurrentText(info.get("pagamento", ""))
            
            self.acconto1_tipo_combo.setCurrentText(info.get("acconto1_tipo", ""))
            self.acconto1_importo_input.setText(info.get("acconto1_importo", ""))
            self.acconto2_tipo_combo.setCurrentText(info.get("acconto2_tipo", ""))
            self.acconto2_importo_input.setText(info.get("acconto2_importo", ""))
            
            self.extra.setText(info.get("altro", ""))
            
            customer = data.get("dati_cliente", {})
            self.customer_name.setText(customer.get("nome_cliente", ""))
            self.customer_number.setText(customer.get("telefono_cliente", ""))
            
            details = data.get("dettagli_ordine", [])
            for item_data in details:
                # Questa funzione non ha il limite di 13 righe, per caricare vecchi file
                self.add_row_with_data(item_data)
                
            min_rows = 6
            while self.table.rowCount() < min_rows:
                self.add_row() # Assicura un minimo di 6 righe
                
            self.toggle_acconto_fields(self.payment_type.currentText())
            
        except Exception as e:
            QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare il file:\n{e}")
            self.prepare_new_order()

    def add_row(self):
        """Aggiunge una riga alla tabella, con un limite massimo di 13."""
        
        # Controllo limite righe (per compatibilità con stampa ODS)
        if self.table.rowCount() >= 13:
            QMessageBox.warning(
                self, 
                "Limite Raggiunto", 
                "Hai raggiunto il limite massimo di 13 articoli per ordine."
            )
            return # Interrompe l'esecuzione e non aggiunge la riga
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        company_combo = QComboBox()
        company_combo.addItems(["","BAGUTTA","BIPAPER","CLARALUNA","CUOREMATTO","DIMAR","DOLCICOSE","HERVIT","EMMEBI","ETM","FAMA","FANTIN","FOGAL","FRANCESCO","LAGUNA","MAS","NEGO","PABEN","QUADRIFOGLIO","TABOR"])
        self.table.setCellWidget(row, 0, company_combo)
        
        for col in range(1, 6):
            item = QTableWidgetItem("")
            if col == 5: # Colonna Prezzo Totale
                item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Rende la cella non modificabile
                item.setText("0.00") 
            else:
                item.setFlags(item.flags() | Qt.ItemIsEditable) # Rende la cella modificabile
            self.table.setItem(row, col, item)
        self.table.resizeRowToContents(row)
        
    def add_row_with_data(self, data):
        """Aggiunge una riga con dati pre-caricati (usato per il caricamento file)."""
        # Questa funzione NON ha il limite di 13 per permettere il caricamento di vecchi file
        row = self.table.rowCount()
        self.table.insertRow(row)
        company_combo = QComboBox()
        company_combo.addItems(["","BAGUTTA","BIPAPER","CLARALUNA","CUOREMATTO","DIMAR","DOLCICOSE","EGAN","EMMEBI","ETM","FAMA","FANTIN","FOGAL","FRANCESCO","LAGUNA","MAS","NEGO","PABEN","QUADRIFOGLIO","TABOR"])
        company_combo.setCurrentText(data.get("ditta", ""))
        self.table.setCellWidget(row, 0, company_combo)
        self.table.setItem(row, 1, QTableWidgetItem(data.get("codice", "")))
        self.table.setItem(row, 2, QTableWidgetItem(data.get("descrizione", "")))
        self.table.setItem(row, 3, QTableWidgetItem(data.get("prezzo_unitario", "0")))
        self.table.setItem(row, 4, QTableWidgetItem(data.get("quantita", "0")))
        total_item = QTableWidgetItem(data.get("prezzo_totale", "0.00"))
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 5, total_item)
        self.table.resizeRowToContents(row)

    def remove_selected_row(self):
        """Rimuove la riga attualmente selezionata dalla tabella."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def update_totals(self, item):
        """Calcola automaticamente il prezzo totale quando quantità o prezzo unitario cambiano."""
        col = item.column()
        # Esegui solo se cambiano Prezzo Unitario (3) o Quantità (4)
        if col not in [3, 4]:  
            return
            
        row = item.row()
        unit_price_item = self.table.item(row, 3)
        quantity_item = self.table.item(row, 4)
        
        try:
            unit_price_str = unit_price_item.text().replace(',', '.') if unit_price_item else "0"
            unit_price = float(unit_price_str if unit_price_str else "0")
        except (ValueError, AttributeError):
            unit_price = 0.0
            
        try:
            quantity_str = quantity_item.text().replace(',', '.') if quantity_item else "0"
            quantity = float(quantity_str if quantity_str else "0")
        except (ValueError, AttributeError):
            quantity = 0.0
            
        total = unit_price * quantity
        
        # Blocca i segnali per evitare ricorsioni mentre modifichiamo la cella
        self.table.blockSignals(True)
        total_item = self.table.item(row, 5)
        if not total_item:
            total_item = QTableWidgetItem()
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable) 
            self.table.setItem(row, 5, total_item)
            
        total_item.setText(f"{total:.2f}")
        # Riattiva i segnali
        self.table.blockSignals(False)
        
    def save_order_and_close(self):
        """Salva l'ordine e chiude la pagina (tornando al menu)."""
        final_data, target_file_path = self.save_order()
        
        if final_data: 
            QMessageBox.information(
                self, 
                "Salvataggio Riuscito", 
                f"Ordine salvato con successo in:\n{target_file_path}"
            )
            # Resetta la pagina dopo il salvataggio
            self.prepare_new_order()

    def save_order_and_print(self):
        """Salva l'ordine, avvia la stampa e chiude la pagina."""
        final_data, target_file_path = self.save_order()
        
        if not final_data:
            return # Salvataggio fallito o annullato

        QMessageBox.information(
            self, 
            "Salvataggio Riuscito", 
            f"Ordine salvato con successo in:\n{target_file_path}"
        )
        
        try:
            base_filename = os.path.basename(target_file_path)
            # Chiama la funzione di stampa
            generate_and_print_order(final_data, base_filename)
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Errore di Stampa", 
                f"L'ordine è stato salvato, ma la stampa è fallita:\n{e}"
            )
        
        # Resetta la pagina dopo salvataggio e stampa
        self.prepare_new_order()
    
    
    def save_order(self):
        """Funzione interna per raccogliere i dati e salvarli in JSON."""
        pagamento_selezionato = self.payment_type.currentText()
        
        order_info = {
            "data_ordine": self.order_date_picker.date().toString(Qt.ISODate),
            "operatore": self.operator_combo.currentText(),
            "data_cerimonia": self.date_picker.date().toString(Qt.ISODate),
            "data_consegna": self.delivery_date_picker.date().toString(Qt.ISODate), # Salva data consegna
            "tipo_cerimonia": self.ceremony_combo.currentText(),
            "colore_nastri": self.ribbon_color.text(),
            "tipo_confetti": self.confetti_combo.currentText(),
            "colore_confetti": self.confetti_color_combo.currentText(),
            "confezione": self.packaging.text(),
            "pagamento": pagamento_selezionato,
            "altro": self.extra.text()
        }
        
        # Salva i dati acconto solo se il tipo di pagamento è "Acconto"
        if pagamento_selezionato == "Acconto":
            order_info["acconto1_tipo"] = self.acconto1_tipo_combo.currentText()
            order_info["acconto1_importo"] = self.acconto1_importo_input.text()
            order_info["acconto2_tipo"] = self.acconto2_tipo_combo.currentText()
            order_info["acconto2_importo"] = self.acconto2_importo_input.text()
        else:
            order_info["acconto1_tipo"] = ""
            order_info["acconto1_importo"] = ""
            order_info["acconto2_tipo"] = ""
            order_info["acconto2_importo"] = ""

        customer_info = {
            "nome_cliente": self.customer_name.text(),
            "telefono_cliente": self.customer_number.text()
        }
        
        table_data = []
        for row in range(self.table.rowCount()):
            company_widget = self.table.cellWidget(row, 0)
            company = company_widget.currentText() if company_widget else ""
            code = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            description = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            unit_price = self.table.item(row, 3).text() if self.table.item(row, 3) else "0"
            quantity = self.table.item(row, 4).text() if self.table.item(row, 4) else "0"
            total_price = self.table.item(row, 5).text() if self.table.item(row, 5) else "0.00"

            # Salva la riga solo se contiene dati utili
            if company or code or description:
                row_data = {
                    "ditta": company, "codice": code, "descrizione": description,
                    "prezzo_unitario": unit_price, "quantita": quantity, "prezzo_totale": total_price
                }
                table_data.append(row_data)

        final_data = {
            "info_ordine": order_info,
            "dati_cliente": customer_info,
            "dettagli_ordine": table_data
        }
        
        if not customer_info.get("nome_cliente", "").strip():
            QMessageBox.warning(
                self, 
                "Dati Mancanti", 
                "Inserire almeno il 'Nome Cliente' prima di salvare."
            )
            return None, None 
        
        # ORDERS_DIR è la costante importata
        if not os.path.exists(ORDERS_DIR):
            os.makedirs(ORDERS_DIR)

        cust_name = customer_info.get("nome_cliente", "Nuovo_Ordine").strip()
        cer_date = order_info.get("data_cerimonia", "")
        
        safe_cust_name = re.sub(r'[\\/*?:"<>|]', "", cust_name)
        safe_cust_name = re.sub(r'\s+', '_', safe_cust_name).strip('_')
        if not safe_cust_name: # Fallback se il nome era vuoto o solo caratteri speciali
            safe_cust_name = "Ordine"

        base_filename = f"Ordine_{safe_cust_name}_{cer_date}"
        file_ext = ".json"
        
        target_file_path = ""
        old_file_to_remove = None

        # Logica per rinominare/sovrascrivere se il file era già esistente
        if self.current_file_path:
            # Usa ORDERS_DIR
            new_potential_path = os.path.join(ORDERS_DIR, base_filename + file_ext)
            # Se il nome non è cambiato, sovrascrivi lo stesso file
            if new_potential_path == self.current_file_path:
                target_file_path = self.current_file_path
            else:
                # Se il nome è cambiato, cerca un nuovo nome univoco
                counter = 1
                target_filename = base_filename + file_ext
                # Usa ORDERS_DIR
                target_file_path = os.path.join(ORDERS_DIR, target_filename)
                
                while os.path.exists(target_file_path):
                    target_filename = f"{base_filename}_{counter}{file_ext}"
                    # Usa ORDERS_DIR
                    target_file_path = os.path.join(ORDERS_DIR, target_filename)
                    counter += 1
                
                # Marca il vecchio file per la rimozione
                old_file_to_remove = self.current_file_path
        
        else:
            # Logica per un file nuovo (gestisce conflitti di nomi)
            counter = 1
            target_filename = base_filename + file_ext
            # Usa ORDERS_DIR
            target_file_path = os.path.join(ORDERS_DIR, target_filename)
            
            while os.path.exists(target_file_path):
                target_filename = f"{base_filename}_{counter}{file_ext}"
                # Usa ORDERS_DIR
                target_file_path = os.path.join(ORDERS_DIR, target_filename)
                counter += 1

        try:
            with open(target_file_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            
            # Se il file è stato rinominato, rimuovi il vecchio file
            if old_file_to_remove and old_file_to_remove != target_file_path:
                if os.path.exists(old_file_to_remove):
                    try:
                        os.remove(old_file_to_remove)
                    except Exception as e:
                        print(f"Attenzione: salvataggio riuscito, ma impossibile rimuovere il vecchio file {old_file_to_remove}: {e}")
            
            self.current_file_path = target_file_path
            
            return final_data, target_file_path
        
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Errore di Salvataggio", 
                f"Impossibile salvare il file:\n{e}"
            )
            return None, None