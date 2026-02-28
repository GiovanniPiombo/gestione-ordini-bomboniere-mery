import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit,
    QHBoxLayout, QFileDialog, QMessageBox
)

# Importiamo get_app_dir per sapere dove si trova il config.json
from paths import get_app_dir

class SettingsPage(QWidget):
    def __init__(self, on_back):
        super().__init__()
        self.on_back = on_back
        
        # Definiamo il percorso del file di configurazione
        self.config_path = os.path.join(get_app_dir(), "config.json")
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("<h2>Impostazioni</h2>")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        info_label = QLabel("Seleziona la cartella principale dove salvare i dati (Ordini, Preventivi, ecc.):\nSe lasci vuoto, verrà usata la cartella predefinita (AppData).")
        layout.addWidget(info_label)
        
        # --- SELETTORE PERCORSO ---
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Percorso predefinito (AppData)...")
        self.path_input.setReadOnly(True) # Evita modifiche manuali sbagliate
        
        btn_browse = QPushButton("📂 Sfoglia...")
        btn_browse.clicked.connect(self.browse_folder)
        
        btn_clear = QPushButton("❌ Ripristina Default")
        btn_clear.clicked.connect(self.clear_folder)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(btn_browse)
        path_layout.addWidget(btn_clear)
        layout.addLayout(path_layout)
        
        # --- BOTTONI AZIONE ---
        btn_layout = QHBoxLayout()
        btn_back = QPushButton("⬅️ Torna al Menu")
        btn_back.clicked.connect(self.on_back)
        
        btn_save = QPushButton("💾 Salva Impostazioni")
        btn_save.clicked.connect(self.save_settings)
        btn_save.setStyleSheet("background-color: #d1e7dd; border: 1px solid #badbcc; color: #0f5132; font-weight: bold;")
        
        btn_layout.addWidget(btn_back)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        
        layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def showEvent(self, event):
        """Carica il config attuale ogni volta che la pagina viene mostrata."""
        self.load_current_config()
        super().showEvent(event)

    def load_current_config(self):
        """Legge il file JSON e aggiorna la barra di testo."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.path_input.setText(config.get("custom_data_path", ""))
            except Exception as e:
                print(f"Errore lettura config: {e}")

    def browse_folder(self):
        """Apre la finestra di dialogo per scegliere una cartella."""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella Dati")
        if folder:
            # Sostituisce i backslash con slash normali per evitare problemi nel JSON
            folder = folder.replace("\\", "/")
            self.path_input.setText(folder)

    def clear_folder(self):
        """Svuota la casella di testo (ritorna ad AppData)."""
        self.path_input.clear()

    def save_settings(self):
        """Salva il nuovo percorso nel file config.json."""
        new_path = self.path_input.text().strip()
        
        config = {"custom_data_path": new_path}
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            QMessageBox.information(
                self, 
                "Impostazioni Salvate", 
                "Le impostazioni sono state salvate con successo.\n\n"
                "⚠️ ATTENZIONE: Chiudi e riapri il programma per applicare le modifiche."
            )
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare le impostazioni:\n{e}")