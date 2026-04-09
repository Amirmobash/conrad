# app.py - Conrad Produktfinder (Deutsch, automatische Suche, Webcam)
# Version: 7.0
# Beschreibung: Lädt PDF/CSV oder scannt per Webcam – sucht automatisch alle Artikel bei conrad.de

import asyncio
import aiohttp
import base64
import hashlib
import io
import os
import re
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image

# ------------------------------------------------------------------------------
# Optionale Importe für OCR, PDF, Barcode
# ------------------------------------------------------------------------------
try:
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

try:
    import pdf2image
    PDF2IMAGE_SUPPORT = True
except ImportError:
    PDF2IMAGE_SUPPORT = False

try:
    from pyzbar.pyzbar import decode
    BARCODE_SUPPORT = True
except ImportError:
    BARCODE_SUPPORT = False

try:
    from PyPDF2 import PdfReader
    PDF_TEXT_SUPPORT = True
except ImportError:
    PDF_TEXT_SUPPORT = False

# ------------------------------------------------------------------------------
# Konfiguration (Umgebungsvariablen oder Standardpfade)
# ------------------------------------------------------------------------------
DEFAULT_TESSERACT_PATH = os.getenv("TESSERACT_PATH", "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
DEFAULT_TESSDATA_PATH = os.getenv("TESSDATA_PATH", "C:\\Program Files\\Tesseract-OCR\\tessdata")
DEFAULT_POPPLER_PATH = os.getenv("POPPLER_PATH", "C:\\poppler\\poppler-23.11.0\\Library\\bin")

DEFAULT_SEARCH_DELAY = float(os.getenv("SEARCH_DELAY", "0.5"))        # automatisch schnell
DEFAULT_MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
DEFAULT_ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
DEFAULT_SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# ------------------------------------------------------------------------------
# Zentrale UI-Texte (Deutsch)
# ------------------------------------------------------------------------------
UI_TEXTE = {
    "title": "🔍 Conrad Produktfinder – Automatische Bestellhilfe",
    "subtitle": "PDF, CSV oder Webcam – ich suche alle Artikel selbstständig bei Conrad",
    "file_upload": "📂 Datei hochladen (CSV oder PDF)",
    "csv_help": "Laden Sie eine CSV-Datei mit Artikelliste hoch",
    "pdf_help": "PDF mit Conrad-Bestellung oder Warenkorb – ich extrahiere alle Nummern",
    "preview_data": "📋 Extrahierte Artikel",
    "column_mapping": "🔧 Spaltenzuordnung (nur bei CSV nötig)",
    "map_columns": "Weisen Sie die Spalten zu:",
    "quantity": "Menge",
    "article_no": "Conrad Artikel-Nr.",
    "description": "Beschreibung",
    "choose_product": "✅ Produkt auswählen",
    "open_new_tab": "🌐 In neuem Tab öffnen",
    "product_title": "📦 Produkttitel",
    "conrad_number": "🔢 Bestell-Nr.",
    "price": "💰 Preis",
    "no_results": "❌ Keine Ergebnisse gefunden",
    "download_csv": "📥 Ergebnis CSV herunterladen",
    "processing_pdf": "📄 PDF wird verarbeitet...",
    "search_settings": "⚙️ Such-Einstellungen",
    "search_delay": "⏱️ Verzögerung zwischen Suchanfragen (Sekunden)",
    "max_results": "📊 Maximale Suchergebnisse pro Produkt",
    "apply_mapping": "Übernehmen",
    "items_found": "Artikel gefunden",
    "final_selection": "🎯 Ausgewählte Produkte",
    "selected_products_count": "Produkte zugeordnet",
    "not_found": "Nicht gefunden",
    "manual_entry": "✏️ Manuelle Eingabe",
    "tesseract_path": "🖨️ Pfad zu Tesseract (tesseract.exe)",
    "tessdata_path": "🗂️ Pfad zum tessdata-Ordner",
    "poppler_path": "📄 Pfad zu Poppler",
    "ocr_config": "📑 OCR-Konfiguration",
    "searching": "🔍 Suche Conrad nach Artikelnr.",
    "no_results_for": "Keine Treffer für Artikelnr.",
    "web_search_fallback": "🌐 Websuche-Fallback",
    "enable_fallback": "Fallback aktivieren",
    "searching_web": "Keine Conrad-Treffer – starte Websuche...",
    "serper_api_key": "🔑 Serper.dev API-Schlüssel",
    "bing_api_key": "🔑 Bing Web Search API-Schlüssel",
    "search_provider": "Anbieter für Fallback",
    "duckduckgo_fallback": "DuckDuckGo (kostenlos)",
    "serper_dev": "Serper.dev (Google)",
    "bing_search": "Bing Search",
    "cache_info": "💾 Cache gültig für {} Sekunden",
    "status_complete": "Suche abgeschlossen.",
    "source_conrad": "Conrad direkt",
    "source_fallback": "Web-Fallback",
    "source_api": "API",
    "ocr_language": "OCR-Sprache(n)",
    "ocr_dpi": "DPI für OCR",
    "data_source": "📁 Datenquelle wählen",
    "csv_option": "📄 CSV hochladen",
    "pdf_option": "📑 PDF hochladen (automatisch)",
    "manual_option": "✏️ Manuelle Eingabe",
    "webcam_option": "📸 Webcam-Scanner (Barcode/OCR)",
    "num_products_manual": "Anzahl Produkte",
    "product": "Produkt",
    "quantity_abbr": "Menge",
    "article_no_abbr": "Art.-Nr.",
    "description_abbr": "Beschreibung",
    "invalid_article": "Ungültige Artikelnummer",
    "take_over": "Übernehmen",
    "search_progress": "Suche Position {}/{}",
    "source_label": "Quelle",
    "webcam_scan": "📸 Artikelnummer scannen",
    "webcam_help": "Richten Sie die Kamera auf einen Barcode oder die gedruckte Nummer. Klicken Sie auf 'Foto aufnehmen'.",
    "scan_button": "🔍 Scannen",
    "scanned_article": "Gescannte Artikelnummer: {}",
    "add_to_list": "➕ Zur Liste hinzufügen",
    "auto_search_active": "✅ Automatische Suche nach dem Hochladen aktiviert",
    "auto_search_done": "Automatische Suche abgeschlossen",
}

UI_TEXTE["cache_info"] = UI_TEXTE["cache_info"].format(CACHE_TTL)

# ------------------------------------------------------------------------------
# Session-State initialisieren
# ------------------------------------------------------------------------------
def init_session_state():
    if 'extrahierte_elemente' not in st.session_state:
        st.session_state.extrahierte_elemente = None
    if 'such_ergebnisse' not in st.session_state:
        st.session_state.such_ergebnisse = {}
    if 'ausgewaehlte_produkte' not in st.session_state:
        st.session_state.ausgewaehlte_produkte = {}
    if 'spalten_zuordnung' not in st.session_state:
        st.session_state.spalten_zuordnung = {}
    if 'such_cache' not in st.session_state:
        st.session_state.such_cache = {}
    if 'cache_zeitstempel' not in st.session_state:
        st.session_state.cache_zeitstempel = {}
    if 'auto_search_triggered' not in st.session_state:
        st.session_state.auto_search_triggered = False

# ------------------------------------------------------------------------------
# Artikelnummer bereinigen
# ------------------------------------------------------------------------------
def bereinige_artikelnummer(artikel_nr: str) -> Optional[str]:
    if not artikel_nr or not isinstance(artikel_nr, str):
        return None
    bereinigt = re.sub(r'[^\d-]', '', artikel_nr)
    if '-' in bereinigt:
        bereinigt = bereinigt.split('-')[0]
    bereinigt = re.sub(r'\s+', '', bereinigt)
    if bereinigt.isdigit() and 5 <= len(bereinigt) <= 8:
        return bereinigt
    return None

# ------------------------------------------------------------------------------
# OCR einrichten
# ------------------------------------------------------------------------------
def richte_ocr_ein(tesseract_pfad=None, tessdata_pfad=None) -> Tuple[bool, str]:
    if not OCR_SUPPORT:
        return False, "pytesseract nicht installiert."
    try:
        if tesseract_pfad and os.path.exists(tesseract_pfad):
            pytesseract.pytesseract.tesseract_cmd = tesseract_pfad
        else:
            pytesseract.get_tesseract_version()
        if tessdata_pfad and os.path.exists(tessdata_pfad):
            os.environ['TESSDATA_PREFIX'] = tessdata_pfad
        return True, "OCR bereit"
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------------------
# Barcode-Erkennung aus Bild
# ------------------------------------------------------------------------------
def erkenne_barcode_im_bild(bild: Image.Image) -> Optional[str]:
    if not BARCODE_SUPPORT:
        return None
    try:
        codes = decode(bild)
        for code in codes:
            nummer = code.data.decode('utf-8').strip()
            bereinigt = bereinige_artikelnummer(nummer)
            if bereinigt:
                return bereinigt
        return None
    except:
        return None

# ------------------------------------------------------------------------------
# OCR auf Bild (für Artikelnummern)
# ------------------------------------------------------------------------------
def erkenne_artikelnummer_mit_ocr(bild: Image.Image, konfig: Dict) -> Optional[str]:
    if not OCR_SUPPORT:
        return None
    erfolg, _ = richte_ocr_ein(konfig.get('tesseract_pfad'), konfig.get('tessdata_pfad'))
    if not erfolg:
        return None
    try:
        bild = bild.convert('L')
        config = '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789-'
        sprache = konfig.get('ocr_sprache', 'deu+eng')
        text = pytesseract.image_to_string(bild, lang=sprache, config=config)
        nummern = re.findall(r'\d{5,8}', text)
        for num in nummern:
            bereinigt = bereinige_artikelnummer(num)
            if bereinigt:
                return bereinigt
        return None
    except:
        return None

# ------------------------------------------------------------------------------
# PDF zu DataFrame (mit OCR-Fallback)
# ------------------------------------------------------------------------------
def extrahiere_text_aus_pdf(pdf_bytes: bytes, konfig: Dict) -> str:
    # Versuche direkten Text
    if PDF_TEXT_SUPPORT:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for seite in reader.pages:
                text += seite.extract_text() or ""
            if text.strip():
                return text
        except:
            pass
    # OCR-Fallback
    if not PDF2IMAGE_SUPPORT:
        return ""
    erfolg, _ = richte_ocr_ein(konfig.get('tesseract_pfad'), konfig.get('tessdata_pfad'))
    if not erfolg:
        return ""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(pdf_bytes)
        tmp_pfad = tmp.name
    try:
        poppler = konfig.get('poppler_pfad')
        bilder = pdf2image.convert_from_path(tmp_pfad, dpi=konfig.get('ocr_dpi', 300),
                                             poppler_path=poppler if poppler and os.path.exists(poppler) else None)
        gesamter_text = ""
        for img in bilder:
            img = img.convert('L')
            text = pytesseract.image_to_string(img, lang=konfig.get('ocr_sprache', 'deu+eng'))
            gesamter_text += text + "\n"
        return gesamter_text
    finally:
        os.unlink(tmp_pfad)

def extrahiere_artikelnummern_aus_text(text: str) -> List[str]:
    if not text:
        return []
    muster = [
        r'bestell[.-]?nr\.?\s*:?\s*(\d{5,8})',
        r'artikel[.-]?nr\.?\s*:?\s*(\d{5,8})',
        r'conrad\s*art\.?\s*nr\.?\s*:?\s*(\d{5,8})',
        r'(\d{5,8})'
    ]
    gefunden = set()
    for pattern in muster:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            num = match.group(1)
            bereinigt = bereinige_artikelnummer(num)
            if bereinigt:
                gefunden.add(bereinigt)
    return list(gefunden)

def pdf_zu_dataframe(pdf_bytes: bytes, konfig: Dict) -> Optional[pd.DataFrame]:
    st.info(UI_TEXTE["processing_pdf"])
    text = extrahiere_text_aus_pdf(pdf_bytes, konfig)
    if not text:
        st.error("Konnte keinen Text aus PDF extrahieren.")
        return None
    artikel_nrn = extrahiere_artikelnummern_aus_text(text)
    if not artikel_nrn:
        st.warning("Keine Conrad-Artikelnummern gefunden.")
        return None
    daten = [{'Menge': 1, 'Artikel-Nr.': art, 'Beschreibung': ""} for art in artikel_nrn]
    df = pd.DataFrame(daten)
    st.success(f"✅ {len(df)} Artikelnummern extrahiert.")
    return df

# ------------------------------------------------------------------------------
# Suchfunktionen (asynchron)
# ------------------------------------------------------------------------------
async def hole_html(session, url, headers):
    try:
        async with session.get(url, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                return await resp.text()
    except:
        return None

async def suche_conrad_async(artikel_nr, session):
    such_url = f"https://www.conrad.de/de/search.html?search={artikel_nr}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    html = await hole_html(session, such_url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    produkte = []
    link_muster = re.compile(r'/de/p/[\w-]+-\d+\.html', re.I)
    for a in soup.find_all('a', href=True):
        if link_muster.search(a['href']):
            url = 'https://www.conrad.de' + a['href'] if a['href'].startswith('/') else a['href']
            produkte.append({
                'url': url,
                'titel': a.get_text(strip=True) or "Produkt",
                'artikel_nr': artikel_nr,
                'preis': None,
                'relevanz': 100,
                'quelle': 'conrad_direkt'
            })
    return produkte

async def suche_duckduckgo_async(artikel_nr, session):
    from urllib.parse import quote
    query = f"site:conrad.de {artikel_nr} Bestell-Nr"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    html = await hole_html(session, url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    produkte = []
    for link in soup.find_all('a', href=True, class_='result__url'):
        href = link.get('href', '')
        if 'conrad.de/de/p/' in href:
            voll_url = href if href.startswith('http') else f'https:{href}'
            produkte.append({
                'url': voll_url,
                'titel': "Conrad Produkt (Web)",
                'artikel_nr': artikel_nr,
                'preis': None,
                'relevanz': 90,
                'quelle': 'web_fallback'
            })
    return produkte[:5]

async def suche_serper_async(artikel_nr, api_key, session):
    query = f"site:conrad.de {artikel_nr}"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {"q": query, "num": 5}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                produkte = []
                for res in data.get('organic', []):
                    if 'conrad.de/de/p/' in res.get('link', ''):
                        produkte.append({
                            'url': res['link'],
                            'titel': res.get('title', 'Conrad Produkt'),
                            'artikel_nr': artikel_nr,
                            'preis': None,
                            'relevanz': 95,
                            'quelle': 'serper_api'
                        })
                return produkte
    except:
        return []

async def suche_bing_async(artikel_nr, api_key, session):
    query = f"site:conrad.de {artikel_nr}"
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {'Ocp-Apim-Subscription-Key': api_key}
    params = {'q': query, 'count': 5, 'responseFilter': 'Webpages'}
    try:
        async with session.get(url, headers=headers, params=params, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                produkte = []
                for res in data.get('webPages', {}).get('value', []):
                    if 'conrad.de/de/p/' in res.get('url', ''):
                        produkte.append({
                            'url': res['url'],
                            'titel': res.get('name', 'Conrad Produkt'),
                            'artikel_nr': artikel_nr,
                            'preis': None,
                            'relevanz': 95,
                            'quelle': 'bing_api'
                        })
                return produkte
    except:
        return []

async def suche_web_fallback_async(artikel_nr, konfig, session):
    anbieter = konfig.get('such_anbieter', 'duckduckgo')
    if anbieter == 'serper' and konfig.get('serper_api_key'):
        return await suche_serper_async(artikel_nr, konfig['serper_api_key'], session)
    elif anbieter == 'bing' and konfig.get('bing_api_key'):
        return await suche_bing_async(artikel_nr, konfig['bing_api_key'], session)
    else:
        return await suche_duckduckgo_async(artikel_nr, session)

async def hole_produkt_details_async(produkt_url, ursp_artikel_nr, session):
    headers = {'User-Agent': 'Mozilla/5.0'}
    html = await hole_html(session, produkt_url, headers)
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    titel = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Titel unbekannt"
    seiten_text = soup.get_text()
    match = re.search(r'Bestell-Nr\.\s*([A-Z0-9\-]+)', seiten_text, re.I)
    artikel_nr = match.group(1) if match else ursp_artikel_nr
    preis_elem = soup.select_one('.price__value, .product__price')
    preis = preis_elem.get_text(strip=True) if preis_elem else None
    return {
        'url': produkt_url,
        'titel': titel,
        'artikel_nr': artikel_nr,
        'preis': preis,
        'relevanz': 100 if artikel_nr == ursp_artikel_nr else 50,
        'quelle': 'produktseite'
    }

async def suche_produkt_async(artikel_nr, konfig):
    cache_key = hashlib.md5(artikel_nr.encode()).hexdigest()
    if cache_key in st.session_state.such_cache and (time.time() - st.session_state.cache_zeitstempel.get(cache_key, 0)) < CACHE_TTL:
        return st.session_state.such_cache[cache_key]
    async with aiohttp.ClientSession() as session:
        produkte = await suche_conrad_async(artikel_nr, session)
        if not produkte and konfig.get('fallback_aktiv', True):
            st.toast(f"{UI_TEXTE['searching_web']} {artikel_nr}", icon="🌐")
            fallback = await suche_web_fallback_async(artikel_nr, konfig, session)
            produkte.extend(fallback)
        max_res = konfig.get('max_ergebnisse', 5)
        detail_produkte = []
        for prod in produkte[:max_res]:
            details = await hole_produkt_details_async(prod['url'], artikel_nr, session)
            if details:
                detail_produkte.append(details)
            else:
                detail_produkte.append(prod)
        detail_produkte.sort(key=lambda x: x.get('relevanz', 0), reverse=True)
        st.session_state.such_cache[cache_key] = detail_produkte
        st.session_state.cache_zeitstempel[cache_key] = time.time()
        return detail_produkte

def suche_conrad_nach_artikelnummer(artikel_nr, konfig):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(suche_produkt_async(artikel_nr, konfig))
    finally:
        loop.close()

# ------------------------------------------------------------------------------
# Automatische Massensuche (startet sofort nach Datenübernahme)
# ------------------------------------------------------------------------------
def automatische_suche(df: pd.DataFrame, konfig: Dict, spalten_map: Dict):
    artikel_spalte = spalten_map.get('artikel_nr', 'Artikel-Nr.')
    gesamt = len(df)
    progress_bar = st.progress(0)
    status = st.empty()
    for idx, zeile in df.iterrows():
        status.text(UI_TEXTE["search_progress"].format(idx+1, gesamt))
        if artikel_spalte in zeile and pd.notna(zeile[artikel_spalte]):
            artikel_nr = str(zeile[artikel_spalte]).strip()
            bereinigt = bereinige_artikelnummer(artikel_nr)
            if bereinigt:
                ergebnisse = suche_conrad_nach_artikelnummer(bereinigt, konfig)
                st.session_state.such_ergebnisse[idx] = ergebnisse
            else:
                st.session_state.such_ergebnisse[idx] = []
        else:
            st.session_state.such_ergebnisse[idx] = []
        time.sleep(konfig.get('such_verzoegerung', 0.5))
        progress_bar.progress((idx+1)/gesamt)
    status.text(UI_TEXTE["status_complete"])
    st.toast(UI_TEXTE["auto_search_done"], icon="✅")
    st.session_state.auto_search_triggered = True

# ------------------------------------------------------------------------------
# UI: Sidebar
# ------------------------------------------------------------------------------
def sidebar_konfiguration() -> Dict:
    st.sidebar.image("https://www.conrad.de/medias/logo.svg", width=200)
    st.sidebar.title("⚙️ Einstellungen")
    
    st.sidebar.subheader(UI_TEXTE["ocr_config"])
    tesseract_pfad = st.sidebar.text_input(UI_TEXTE["tesseract_path"], value=DEFAULT_TESSERACT_PATH)
    tessdata_pfad = st.sidebar.text_input(UI_TEXTE["tessdata_path"], value=DEFAULT_TESSDATA_PATH)
    poppler_pfad = st.sidebar.text_input(UI_TEXTE["poppler_path"], value=DEFAULT_POPPLER_PATH)
    
    ocr_sprache = "deu+eng"
    ocr_dpi = 300
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        ocr_sprache = st.sidebar.selectbox(UI_TEXTE["ocr_language"], ["deu+eng", "deu", "eng"])
        ocr_dpi = st.sidebar.selectbox(UI_TEXTE["ocr_dpi"], [200,300,400], index=1)
    
    st.sidebar.subheader(UI_TEXTE["search_settings"])
    such_verzoegerung = st.sidebar.number_input(UI_TEXTE["search_delay"], 0.0, 5.0, DEFAULT_SEARCH_DELAY, 0.5)
    max_ergebnisse = st.sidebar.number_input(UI_TEXTE["max_results"], 1, 10, DEFAULT_MAX_RESULTS)
    
    st.sidebar.subheader(UI_TEXTE["web_search_fallback"])
    fallback_aktiv = st.sidebar.checkbox(UI_TEXTE["enable_fallback"], DEFAULT_ENABLE_FALLBACK)
    anbieter = st.sidebar.selectbox(UI_TEXTE["search_provider"], ["duckduckgo", "serper", "bing"],
                                    format_func=lambda x: UI_TEXTE[f"{x}_fallback" if x!="bing" else "bing_search"])
    api_key = None
    if anbieter == "serper":
        api_key = st.sidebar.text_input(UI_TEXTE["serper_api_key"], type="password", value=SERPER_API_KEY or "")
    elif anbieter == "bing":
        api_key = st.sidebar.text_input(UI_TEXTE["bing_api_key"], type="password", value=BING_API_KEY or "")
    
    st.sidebar.info(UI_TEXTE["cache_info"])
    return {
        'tesseract_pfad': tesseract_pfad, 'tessdata_pfad': tessdata_pfad, 'poppler_pfad': poppler_pfad,
        'ocr_sprache': ocr_sprache, 'ocr_dpi': ocr_dpi, 'such_verzoegerung': such_verzoegerung,
        'max_ergebnisse': max_ergebnisse, 'fallback_aktiv': fallback_aktiv,
        'such_anbieter': anbieter, 'serper_api_key': api_key if anbieter=="serper" else None,
        'bing_api_key': api_key if anbieter=="bing" else None,
    }

# ------------------------------------------------------------------------------
# UI: Ergebnisse anzeigen
# ------------------------------------------------------------------------------
def zeige_suchergebnisse(idx: int, konfig: Dict):
    ergebnisse = st.session_state.such_ergebnisse.get(idx, [])
    if not ergebnisse:
        st.write(UI_TEXTE["no_results"])
        return
    optionen = []
    for res in ergebnisse:
        quelle = res.get('quelle', '')
        quelle_txt = ""
        if quelle == 'conrad_direkt': quelle_txt = f" [{UI_TEXTE['source_conrad']}]"
        elif quelle == 'web_fallback': quelle_txt = f" [{UI_TEXTE['source_fallback']}]"
        elif quelle in ('serper_api','bing_api'): quelle_txt = f" [{UI_TEXTE['source_api']}]"
        optionen.append(f"{res['titel']} | {res['artikel_nr']} | {res['preis'] or '?'}{quelle_txt}")
    auswahl = st.radio(f"{UI_TEXTE['choose_product']} #{idx+1}:", range(len(optionen)), format_func=lambda i: optionen[i], key=f"ausw_{idx}")
    if auswahl is not None:
        ausgew = ergebnisse[auswahl]
        st.session_state.ausgewaehlte_produkte[idx] = ausgew
        col1, col2 = st.columns([3,1])
        col1.write(f"**{UI_TEXTE['product_title']}:** {ausgew['titel']}")
        col1.write(f"**{UI_TEXTE['conrad_number']}:** {ausgew['artikel_nr']}")
        col1.write(f"**{UI_TEXTE['price']}:** {ausgew['preis'] or 'N/A'}")
        col2.markdown(f'<a href="{ausgew["url"]}" target="_blank"><button>{UI_TEXTE["open_new_tab"]}</button></a>', unsafe_allow_html=True)

def erstelle_endgueltigen_dataframe(original_df: pd.DataFrame, spalten_map: Dict) -> pd.DataFrame:
    enddaten = []
    for idx, zeile in original_df.iterrows():
        zeile_dict = zeile.to_dict()
        if idx in st.session_state.ausgewaehlte_produkte:
            sel = st.session_state.ausgewaehlte_produkte[idx]
            zeile_dict['Conrad URL'] = sel['url']
            zeile_dict['Bestell-Nr. (Conrad)'] = sel['artikel_nr']
            zeile_dict['Titel'] = sel['titel']
            zeile_dict['Preis'] = sel['preis'] or ''
            zeile_dict['Status'] = 'Gefunden'
        else:
            zeile_dict['Conrad URL'] = ''
            zeile_dict['Bestell-Nr. (Conrad)'] = ''
            zeile_dict['Titel'] = ''
            zeile_dict['Preis'] = ''
            zeile_dict['Status'] = UI_TEXTE['not_found']
        enddaten.append(zeile_dict)
    return pd.DataFrame(enddaten)

# ------------------------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Conrad Produktfinder", page_icon="🔍", layout="wide")
    st.title(UI_TEXTE["title"])
    st.markdown(f"### {UI_TEXTE['subtitle']}")
    init_session_state()
    konfig = sidebar_konfiguration()
    
    datenquellen = [UI_TEXTE["csv_option"], UI_TEXTE["manual_option"]]
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        datenquellen.append(UI_TEXTE["pdf_option"])
    if BARCODE_SUPPORT or OCR_SUPPORT:
        datenquellen.append(UI_TEXTE["webcam_option"])
    quelle = st.radio(UI_TEXTE["data_source"], datenquellen, horizontal=True)
    
    # -------------------- CSV --------------------
    if quelle == UI_TEXTE["csv_option"]:
        uploaded = st.file_uploader(UI_TEXTE["file_upload"], type=['csv'], help=UI_TEXTE['csv_help'])
        if uploaded:
            df = pd.read_csv(uploaded)
            st.session_state.extrahierte_elemente = df
            st.session_state.auto_search_triggered = False
    
    # -------------------- PDF --------------------
    elif quelle == UI_TEXTE["pdf_option"]:
        uploaded = st.file_uploader(UI_TEXTE["file_upload"], type=['pdf'], help=UI_TEXTE['pdf_help'])
        if uploaded:
            df = pdf_zu_dataframe(uploaded.getvalue(), konfig)
            if df is not None:
                st.session_state.extrahierte_elemente = df
                st.session_state.auto_search_triggered = False
    
    # -------------------- Manuell --------------------
    elif quelle == UI_TEXTE["manual_option"]:
        st.subheader(UI_TEXTE["manual_entry"])
        anzahl = st.number_input(UI_TEXTE["num_products_manual"], 1, 50, 3)
        produkte = []
        for i in range(anzahl):
            with st.expander(f"{UI_TEXTE['product']} {i+1}"):
                col1, col2 = st.columns(2)
                menge = col1.number_input(f"{UI_TEXTE['quantity_abbr']} {i+1}", 1, 999, 1, key=f"menge_{i}")
                art = col1.text_input(f"{UI_TEXTE['article_no_abbr']} {i+1}", key=f"art_{i}")
                beschr = col2.text_input(f"{UI_TEXTE['description_abbr']} {i+1}", key=f"beschr_{i}")
                if art:
                    bereinigt = bereinige_artikelnummer(art)
                    if bereinigt:
                        produkte.append({'Menge': menge, 'Artikel-Nr.': bereinigt, 'Beschreibung': beschr})
        if produkte and st.button(UI_TEXTE["take_over"]):
            st.session_state.extrahierte_elemente = pd.DataFrame(produkte)
            st.session_state.auto_search_triggered = False
    
    # -------------------- Webcam --------------------
    elif quelle == UI_TEXTE["webcam_option"]:
        st.subheader(UI_TEXTE["webcam_scan"])
        st.markdown(UI_TEXTE["webcam_help"])
        bild = st.camera_input("📸 Kamera")
        if bild:
            img = Image.open(bild)
            artikel_nr = erkenne_barcode_im_bild(img)
            if not artikel_nr:
                artikel_nr = erkenne_artikelnummer_mit_ocr(img, konfig)
            if artikel_nr:
                st.success(UI_TEXTE["scanned_article"].format(artikel_nr))
                if st.button(UI_TEXTE["add_to_list"]):
                    neue_zeile = pd.DataFrame([{'Menge': 1, 'Artikel-Nr.': artikel_nr, 'Beschreibung': ''}])
                    if st.session_state.extrahierte_elemente is None:
                        st.session_state.extrahierte_elemente = neue_zeile
                    else:
                        st.session_state.extrahierte_elemente = pd.concat([st.session_state.extrahierte_elemente, neue_zeile], ignore_index=True)
                    st.session_state.auto_search_triggered = False
                    st.rerun()
            else:
                st.warning("Keine gültige Conrad-Artikelnummer erkannt.")
    
    # -------------------- Verarbeitung der extrahierten Daten --------------------
    if st.session_state.extrahierte_elemente is not None:
        df = st.session_state.extrahierte_elemente
        st.subheader(UI_TEXTE["preview_data"])
        st.dataframe(df, use_container_width=True)
        
        # Spaltenzuordnung (nur bei CSV sinnvoll, sonst Standard)
        if quelle == UI_TEXTE["csv_option"]:
            st.subheader(UI_TEXTE["column_mapping"])
            col1, col2, col3 = st.columns(3)
            menge_map = col1.selectbox(UI_TEXTE["quantity"], [''] + list(df.columns), key="menge_map_csv")
            artikel_map = col2.selectbox(UI_TEXTE["article_no"], [''] + list(df.columns), key="artikel_map_csv")
            beschr_map = col3.selectbox(UI_TEXTE["description"], [''] + list(df.columns), key="beschr_map_csv")
            spalten_zuordnung = {
                'menge': menge_map if menge_map else 'Menge',
                'artikel_nr': artikel_map if artikel_map else 'Artikel-Nr.',
                'beschreibung': beschr_map if beschr_map else 'Beschreibung'
            }
            if st.button(UI_TEXTE["apply_mapping"]):
                st.session_state.spalten_zuordnung = spalten_zuordnung
                st.success("Zuordnung übernommen")
        else:
            st.session_state.spalten_zuordnung = {
                'menge': 'Menge',
                'artikel_nr': 'Artikel-Nr.',
                'beschreibung': 'Beschreibung'
            }
            if quelle != UI_TEXTE["csv_option"]:
                st.info("Spalten sind bereits korrekt zugeordnet.")
        
        # Automatische Suche starten (einmalig nach Laden/Zuordnung)
        if st.session_state.spalten_zuordnung and not st.session_state.auto_search_triggered:
            with st.spinner("🔍 Automatische Suche läuft für alle Artikel..."):
                automatische_suche(df, konfig, st.session_state.spalten_zuordnung)
        
        # Ergebnisse anzeigen
        if st.session_state.such_ergebnisse:
            for idx, zeile in df.iterrows():
                artikel_nr = zeile.get(st.session_state.spalten_zuordnung.get('artikel_nr', 'Artikel-Nr.'), '?')
                with st.expander(f"Position {idx+1}: Artikelnr. {artikel_nr}"):
                    st.write(f"**Menge:** {zeile.get(st.session_state.spalten_zuordnung.get('menge', 'Menge'), '1')}")
                    if idx in st.session_state.such_ergebnisse:
                        zeige_suchergebnisse(idx, konfig)
                    else:
                        st.info("Suche läuft oder noch nicht gestartet.")
        
        # Finale Auswahl und Download
        if st.session_state.ausgewaehlte_produkte:
            st.subheader(UI_TEXTE["final_selection"])
            final_df = erstelle_endgueltigen_dataframe(df, st.session_state.spalten_zuordnung)
            st.dataframe(final_df, use_container_width=True)
            csv = final_df.to_csv(index=False, encoding='utf-8-sig')
            b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
            st.markdown(f'<a href="data:file/csv;base64,{b64}" download="conrad_ergebnisse.csv">{UI_TEXTE["download_csv"]}</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
