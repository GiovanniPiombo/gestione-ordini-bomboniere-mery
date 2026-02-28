# Gestionale Ordini "Bomboniere Mery"

Questo progetto è un'applicazione desktop personalizzata, creata per ottimizzare e semplificare la gestione degli ordini e dei preventivi per l'attività di famiglia "Bomboniere Mery".

## Contesto del Progetto

L'obiettivo di questo progetto era **semplificare il flusso di lavoro** creando uno strumento unificato. L'applicazione centralizza la presa ordini e preventivi, automatizza la generazione di stampe professionali e riduce il rischio di errori manuali, rendendo l'intero processo più rapido ed efficiente, inoltre consente anche il salvataggio sicuro dei documenti.

## Funzionalità Principali

* **Creazione Nuovi Ordini e Preventivi:** Un modulo dedicato permette di inserire tutti i dettagli di un nuovo documento, inclusi i dati del cliente, il tipo di cerimonia, le preferenze (colore nastri, tipo confetti) e i dettagli di pagamento (acconto, saldo).
* **Conversione Preventivi:** È possibile trasformare un preventivo esistente in un ordine effettivo con un solo clic, aggiornando automaticamente la data e i metadati.
* **Gestione Articoli:** Una tabella dinamica permette di aggiungere o rimuovere righe per i diversi articoli dell'ordine, calcolando automaticamente i totali parziali. (Nei preventivi il totale finale viene automaticamente nascosto in fase di stampa).
* **Condivisione in Rete e Impostazioni:** Tramite una pagina "Impostazioni" dedicata, è possibile mappare un percorso di rete o una cartella cloud personalizzata (i dati vengono salvati in un file `config.json` locale). Questo permette a più postazioni di lavorare simultaneamente sullo stesso archivio clienti.
* **Salvataggio e Archiviazione:** Gli ordini e i preventivi vengono salvati in modo sicuro come file `.json` individuali all'interno di cartelle separate, rendendo i dati facili da backuppare e gestire.
* **Ricerca, Filtro ed Eliminazione:** Una pagina di ricerca permette di visualizzare tutti i documenti salvati, ordinarli per data della cerimonia, filtrarli in tempo reale per nome cliente ed eliminare definitivamente quelli non più necessari.
* **Modifica Documenti Esistenti:** Con un doppio clic su un elemento nella lista di ricerca, è possibile caricare tutti i dati nel modulo e apportare modifiche.
* **Stampa Automatizzata:**
    * Una funzione di stampa popola automaticamente un template `template.ods` (LibreOffice/OpenOffice) con tutti i dati dell'ordine.
    * Tenta di convertire il file in **PDF** utilizzando un'installazione di LibreOffice presente sul computer (se trovata).
    * Invia il file (PDF o ODS) direttamente alla stampante predefinita del sistema o lo apre per la visualizzazione.
* **Interfaccia Personalizzata:** L'intera applicazione utilizza un foglio di stile QSS personalizzato (`style.qss`) per un look elegante e professionale, in linea con la palette di colori rosa tenue richiesta.

## Tecnologie Utilizzate

* **Python:** Linguaggio di programmazione principale.
* **PySide6:** Il framework Qt ufficiale per la creazione dell'interfaccia grafica (GUI).
* **ezodf:** Una libreria Python utilizzata per leggere e scrivere file ODS (OpenDocument Spreadsheet), usata per popolare il template di stampa.
* **QSS (Qt Style Sheets):** L'equivalente di CSS per Qt, utilizzato per personalizzare l'aspetto dell'applicazione.

## Installazione e Avvio

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
    venv\Scripts\activate
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

(Al primo avvio, il programma genererà automaticamente un file config.json per gestire i percorsi di salvataggio).

## Struttura del Progetto

```bash
├── main.py             # File principale, avvia l'applicazione
├── main_window.py      # Gestisce la finestra principale e la navigazione tra pagine (Stack)
├── paths.py            # Definisce tutti i percorsi (dati, risorse, output) e legge config.json
├── style.qss           # Foglio di stile QSS per l'interfaccia
├── template.ods        # Il template per la stampa
├── icon.png            # Icona dell'applicazione
│
├── pages/
│   ├── menu_page.py        # Pagina del menu principale
│   ├── new_order_page.py   # Pagina per la creazione/modifica degli ordini e preventivi
│   ├── search_page.py      # Pagina per la ricerca, conversione ed eliminazione dei documenti
│   └── settings_page.py    # Pagina per configurare il percorso di salvataggio dei dati
│
└── core/
    └── print_order.py      # Logica per la stampa e la generazione dei file ODS/PDF
```
