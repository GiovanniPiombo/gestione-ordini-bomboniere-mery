from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

class MenuPage(QWidget):
    """
    Pagina del menu principale.
    Fornisce l'accesso alla ricerca ordini, alla creazione di nuovi documenti e alle impostazioni.
    """
    def __init__(self, on_search, on_new_order, on_settings):
        super().__init__()
        layout = QVBoxLayout()

        title = QLabel("<h2>Menu Principale</h2>")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        btn_search = QPushButton("🔍 Cerca File")
        btn_new_order = QPushButton("📝 Nuovo Ordine/Preventivo")
        btn_settings = QPushButton("⚙️ Impostazioni")

        btn_search.clicked.connect(on_search)
        btn_new_order.clicked.connect(on_new_order)
        btn_settings.clicked.connect(on_settings)

        layout.addWidget(btn_search)
        layout.addWidget(btn_new_order)
        layout.addWidget(btn_settings)
        layout.addStretch()

        self.setLayout(layout)