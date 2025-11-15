# Gestionale Ordini "Bomboniere Mery"

Questo progetto è un'applicazione desktop personalizzata, creata per ottimizzare e semplificare la gestione degli ordini per l'attività di famiglia "Bomboniere Mery".

## 🎯 Contesto del Progetto

L'obiettivo di questo progetto era **semplificare il flusso di lavoro** creando uno strumento unificato. L'applicazione centralizza la presa ordini, automatizza la generazione di stampe professionali e riduce il rischio di errori manuali, rendendo l'intero processo più rapido ed efficiente, inoltre consente anche il salvataggio degli ordini.

## ✨ Funzionalità Principali

* **Creazione Nuovi Ordini:** Un modulo dedicato permette di inserire tutti i dettagli di un nuovo ordine, inclusi i dati del cliente, il tipo di cerimonia, le preferenze (colore nastri, tipo confetti) e i dettagli di pagamento (acconto, saldo).
* **Gestione Articoli:** Una tabella dinamica permette di aggiungere o rimuovere righe per i diversi articoli dell'ordine, calcolando automaticamente i totali parziali.
* **Salvataggio e Archiviazione:** Gli ordini vengono salvati in modo sicuro come file `.json` individuali, rendendo i dati facili da backuppare e gestire.
* **Ricerca e Filtro:** Una pagina di ricerca permette di visualizzare tutti gli ordini salvati, ordinarli per data della cerimonia e filtrarli in tempo reale per nome cliente.
* **Modifica Ordini Esistenti:** Con un doppio clic su un ordine nella lista di ricerca, è possibile caricare tutti i dati nel modulo e apportare modifiche.
* **Stampa Automatizzata:**
    * Una funzione di stampa popola automaticamente un template `template.ods` (LibreOffice/OpenOffice) con tutti i dati dell'ordine.
    * Tenta di convertire il file in **PDF** utilizzando un'installazione di LibreOffice presente sul computer (se trovata).
    * Invia il file (PDF o ODS) direttamente alla stampante predefinita del sistema.
* **Interfaccia Personalizzata:** L'intera applicazione utilizza un foglio di stile QSS personalizzato (`style.qss`) per un look elegante e professionale, in linea con la palette di colori rosa tenue richiesta.

## 🛠️ Tecnologie Utilizzate

* **Python:** Linguaggio di programmazione principale.
* **PySide6:** Il framework Qt ufficiale per la creazione dell'interfaccia grafica (GUI).
* **ezodf:** Una libreria Python utilizzata per leggere e scrivere file ODS (OpenDocument Spreadsheet), usata per popolare il template di stampa.
* **QSS (Qt Style Sheets):** L'equivalente di CSS per Qt, utilizzato per personalizzare l'aspetto dell'applicazione.

## 🚀 Installazione e Avvio

Per eseguire questo progetto in un ambiente di sviluppo:

### 1. Prerequisiti

* **Python 3.10+**
* **LibreOffice:** (Fortemente consigliato). La funzione di stampa e conversione PDF (`print_order.py`) è progettata per funzionare con LibreOffice. Assicurati che sia installato nel percorso predefinito.
* **File Template:** Assicurati che il file `template.ods` sia presente nella directory principale (o dove specificato in `paths.py`).

### 2. Setup dell'Ambiente

1.  Clona o scarica questo repository.
    ```bash
    git clone https://github.com/GiovanniPiombo/gestione-ordini-bomboniere-mery.git
    ```
2.  Crea un ambiente virtuale (consigliato):
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Su Windows
    source venv/bin/activate # Su macOS/Linux
    ```
3.  Installa le dipendenze Python:
    ```bash
    pip install PySide6 ezodf
    ```

### 3. Avvio

Per avviare l'applicazione, esegui il file `main.py`:

```bash
python main.py
```
## 📂 Struttura del Progetto

```bash
.
├── main.py             # File principale, avvia l'applicazione
├── main_window.py      # Gestisce la finestra principale e la navigazione tra pagine (Stack)
├── paths.py            # Definisce tutti i percorsi (dati, risorse, output)
├── style.qss           # Foglio di stile QSS per l'interfaccia
├── template.ods        # Il template per la stampa
├── icon.png            # Icona dell'applicazione
│
├── pages/
│   ├── menu_page.py        # Pagina del menu principale
│   ├── new_order_page.py   # Pagina per la creazione/modifica degli ordini
│   └── search_page.py      # Pagina per la ricerca e il caricamento di ordini esistenti
│
└── core/
    └── print_order.py      # Logica per la stampa e la generazione dei file ODS/PDF
```
