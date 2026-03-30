import base64
import re
import time
from typing import Optional

import pandas as pd
import streamlit as st

from config import Config
from utils.pdf import extract_text_from_pdf, extract_article_numbers_from_text
from utils.search import search_conrad_by_article_number
from utils.ocr import setup_ocr_environment

# ------------------------------------------------------------------------------
# UI Texts (German)
# ------------------------------------------------------------------------------
UI_TEXTS = {
    "title": "Conrad Produktfinder - Bestellungen wiederfinden",
    "file_upload": "Datei hochladen (CSV oder PDF)",
    "csv_help": "Laden Sie eine CSV-Datei mit Artikelliste hoch",
    "pdf_help": "Oder laden Sie einen Conrad Warenkorb/Bestellung PDF hoch",
    "preview_data": "Vorschau der extrahierten Daten",
    "column_mapping": "Spaltenzuordnung",
    "map_columns": "Weisen Sie die Spalten Ihrer Datei den erforderlichen Feldern zu:",
    "quantity": "Menge",
    "article_no": "Conrad Artikel-Nr.",
    "description": "Beschreibung",
    "search_all": "Alle Positionen suchen",
    "search_row": "Diese Position suchen",
    "choose_product": "Produkt auswählen",
    "open_new_tab": "In neuem Tab öffnen",
    "product_title": "Produkttitel",
    "conrad_number": "Bestell-Nr.",
    "price": "Preis",
    "no_results": "Keine Ergebnisse gefunden",
    "download_csv": "CSV herunterladen",
    "processing_pdf": "PDF wird verarbeitet...",
    "search_settings": "Such-Einstellungen",
    "search_delay": "Verzögerung zwischen Suchanfragen (Sekunden)",
    "max_results": "Maximale Suchergebnisse pro Produkt",
    "apply_mapping": "Zuordnung anwenden",
    "items_found": "Artikel gefunden",
    "final_selection": "Finale Auswahl",
    "selected_products_count": "Ausgewählte Produkte",
    "not_found": "Nicht gefunden",
    "manual_entry": "Manuelle Eingabe",
    "tesseract_path": "Pfad zu Tesseract (tesseract.exe)",
    "tessdata_path": "Pfad zum tessdata-Ordner (optional)",
    "poppler_path": "Pfad zu Poppler (optional)",
    "ocr_config": "OCR-Konfiguration",
    "no_article_number": "Keine Artikelnr. gefunden",
    "searching": "Suche Conrad nach Artikelnr.",
    "results_found": "Produkte gefunden",
    "no_results_for": "Keine Treffer für Artikelnr.",
    "web_search_fallback": "Websuche-Fallback",
    "enable_fallback": "Fallback-Suche aktivieren",
    "search_api_key": "API-Schlüssel für Websuche (optional)",
    "searching_web": "Keine Conrad-Treffer gefunden – starte Websuche...",
    "no_web_results": "Keine Web-Treffer für Artikelnr.",
    "serper_api_key": "Serper.dev API-Schlüssel",
    "bing_api_key": "Bing Web Search API-Schlüssel",
    "search_provider": "Suchanbieter für Fallback",
    "duckduckgo_fallback": "DuckDuckGo (kein API-Schlüssel nötig)",
    "serper_dev": "Serper.dev (Google Search)",
    "bing_search": "Bing Web Search"
}

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def setup_sidebar() -> dict:
    """Sidebar with configuration options."""
    st.sidebar.title("Einstellungen")
    
    # OCR configuration
    st.sidebar.subheader(UI_TEXTS["ocr_config"])
    tesseract_path = st.sidebar.text_input(
        UI_TEXTS["tesseract_path"],
        value=Config.DEFAULT_TESSERACT_PATH,
        help="Vollständiger Pfad zur tesseract.exe"
    )
    tessdata_path = st.sidebar.text_input(
        UI_TEXTS["tessdata_path"],
        value=Config.DEFAULT_TESSDATA_PATH,
        help="Pfad zum tessdata-Ordner"
    )
    poppler_path = st.sidebar.text_input(
        UI_TEXTS["poppler_path"],
        value=Config.DEFAULT_POPPLER_PATH,
        help="Pfad zu Poppler (enthält pdftoppm.exe)"
    )
    
    # Check if Tesseract works
    if tesseract_path:
        success, msg = setup_ocr_environment(tesseract_path, tessdata_path)
        if not success:
            st.sidebar.warning(f"OCR nicht verfügbar: {msg}")
    
    # Search settings
    st.sidebar.subheader(UI_TEXTS["search_settings"])
    search_delay = st.sidebar.number_input(
        UI_TEXTS["search_delay"],
        min_value=0.5, max_value=10.0, value=Config.DEFAULT_SEARCH_DELAY, step=0.5
    )
    max_results = st.sidebar.number_input(
        UI_TEXTS["max_results"],
        min_value=1, max_value=10, value=Config.DEFAULT_MAX_RESULTS
    )
    
    # Web search fallback
    st.sidebar.subheader(UI_TEXTS["web_search_fallback"])
    enable_fallback = st.sidebar.checkbox(
        UI_TEXTS["enable_fallback"], value=Config.DEFAULT_ENABLE_FALLBACK
    )
    
    provider_names = {
        "duckduckgo": UI_TEXTS["duckduckgo_fallback"],
        "serper": UI_TEXTS["serper_dev"],
        "bing": UI_TEXTS["bing_search"]
    }
    provider_options = list(provider_names.keys())
    provider_labels = [provider_names[p] for p in provider_options]
    provider_index = provider_options.index(Config.DEFAULT_SEARCH_PROVIDER) if Config.DEFAULT_SEARCH_PROVIDER in provider_options else 0
    search_provider = st.sidebar.selectbox(
        UI_TEXTS["search_provider"],
        provider_options,
        format_func=lambda x: provider_names[x],
        index=provider_index
    )
    
    api_key = None
    if search_provider == "serper":
        api_key = st.sidebar.text_input(
            UI_TEXTS["serper_api_key"],
            type="password",
            value=Config.SERPER_API_KEY or "",
            help="API-Schlüssel von serper.dev"
        )
    elif search_provider == "bing":
        api_key = st.sidebar.text_input(
            UI_TEXTS["bing_api_key"],
            type="password",
            value=Config.BING_API_KEY or "",
            help="Bing Web Search API-Schlüssel"
        )
    
    # Additional OCR settings for PDF
    ocr_dpi = st.sidebar.selectbox("DPI für OCR", [200, 250, 300, 350, 400], index=2)
    ocr_language = st.sidebar.selectbox("OCR-Sprache", ["deu+eng", "deu", "eng"], index=0)
    
    return {
        'tesseract_path': tesseract_path,
        'tessdata_path': tessdata_path,
        'poppler_path': poppler_path,
        'ocr_dpi': ocr_dpi,
        'ocr_language': ocr_language,
        'search_delay': search_delay,
        'max_results': max_results,
        'enable_fallback': enable_fallback,
        'search_provider': search_provider,
        'api_key': api_key,
        'serper_api_key': api_key if search_provider == "serper" else None,
        'bing_api_key': api_key if search_provider == "bing" else None,
    }

def pdf_to_df(pdf_bytes: bytes, config: dict) -> Optional[pd.DataFrame]:
    """Convert PDF to DataFrame with article numbers only."""
    st.info(UI_TEXTS["processing_pdf"])
    try:
        text = extract_text_from_pdf(pdf_bytes, config)
        if not text.strip():
            st.error("Konnte keinen Text aus PDF extrahieren.")
            return None
        
        article_numbers = extract_article_numbers_from_text(text)
        if not article_numbers:
            st.warning("Keine Conrad Artikelnummern im PDF gefunden.")
            return None
        
        # Create DataFrame with default quantity = 1
        items = [{'quantity': 1, 'article_no': art_no, 'description': ""} for art_no in article_numbers]
        df = pd.DataFrame(items)
        st.success(f"**Erfolgreich {len(df)} Artikelnummern extrahiert!**")
        return df
    except Exception as e:
        st.error(f"Fehler bei PDF-Verarbeitung: {str(e)}")
        return None

def manual_data_entry():
    """Manual product entry form."""
    st.subheader(UI_TEXTS["manual_entry"])
    num_products = st.number_input("Anzahl der Produkte", min_value=1, max_value=50, value=3)
    products = []
    for i in range(num_products):
        with st.expander(f"Produkt {i+1}"):
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input(f"Menge {i+1}", min_value=1, value=1, key=f"qty_{i}")
                article_no = st.text_input(f"Artikel-Nr. {i+1}", key=f"art_{i}")
            with col2:
                description = st.text_input(f"Beschreibung {i+1} (optional)", key=f"desc_{i}")
            if article_no:
                clean_article_no = re.sub(r'[^\d-]', '', article_no)
                if '-' in clean_article_no:
                    clean_article_no = clean_article_no.split('-')[0]
                products.append({
                    'quantity': quantity,
                    'article_no': clean_article_no,
                    'description': description if description else ""
                })
    if products and st.button("Produkte übernehmen"):
        df = pd.DataFrame(products)
        st.session_state.extracted_items = df
        st.success(f"{len(products)} Produkte übernommen")

def perform_single_search(idx: int, row: pd.Series, config: dict, column_mapping: dict):
    """Search for a single row."""
    article_col = column_mapping.get('article_no', 'article_no')
    if article_col not in row or pd.isna(row[article_col]) or not row[article_col]:
        st.error("Keine Artikelnummer für diese Position verfügbar")
        return
    
    article_no = str(row[article_col]).strip()
    clean_article_no = re.sub(r'[^\d-]', '', article_no)
    if '-' in clean_article_no:
        clean_article_no = clean_article_no.split('-')[0]
    if not clean_article_no.isdigit():
        st.error(f"Ungültige Artikelnummer: {article_no}")
        return
    
    with st.spinner(f"Suche nach Artikel {clean_article_no}..."):
        candidates = search_conrad_by_article_number(clean_article_no, config)
        st.session_state.search_results[idx] = candidates
        if not candidates:
            st.warning(f"{UI_TEXTS['no_results_for']} {clean_article_no}")

def perform_bulk_search(df: pd.DataFrame, config: dict, column_mapping: dict):
    """Bulk search for all rows."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    article_col = column_mapping.get('article_no', 'article_no')
    
    for idx, row in df.iterrows():
        status_text.text(f"Suche Position {idx+1}/{len(df)}...")
        if article_col in row and pd.notna(row[article_col]) and row[article_col]:
            article_no = str(row[article_col]).strip()
            clean_article_no = re.sub(r'[^\d-]', '', article_no)
            if '-' in clean_article_no:
                clean_article_no = clean_article_no.split('-')[0]
            if clean_article_no.isdigit():
                candidates = search_conrad_by_article_number(clean_article_no, config)
                st.session_state.search_results[idx] = candidates
            else:
                st.session_state.search_results[idx] = []
        else:
            st.session_state.search_results[idx] = []
        time.sleep(config['search_delay'])
        progress_bar.progress((idx + 1) / len(df))
    
    status_text.text("Suche abgeschlossen")

def display_search_results(idx: int, config: dict):
    """Display search results for a specific row."""
    results = st.session_state.search_results.get(idx, [])
    if not results:
        st.write(UI_TEXTS["no_results"])
        return
    
    # Build radio options
    options = []
    for res in results:
        source_tag = ""
        if res.get('source') == 'web_fallback':
            source_tag = " [Web-Fallback]"
        elif res.get('source') in ('serper_api', 'bing_api'):
            source_tag = f" [{res['source']}]"
        option_text = f"{res['title']} | {res['article_no']} | {res['price'] or 'Preis unbekannt'}{source_tag}"
        options.append(option_text)
    
    selected_index = st.radio(
        f"{UI_TEXTS['choose_product']} #{idx+1}:",
        range(len(options)),
        format_func=lambda i: options[i],
        key=f"select_{idx}"
    )
    
    if selected_index is not None and selected_index < len(results):
        selected = results[selected_index]
        st.session_state.selected_products[idx] = selected
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{UI_TEXTS['product_title']}:** {selected['title']}")
            st.write(f"**{UI_TEXTS['conrad_number']}:** {selected['article_no']}")
            st.write(f"**{UI_TEXTS['price']}:** {selected['price'] or 'N/A'}")
            source = selected.get('source', 'conrad_direct')
            if source != 'conrad_direct':
                st.write(f"**Quelle:** {source}")
        with col2:
            st.markdown(
                f'<a href="{selected["url"]}" target="_blank">'
                f'<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">'
                f'{UI_TEXTS["open_new_tab"]}'
                f'</button></a>', 
                unsafe_allow_html=True
            )

def create_final_dataframe(original_df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """Create final DataFrame with selected products."""
    final_data = []
    for idx, row in original_df.iterrows():
        row_data = row.to_dict()
        if idx in st.session_state.selected_products:
            sel = st.session_state.selected_products[idx]
            row_data['Gewählte Conrad URL'] = sel['url']
            row_data['Gewählte Bestell-Nr.'] = sel['article_no']
            row_data['Gewählter Titel'] = sel['title']
            row_data['Gewählter Preis'] = sel['price'] or ''
            row_data['Status'] = 'Gefunden'
            row_data['Quelle'] = sel.get('source', 'conrad_direct')
        else:
            row_data['Gewählte Conrad URL'] = ''
            row_data['Gewählte Bestell-Nr.'] = ''
            row_data['Gewählter Titel'] = ''
            row_data['Gewählter Preis'] = ''
            row_data['Status'] = UI_TEXTS['not_found']
            row_data['Quelle'] = ''
        final_data.append(row_data)
    return pd.DataFrame(final_data)

def main():
    st.set_page_config(page_title="Conrad Produktfinder", page_icon="🔍", layout="wide")
    st.title(UI_TEXTS["title"])
    
    # Initialize session state
    if 'extracted_items' not in st.session_state:
        st.session_state.extracted_items = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = {}
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = {}
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    
    config = setup_sidebar()
    
    # Data source selection
    upload_options = ["CSV hochladen", "Manuelle Eingabe"]
    if True:  # OCR is always attempted, but might fail
        upload_options.insert(1, "PDF hochladen")
    
    upload_option = st.radio("Datenquelle wählen:", upload_options)
    
    if upload_option == "CSV hochladen":
        uploaded_file = st.file_uploader(UI_TEXTS["file_upload"], type=['csv'], help=UI_TEXTS['csv_help'])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.extracted_items = df
    elif upload_option == "PDF hochladen":
        uploaded_file = st.file_uploader(UI_TEXTS["file_upload"], type=['pdf'], help=UI_TEXTS['pdf_help'])
        if uploaded_file is not None:
            df = pdf_to_df(uploaded_file.getvalue(), config)
            if df is not None:
                st.session_state.extracted_items = df
    elif upload_option == "Manuelle Eingabe":
        manual_data_entry()
    
    # Process extracted items
    if st.session_state.extracted_items is not None:
        df = st.session_state.extracted_items
        st.subheader(UI_TEXTS["preview_data"])
        st.dataframe(df)
        st.write(f"{len(df)} {UI_TEXTS['items_found']}")
        
        # Column mapping
        st.subheader(UI_TEXTS["column_mapping"])
        st.write(UI_TEXTS["map_columns"])
        cols = list(df.columns)
        col1, col2, col3 = st.columns(3)
        with col1:
            qty_map = st.selectbox(UI_TEXTS["quantity"], [''] + cols)
        with col2:
            art_map = st.selectbox(UI_TEXTS["article_no"], [''] + cols)
        with col3:
            desc_map = st.selectbox(UI_TEXTS["description"], [''] + cols)
        
        column_mapping = {
            'quantity': qty_map if qty_map else 'quantity',
            'article_no': art_map if art_map else 'article_no',
            'description': desc_map if desc_map else 'description'
        }
        
        if st.button(UI_TEXTS["apply_mapping"]):
            st.session_state.column_mapping = column_mapping
            st.success("Zuordnung angewendet")
        
        if st.session_state.column_mapping:
            st.subheader("Produktsuche")
            if st.button(UI_TEXTS["search_all"]):
                perform_bulk_search(df, config, st.session_state.column_mapping)
            
            for idx, row in df.iterrows():
                article_col = st.session_state.column_mapping.get('article_no', 'article_no')
                article_no = row.get(article_col, 'Keine Artikelnr.')
                with st.expander(f"Position {idx+1}: Artikelnr. {article_no}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Menge:** {row.get(st.session_state.column_mapping.get('quantity', 'quantity'), 'N/A')}")
                        st.write(f"**Artikel-Nr.:** {article_no}")
                        desc = row.get(st.session_state.column_mapping.get('description', 'description'), '')
                        if desc:
                            st.write(f"**Beschreibung:** {desc}")
                    with col2:
                        if st.button(UI_TEXTS["search_row"], key=f"search_{idx}"):
                            perform_single_search(idx, row, config, st.session_state.column_mapping)
                    if idx in st.session_state.search_results:
                        display_search_results(idx, config)
            
            if st.session_state.selected_products:
                st.subheader(UI_TEXTS["final_selection"])
                st.write(f"{len(st.session_state.selected_products)} {UI_TEXTS['selected_products_count']}")
                final_df = create_final_dataframe(df, st.session_state.column_mapping)
                st.dataframe(final_df)
                
                csv = final_df.to_csv(index=False, encoding='utf-8-sig')
                b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="conrad_bestellung.csv">{UI_TEXTS["download_csv"]}</a>'
                st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
