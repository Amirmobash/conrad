# app.py - Conrad Produktfinder (Ultimative Version)
# Autor: Amir Mobasheraghdam (optimiert)
# Datum: 2026-04-06
# Version: 4.0
# Beschreibung: Streamlit-Anwendung zum Extrahieren von Conrad Artikelnummern
#              aus CSV/PDF und Suchen der entsprechenden Produkte auf conrad.de.
#              Enthält OCR, Websuche-Fallback, asynchrone Anfragen, intelligentes Caching.
#              Vollständig auf Deutsch.

import asyncio
import aiohttp
import base64
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urljoin, quote

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import requests

# ------------------------------------------------------------------------------
# Optionale OCR-Bibliotheken
# ------------------------------------------------------------------------------
try:
    import pytesseract
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False
    st.warning("Pytesseract oder PIL nicht installiert. OCR deaktiviert.")

try:
    import pdf2image
    PDF2IMAGE_SUPPORT = True
except ImportError:
    PDF2IMAGE_SUPPORT = False
    st.warning("pdf2image nicht installiert. PDF-OCR deaktiviert.")

# ------------------------------------------------------------------------------
# Konfiguration (kann über Umgebungsvariablen überschrieben werden)
# ------------------------------------------------------------------------------
DEFAULT_TESSERACT_PATH = os.getenv("TESSERACT_PATH", "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
DEFAULT_TESSDATA_PATH = os.getenv("TESSDATA_PATH", "C:\\Program Files\\Tesseract-OCR\\tessdata")
DEFAULT_POPPLER_PATH = os.getenv("POPPLER_PATH", "C:\\poppler\\poppler-23.11.0\\Library\\bin")

DEFAULT_SEARCH_DELAY = float(os.getenv("SEARCH_DELAY", "1.0"))       # Sekunden zwischen Anfragen
DEFAULT_MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
DEFAULT_ENABLE_FALLBACK = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
DEFAULT_SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # duckduckgo, serper, bing

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))   # Cache-Gültigkeit in Sekunden

# ------------------------------------------------------------------------------
# Zentrale deutsche UI-Texte (für einfache Übersetzung und Wartung)
# ------------------------------------------------------------------------------
UI_TEXTE = {
    "title": "🔍 Conrad Produktfinder – Bestellungen wiederfinden",
    "subtitle": "Automatische Suche nach Conrad Artikelnummern aus CSV, PDF oder per Hand",
    "file_upload": "📂 Datei hochladen (CSV oder PDF)",
    "csv_help": "Laden Sie eine CSV-Datei mit Artikelliste hoch (beliebige Spalten)",
    "pdf_help": "Oder laden Sie einen Conrad Warenkorb / Bestellung als PDF hoch (OCR unterstützt)",
    "preview_data": "📋 Vorschau der extrahierten Daten",
    "column_mapping": "🔧 Spaltenzuordnung",
    "map_columns": "Weisen Sie die Spalten Ihrer Datei den erforderlichen Feldern zu:",
    "quantity": "Menge",
    "article_no": "Conrad Artikel-Nr.",
    "description": "Beschreibung",
    "search_all": "🚀 Alle Positionen suchen",
    "search_row": "🔎 Diese Position suchen",
    "choose_product": "✅ Produkt auswählen",
    "open_new_tab": "🌐 In neuem Tab öffnen",
    "product_title": "📦 Produkttitel",
    "conrad_number": "🔢 Bestell-Nr.",
    "price": "💰 Preis",
    "no_results": "❌ Keine Ergebnisse gefunden",
    "download_csv": "📥 CSV herunterladen",
    "processing_pdf": "📄 PDF wird verarbeitet (OCR läuft)...",
    "search_settings": "⚙️ Such-Einstellungen",
    "search_delay": "⏱️ Verzögerung zwischen Suchanfragen (Sekunden)",
    "max_results": "📊 Maximale Suchergebnisse pro Produkt",
    "apply_mapping": "Übernehmen",
    "items_found": "Artikel gefunden",
    "final_selection": "🎯 Finale Auswahl",
    "selected_products_count": "Ausgewählte Produkte",
    "not_found": "Nicht gefunden",
    "manual_entry": "✏️ Manuelle Eingabe",
    "tesseract_path": "🖨️ Pfad zu Tesseract (tesseract.exe)",
    "tessdata_path": "🗂️ Pfad zum tessdata-Ordner (optional)",
    "poppler_path": "📄 Pfad zu Poppler (optional, für PDF->Bilder)",
    "ocr_config": "📑 OCR-Konfiguration",
    "no_article_number": "Keine Artikelnummer gefunden",
    "searching": "🔍 Suche Conrad nach Artikelnr.",
    "results_found": "Produkte gefunden",
    "no_results_for": "Keine Treffer für Artikelnr.",
    "web_search_fallback": "🌐 Websuche-Fallback",
    "enable_fallback": "Fallback-Suche aktivieren (falls Conrad nichts findet)",
    "searching_web": "Keine Conrad-Treffer – starte Websuche...",
    "serper_api_key": "🔑 Serper.dev API-Schlüssel",
    "bing_api_key": "🔑 Bing Web Search API-Schlüssel",
    "search_provider": "Anbieter für Fallback-Suche",
    "duckduckgo_fallback": "DuckDuckGo (kostenlos, kein API-Key)",
    "serper_dev": "Serper.dev (Google Ergebnisse, kostenpflichtig)",
    "bing_search": "Bing Web Search (kostenpflichtig)",
    "use_async": "⚡ Asynchrone Suche (schneller, mehrere Anfragen gleichzeitig)",
    "cache_info": "💾 Ergebnisse werden zwischengespeichert (TTL: {} Sekunden)",
    "status_searching": "Suche läuft...",
    "status_complete": "Suche abgeschlossen.",
    "status_error": "Fehler bei der Suche",
    "source_conrad": "Conrad direkt",
    "source_fallback": "Web-Fallback",
    "source_api": "API-Suche",
    "source_detail": "Produktseite",
    "ocr_language": "OCR-Sprache(n)",
    "ocr_dpi": "DPI für OCR",
    "data_source": "📁 Datenquelle wählen",
    "csv_option": "CSV hochladen",
    "pdf_option": "PDF hochladen (OCR)",
    "manual_option": "Manuelle Eingabe",
    "num_products_manual": "Anzahl der Produkte",
    "product": "Produkt",
    "quantity_abbr": "Menge",
    "article_no_abbr": "Art.-Nr.",
    "description_abbr": "Beschreibung (optional)",
    "invalid_article": "Ungültige Artikelnummer",
    "take_over": "Übernehmen",
    "search_progress": "Suche Position {}/{}",
    "select_product": "Produkt auswählen für Zeile {}",
    "source_label": "Quelle",
}

# Cache-TTL in den Text einfügen
UI_TEXTE["cache_info"] = UI_TEXTE["cache_info"].format(CACHE_TTL)

# ------------------------------------------------------------------------------
# Session-State initialisieren
# ------------------------------------------------------------------------------
def init_session_state() -> None:
    """Initialisiert alle benötigten Session-State-Variablen."""
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
    if 'letzte_suche' not in st.session_state:
        st.session_state.letzte_suche = None

# ------------------------------------------------------------------------------
# Hilfsfunktionen für Caching
# ------------------------------------------------------------------------------
def cache_schluessel(artikel_nr: str) -> str:
    """Erzeugt einen eindeutigen Cache-Schlüssel für eine Artikelnummer."""
    return hashlib.md5(artikel_nr.encode()).hexdigest()

def ist_cache_gueltig(schluessel: str) -> bool:
    """Prüft, ob ein Cache-Eintrag noch gültig ist (TTL nicht überschritten)."""
    if schluessel not in st.session_state.such_cache:
        return False
    zeitstempel = st.session_state.cache_zeitstempel.get(schluessel, 0)
    return (time.time() - zeitstempel) < CACHE_TTL

def setze_cache(schluessel: str, wert: Any) -> None:
    """Speichert einen Wert im Cache mit aktuellem Zeitstempel."""
    st.session_state.such_cache[schluessel] = wert
    st.session_state.cache_zeitstempel[schluessel] = time.time()

# ------------------------------------------------------------------------------
# Artikelnummern bereinigen
# ------------------------------------------------------------------------------
def bereinige_artikelnummer(artikel_nr: str) -> Optional[str]:
    """
    Bereinigt eine Roh-Artikelnummer:
    - Entfernt alles außer Ziffern und Bindestrich
    - Schneidet Suffixe nach Bindestrich ab
    - Entfernt Leerzeichen
    - Prüft auf Länge zwischen 5 und 8 Ziffern
    """
    if not artikel_nr or not isinstance(artikel_nr, str):
        return None
    # Nur Ziffern und Bindestriche behalten
    bereinigt = re.sub(r'[^\d-]', '', artikel_nr)
    # Alles nach einem Bindestrich abschneiden (falls vorhanden)
    if '-' in bereinigt:
        bereinigt = bereinigt.split('-')[0]
    # Leerzeichen entfernen
    bereinigt = re.sub(r'\s+', '', bereinigt)
    # Prüfen, ob nur Ziffern übrig sind und Länge passt
    if bereinigt.isdigit() and 5 <= len(bereinigt) <= 8:
        return bereinigt
    return None

# ------------------------------------------------------------------------------
# OCR-Umgebung einrichten
# ------------------------------------------------------------------------------
def richte_ocr_ein(tesseract_pfad: str = None, tessdata_pfad: str = None) -> Tuple[bool, str]:
    """
    Konfiguriert Tesseract OCR.
    Gibt (Erfolg, Nachricht) zurück.
    """
    if not OCR_SUPPORT:
        return False, "OCR-Bibliotheken (pytesseract, PIL) nicht installiert."
    try:
        if tesseract_pfad and os.path.exists(tesseract_pfad):
            pytesseract.pytesseract.tesseract_cmd = tesseract_pfad
        else:
            # Versuche, Tesseract über den System-PATH zu finden
            try:
                pytesseract.get_tesseract_version()
            except pytesseract.TesseractNotFoundError:
                return False, "Tesseract nicht gefunden. Bitte Pfad angeben oder installieren."
        if tessdata_pfad and os.path.exists(tessdata_pfad):
            os.environ['TESSDATA_PREFIX'] = tessdata_pfad
        return True, "OCR erfolgreich konfiguriert."
    except Exception as e:
        return False, f"OCR-Konfigurationsfehler: {e}"

# ------------------------------------------------------------------------------
# PDF-Text extrahieren (mit OCR)
# ------------------------------------------------------------------------------
def extrahiere_text_aus_pdf(pdf_bytes: bytes, konfig: Dict[str, Any]) -> str:
    """
    Wandelt eine PDF in Text um (zuerst direkter Text, dann OCR-Fallback).
    Gibt den extrahierten Text zurück.
    """
    try:
        # Zuerst versuchen, eingebetteten Text zu extrahieren (falls vorhanden)
        import io
        from PyPDF2 import PdfReader
        text_direkt = ""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for seite in reader.pages:
                seiten_text = seite.extract_text()
                if seiten_text:
                    text_direkt += seiten_text + "\n"
            if text_direkt.strip():
                st.info("📄 Eingebetteter Text aus PDF extrahiert (OCR nicht nötig).")
                return text_direkt
        except Exception:
            pass  # Fallback auf OCR

        # OCR erforderlich
        if not PDF2IMAGE_SUPPORT:
            st.error("pdf2image nicht installiert. Kann PDF nicht in Bilder wandeln.")
            return ""

        erfolg, msg = richte_ocr_ein(konfig.get('tesseract_pfad'), konfig.get('tessdata_pfad'))
        if not erfolg:
            st.error(msg)
            return ""

        # Temporäre PDF-Datei
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_bytes)
            tmp_pfad = tmp.name

        try:
            poppler_pfad = konfig.get('poppler_pfad')
            bilder = pdf2image.convert_from_path(
                tmp_pfad,
                dpi=konfig.get('ocr_dpi', 300),
                poppler_path=poppler_pfad if poppler_pfad and os.path.exists(poppler_pfad) else None
            )
        finally:
            os.unlink(tmp_pfad)

        if not bilder:
            st.error("Keine Seiten aus PDF extrahiert.")
            return ""

        gesamter_text = ""
        for idx, img in enumerate(bilder):
            st.write(f"📄 Verarbeite Seite {idx+1}/{len(bilder)} mit OCR...")
            # Bild in Graustufen umwandeln für bessere Erkennung
            img = img.convert('L')
            tesseract_config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
            sprache = konfig.get('ocr_sprache', 'deu+eng')
            try:
                text = pytesseract.image_to_string(img, lang=sprache, config=tesseract_config)
            except Exception:
                # Fallback: nur Englisch
                text = pytesseract.image_to_string(img, lang='eng')
            gesamter_text += text + "\n\n"
        return gesamter_text
    except Exception as e:
        st.error(f"Fehler bei der PDF-Verarbeitung: {e}")
        return ""

def extrahiere_artikelnummern_aus_text(text: str) -> List[str]:
    """
    Durchsucht Rohtext nach Conrad-Artikelnummern.
    Verwendet mehrere reguläre Ausdrücke.
    """
    if not text:
        return []
    artikel_nrn = []
    muster = [
        r'bestell[.-]?nr\.?\s*:?\s*([0-9]+)\s*-?\s*[0-9]*',
        r'bestell[.-]?nr\.?\s*:?\s*([0-9]+[-\s]*[0-9]*)',
        r'bestellnummer\s*:?\s*([0-9]+)',
        r'artikel[.-]?nr\.?\s*:?\s*([0-9]+)',
        r'conrad\s*art\.?\s*nr\.?\s*:?\s*([0-9]+)',
        r'([0-9]{5,8})',          # generische 5-8 stellige Zahl (kann false positives geben)
    ]
    zeilen = text.split('\n')
    for zeile in zeilen:
        zeile = zeile.strip()
        if not zeile:
            continue
        for pattern in muster:
            treffer = re.finditer(pattern, zeile, re.IGNORECASE)
            for match in treffer:
                roh = match.group(1)
                bereinigt = re.sub(r'[\s-]', '', roh)
                if bereinigt.isdigit() and 5 <= len(bereinigt) <= 8:
                    if bereinigt not in artikel_nrn:
                        artikel_nrn.append(bereinigt)
    return artikel_nrn

def pdf_zu_dataframe(pdf_bytes: bytes, konfig: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Hauptfunktion: Wandelt PDF in DataFrame um.
    Extrahiert Artikelnummern und erstellt Zeilen mit Menge=1.
    """
    st.info(UI_TEXTE["processing_pdf"])
    text = extrahiere_text_aus_pdf(pdf_bytes, konfig)
    if not text.strip():
        st.error("Konnte keinen Text aus PDF extrahieren (auch nicht mit OCR).")
        return None

    artikel_nrn = extrahiere_artikelnummern_aus_text(text)
    if not artikel_nrn:
        st.warning("Keine Conrad-Artikelnummern im PDF gefunden.")
        return None

    # DataFrame mit je einer Zeile pro Artikelnummer (Menge=1, Beschreibung leer)
    daten = [{'Menge': 1, 'Artikel-Nr.': art, 'Beschreibung': ""} for art in artikel_nrn]
    df = pd.DataFrame(daten)
    st.success(f"✅ **Erfolgreich {len(df)} Artikelnummern extrahiert!**")
    return df

# ------------------------------------------------------------------------------
# Asynchrone Suchfunktionen
# ------------------------------------------------------------------------------
async def hole_html(session: aiohttp.ClientSession, url: str, headers: Dict) -> Optional[str]:
    """Holt asynchron den HTML-Inhalt einer URL."""
    try:
        async with session.get(url, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None

async def suche_conrad_async(artikel_nr: str, session: aiohttp.ClientSession) -> List[Dict]:
    """
    Durchsucht conrad.de direkt nach der Artikelnummer.
    Extrahiert Produkt-Links aus der Suchergebnisseite.
    """
    such_url = f"https://www.conrad.de/de/search.html?search={artikel_nr}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    html = await hole_html(session, such_url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    produkte = []
    link_muster = re.compile(r'/de/p/[\w-]+-\d+\.html', re.IGNORECASE)
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if link_muster.search(href):
            voll_url = urljoin('https://www.conrad.de', href)
            if voll_url not in [p['url'] for p in produkte]:
                produkte.append({
                    'url': voll_url,
                    'titel': a_tag.get_text(strip=True) or "Produktseite",
                    'artikel_nr': artikel_nr,
                    'preis': None,
                    'relevanz': 100,
                    'quelle': 'conrad_direkt'
                })
    return produkte

async def suche_duckduckgo_async(artikel_nr: str, session: aiohttp.ClientSession) -> List[Dict]:
    """DuckDuckGo HTML-Suche – beschränkt auf conrad.de."""
    query = f"site:conrad.de {artikel_nr} Bestell-Nr"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
    }
    html = await hole_html(session, url, headers)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    produkte = []
    link_muster = re.compile(r'conrad\.de/de/p/[\w-]+-\d+\.html', re.IGNORECASE)
    for link in soup.find_all('a', href=True, class_='result__url'):
        href = link.get('href', '')
        if link_muster.search(href):
            voll_url = href if href.startswith('http') else f'https:{href}'
            produkte.append({
                'url': voll_url,
                'titel': "Conrad Produkt (via Web-Suche)",
                'artikel_nr': artikel_nr,
                'preis': None,
                'relevanz': 90,
                'quelle': 'web_fallback'
            })
    return produkte[:5]

async def suche_serper_async(artikel_nr: str, api_key: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Serper.dev API (Google Search)."""
    query = f"site:conrad.de {artikel_nr} Bestell-Nr"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {"q": query, "num": 5}
    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                produkte = []
                for ergebnis in data.get('organic', []):
                    link = ergebnis.get('link', '')
                    if re.search(r'conrad\.de/de/p/[\w-]+-\d+\.html', link, re.IGNORECASE):
                        produkte.append({
                            'url': link,
                            'titel': ergebnis.get('title', 'Conrad Produkt'),
                            'artikel_nr': artikel_nr,
                            'preis': None,
                            'relevanz': 95,
                            'quelle': 'serper_api'
                        })
                return produkte
    except Exception:
        pass
    return []

async def suche_bing_async(artikel_nr: str, api_key: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Bing Web Search API."""
    query = f"site:conrad.de {artikel_nr} Bestell-Nr"
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {'Ocp-Apim-Subscription-Key': api_key}
    params = {'q': query, 'count': 5, 'responseFilter': 'Webpages'}
    try:
        async with session.get(url, headers=headers, params=params, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                produkte = []
                for ergebnis in data.get('webPages', {}).get('value', []):
                    link = ergebnis.get('url', '')
                    if re.search(r'conrad\.de/de/p/[\w-]+-\d+\.html', link, re.IGNORECASE):
                        produkte.append({
                            'url': link,
                            'titel': ergebnis.get('name', 'Conrad Produkt'),
                            'artikel_nr': artikel_nr,
                            'preis': None,
                            'relevanz': 95,
                            'quelle': 'bing_api'
                        })
                return produkte
    except Exception:
        pass
    return []

async def suche_web_fallback_async(artikel_nr: str, konfig: Dict[str, Any], session: aiohttp.ClientSession) -> List[Dict]:
    """Web-Fallback basierend auf gewähltem Anbieter."""
    anbieter = konfig.get('such_anbieter', 'duckduckgo')
    if anbieter == 'serper' and konfig.get('serper_api_key'):
        return await suche_serper_async(artikel_nr, konfig['serper_api_key'], session)
    elif anbieter == 'bing' and konfig.get('bing_api_key'):
        return await suche_bing_async(artikel_nr, konfig['bing_api_key'], session)
    else:
        return await suche_duckduckgo_async(artikel_nr, session)

async def hole_produkt_details_async(produkt_url: str, ursp_artikel_nr: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """
    Ruft asynchron die Produktseite ab und extrahiert Titel, Bestellnummer und Preis.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    html = await hole_html(session, produkt_url, headers)
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')

    # Titel
    titel = "Titel nicht gefunden"
    for selector in ['h1', '.product-title', '.product__title', '[class*="title"]']:
        elem = soup.select_one(selector)
        if elem:
            titel = elem.get_text(strip=True)
            break

    # Artikelnummer (Bestell-Nr.)
    artikel_nr = ursp_artikel_nr
    seiten_text = soup.get_text()
    muster = [r'Bestell-Nr\.\s*([A-Z0-9\-]+)', r'Artikel-Nr\.\s*([A-Z0-9\-]+)']
    for pattern in muster:
        match = re.search(pattern, seiten_text, re.IGNORECASE)
        if match:
            artikel_nr = match.group(1)
            break

    # Preis
    preis = None
    for selector in ['.price__value', '.product__price', '.current-price', '[class*="price"]']:
        elem = soup.select_one(selector)
        if elem:
            preis_text = elem.get_text(strip=True)
            preis_match = re.search(r'[\d,.]+\s*€', preis_text)
            if preis_match:
                preis = preis_match.group(0)
                break

    relevanz = 100 if ursp_artikel_nr == artikel_nr else 50
    return {
        'url': produkt_url,
        'titel': titel,
        'artikel_nr': artikel_nr,
        'preis': preis,
        'relevanz': relevanz,
        'quelle': 'produktseite'
    }

async def suche_produkt_async(artikel_nr: str, konfig: Dict[str, Any]) -> List[Dict]:
    """
    Hauptsuchroutine:
    1. Cache prüfen
    2. Conrad-Direktsuche
    3. Fallback (falls aktiviert)
    4. Details von Produktseiten abrufen
    5. Sortieren nach Relevanz
    6. Cache speichern
    """
    cache_key = cache_schluessel(artikel_nr)
    if ist_cache_gueltig(cache_key):
        return st.session_state.such_cache[cache_key]

    async with aiohttp.ClientSession() as session:
        # Conrad-Suche
        produkte = await suche_conrad_async(artikel_nr, session)

        # Fallback, falls keine Ergebnisse und gewünscht
        if not produkte and konfig.get('fallback_aktiv', True):
            st.info(f"{UI_TEXTE['searching_web']} {artikel_nr}")
            fallback = await suche_web_fallback_async(artikel_nr, konfig, session)
            produkte.extend(fallback)

        # Detaillierte Informationen abrufen (max. 5 Produkte)
        max_ergebnisse = konfig.get('max_ergebnisse', 5)
        detail_produkte = []
        for prod in produkte[:max_ergebnisse]:
            details = await hole_produkt_details_async(prod['url'], artikel_nr, session)
            if details:
                # Ursprüngliche Quelle beibehalten, falls vorhanden
                if 'quelle' in prod and details.get('quelle') == 'produktseite':
                    details['quelle'] = prod['quelle']
                detail_produkte.append(details)
            else:
                detail_produkte.append(prod)

        # Nach Relevanz sortieren (höhere Punktzahl zuerst)
        detail_produkte.sort(key=lambda x: x.get('relevanz', 0), reverse=True)
        setze_cache(cache_key, detail_produkte)
        return detail_produkte

def suche_conrad_nach_artikelnummer(artikel_nr: str, konfig: Dict[str, Any]) -> List[Dict]:
    """Synchroner Wrapper für die asynchrone Suche (wird in Streamlit benötigt)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(suche_produkt_async(artikel_nr, konfig))
    finally:
        loop.close()

# ------------------------------------------------------------------------------
# UI-Komponenten
# ------------------------------------------------------------------------------
def sidebar_konfiguration() -> Dict[str, Any]:
    """Erstellt die Sidebar mit allen Konfigurationsmöglichkeiten."""
    st.sidebar.image("https://www.conrad.de/medias/logo.svg?context=bWFzdGVyfGltYWdlc3wxNTI5fGltYWdlL3N2Zyt4bWx8YUdFeUwyaGxaaTg0TURBd01ERXpNREF3TWpBd0w2SjFjMmx1Wnk5dFlYSnBlR2xrWlM4eE1UTTJNREF3TkRFeU5qQTVNVEV4TG5Cb2NnPT0", width=200)
    st.sidebar.title("⚙️ Einstellungen")

    # OCR-Konfiguration (nur anzeigen, wenn unterstützt)
    st.sidebar.subheader(UI_TEXTE["ocr_config"])
    tesseract_pfad = st.sidebar.text_input(
        UI_TEXTE["tesseract_path"],
        value=DEFAULT_TESSERACT_PATH,
        help="Vollständiger Pfad zur tesseract.exe (z.B. C:\\Program Files\\Tesseract-OCR\\tesseract.exe)"
    )
    tessdata_pfad = st.sidebar.text_input(
        UI_TEXTE["tessdata_path"],
        value=DEFAULT_TESSDATA_PATH,
        help="Pfad zum tessdata-Ordner (z.B. C:\\Program Files\\Tesseract-OCR\\tessdata)"
    )
    poppler_pfad = st.sidebar.text_input(
        UI_TEXTE["poppler_path"],
        value=DEFAULT_POPPLER_PATH,
        help="Pfad zu Poppler (enthält pdftoppm.exe) – nur für PDF-OCR nötig"
    )

    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        ocr_sprache = st.sidebar.selectbox(
            UI_TEXTE["ocr_language"],
            ["deu+eng", "deu", "eng"],
            index=0,
            help="Mehrere Sprachen mit '+' trennen, z.B. deu+eng+fra"
        )
        ocr_dpi = st.sidebar.selectbox(
            UI_TEXTE["ocr_dpi"],
            [200, 250, 300, 350, 400],
            index=2,
            help="Höhere DPI verbessern die Erkennung, verlangsamen aber die Verarbeitung."
        )
    else:
        ocr_sprache = "deu+eng"
        ocr_dpi = 300
        st.sidebar.warning("OCR nicht vollständig verfügbar (pytesseract/pdf2image fehlen).")

    # Such-Einstellungen
    st.sidebar.subheader(UI_TEXTE["search_settings"])
    such_verzoegerung = st.sidebar.number_input(
        UI_TEXTE["search_delay"],
        min_value=0.0, max_value=10.0, value=DEFAULT_SEARCH_DELAY, step=0.5,
        help="Verzögerung zwischen einzelnen Suchanfragen (vermeidet Überlastung). Bei 0 Sekunden so schnell wie möglich."
    )
    max_ergebnisse = st.sidebar.number_input(
        UI_TEXTE["max_results"],
        min_value=1, max_value=10, value=DEFAULT_MAX_RESULTS,
        help="Maximale Anzahl angezeigter Produkte pro Artikelnummer."
    )
    verwende_async = st.sidebar.checkbox(
        UI_TEXTE["use_async"],
        value=True,
        help="Aktiviert parallele Anfragen für schnellere Suche (empfohlen)."
    )

    # Web-Fallback
    st.sidebar.subheader(UI_TEXTE["web_search_fallback"])
    fallback_aktiv = st.sidebar.checkbox(
        UI_TEXTE["enable_fallback"],
        value=DEFAULT_ENABLE_FALLBACK,
        help="Falls Conrad direkt keine Ergebnisse liefert, wird eine Websuche gestartet."
    )

    anbieter_optionen = ["duckduckgo", "serper", "bing"]
    anbieter_labels = [UI_TEXTE["duckduckgo_fallback"], UI_TEXTE["serper_dev"], UI_TEXTE["bing_search"]]
    standard_index = anbieter_optionen.index(DEFAULT_SEARCH_PROVIDER) if DEFAULT_SEARCH_PROVIDER in anbieter_optionen else 0
    such_anbieter = st.sidebar.selectbox(
        UI_TEXTE["search_provider"],
        anbieter_optionen,
        format_func=lambda x: anbieter_labels[anbieter_optionen.index(x)],
        index=standard_index
    )

    api_key = None
    if such_anbieter == "serper":
        api_key = st.sidebar.text_input(UI_TEXTE["serper_api_key"], type="password", value=SERPER_API_KEY or "")
    elif such_anbieter == "bing":
        api_key = st.sidebar.text_input(UI_TEXTE["bing_api_key"], type="password", value=BING_API_KEY or "")

    st.sidebar.info(UI_TEXTE["cache_info"])

    return {
        'tesseract_pfad': tesseract_pfad,
        'tessdata_pfad': tessdata_pfad,
        'poppler_pfad': poppler_pfad,
        'ocr_sprache': ocr_sprache,
        'ocr_dpi': ocr_dpi,
        'such_verzoegerung': such_verzoegerung,
        'max_ergebnisse': max_ergebnisse,
        'verwende_async': verwende_async,
        'fallback_aktiv': fallback_aktiv,
        'such_anbieter': such_anbieter,
        'serper_api_key': api_key if such_anbieter == "serper" else None,
        'bing_api_key': api_key if such_anbieter == "bing" else None,
    }

def manuelle_dateneingabe() -> None:
    """Ermöglicht die manuelle Eingabe von Produkten."""
    st.subheader(UI_TEXTE["manual_entry"])
    anzahl = st.number_input(UI_TEXTE["num_products_manual"], min_value=1, max_value=50, value=3)
    produkte = []
    for i in range(anzahl):
        with st.expander(f"{UI_TEXTE['product']} {i+1}"):
            col1, col2 = st.columns(2)
            with col1:
                menge = st.number_input(f"{UI_TEXTE['quantity_abbr']} {i+1}", min_value=1, value=1, key=f"menge_{i}")
                artikel_nr = st.text_input(f"{UI_TEXTE['article_no_abbr']} {i+1}", key=f"art_{i}")
            with col2:
                beschreibung = st.text_input(f"{UI_TEXTE['description_abbr']} {i+1}", key=f"beschr_{i}")
            if artikel_nr:
                bereinigt = bereinige_artikelnummer(artikel_nr)
                if bereinigt:
                    produkte.append({
                        'Menge': menge,
                        'Artikel-Nr.': bereinigt,
                        'Beschreibung': beschreibung if beschreibung else ""
                    })
                else:
                    st.warning(f"{UI_TEXTE['invalid_article']}: {artikel_nr}")
    if produkte and st.button(UI_TEXTE["take_over"]):
        df = pd.DataFrame(produkte)
        st.session_state.extrahierte_elemente = df
        st.success(f"{len(produkte)} Produkte übernommen")

def einzel_suche(idx: int, zeile: pd.Series, konfig: Dict[str, Any], spalten_map: Dict[str, str]) -> None:
    """Führt eine Suche für eine einzelne Zeile durch."""
    artikel_spalte = spalten_map.get('artikel_nr', 'Artikel-Nr.')
    if artikel_spalte not in zeile or pd.isna(zeile[artikel_spalte]) or not zeile[artikel_spalte]:
        st.error("Keine Artikelnummer für diese Position verfügbar")
        return
    artikel_nr = str(zeile[artikel_spalte]).strip()
    bereinigt = bereinige_artikelnummer(artikel_nr)
    if not bereinigt:
        st.error(f"{UI_TEXTE['invalid_article']}: {artikel_nr}")
        return
    with st.spinner(f"{UI_TEXTE['searching']} {bereinigt} ..."):
        kandidaten = suche_conrad_nach_artikelnummer(bereinigt, konfig)
        st.session_state.such_ergebnisse[idx] = kandidaten
        if not kandidaten:
            st.warning(f"{UI_TEXTE['no_results_for']} {bereinigt}")

def massen_suche(df: pd.DataFrame, konfig: Dict[str, Any], spalten_map: Dict[str, str]) -> None:
    """Führt eine Suche für alle Zeilen durch (mit Verzögerung)."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    artikel_spalte = spalten_map.get('artikel_nr', 'Artikel-Nr.')
    gesamt = len(df)
    for idx, zeile in df.iterrows():
        status_text.text(UI_TEXTE["search_progress"].format(idx+1, gesamt))
        if artikel_spalte in zeile and pd.notna(zeile[artikel_spalte]) and zeile[artikel_spalte]:
            artikel_nr = str(zeile[artikel_spalte]).strip()
            bereinigt = bereinige_artikelnummer(artikel_nr)
            if bereinigt:
                kandidaten = suche_conrad_nach_artikelnummer(bereinigt, konfig)
                st.session_state.such_ergebnisse[idx] = kandidaten
            else:
                st.session_state.such_ergebnisse[idx] = []
        else:
            st.session_state.such_ergebnisse[idx] = []
        time.sleep(konfig['such_verzoegerung'])
        progress_bar.progress((idx+1) / gesamt)
    status_text.text(UI_TEXTE["status_complete"])

def zeige_suchergebnisse(idx: int, konfig: Dict[str, Any]) -> None:
    """Zeigt die Suchergebnisse für eine bestimmte Zeile an und erlaubt Auswahl."""
    ergebnisse = st.session_state.such_ergebnisse.get(idx, [])
    if not ergebnisse:
        st.write(UI_TEXTE["no_results"])
        return
    optionen = []
    for res in ergebnisse:
        quelle_info = ""
        if res.get('quelle') == 'web_fallback':
            quelle_info = f" [{UI_TEXTE['source_fallback']}]"
        elif res.get('quelle') in ('serper_api', 'bing_api'):
            quelle_info = f" [{UI_TEXTE['source_api']}]"
        elif res.get('quelle') == 'conrad_direkt':
            quelle_info = f" [{UI_TEXTE['source_conrad']}]"
        option_text = f"{res['titel']} | {res['artikel_nr']} | {res['preis'] or 'Preis unbekannt'}{quelle_info}"
        optionen.append(option_text)

    ausgew_index = st.radio(
        f"{UI_TEXTE['choose_product']} #{idx+1}:",
        range(len(optionen)),
        format_func=lambda i: optionen[i],
        key=f"auswahl_{idx}"
    )
    if ausgew_index is not None and ausgew_index < len(ergebnisse):
        ausgewaehlt = ergebnisse[ausgew_index]
        st.session_state.ausgewaehlte_produkte[idx] = ausgewaehlt
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{UI_TEXTE['product_title']}:** {ausgewaehlt['titel']}")
            st.write(f"**{UI_TEXTE['conrad_number']}:** {ausgewaehlt['artikel_nr']}")
            st.write(f"**{UI_TEXTE['price']}:** {ausgewaehlt['preis'] or 'N/A'}")
            st.write(f"**{UI_TEXTE['source_label']}:** {ausgewaehlt.get('quelle', 'unbekannt')}")
        with col2:
            st.markdown(
                f'<a href="{ausgewaehlt["url"]}" target="_blank">'
                f'<button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">'
                f'{UI_TEXTE["open_new_tab"]}'
                f'</button></a>',
                unsafe_allow_html=True
            )

def erstelle_endgueltigen_dataframe(original_df: pd.DataFrame, spalten_map: Dict[str, str]) -> pd.DataFrame:
    """
    Erstellt einen DataFrame mit den ursprünglichen Daten plus den ausgewählten Produktinformationen.
    """
    enddaten = []
    for idx, zeile in original_df.iterrows():
        zeile_dict = zeile.to_dict()
        if idx in st.session_state.ausgewaehlte_produkte:
            sel = st.session_state.ausgewaehlte_produkte[idx]
            zeile_dict['Gewählte Conrad URL'] = sel['url']
            zeile_dict['Gewählte Bestell-Nr.'] = sel['artikel_nr']
            zeile_dict['Gewählter Titel'] = sel['titel']
            zeile_dict['Gewählter Preis'] = sel['preis'] or ''
            zeile_dict['Status'] = 'Gefunden'
            zeile_dict['Quelle'] = sel.get('quelle', 'conrad_direkt')
        else:
            zeile_dict['Gewählte Conrad URL'] = ''
            zeile_dict['Gewählte Bestell-Nr.'] = ''
            zeile_dict['Gewählter Titel'] = ''
            zeile_dict['Gewählter Preis'] = ''
            zeile_dict['Status'] = UI_TEXTE['not_found']
            zeile_dict['Quelle'] = ''
        enddaten.append(zeile_dict)
    return pd.DataFrame(enddaten)

# ------------------------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Conrad Produktfinder",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title(UI_TEXTE["title"])
    st.markdown(f"### {UI_TEXTE['subtitle']}")
    init_session_state()

    konfig = sidebar_konfiguration()

    # Datenquelle auswählen
    datenquellen = [UI_TEXTE["csv_option"]]
    if OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        datenquellen.append(UI_TEXTE["pdf_option"])
    datenquellen.append(UI_TEXTE["manual_option"])
    quelle = st.radio(UI_TEXTE["data_source"], datenquellen, horizontal=True)

    if quelle == UI_TEXTE["csv_option"]:
        hochgeladene_datei = st.file_uploader(UI_TEXTE["file_upload"], type=['csv'], help=UI_TEXTE['csv_help'])
        if hochgeladene_datei is not None:
            df = pd.read_csv(hochgeladene_datei)
            st.session_state.extrahierte_elemente = df
    elif quelle == UI_TEXTE["pdf_option"] and OCR_SUPPORT and PDF2IMAGE_SUPPORT:
        hochgeladene_datei = st.file_uploader(UI_TEXTE["file_upload"], type=['pdf'], help=UI_TEXTE['pdf_help'])
        if hochgeladene_datei is not None:
            df = pdf_zu_dataframe(hochgeladene_datei.getvalue(), konfig)
            if df is not None:
                st.session_state.extrahierte_elemente = df
    elif quelle == UI_TEXTE["manual_option"]:
        manuelle_dateneingabe()

    # Verarbeitung der extrahierten Daten
    if st.session_state.extrahierte_elemente is not None:
        df = st.session_state.extrahierte_elemente
        st.subheader(UI_TEXTE["preview_data"])
        st.dataframe(df, use_container_width=True)
        st.write(f"{len(df)} {UI_TEXTE['items_found']}")

        # Spaltenzuordnung
        st.subheader(UI_TEXTE["column_mapping"])
        st.write(UI_TEXTE["map_columns"])
        spalten = list(df.columns)
        col1, col2, col3 = st.columns(3)
        with col1:
            menge_map = st.selectbox(UI_TEXTE["quantity"], [''] + spalten, key="menge_map")
        with col2:
            artikel_map = st.selectbox(UI_TEXTE["article_no"], [''] + spalten, key="artikel_map")
        with col3:
            beschr_map = st.selectbox(UI_TEXTE["description"], [''] + spalten, key="beschr_map")

        spalten_zuordnung = {
            'menge': menge_map if menge_map else 'Menge',
            'artikel_nr': artikel_map if artikel_map else 'Artikel-Nr.',
            'beschreibung': beschr_map if beschr_map else 'Beschreibung'
        }
        if st.button(UI_TEXTE["apply_mapping"]):
            st.session_state.spalten_zuordnung = spalten_zuordnung
            st.success("Zuordnung angewendet")

        if st.session_state.spalten_zuordnung:
            st.subheader("🔍 Produktsuche")
            if st.button(UI_TEXTE["search_all"], type="primary"):
                massen_suche(df, konfig, st.session_state.spalten_zuordnung)

            # Einzelne Positionen anzeigen
            for idx, zeile in df.iterrows():
                artikel_spalte = st.session_state.spalten_zuordnung.get('artikel_nr', 'Artikel-Nr.')
                artikel_nr = zeile.get(artikel_spalte, 'Keine Artikelnr.')
                with st.expander(f"Position {idx+1}: Artikelnr. {artikel_nr}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{UI_TEXTE['quantity']}:** {zeile.get(st.session_state.spalten_zuordnung.get('menge', 'Menge'), 'N/A')}")
                        st.write(f"**{UI_TEXTE['article_no']}:** {artikel_nr}")
                        beschr = zeile.get(st.session_state.spalten_zuordnung.get('beschreibung', 'Beschreibung'), '')
                        if beschr:
                            st.write(f"**{UI_TEXTE['description']}:** {beschr}")
                    with col2:
                        if st.button(UI_TEXTE["search_row"], key=f"suche_{idx}"):
                            einzel_suche(idx, zeile, konfig, st.session_state.spalten_zuordnung)
                    if idx in st.session_state.such_ergebnisse:
                        zeige_suchergebnisse(idx, konfig)

            if st.session_state.ausgewaehlte_produkte:
                st.subheader(UI_TEXTE["final_selection"])
                st.write(f"{len(st.session_state.ausgewaehlte_produkte)} {UI_TEXTE['selected_products_count']}")
                final_df = erstelle_endgueltigen_dataframe(df, st.session_state.spalten_zuordnung)
                st.dataframe(final_df, use_container_width=True)
                # CSV-Download
                csv = final_df.to_csv(index=False, encoding='utf-8-sig')
                b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="conrad_bestellung.csv">{UI_TEXTE["download_csv"]}</a>'
                st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
