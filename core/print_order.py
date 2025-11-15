import ezodf
import os
import re
import platform
import subprocess
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import QMessageBox

# Importa i nostri nuovi percorsi
from paths import TEMPLATE_PATH, OUTPUT_DIR

# ======================================================================
# --- CONFIGURAZIONE ---
# ======================================================================

# Mappa delle celle dove inserire i dati.
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
    
    # Info Cerimonia
    "colore_nastri": "C35",
    "tipo_confetti": "C37",
    "colore_confetti": "E37",
    "confezione": "C39",
    "pagamento": "C41",
    "altro": "C15",

    # Dati Acconto
    "acconto1_tipo": "B43",
    "acconto1_importo": "C43",
    "acconto2_tipo": "B44",
    "acconto2_importo": "C44",

    # Tabella Dettagli Ordine (INDICI 0-BASED)
    "tabella_start_row_index": 19, # Riga 20 nel foglio
    "tabella_total_row_index": 32  # Riga 33
}
# ======================================================================
# --- FINE CONFIGURAZIONE ---
# ======================================================================


def _format_date(iso_date_str):
    if not iso_date_str:
        return "N.D."
    try:
        date_obj = datetime.fromisoformat(iso_date_str)
        return date_obj.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_date_str

def _trigger_print_or_open(file_path):
    """
    Tenta di inviare il file direttamente alla stampante predefinita.
    Se fallisce, apre semplicemente il file (anteprima).
    """
    try:
        full_path = os.path.realpath(file_path)
        system = platform.system()
        
        if system == "Windows":
            # "print" invia il file alla stampante predefinita.
            os.startfile(full_path, "print")
            
        elif system == "Darwin": # macOS
            # 'lpr' invia al sistema di stampa CUPS
            subprocess.run(["lpr", full_path], check=True)
            
        else: # Linux
            # 'lpr' (o 'lp') invia al sistema di stampa CUPS
            subprocess.run(["lpr", full_path], check=True)
            
    except Exception as e:
        # --- Fallback: Apri il file (comportamento precedente) ---
        print(f"Stampa diretta fallita ({e}). Apro il file in anteprima.")
        try:
            full_path = os.path.realpath(file_path)
            system = platform.system()
            if system == "Windows":
                os.startfile(full_path)
            elif system == "Darwin": # macOS
                subprocess.run(["open", full_path], check=True)
            else: # Linux
                subprocess.run(["xdg-open", full_path], check=True)
        except Exception as web_e:
            try:
                webbrowser.open(f"file://{full_path}")
            except Exception as final_e:
                QMessageBox.critical(
                    None, 
                    "Errore Apertura File",
                    f"Impossibile stampare o aprire il file: {final_e}\n"
                    f"Puoi trovarlo qui: {full_path}"
                )

def _clean_value_for_ods(value, is_numeric=False):
    """Pulisce i valori per l'inserimento nel foglio ODS."""
    if value is None:
        return 0.0 if is_numeric else ""
    text_val = str(value).strip()
    if not text_val:
        return 0.0 if is_numeric else ""
    if is_numeric:
        try:
            # Converte sia la virgola che il punto come separatore decimale
            return float(text_val.replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0
    return text_val

# --- Funzioni per la conversione PDF ---

def _get_libreoffice_command():
    """Cerca l'eseguibile di LibreOffice/Soffice."""
    system = platform.system()
    if system == "Windows":
        # Prova i percorsi comuni
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return "soffice" # Prova 'soffice' se è nel PATH
    elif system == "Darwin": # macOS
        path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(path):
            return path
        return "libreoffice" # Prova 'libreoffice' se è nel PATH
    else: # Linux
        return "libreoffice" # Di solito è nel PATH

def _convert_to_pdf(ods_path, output_dir):
    """Converte un file ODS in PDF usando LibreOffice headless."""
    soffice_cmd = _get_libreoffice_command()
    
    # Percorso del PDF di output
    pdf_name = os.path.splitext(os.path.basename(ods_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)

    abs_output_dir = os.path.abspath(output_dir)
    abs_ods_path = os.path.abspath(ods_path)

    command = [
        soffice_cmd,
        "--headless",       # Non avviare l'interfaccia utente
        "--convert-to", "pdf",
        "--outdir", abs_output_dir, # Cartella dove salvare il PDF
        abs_ods_path      # File ODS da convertire
    ]
    
    try:
        # Esegue il comando con un timeout
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30, encoding='utf-8')
        
        if os.path.exists(pdf_path):
            return pdf_path
        else:
            print(f"Errore: LibreOffice non ha creato il PDF. Output: {result.stdout} {result.stderr}")
            return None
            
    except FileNotFoundError:
        QMessageBox.critical(
            None, "Errore di Conversione PDF",
            f"Comando '{soffice_cmd}' non trovato.\n\n"
            "Per generare il PDF, assicurati che **LibreOffice** sia installato."
        )
        return None
    except subprocess.CalledProcessError as e:
        QMessageBox.critical(
            None, "Errore di Conversione PDF",
            f"LibreOffice ha restituito un errore:\n{e.stderr}"
        )
        return None
    except subprocess.TimeoutExpired:
        QMessageBox.critical(
            None, "Errore di Conversione PDF",
            "La conversione in PDF ha impiegato troppo tempo (timeout)."
        )
        return None
    except Exception as e:
        QMessageBox.critical(
            None, "Errore Sconosciuto",
            f"Errore imprevisto durante la conversione PDF:\n{e}"
        )
        return None

# --- FUNZIONE PRINCIPALE ---

def generate_and_print_order(order_data, original_json_filename):
    
    if not os.path.exists(TEMPLATE_PATH):
        QMessageBox.critical(
            None, "Errore Stampa",
            f"File template non trovato: '{TEMPLATE_PATH}'\n"
            f"Assicurati di aver rinominato il tuo file in 'template.ods'."
        )
        return False

    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
        except Exception as e:
            QMessageBox.critical(None, "Errore Stampa",
                                 f"Impossibile creare la cartella di output: {e}")
            return False

    try:
        # --- 1. Genera il file ODS ---
        doc = ezodf.opendoc(TEMPLATE_PATH)
        sheet = doc.sheets[0] # Accede al primo foglio di calcolo
        
        info = order_data.get("info_ordine", {})
        customer = order_data.get("dati_cliente", {})
        details = order_data.get("dettagli_ordine", [])

        # --- Mappatura campi singoli ---
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

        # --- Scrittura dati acconto ---
        ac1_tipo = _clean_value_for_ods(info.get('acconto1_tipo'))
        ac1_importo = _clean_value_for_ods(info.get('acconto1_importo'), is_numeric=True)
        
        if ac1_tipo: # Scrivi solo se il tipo è impostato
            sheet[CELL_MAP["acconto1_tipo"]].set_value(ac1_tipo)
            sheet[CELL_MAP["acconto1_importo"]].set_value(ac1_importo, currency='EUR')
        else:
            sheet[CELL_MAP["acconto1_tipo"]].set_value("")
            sheet[CELL_MAP["acconto1_importo"]].set_value("") # Pulisce la cella

        ac2_tipo = _clean_value_for_ods(info.get('acconto2_tipo'))
        ac2_importo = _clean_value_for_ods(info.get('acconto2_importo'), is_numeric=True)
        
        if ac2_tipo: # Scrivi solo se il tipo è impostato
            sheet[CELL_MAP["acconto2_tipo"]].set_value(ac2_tipo)
            sheet[CELL_MAP["acconto2_importo"]].set_value(ac2_importo, currency='EUR')
        else:
            sheet[CELL_MAP["acconto2_tipo"]].set_value("")
            sheet[CELL_MAP["acconto2_importo"]].set_value("") # Pulisce la cella

        # --- Popolamento tabella ---
        start_row_index = CELL_MAP.get("tabella_start_row_index")
        total_row_index = CELL_MAP.get("tabella_total_row_index")
        
        template_available_rows = total_row_index - start_row_index
        num_items = len(details)

        # 1. Popola i dati dell'ordine
        for i, item in enumerate(details):
            if i >= template_available_rows:
                break # Interrompi se abbiamo più item che righe disponibili
            
            row_idx = start_row_index + i
            
            # Nota: gli indici di colonna sono (0=A, 1=B, 2=C, ...)
            sheet[(row_idx, 0)].set_value(_clean_value_for_ods(item.get('ditta')))
            sheet[(row_idx, 1)].set_value(_clean_value_for_ods(item.get('codice')))
            sheet[(row_idx, 2)].set_value(_clean_value_for_ods(item.get('descrizione')))
            sheet[(row_idx, 4)].set_value(_clean_value_for_ods(item.get('quantita'), is_numeric=True))
            sheet[(row_idx, 5)].set_value(_clean_value_for_ods(item.get('prezzo_unitario'), is_numeric=True), currency='EUR')
            
            # Col G (Indice 6) - Scriviamo la FORMULA
            # (gli indici delle righe nel foglio sono +1 rispetto a quelli 0-based)
            formula = f"of:=E{row_idx + 1}*F{row_idx + 1}"
            sheet[(row_idx, 6)].formula = formula

        # 2. Pulisce le righe vuote rimanenti nel template
        start_cleaning_index = start_row_index + num_items
        for row_idx_to_clean in range(start_cleaning_index, total_row_index):
            sheet[(row_idx_to_clean, 0)].set_value("")
            sheet[(row_idx_to_clean, 1)].set_value("")
            sheet[(row_idx_to_clean, 2)].set_value("")
            sheet[(row_idx_to_clean, 4)].set_value("") 
            sheet[(row_idx_to_clean, 5)].set_value("") 
            sheet[(row_idx_to_clean, 6)].set_value("")

        # 3. Avviso se gli articoli sono stati troncati
        if num_items > template_available_rows:
            QMessageBox.warning(None, "Avviso Stampa",
                f"ATTENZIONE: L'ordine ha {num_items} articoli,\n"
                f"ma il template ha spazio solo per {template_available_rows}.\n\n"
                "Gli articoli in eccesso NON sono stati stampati."
            )
        
        # --- 2. Salvataggio ODS ---
        base_name = os.path.splitext(original_json_filename)[0]
        safe_base_name = re.sub(r'[\\/*?:"<>|]', "_", base_name)
        
        output_filename_ods = f"{safe_base_name}.ods"
        output_path_ods = os.path.join(OUTPUT_DIR, output_filename_ods)
        
        doc.saveas(output_path_ods)
        
        # --- 3. Conversione in PDF ---
        # (La cartella di output è la stessa, OUTPUT_DIR)
        pdf_path = _convert_to_pdf(output_path_ods, OUTPUT_DIR)
        
        # --- 4. Apertura del file ---
        if pdf_path:
            # SUCCESSO: Tenta la stampa diretta (nuova funzione)
            _trigger_print_or_open(pdf_path)
            return True
        else:
            # FALLIMENTO PDF: Tenta la stampa diretta del file ODS (fallback)
            QMessageBox.warning(
                None, "Fallback Stampa",
                "Conversione in PDF fallita (assicurati che LibreOffice sia installato).\n\n"
                "Verrà tentata la stampa diretta del file ODS originale."
            )
            _trigger_print_or_open(output_path_ods)
            return False

    except Exception as e:
        QMessageBox.critical(
            None, 
            "Errore di Stampa",
            f"Si è verificato un errore durante la generazione del file:\n{e}"
        )
        import traceback
        traceback.print_exc()
        return False