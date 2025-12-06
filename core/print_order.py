import ezodf
import os
import re
import platform
import subprocess
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import QMessageBox

# Importa i percorsi dinamici (gestione exe/sviluppo)
from paths import TEMPLATE_PATH, OUTPUT_DIR

# ======================================================================
# --- CONFIGURAZIONE MAPPING CELLE ---
# Qui definiamo dove vanno a finire i dati nel file template.ods
# Se sposti una cella nel file Excel, aggiorna solo questa mappa.
# ======================================================================

CELL_MAP = {
    # Dati Cliente
    "nome_cliente": "C11",
    "telefono_cliente": "C17",
    
    # Info Ordine
    "data_ordine": "C6",
    "data_cerimonia": "C13",
    "data_consegna": "E41", 
    "operatore": "G6",
    "tipo_cerimonia": "C9",
    
    # Info Cerimonia / Prodotto
    "colore_nastri": "C35",
    "tipo_confetti": "C37",
    "colore_confetti": "F37",
    "confezione": "C39",
    "pagamento": "C41",
    "altro": "C15",

    # Dati Acconto (Celle specifiche)
    "acconto1_tipo": "B43",
    "acconto1_importo": "C43",
    "acconto2_tipo": "B44",
    "acconto2_importo": "C44",

    # Configurazione Tabella Articoli (0-based index)
    # Riga 19 excel = Indice 18 (o 19 a seconda della lib). Qui è settato 19.
    "tabella_start_row_index": 19, 
    "tabella_total_row_index": 32  # Dove si trova la riga del TOTALE
}

# ======================================================================
# --- FUNZIONI DI UTILITÀ (HELPER) ---
# ======================================================================

def _format_date(iso_date_str):
    """Converte una data ISO (YYYY-MM-DD) in formato italiano (DD/MM/YYYY)."""
    if not iso_date_str:
        return "N.D."
    try:
        date_obj = datetime.fromisoformat(iso_date_str)
        return date_obj.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_date_str

def _clean_value_for_ods(value, is_numeric=False):
    """
    Pulisce i dati prima di scriverli nell'ODS.
    Gestisce conversioni stringa -> float per i prezzi e rimuove spazi extra.
    """
    if value is None:
        return 0.0 if is_numeric else ""
    
    text_val = str(value).strip()
    
    if not text_val:
        return 0.0 if is_numeric else ""
    
    if is_numeric:
        try:
            # Accetta sia '10.50' che '10,50'
            return float(text_val.replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0
            
    return text_val

def _trigger_print_or_open(file_path):
    """
    Gestisce l'azione finale:
    1. Prova a STAMPARE direttamente (senza aprire finestre).
    2. Se fallisce, APRE il file con il visualizzatore predefinito (es. Acrobat, Anteprima).
    3. Se fallisce anche quello, apre nel Browser.
    """
    full_path = os.path.realpath(file_path)
    system = platform.system()
    
    # --- TENTATIVO 1: Stampa Diretta ---
    try:
        if system == "Windows":
            # 'print' è un verbo speciale di ShellExecute per mandare alla stampante default
            os.startfile(full_path, "print")
            
        elif system == "Darwin": # macOS
            subprocess.run(["lpr", full_path], check=True)
            
        else: # Linux
            subprocess.run(["lpr", full_path], check=True)
            
    except Exception as e:
        # --- TENTATIVO 2: Fallback (Apertura File) ---
        print(f"Stampa diretta non riuscita ({e}). Apro il file in anteprima.")
        try:
            if system == "Windows":
                os.startfile(full_path)
            elif system == "Darwin":
                subprocess.run(["open", full_path], check=True)
            else:
                subprocess.run(["xdg-open", full_path], check=True)
        except Exception as final_e:
             QMessageBox.critical(None, "Errore Apertura", f"Impossibile aprire il file: {final_e}")

# ======================================================================
# --- MOTORE PDF (LibreOffice) ---
# ======================================================================

def _get_libreoffice_command():
    """
    Cerca l'eseguibile di LibreOffice nel sistema operativo.
    Necessario per la conversione "headless" (senza interfaccia) da ODS a PDF.
    """
    system = platform.system()
    if system == "Windows":
        # Percorsi standard di installazione Windows
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return "soffice" # Tenta di usare il comando globale se nel PATH
    elif system == "Darwin": # macOS
        path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(path):
            return path
        return "libreoffice"
    else: # Linux
        return "libreoffice"

def _convert_to_pdf(ods_path, output_dir):
    """
    Chiama LibreOffice da riga di comando per convertire ODS -> PDF.
    Ritorna il percorso del PDF creato o None se fallisce.
    """
    soffice_cmd = _get_libreoffice_command()
    
    pdf_name = os.path.splitext(os.path.basename(ods_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)

    # Nota: LibreOffice richiede percorsi assoluti per funzionare bene in headless
    abs_output_dir = os.path.abspath(output_dir)
    abs_ods_path = os.path.abspath(ods_path)

    command = [
        soffice_cmd,
        "--headless",       # Modalità silenziosa (niente GUI)
        "--convert-to", "pdf",
        "--outdir", abs_output_dir,
        abs_ods_path
    ]
    
    try:
        # Timeout di 30 secondi per evitare che l'app si blocchi se LibreOffice s'incastra
        subprocess.run(command, capture_output=True, check=True, timeout=30)
        
        if os.path.exists(pdf_path):
            return pdf_path
        return None
            
    except Exception as e:
        print(f"Errore conversione PDF: {e}")
        return None

# ======================================================================
# --- FUNZIONE PRINCIPALE DI GENERAZIONE ---
# ======================================================================

def generate_and_print_order(order_data, original_json_filename):
    """
    Flusso principale:
    1. Apre template.ods.
    2. Scrive i dati (Cliente, Info, Tabella).
    3. Gestisce logica Preventivo (nasconde totali).
    4. Salva .ODS temporaneo.
    5. Converte in PDF.
    6. Stampa/Apre il PDF.
    """
    
    # 1. Controlli Preliminari
    if not os.path.exists(TEMPLATE_PATH):
        QMessageBox.critical(None, "Errore Template", f"File non trovato: '{TEMPLATE_PATH}'")
        return False

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # 2. Caricamento Template
        doc = ezodf.opendoc(TEMPLATE_PATH)
        sheet = doc.sheets[0] 
        
        # Estrazione dati dal JSON
        info = order_data.get("info_ordine", {})
        customer = order_data.get("dati_cliente", {})
        details = order_data.get("dettagli_ordine", [])

        # --- FASE A: Scrittura Campi Singoli ---
        # Usiamo set_value per inserire i dati nelle coordinate mappate
        sheet[CELL_MAP["nome_cliente"]].set_value(customer.get("nome_cliente", ""))
        sheet[CELL_MAP["telefono_cliente"]].set_value(customer.get("telefono_cliente", ""))
        
        sheet[CELL_MAP["data_ordine"]].set_value(_format_date(info.get("data_ordine")))
        sheet[CELL_MAP["data_cerimonia"]].set_value(_format_date(info.get("data_cerimonia")))
        sheet[CELL_MAP["data_consegna"]].set_value(_format_date(info.get("data_consegna")))
        sheet[CELL_MAP["operatore"]].set_value(info.get("operatore", ""))
        sheet[CELL_MAP["tipo_cerimonia"]].set_value(info.get("tipo_cerimonia", ""))
        
        sheet[CELL_MAP["colore_nastri"]].set_value(info.get("colore_nastri", ""))
        sheet[CELL_MAP["tipo_confetti"]].set_value(info.get("tipo_confetti", ""))
        sheet[CELL_MAP["colore_confetti"]].set_value(info.get("colore_confetti", ""))
        sheet[CELL_MAP["confezione"]].set_value(info.get("confezione", ""))
        sheet[CELL_MAP["pagamento"]].set_value(info.get("pagamento", ""))
        sheet[CELL_MAP["altro"]].set_value(info.get("altro", ""))

        # --- FASE B: Gestione Acconti ---
        # Scrive l'acconto solo se il tipo è definito (es. "Contanti")
        ac1_tipo = _clean_value_for_ods(info.get('acconto1_tipo'))
        ac1_importo = _clean_value_for_ods(info.get('acconto1_importo'), is_numeric=True)
        
        if ac1_tipo:
            sheet[CELL_MAP["acconto1_tipo"]].set_value(ac1_tipo)
            sheet[CELL_MAP["acconto1_importo"]].set_value(ac1_importo, currency='EUR')
        else:
            # Pulisce le celle se non c'è acconto
            sheet[CELL_MAP["acconto1_tipo"]].set_value("")
            sheet[CELL_MAP["acconto1_importo"]].set_value("") 

        ac2_tipo = _clean_value_for_ods(info.get('acconto2_tipo'))
        ac2_importo = _clean_value_for_ods(info.get('acconto2_importo'), is_numeric=True)
        
        if ac2_tipo:
            sheet[CELL_MAP["acconto2_tipo"]].set_value(ac2_tipo)
            sheet[CELL_MAP["acconto2_importo"]].set_value(ac2_importo, currency='EUR')
        else:
            sheet[CELL_MAP["acconto2_tipo"]].set_value("")
            sheet[CELL_MAP["acconto2_importo"]].set_value("") 

        # --- FASE C: Popolamento Tabella ---
        start_row = CELL_MAP.get("tabella_start_row_index")
        total_row = CELL_MAP.get("tabella_total_row_index")
        
        available_rows = total_row - start_row
        python_grand_total = 0.0 # Calcoliamo il totale in Python per sicurezza

        for i, item in enumerate(details):
            if i >= available_rows:
                break # Interrompe se superiamo lo spazio nel foglio
            
            row_idx = start_row + i
            
            q_val = _clean_value_for_ods(item.get('quantita'), is_numeric=True)
            p_val = _clean_value_for_ods(item.get('prezzo_unitario'), is_numeric=True)
            
            # Calcolo parziale
            python_grand_total += (q_val * p_val)

            # Scrittura Riga (Colonne fisse: 0=Ditta, 1=Codice, 2=Descr, 4=Qt, 5=Prezzo)
            sheet[(row_idx, 0)].set_value(_clean_value_for_ods(item.get('ditta')))
            sheet[(row_idx, 1)].set_value(_clean_value_for_ods(item.get('codice')))
            sheet[(row_idx, 2)].set_value(_clean_value_for_ods(item.get('descrizione')))
            sheet[(row_idx, 4)].set_value(q_val)
            sheet[(row_idx, 5)].set_value(p_val, currency='EUR')
            
            # Formula Excel per la riga (per estetica se si apre il file ODS)
            sheet[(row_idx, 6)].formula = f"of:=E{row_idx + 1}*F{row_idx + 1}"

        # Pulizia righe rimaste vuote
        for row_idx in range(start_row + len(details), total_row):
            for col in [0, 1, 2, 4, 5, 6]:
                sheet[(row_idx, col)].set_value("")

        # Avviso se articoli troncati
        if len(details) > available_rows:
            QMessageBox.warning(None, "Attenzione", f"Alcuni articoli sono stati esclusi dalla stampa (Max {available_rows}).")
        
        # --- FASE D: Gestione Totale (Ordine vs Preventivo) ---
        tipo_documento = info.get("tipo_documento", "ordine") 
        
        if tipo_documento == "preventivo":
            # Se è un preventivo, NASCONDIAMO il totale finale
            sheet[(total_row, 5)].set_value("") 
            sheet[(total_row, 6)].set_value(" ")
            sheet[(total_row, 6)].formula = ""
        else:
            # Se è un ordine, scriviamo il totale calcolato
            sheet[(total_row, 5)].set_value("TOTALE")
            sheet[(total_row, 6)].set_value(python_grand_total, currency='EUR')

        # --- FASE E: Salvataggio e Conversione ---
        # 1. Salva ODS
        base_name = os.path.splitext(original_json_filename)[0]
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", base_name)
        ods_filename = f"{safe_name}.ods"
        output_path_ods = os.path.join(OUTPUT_DIR, ods_filename)
        
        doc.saveas(output_path_ods)
        
        # 2. Converti in PDF
        pdf_path = _convert_to_pdf(output_path_ods, OUTPUT_DIR)
        
        # 3. Lancia Stampa/Apertura
        if pdf_path:
            _trigger_print_or_open(pdf_path)
            return True
        else:
            # Fallback: se PDF fallisce, apre l'ODS
            QMessageBox.warning(None, "Info", "Conversione PDF non riuscita. Apro il file modificabile.")
            _trigger_print_or_open(output_path_ods)
            return False

    except Exception as e:
        QMessageBox.critical(None, "Errore Critico Stampa", f"{e}")
        import traceback
        traceback.print_exc()
        return False