# app.py - Conrad Produktfinder (Vereinfachte Version mit Artikelnummer-Fokus)
# Author: Amir Mobasheraghdam
# Date: 2025-03-14
# Version: 2.0
# Description: Streamlit-Anwendung zum Extrahieren von Conrad Artikelnummern
#              aus CSV/PDF und Suchen der entsprechenden Produkte auf conrad.de.
#              Inkl. OCR-Unterstützung und Web-Fallback-Suche.

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tempfile
import os
import time
import re
import base64
from urllib.parse import urljoin, quote
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple

# Versuche OCR-Bibliotheken zu importieren
try:
    import pytesseract
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False
    st.warning("OCR-Unterstützung deaktiviert: pytesseract nicht installiert")

try:
    import pdf2image
    PDF2IMAGE_SUPPORT = True
except ImportError:
    PDF2IMAGE_SUPPORT = False
    st.warning("PDF2Image-Unterstützung deaktiviert: pdf2image nicht installiert")

# ------------------------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Conrad Produktfinder",
    page_icon="🔍",
    layout="wide"
)

# Session State Initialisierung
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
# Hilfsfunktionen
# ------------------------------------------------------------------------------
def setup_sidebar() -> Dict[str, Any]:
    """Sidebar mit Konfigurationsoptionen"""
    st.sidebar.title("Einstellungen")
    
    # OCR-Konfiguration
    st.sidebar.subheader(UI_TEXTS["ocr_config"])
    
    # Tesseract Pfad-Einstellung
    default_tesseract_path = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    tesseract_path = st.sidebar.text_input(
        UI_TEXTS["tesseract_path"],
        value=default_tesseract_path,
        help="Vollständiger Pfad zur tesseract.exe"
    )
    
    # Tessdata Pfad-Einstellung
    default_tessdata_path = "C:\\Program Files\\Tesseract-OCR\\tessdata"
    tessdata_path = st.sidebar.text_input(
        UI_TEXTS["tessdata_path"],
        value=default_tessdata_path,
        help="Pfad zum tessdata-Ordner (enthält .traineddata Dateien)"
    )
    
    # Poppler Pfad-Einstellung
    default_poppler_path = "C:\\poppler\\poppler-23.11.0\\Library\\bin"
    poppler_path = st.sidebar.text_input(
        UI_TEXTS["poppler_path"],
        value=default_poppler_path,
        help="Pfad zu Poppler (enthält pdftoppm.exe)"
    )
    
    # OCR-Einstellungen nur anzeigen wenn verfügbar
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        st.sidebar.subheader("OCR-Einstellungen")
        
        ocr_language = st.sidebar.selectbox(
            "OCR-Sprache",
            ["deu+eng", "deu", "eng"],
            index=0,
            help="deu+eng für beste Ergebnisse mit deutschen PDFs"
        )
        
        ocr_dpi = st.sidebar.selectbox(
            "DPI für OCR",
            [200, 250, 300, 350, 400],
            index=2,
            help="Höhere DPI = bessere Qualität, aber langsamer"
        )
    else:
        ocr_language = "deu+eng"
        ocr_dpi = 300
    
    st.sidebar.subheader(UI_TEXTS["search_settings"])
    search_delay = st.sidebar.number_input(
        UI_TEXTS["search_delay"],
        min_value=0.5,
        max_value=10.0,
        value=2.0,
        step=0.5
    )
    max_results = st.sidebar.number_input(
        UI_TEXTS["max_results"],
        min_value=1,
        max_value=10,
        value=5
    )
    
    # Web Search Fallback Einstellungen
    st.sidebar.subheader(UI_TEXTS["web_search_fallback"])
    
    enable_fallback = st.sidebar.checkbox(
        UI_TEXTS["enable_fallback"],
        value=True,
        help="Websuche aktivieren wenn Conrad-Suche keine Ergebnisse liefert"
    )
    
    search_provider = st.sidebar.selectbox(
        UI_TEXTS["search_provider"],
        [UI_TEXTS["duckduckgo_fallback"], UI_TEXTS["serper_dev"], UI_TEXTS["bing_search"]],
        index=0,
        help="Suchanbieter für Fallback-Suche"
    )
    
    api_key = None
    if search_provider == UI_TEXTS["serper_dev"]:
        api_key = st.sidebar.text_input(
            UI_TEXTS["serper_api_key"],
            type="password",
            help="Kostenloser API-Schlüssel von serper.dev"
        )
    elif search_provider == UI_TEXTS["bing_search"]:
        api_key = st.sidebar.text_input(
            UI_TEXTS["bing_api_key"],
            type="password",
            help="Bing Web Search API-Schlüssel von Azure"
        )
    
    return {
        'tesseract_path': tesseract_path,
        'tessdata_path': tessdata_path,
        'poppler_path': poppler_path,
        'ocr_language': ocr_language,
        'ocr_dpi': ocr_dpi,
        'search_delay': search_delay,
        'max_results': max_results,
        'enable_fallback': enable_fallback,
        'search_provider': search_provider,
        'api_key': api_key
    }

def setup_ocr_environment(config: Dict[str, Any]) -> Tuple[bool, str]:
    """OCR-Umgebung einrichten und validieren"""
    if not OCR_SUPPORT:
        return False, "OCR-Unterstützung nicht verfügbar"
    
    try:
        # Tesseract Pfad setzen
        tesseract_path = config.get('tesseract_path', '')
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            return False, f"Tesseract nicht gefunden: {tesseract_path}"
        
        # Tessdata Pfad setzen
        tessdata_path = config.get('tessdata_path', '')
        if tessdata_path and os.path.exists(tessdata_path):
            os.environ['TESSDATA_PREFIX'] = tessdata_path
        
        return True, "OCR erfolgreich konfiguriert"
        
    except Exception as e:
        return False, f"OCR-Konfigurationsfehler: {str(e)}"

def extract_text_with_ocr(pdf_file, config: Dict[str, Any]) -> str:
    """Extrahiere Text aus PDF mit OCR"""
    try:
        # OCR-Umgebung einrichten
        success, message = setup_ocr_environment(config)
        if not success:
            st.error(f"OCR-Fehler: {message}")
            return ""
        
        # Temporäre Datei speichern
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        # Poppler Pfad setzen
        poppler_path = config.get('poppler_path', '')
        
        tesseract_config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        
        if poppler_path and os.path.exists(poppler_path):
            # PDF zu Bildern konvertieren mit Poppler-Pfad
            images = pdf2image.convert_from_path(
                tmp_path, 
                dpi=config['ocr_dpi'],
                poppler_path=poppler_path
            )
        else:
            # Ohne speziellen Poppler-Pfad
            images = pdf2image.convert_from_path(tmp_path, config['ocr_dpi'])
        
        # Aufräumen
        os.unlink(tmp_path)
        
        if not images:
            st.error("Keine Bilder aus PDF extrahiert")
            return ""
        
        # OCR auf jedes Bild anwenden
        all_text = ""
        progress_bar = st.progress(0)
        
        for idx, image in enumerate(images):
            st.write(f"Verarbeite Seite {idx + 1}/{len(images)}...")
            
            try:
                # Bild für OCR vorverarbeiten
                image = image.convert('L')  # Zu Graustufen
                
                # OCR mit optimierter Konfiguration
                text = pytesseract.image_to_string(
                    image, 
                    lang=config['ocr_language'],
                    config=tesseract_config
                )
                all_text += text + "\n\n"
                
            except Exception as e:
                st.error(f"OCR-Fehler auf Seite {idx + 1}: {str(e)}")
                # Fallback: Einfache Konfiguration
                try:
                    text = pytesseract.image_to_string(image, lang='eng')
                    all_text += text + "\n\n"
                    st.warning(f"Seite {idx + 1} mit Fallback verarbeitet")
                except:
                    st.error(f"OCR komplett fehlgeschlagen auf Seite {idx + 1}")
            
            progress_bar.progress((idx + 1) / len(images))
        
        return all_text
        
    except Exception as e:
        st.error(f"OCR-Verarbeitungsfehler: {str(e)}")
        return ""

def extract_article_numbers_from_pdf(text: str) -> List[str]:
    """
    Extrahiert Conrad Artikelnummern aus OCR-Text
    Fokus NUR auf Bestell-Nr., ignoriert Beschreibungen
    """
    article_numbers = []
    
    # Robuste Regex für Bestell-Nr. Varianten
    patterns = [
        r'bestell.?nr\.?\s*:?\s*([0-9]+)\s*-?\s*[0-9]*',  # Bestell-Nr.: 1667360 - 62
        r'bestell.?nr\.?\s*:?\s*([0-9]+[-\s]*[0-9]*)',    # Bestell-Nr. 1234567-62
        r'bestellnummer\s*:?\s*([0-9]+)',                 # Bestellnummer 1234567
        r'artikel.?nr\.?\s*:?\s*([0-9]+)',                # Artikel-Nr. 1234567
    ]
    
    lines = text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        for pattern in patterns:
            matches = re.finditer(pattern, line_clean, re.IGNORECASE)
            for match in matches:
                article_no = match.group(1)
                # Suffix entfernen und bereinigen
                if '-' in article_no:
                    article_no = article_no.split('-')[0]
                article_no = re.sub(r'\s+', '', article_no)
                
                # Nur gültige Artikelnummern hinzufügen (typisch 6-7 Stellen)
                if article_no.isdigit() and 5 <= len(article_no) <= 8:
                    if article_no not in article_numbers:
                        article_numbers.append(article_no)
    
    return article_numbers

def pdf_to_df_simple(pdf_file, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Konvertiere PDF zu DataFrame - NUR Artikelnummern"""
    st.info(UI_TEXTS["processing_pdf"])
    
    try:
        # OCR Text extrahieren
        text = extract_text_with_ocr(pdf_file, config)
        
        if not text.strip():
            st.error("Konnte keinen Text aus PDF extrahieren.")
            return None
        
        # NUR Artikelnummern extrahieren
        article_numbers = extract_article_numbers_from_pdf(text)
        
        if not article_numbers:
            st.warning("Keine Conrad Artikelnummern im PDF gefunden.")
            return None
        
        # DataFrame erstellen
        items = []
        for art_no in article_numbers:
            items.append({
                'quantity': 1,  # Default Menge
                'article_no': art_no,
                'description': ""  # Leer lassen - nicht benötigt
            })
        
        df = pd.DataFrame(items)
        
        st.success(f"**Erfolgreich {len(df)} Artikelnummern extrahiert!**")
        return df
        
    except Exception as e:
        st.error(f"Fehler bei PDF-Verarbeitung: {str(e)}")
        return None

def get_cache_key(article_no: str) -> str:
    """Erstellt Cache-Schlüssel für Artikelnummer"""
    return hashlib.md5(article_no.encode()).hexdigest()

def search_web_fallback(article_no: str, config: Dict[str, Any], max_results: int = 5) -> List[Dict]:
    """
    Web-Suche Fallback für Conrad Artikelnummern
    Verwendet verschiedene Suchanbieter
    """
    search_provider = config.get('search_provider', UI_TEXTS["duckduckgo_fallback"])
    api_key = config.get('api_key')
    
    try:
        st.info(f"{UI_TEXTS['searching_web']} {article_no}")
        
        if search_provider == UI_TEXTS["serper_dev"] and api_key:
            return search_with_serper(article_no, api_key, max_results)
        elif search_provider == UI_TEXTS["bing_search"] and api_key:
            return search_with_bing(article_no, api_key, max_results)
        else:
            return search_with_duckduckgo(article_no, max_results)
            
    except Exception as e:
        st.error(f"Web-Suche fehlgeschlagen: {str(e)}")
        return []

def search_with_duckduckgo(article_no: str, max_results: int = 5) -> List[Dict]:
    """DuckDuckGo Fallback-Suche (kein API-Schlüssel nötig)"""
    try:
        query = f"site:conrad.de {article_no} Bestell-Nr"
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        
        # DuckDuckGo Ergebnis-Links finden
        for link in soup.find_all('a', href=True, class_='result__url'):
            href = link.get('href', '')
            
            # Conrad Produktlinks erkennen
            if re.search(r'conrad\.de/de/p/[\w-]+-\d+\.html', href, re.IGNORECASE):
                full_url = href if href.startswith('http') else f'https:{href}'
                
                # Duplikate vermeiden
                if full_url not in [p['url'] for p in products]:
                    products.append({
                        'url': full_url,
                        'title': "Conrad Produkt (via Web-Suche)",
                        'article_no': article_no,
                        'price': None,
                        'relevance_score': 90,  # Hohe Relevanz für Web-Fund
                        'source': 'web_fallback'
                    })
        
        return products[:max_results]
        
    except Exception as e:
        st.error(f"DuckDuckGo-Suche fehlgeschlagen: {str(e)}")
        return []

def search_with_serper(article_no: str, api_key: str, max_results: int = 5) -> List[Dict]:
    """Serper.dev Google Search API"""
    try:
        query = f"site:conrad.de {article_no} Bestell-Nr"
        url = "https://google.serper.dev/search"
        
        payload = json.dumps({
            "q": query,
            "num": max_results
        })
        
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        products = []
        
        for result in data.get('organic', []):
            link = result.get('link', '')
            
            # Nur Conrad Produktlinks
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
        
    except Exception as e:
        st.error(f"Serper API-Suche fehlgeschlagen: {str(e)}")
        return []

def search_with_bing(article_no: str, api_key: str, max_results: int = 5) -> List[Dict]:
    """Bing Web Search API"""
    try:
        query = f"site:conrad.de {article_no} Bestell-Nr"
        url = "https://api.bing.microsoft.com/v7.0/search"
        
        headers = {
            'Ocp-Apim-Subscription-Key': api_key
        }
        
        params = {
            'q': query,
            'count': max_results,
            'responseFilter': 'Webpages'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        products = []
        
        for result in data.get('webPages', {}).get('value', []):
            link = result.get('url', '')
            
            # Nur Conrad Produktlinks
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
        
    except Exception as e:
        st.error(f"Bing API-Suche fehlgeschlagen: {str(e)}")
        return []

def search_conrad_by_article_number(article_no: str, config: Dict[str, Any], max_results: int = 5) -> List[Dict]:
    """
    Sucht Conrad NUR mit Artikelnummer mit Web-Fallback
    """
    cache_key = get_cache_key(article_no)
    
    # Cache prüfen
    if cache_key in st.session_state.search_cache:
        return st.session_state.search_cache[cache_key]
    
    try:
        st.write(f"{UI_TEXTS['searching']} {article_no}...")
        
        # Conrad-Suche mit Artikelnummer
        search_url = f"https://www.conrad.de/de/search.html?search={article_no}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        
        # METHODE 1: Produktlinks mit Regex finden (robust)
        link_pattern = r'/de/p/[\w-]+-\d+\.html'
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            if re.search(link_pattern, href, re.IGNORECASE):
                full_url = urljoin('https://www.conrad.de', href)
                
                # Duplikate vermeiden
                if full_url not in [p['url'] for p in products]:
                    products.append({
                        'url': full_url,
                        'title': a_tag.get_text(strip=True) or "Produktseite",
                        'article_no': article_no,
                        'price': None,
                        'relevance_score': 100,  # Höchste Relevanz bei direkter Nummernübereinstimmung
                        'source': 'conrad_direct'
                    })
        
        # METHODE 2: Fallback - traditionelle Selektoren
        if not products:
            selectors = ['[data-product-id]', '.product--box', '.product__body']
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements[:max_results]:
                    product_info = extract_product_info_simple(element, article_no)
                    if product_info:
                        product_info['source'] = 'conrad_fallback'
                        products.append(product_info)
        
        # WEB FALLBACK: Wenn keine Conrad-Ergebnisse und Fallback aktiviert
        if not products and config.get('enable_fallback', True):
            web_products = search_web_fallback(article_no, config, max_results)
            products.extend(web_products)
        
        # Produktinformationen von den Links holen
        detailed_products = []
        for product in products[:max_results]:
            detailed_info = fetch_product_details(product['url'], article_no)
            if detailed_info:
                detailed_info['source'] = product.get('source', 'unknown')
                detailed_products.append(detailed_info)
            else:
                detailed_products.append(product)  # Fallback zu Basis-Info
        
        # Nach Relevanz sortieren
        ranked_products = sorted(detailed_products, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # In Cache speichern
        st.session_state.search_cache[cache_key] = ranked_products
        
        return ranked_products
        
    except Exception as e:
        st.error(f"Suchfehler für Artikelnr. {article_no}: {str(e)}")
        
        # Fallback bei Fehler
        if config.get('enable_fallback', True):
            return search_web_fallback(article_no, config, max_results)
        return []

def extract_product_info_simple(element, original_article_no: str) -> Optional[Dict]:
    """Einfache Produktinfo-Extraktion"""
    try:
        # Link finden
        link_element = element.find('a', href=True)
        if not link_element:
            return None
        
        product_url = link_element['href']
        if not product_url.startswith('http'):
            product_url = 'https://www.conrad.de' + product_url
        
        # Titel finden
        title = "Produkttitel nicht gefunden"
        title_element = element.find(['h1', 'h2', 'h3', 'h4']) or element.find(class_=re.compile(r'title|name'))
        if title_element:
            title = title_element.get_text(strip=True)
        
        return {
            'url': product_url,
            'title': title,
            'article_no': original_article_no,
            'price': None,
            'relevance_score': 80
        }
    except Exception:
        return None

def fetch_product_details(product_url: str, original_article_no: str) -> Optional[Dict]:
    """Holt detaillierte Produktinformationen von der Produktseite"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(product_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titel extrahieren
        title = "Titel nicht gefunden"
        title_selectors = ['h1', '.product-title', '.product__title', '[class*="title"]']
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                break
        
        # Artikelnummer von der Produktseite
        article_no = original_article_no
        article_patterns = [
            r'Bestell-Nr\.\s*([A-Z0-9\-]+)',
            r'Artikel-Nr\.\s*([A-Z0-9\-]+)',
        ]
        
        page_text = soup.get_text()
        for pattern in article_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                article_no = match.group(1)
                break
        
        # Preis extrahieren
        price = None
        price_selectors = ['.price__value', '.product__price', '.current-price', '[class*="price"]']
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'[\d,.]+\s*€?', price_text)
                if price_match:
                    price = price_match.group(0).strip()
                    break
        
        # Relevanz berechnen (100 bei exakter Übereinstimmung)
        relevance_score = 100 if original_article_no == article_no else 50
        
        return {
            'url': product_url,
            'title': title,
            'article_no': article_no,
            'price': price,
            'relevance_score': relevance_score
        }
        
    except Exception:
        return None

def manual_data_entry():
    """Manuelle Produkteingabe - NUR Artikelnummern"""
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
            
            if article_no:  # Nur wenn Artikelnummer vorhanden
                # Artikelnummer bereinigen
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

def perform_single_search(idx: int, row: pd.Series, config: Dict[str, Any], column_mapping: Dict[str, str]):
    """Suche für eine einzelne Zeile durchführen - NUR mit Artikelnummer"""
    article_col = column_mapping.get('article_no', 'article_no')
    
    if article_col not in row or pd.isna(row[article_col]) or not row[article_col]:
        st.error("Keine Artikelnummer für diese Position verfügbar")
        return
    
    article_no = str(row[article_col]).strip()
    
    # Artikelnummer bereinigen
    clean_article_no = re.sub(r'[^\d-]', '', article_no)
    if '-' in clean_article_no:
        clean_article_no = clean_article_no.split('-')[0]
    
    if not clean_article_no.isdigit():
        st.error(f"Ungültige Artikelnummer: {article_no}")
        return
    
    candidates = search_conrad_by_article_number(clean_article_no, config, config['max_results'])
    st.session_state.search_results[idx] = candidates
    
    if not candidates:
        st.warning(f"{UI_TEXTS['no_results_for']} {clean_article_no}")

def perform_bulk_search(df: pd.DataFrame, config: Dict[str, Any], column_mapping: Dict[str, str]):
    """MassenSuche für alle Zeilen - NUR mit Artikelnummern"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    article_col = column_mapping.get('article_no', 'article_no')
    
    for idx, row in df.iterrows():
        status_text.text(f"Suche Position {idx+1}/{len(df)}...")
        
        if article_col in row and pd.notna(row[article_col]) and row[article_col]:
            article_no = str(row[article_col]).strip()
            
            # Artikelnummer bereinigen
            clean_article_no = re.sub(r'[^\d-]', '', article_no)
            if '-' in clean_article_no:
                clean_article_no = clean_article_no.split('-')[0]
            
            if clean_article_no.isdigit():
                candidates = search_conrad_by_article_number(clean_article_no, config, config['max_results'])
                st.session_state.search_results[idx] = candidates
            else:
                st.session_state.search_results[idx] = []
        else:
            st.session_state.search_results[idx] = []
        
        time.sleep(config['search_delay'])
        progress_bar.progress((idx + 1) / len(df))
    
    status_text.text("Suche abgeschlossen")

def display_search_results(idx: int, config: Dict[str, Any]):
    """Suchergebnisse für eine bestimmte Zeile anzeigen"""
    results = st.session_state.search_results.get(idx, [])
    
    if not results:
        st.write(UI_TEXTS["no_results"])
        return
    
    # Optionen für Radio-Buttons erstellen
    options = []
    for result in results:
        source_info = ""
        if result.get('source') == 'web_fallback':
            source_info = " [Web-Fallback]"
        elif result.get('source') == 'serper_api':
            source_info = " [Serper API]"
        elif result.get('source') == 'bing_api':
            source_info = " [Bing API]"
        
        option_text = f"{result['title']} | {result['article_no']} | {result['price'] or 'Preis unbekannt'}{source_info}"
        options.append(option_text)
    
    selected_index = st.radio(
        f"{UI_TEXTS['choose_product']} #{idx+1}:",
        range(len(options)),
        format_func=lambda i: options[i],
        key=f"select_{idx}"
    )
    
    if selected_index is not None and selected_index < len(results):
        selected_product = results[selected_index]
        st.session_state.selected_products[idx] = selected_product
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{UI_TEXTS['product_title']}:** {selected_product['title']}")
            st.write(f"**{UI_TEXTS['conrad_number']}:** {selected_product['article_no']}")
            st.write(f"**{UI_TEXTS['price']}:** {selected_product['price'] or 'N/A'}")
            
            # Quelle anzeigen
            source = selected_product.get('source', 'conrad_direct')
            if source != 'conrad_direct':
                st.write(f"**Quelle:** {source}")
        
        with col2:
            product_url = selected_product['url']
            st.markdown(
                f'<a href="{product_url}" target="_blank">'
                f'<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">'
                f'{UI_TEXTS["open_new_tab"]}'
                f'</button></a>', 
                unsafe_allow_html=True
            )

def create_final_dataframe(original_df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    """Finalen DataFrame mit ausgewählten Produkten erstellen"""
    final_data = []
    
    for idx, row in original_df.iterrows():
        row_data = row.to_dict()
        
        if idx in st.session_state.selected_products:
            selected = st.session_state.selected_products[idx]
            row_data['Gewählte Conrad URL'] = selected['url']
            row_data['Gewählte Bestell-Nr.'] = selected['article_no']
            row_data['Gewählter Titel'] = selected['title']
            row_data['Gewählter Preis'] = selected['price'] or ''
            row_data['Status'] = 'Gefunden'
            row_data['Quelle'] = selected.get('source', 'conrad_direct')
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
    """Hauptfunktion der Anwendung"""
    st.title(UI_TEXTS["title"])
    
    # Sidebar einrichten
    config = setup_sidebar()
    
    # Upload-Optionen
    upload_options = ["CSV hochladen", "Manuelle Eingabe"]
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        upload_options.insert(1, "PDF hochladen")
    
    upload_option = st.radio(
        "Datenquelle wählen:",
        upload_options
    )
    
    if upload_option == "CSV hochladen":
        uploaded_file = st.file_uploader(
            UI_TEXTS["file_upload"],
            type=['csv'],
            help=UI_TEXTS['csv_help']
        )
        
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.extracted_items = df
            
    elif upload_option == "PDF hochladen" and OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        uploaded_file = st.file_uploader(
            UI_TEXTS["file_upload"],
            type=['pdf'],
            help=UI_TEXTS['pdf_help']
        )
        
        if uploaded_file is not None:
            df = pdf_to_df_simple(uploaded_file, config)
            if df is not None:
                st.session_state.extracted_items = df
                
    elif upload_option == "Manuelle Eingabe":
        manual_data_entry()
    
    # Extrahierte Daten anzeigen
    if st.session_state.extracted_items is not None:
        df = st.session_state.extracted_items
        
        st.subheader(UI_TEXTS["preview_data"])
        st.dataframe(df)
        st.write(f"{len(df)} {UI_TEXTS['items_found']}")
        
        # Spaltenzuordnung
        st.subheader(UI_TEXTS["column_mapping"])
        st.write(UI_TEXTS["map_columns"])
        
        available_columns = list(df.columns)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantity_map = st.selectbox(UI_TEXTS["quantity"], [''] + available_columns)
        with col2:
            article_map = st.selectbox(UI_TEXTS["article_no"], [''] + available_columns)
        with col3:
            description_map = st.selectbox(UI_TEXTS["description"], [''] + available_columns)
        
        column_mapping = {
            'quantity': quantity_map if quantity_map else 'quantity',
            'article_no': article_map if article_map else 'article_no',
            'description': description_map if description_map else 'description'
        }
        
        if st.button(UI_TEXTS["apply_mapping"]):
            st.session_state.column_mapping = column_mapping
            st.success("Zuordnung angewendet")
        
        # Suchinterface
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
                        desc_col = st.session_state.column_mapping.get('description', 'description')
                        description = row.get(desc_col, '')
                        if description:
                            st.write(f"**Beschreibung:** {description}")
                    
                    with col2:
                        if st.button(UI_TEXTS["search_row"], key=f"search_{idx}"):
                            perform_single_search(idx, row, config, st.session_state.column_mapping)
                    
                    if idx in st.session_state.search_results:
                        display_search_results(idx, config)
            
            # Finale Auswahl und Download
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
    main()          -----make die kod beste besteund besser
