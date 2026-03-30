# app.py - Conrad Produktfinder (Optimierte Version mit Artikelnummer-Fokus)
# Author: Amir Mobasheraghdam
# Date: 2026-03-30
# Version: 3.0
# Description: Streamlit-Anwendung zum Extrahieren von Conrad Artikelnummern
#              aus CSV/PDF und Suchen der entsprechenden Produkte auf conrad.de.
#              Inkl. OCR-Unterstützung, Web-Fallback-Suche und asynchronen Anfragen.

import asyncio
import aiohttp
import base64
import hashlib
import json
import os
import re
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, quote

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import requests

# ------------------------------------------------------------------------------
# OCR-Bibliotheken (optional)
# ------------------------------------------------------------------------------
try:
    import pytesseract
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

try:
    import pdf2image
    PDF2IMAGE_SUPPORT = True
except ImportError:
    PDF2IMAGE_SUPPORT = False

# ------------------------------------------------------------------------------
# Konfiguration (kann via Umgebungsvariablen überschrieben werden)
# ------------------------------------------------------------------------------
DEFAULT_TESSERACT_PATH = os.getenv("TESSERACT_PATH", "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
DEFAULT_TESSDATA_PATH = os.getenv("TESSDATA_PATH", "C:\\Program Files\\Tesseract-OCR\\tessdata")
DEFAULT_POPPLER_PATH = os.getenv("POPPLER_PATH", "C:\\poppler\\poppler-23.11.0\\Library\\bin")

DEFAULT_SEARCH_DELAY = float(os.getenv("SEARCH_DELAY", "2.0"))
DEFAULT_MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
DEFAULT_ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
DEFAULT_SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # duckduckgo, serper, bing

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # Cache-Gültigkeit in Sekunden

# ------------------------------------------------------------------------------
# Deutsche UI-Texte (zentralisiert)
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
    "searching_web": "Keine Conrad-Treffer gefunden – starte Websuche...",
    "serper_api_key": "Serper.dev API-Schlüssel",
    "bing_api_key": "Bing Web Search API-Schlüssel",
    "search_provider": "Suchanbieter für Fallback",
    "duckduckgo_fallback": "DuckDuckGo (kein API-Schlüssel nötig)",
    "serper_dev": "Serper.dev (Google Search)",
    "bing_search": "Bing Web Search",
    "use_async": "Asynchrone Suche (schneller)",
    "cache_info": "Ergebnisse werden zwischengespeichert"
}

# ------------------------------------------------------------------------------
# Session State Initialisierung
# ------------------------------------------------------------------------------
def init_session_state():
    """Initialisiert alle Session-State-Variablen."""
    if 'extracted_items' not in st.session_state:
        st.session_state.extracted_items = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = {}
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = {}
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'search_cache' not in st.session_state:
        st.session_state.search_cache = {}
    if 'cache_timestamps' not in st.session_state:
        st.session_state.cache_timestamps = {}

# ------------------------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------------------------
def get_cache_key(article_no: str) -> str:
    """Erstellt einen Cache-Schlüssel für eine Artikelnummer."""
    return hashlib.md5(article_no.encode()).hexdigest()

def is_cache_valid(key: str) -> bool:
    """Prüft, ob ein Cache-Eintrag noch gültig ist."""
    if key not in st.session_state.search_cache:
        return False
    timestamp = st.session_state.cache_timestamps.get(key, 0)
    return (time.time() - timestamp) < CACHE_TTL

def set_cache(key: str, value: Any):
    """Speichert einen Wert im Cache mit aktuellem Zeitstempel."""
    st.session_state.search_cache[key] = value
    st.session_state.cache_timestamps[key] = time.time()

def clean_article_number(article_no: str) -> Optional[str]:
    """Bereinigt eine Artikelnummer: entfernt Nicht-Ziffern, kürzt Suffixe."""
    cleaned = re.sub(r'[^\d-]', '', article_no)
    if '-' in cleaned:
        cleaned = cleaned.split('-')[0]
    cleaned = re.sub(r'\s+', '', cleaned)
    if cleaned.isdigit() and 5 <= len(cleaned) <= 8:
        return cleaned
    return None

def setup_ocr_environment(tesseract_path: str = None, tessdata_path: str = None) -> Tuple[bool, str]:
    """Richtet die OCR-Umgebung ein und gibt (Erfolg, Nachricht) zurück."""
    if not OCR_SUPPORT:
        return False, "OCR-Bibliotheken nicht installiert."
    try:
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            # Versuche, Tesseract über PATH zu finden
            try:
                pytesseract.get_tesseract_version()
            except pytesseract.TesseractNotFoundError:
                return False, "Tesseract nicht gefunden. Bitte Pfad angeben oder installieren."
        if tessdata_path and os.path.exists(tessdata_path):
            os.environ['TESSDATA_PREFIX'] = tessdata_path
        return True, "OCR erfolgreich konfiguriert."
    except Exception as e:
        return False, f"OCR-Konfigurationsfehler: {e}"

# ------------------------------------------------------------------------------
# PDF-Verarbeitung mit OCR
# ------------------------------------------------------------------------------
def extract_text_from_pdf(pdf_bytes: bytes, config: Dict[str, Any]) -> str:
    """Extrahiert Text aus einer PDF-Datei mittels OCR."""
    try:
        success, msg = setup_ocr_environment(config.get('tesseract_path'), config.get('tessdata_path'))
        if not success:
            st.error(msg)
            return ""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            poppler_path = config.get('poppler_path')
            images = pdf2image.convert_from_path(
                tmp_path,
                dpi=config.get('ocr_dpi', 300),
                poppler_path=poppler_path if poppler_path and os.path.exists(poppler_path) else None
            )
        finally:
            os.unlink(tmp_path)

        if not images:
            st.error("Keine Seiten aus PDF extrahiert.")
            return ""

        all_text = ""
        progress_bar = st.progress(0)
        tesseract_config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        lang = config.get('ocr_language', 'deu+eng')

        for idx, img in enumerate(images):
            st.write(f"Verarbeite Seite {idx+1}/{len(images)}...")
            try:
                img = img.convert('L')  # Graustufen
                text = pytesseract.image_to_string(img, lang=lang, config=tesseract_config)
                all_text += text + "\n\n"
            except Exception as e:
                st.warning(f"OCR-Fehler auf Seite {idx+1}: {e} – verwende Fallback (Englisch).")
                try:
                    text = pytesseract.image_to_string(img, lang='eng')
                    all_text += text + "\n\n"
                except Exception:
                    st.error(f"OCR komplett fehlgeschlagen auf Seite {idx+1}.")
            progress_bar.progress((idx+1) / len(images))
        return all_text
    except Exception as e:
        st.error(f"Fehler bei der PDF-Verarbeitung: {e}")
        return ""

def extract_article_numbers_from_text(text: str) -> List[str]:
    """Extrahiert Conrad Artikelnummern aus OCR-Text."""
    article_numbers = []
    patterns = [
        r'bestell[.-]?nr\.?\s*:?\s*([0-9]+)\s*-?\s*[0-9]*',
        r'bestell[.-]?nr\.?\s*:?\s*([0-9]+[-\s]*[0-9]*)',
        r'bestellnummer\s*:?\s*([0-9]+)',
        r'artikel[.-]?nr\.?\s*:?\s*([0-9]+)',
    ]
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        for pattern in patterns:
            matches = re.finditer(pattern, line_clean, re.IGNORECASE)
            for match in matches:
                raw = match.group(1)
                cleaned = re.sub(r'[\s-]', '', raw)
                if cleaned.isdigit() and 5 <= len(cleaned) <= 8 and cleaned not in article_numbers:
                    article_numbers.append(cleaned)
    return article_numbers

def pdf_to_df(pdf_bytes: bytes, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Wandelt PDF in DataFrame mit Artikelnummern um."""
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
        items = [{'quantity': 1, 'article_no': art, 'description': ""} for art in article_numbers]
        df = pd.DataFrame(items)
        st.success(f"**Erfolgreich {len(df)} Artikelnummern extrahiert!**")
        return df
    except Exception as e:
        st.error(f"Fehler bei PDF-Verarbeitung: {e}")
        return None

# ------------------------------------------------------------------------------
# Suchfunktionen (asynchron)
# ------------------------------------------------------------------------------
async def fetch_html(session: aiohttp.ClientSession, url: str, headers: Dict) -> Optional[str]:
    """Holt asynchron den HTML-Inhalt einer URL."""
    try:
        async with session.get(url, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None

async def search_conrad_async(article_no: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Sucht asynchron auf conrad.de nach einer Artikelnummer."""
    search_url = f"https://www.conrad.de/de/search.html?search={article_no}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    html = await fetch_html(session, search_url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    link_pattern = re.compile(r'/de/p/[\w-]+-\d+\.html', re.IGNORECASE)
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if link_pattern.search(href):
            full_url = urljoin('https://www.conrad.de', href)
            if full_url not in [p['url'] for p in products]:
                products.append({
                    'url': full_url,
                    'title': a_tag.get_text(strip=True) or "Produktseite",
                    'article_no': article_no,
                    'price': None,
                    'relevance_score': 100,
                    'source': 'conrad_direct'
                })
    return products

async def search_duckduckgo_async(article_no: str, session: aiohttp.ClientSession) -> List[Dict]:
    """DuckDuckGo-Suche (HTML-Scraping)."""
    query = f"site:conrad.de {article_no} Bestell-Nr"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
    }
    html = await fetch_html(session, url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    link_pattern = re.compile(r'conrad\.de/de/p/[\w-]+-\d+\.html', re.IGNORECASE)
    for link in soup.find_all('a', href=True, class_='result__url'):
        href = link.get('href', '')
        if link_pattern.search(href):
            full_url = href if href.startswith('http') else f'https:{href}'
            products.append({
                'url': full_url,
                'title': "Conrad Produkt (via Web-Suche)",
                'article_no': article_no,
                'price': None,
                'relevance_score': 90,
                'source': 'web_fallback'
            })
    return products[:5]

async def search_serper_async(article_no: str, api_key: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Serper.dev Google Search API."""
    query = f"site:conrad.de {article_no} Bestell-Nr"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {"q": query, "num": 5}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                products = []
                for result in data.get('organic', []):
                    link = result.get('link', '')
                    if re.search(r'conrad\.de/de/p/[\w-]+-\d+\.html', link, re.IGNORECASE):
                        products.append({
                            'url': link,
                            'title': result.get('title', 'Conrad Produkt'),
                            'article_no': article_no,
                            'price': None,
                            'relevance_score': 95,
                            'source': 'serper_api'
                        })
                return products
    except Exception:
        pass
    return []

async def search_bing_async(article_no: str, api_key: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Bing Web Search API."""
    query = f"site:conrad.de {article_no} Bestell-Nr"
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {'Ocp-Apim-Subscription-Key': api_key}
    params = {'q': query, 'count': 5, 'responseFilter': 'Webpages'}
    try:
        async with session.get(url, headers=headers, params=params, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                products = []
                for result in data.get('webPages', {}).get('value', []):
                    link = result.get('url', '')
                    if re.search(r'conrad\.de/de/p/[\w-]+-\d+\.html', link, re.IGNORECASE):
                        products.append({
                            'url': link,
                            'title': result.get('name', 'Conrad Produkt'),
                            'article_no': article_no,
                            'price': None,
                            'relevance_score': 95,
                            'source': 'bing_api'
                        })
                return products
    except Exception:
        pass
    return []

async def search_web_fallback_async(article_no: str, config: Dict[str, Any], session: aiohttp.ClientSession) -> List[Dict]:
    """Fallback-Websuche je nach gewähltem Anbieter."""
    provider = config.get('search_provider', 'duckduckgo')
    if provider == 'serper' and config.get('serper_api_key'):
        return await search_serper_async(article_no, config['serper_api_key'], session)
    elif provider == 'bing' and config.get('bing_api_key'):
        return await search_bing_async(article_no, config['bing_api_key'], session)
    else:
        return await search_duckduckgo_async(article_no, session)

def fetch_product_details(product_url: str, original_article_no: str) -> Optional[Dict]:
    """Ruft detaillierte Produktinformationen von der Produktseite ab."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(product_url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Titel
        title = "Titel nicht gefunden"
        for selector in ['h1', '.product-title', '.product__title', '[class*="title"]']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break

        # Artikelnummer
        article_no = original_article_no
        page_text = soup.get_text()
        patterns = [r'Bestell-Nr\.\s*([A-Z0-9\-]+)', r'Artikel-Nr\.\s*([A-Z0-9\-]+)']
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                article_no = match.group(1)
                break

        # Preis
        price = None
        for selector in ['.price__value', '.product__price', '.current-price', '[class*="price"]']:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True)
                price_match = re.search(r'[\d,.]+\s*€', price_text)
                if price_match:
                    price = price_match.group(0)
                    break

        relevance = 100 if original_article_no == article_no else 50
        return {
            'url': product_url,
            'title': title,
            'article_no': article_no,
            'price': price,
            'relevance_score': relevance,
            'source': 'conrad_product_page'
        }
    except Exception:
        return None

async def search_product_async(article_no: str, config: Dict[str, Any]) -> List[Dict]:
    """Hauptsuchfunktion: zuerst Conrad, dann Fallback, dann Details."""
    cache_key = get_cache_key(article_no)
    if is_cache_valid(cache_key):
        return st.session_state.search_cache[cache_key]

    async with aiohttp.ClientSession() as session:
        # Conrad-Suche
        products = await search_conrad_async(article_no, session)
        # Fallback, falls keine Ergebnisse
        if not products and config.get('enable_fallback', True):
            st.info(f"{UI_TEXTS['searching_web']} {article_no}")
            fallback = await search_web_fallback_async(article_no, config, session)
            products.extend(fallback)

        # Detaillierte Informationen abrufen (max. 5)
        max_results = config.get('max_results', 5)
        detailed = []
        for prod in products[:max_results]:
            details = fetch_product_details(prod['url'], article_no)
            if details:
                # Quelle aus der ursprünglichen Suche übernehmen, falls nicht gesetzt
                if 'source' in prod and details.get('source') == 'conrad_product_page':
                    details['source'] = prod['source']
                detailed.append(details)
            else:
                detailed.append(prod)

        # Nach Relevanz sortieren
        detailed.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        set_cache(cache_key, detailed)
        return detailed

def search_conrad_by_article_number(article_no: str, config: Dict[str, Any]) -> List[Dict]:
    """Synchroner Wrapper für asynchrone Suche."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(search_product_async(article_no, config))
    finally:
        loop.close()

# ------------------------------------------------------------------------------
# UI-Komponenten
# ------------------------------------------------------------------------------
def setup_sidebar() -> Dict[str, Any]:
    """Sidebar mit Konfigurationseinstellungen."""
    st.sidebar.title("Einstellungen")

    # OCR-Konfiguration
    st.sidebar.subheader(UI_TEXTS["ocr_config"])
    tesseract_path = st.sidebar.text_input(
        UI_TEXTS["tesseract_path"],
        value=DEFAULT_TESSERACT_PATH,
        help="Vollständiger Pfad zur tesseract.exe"
    )
    tessdata_path = st.sidebar.text_input(
        UI_TEXTS["tessdata_path"],
        value=DEFAULT_TESSDATA_PATH,
        help="Pfad zum tessdata-Ordner"
    )
    poppler_path = st.sidebar.text_input(
        UI_TEXTS["poppler_path"],
        value=DEFAULT_POPPLER_PATH,
        help="Pfad zu Poppler (enthält pdftoppm.exe)"
    )

    # OCR-Einstellungen (nur wenn Bibliotheken vorhanden)
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        ocr_language = st.sidebar.selectbox(
            "OCR-Sprache", ["deu+eng", "deu", "eng"], index=0
        )
        ocr_dpi = st.sidebar.selectbox(
            "DPI für OCR", [200, 250, 300, 350, 400], index=2
        )
    else:
        ocr_language = "deu+eng"
        ocr_dpi = 300

    # Such-Einstellungen
    st.sidebar.subheader(UI_TEXTS["search_settings"])
    search_delay = st.sidebar.number_input(
        UI_TEXTS["search_delay"],
        min_value=0.5, max_value=10.0, value=DEFAULT_SEARCH_DELAY, step=0.5
    )
    max_results = st.sidebar.number_input(
        UI_TEXTS["max_results"], min_value=1, max_value=10, value=DEFAULT_MAX_RESULTS
    )
    use_async = st.sidebar.checkbox(UI_TEXTS["use_async"], value=True, help="Aktiviert parallele Anfragen für schnellere Suche.")

    # Web-Fallback
    st.sidebar.subheader(UI_TEXTS["web_search_fallback"])
    enable_fallback = st.sidebar.checkbox(UI_TEXTS["enable_fallback"], value=DEFAULT_ENABLE_FALLBACK)

    provider_options = ["duckduckgo", "serper", "bing"]
    provider_labels = [UI_TEXTS["duckduckgo_fallback"], UI_TEXTS["serper_dev"], UI_TEXTS["bing_search"]]
    provider_index = provider_options.index(DEFAULT_SEARCH_PROVIDER) if DEFAULT_SEARCH_PROVIDER in provider_options else 0
    search_provider = st.sidebar.selectbox(
        UI_TEXTS["search_provider"],
        provider_options,
        format_func=lambda x: provider_labels[provider_options.index(x)],
        index=provider_index
    )

    api_key = None
    if search_provider == "serper":
        api_key = st.sidebar.text_input(UI_TEXTS["serper_api_key"], type="password", value=SERPER_API_KEY or "")
    elif search_provider == "bing":
        api_key = st.sidebar.text_input(UI_TEXTS["bing_api_key"], type="password", value=BING_API_KEY or "")

    st.sidebar.info(UI_TEXTS["cache_info"])

    return {
        'tesseract_path': tesseract_path,
        'tessdata_path': tessdata_path,
        'poppler_path': poppler_path,
        'ocr_language': ocr_language,
        'ocr_dpi': ocr_dpi,
        'search_delay': search_delay,
        'max_results': max_results,
        'use_async': use_async,
        'enable_fallback': enable_fallback,
        'search_provider': search_provider,
        'serper_api_key': api_key if search_provider == "serper" else None,
        'bing_api_key': api_key if search_provider == "bing" else None,
    }

def manual_data_entry():
    """Manuelle Produkteingabe."""
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
                cleaned = clean_article_number(article_no)
                if cleaned:
                    products.append({
                        'quantity': quantity,
                        'article_no': cleaned,
                        'description': description if description else ""
                    })
                else:
                    st.warning(f"Ungültige Artikelnummer: {article_no}")
    if products and st.button("Produkte übernehmen"):
        df = pd.DataFrame(products)
        st.session_state.extracted_items = df
        st.success(f"{len(products)} Produkte übernommen")

def perform_single_search(idx: int, row: pd.Series, config: Dict[str, Any], column_mapping: Dict[str, str]):
    """Sucht eine einzelne Position."""
    article_col = column_mapping.get('article_no', 'article_no')
    if article_col not in row or pd.isna(row[article_col]) or not row[article_col]:
        st.error("Keine Artikelnummer für diese Position verfügbar")
        return
    article_no = str(row[article_col]).strip()
    cleaned = clean_article_number(article_no)
    if not cleaned:
        st.error(f"Ungültige Artikelnummer: {article_no}")
        return
    with st.spinner(f"Suche nach {cleaned} ..."):
        candidates = search_conrad_by_article_number(cleaned, config)
        st.session_state.search_results[idx] = candidates
        if not candidates:
            st.warning(f"{UI_TEXTS['no_results_for']} {cleaned}")

def perform_bulk_search(df: pd.DataFrame, config: Dict[str, Any], column_mapping: Dict[str, str]):
    """Massen-Suche für alle Zeilen."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    article_col = column_mapping.get('article_no', 'article_no')
    total = len(df)
    for idx, row in df.iterrows():
        status_text.text(f"Suche Position {idx+1}/{total}...")
        if article_col in row and pd.notna(row[article_col]) and row[article_col]:
            article_no = str(row[article_col]).strip()
            cleaned = clean_article_number(article_no)
            if cleaned:
                candidates = search_conrad_by_article_number(cleaned, config)
                st.session_state.search_results[idx] = candidates
            else:
                st.session_state.search_results[idx] = []
        else:
            st.session_state.search_results[idx] = []
        time.sleep(config['search_delay'])
        progress_bar.progress((idx+1) / total)
    status_text.text("Suche abgeschlossen")

def display_search_results(idx: int, config: Dict[str, Any]):
    """Zeigt die Suchergebnisse für eine Zeile an."""
    results = st.session_state.search_results.get(idx, [])
    if not results:
        st.write(UI_TEXTS["no_results"])
        return
    options = []
    for res in results:
        source_info = ""
        if res.get('source') == 'web_fallback':
            source_info = " [Web-Fallback]"
        elif res.get('source') in ('serper_api', 'bing_api'):
            source_info = f" [{res['source']}]"
        option_text = f"{res['title']} | {res['article_no']} | {res['price'] or 'Preis unbekannt'}{source_info}"
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
            if selected.get('source') != 'conrad_direct':
                st.write(f"**Quelle:** {selected['source']}")
        with col2:
            st.markdown(
                f'<a href="{selected["url"]}" target="_blank">'
                f'<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">'
                f'{UI_TEXTS["open_new_tab"]}'
                f'</button></a>',
                unsafe_allow_html=True
            )

def create_final_dataframe(original_df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    """Erstellt den finalen DataFrame mit ausgewählten Produkten."""
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

# ------------------------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Conrad Produktfinder", page_icon="🔍", layout="wide")
    st.title(UI_TEXTS["title"])
    init_session_state()

    config = setup_sidebar()

    # Datenquelle auswählen
    upload_options = ["CSV hochladen", "Manuelle Eingabe"]
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        upload_options.insert(1, "PDF hochladen")
    upload_option = st.radio("Datenquelle wählen:", upload_options)

    if upload_option == "CSV hochladen":
        uploaded_file = st.file_uploader(UI_TEXTS["file_upload"], type=['csv'], help=UI_TEXTS['csv_help'])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.extracted_items = df
    elif upload_option == "PDF hochladen" and OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        uploaded_file = st.file_uploader(UI_TEXTS["file_upload"], type=['pdf'], help=UI_TEXTS['pdf_help'])
        if uploaded_file is not None:
            df = pdf_to_df(uploaded_file.getvalue(), config)
            if df is not None:
                st.session_state.extracted_items = df
    elif upload_option == "Manuelle Eingabe":
        manual_data_entry()

    # Verarbeitung der extrahierten Daten
    if st.session_state.extracted_items is not None:
        df = st.session_state.extracted_items
        st.subheader(UI_TEXTS["preview_data"])
        st.dataframe(df)
        st.write(f"{len(df)} {UI_TEXTS['items_found']}")

        # Spaltenzuordnung
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
