# 🔍 Conrad Produktfinder – Bestellungen wiederfinden

Eine **Streamlit**-Webanwendung, die Ihnen hilft, **Conrad-Bestellungen zu rekonstruieren**, indem sie Conrad-Artikelnummern aus CSV- oder PDF-Dokumenten extrahiert und mit aktuellen Produktseiten auf [conrad.de](https://www.conrad.de) abgleicht.  
Die App unterstützt OCR für gescannte PDFs und kann optional auf Websuche zurückgreifen, wenn die Conrad-Suche keine Ergebnisse liefert.

**Autor:** Amir Mobasheraghdam

---

## Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Technologie-Stack](#technologie-stack)
- [Projektstruktur](#projektstruktur)
- [Installation](#installation)
  - [Python-Abhängigkeiten](#python-abhängigkeiten)
  - [Systemabhängigkeiten](#systemabhängigkeiten)
- [Konfiguration](#konfiguration)
- [Nutzung](#nutzung)
  - [1. App starten](#1-app-starten)
  - [2. Datenquelle wählen](#2-datenquelle-wählen)
  - [3. Extrahierte Daten ansehen](#3-extrahierte-daten-ansehen)
  - [4. Spalten zuordnen (nur CSV)](#4-spalten-zuordnen-nur-csv)
  - [5. Produkte suchen](#5-produkte-suchen)
  - [6. Ergebnisse prüfen und auswählen](#6-ergebnisse-prüfen-und-auswählen)
  - [7. Endgültige Auswahl exportieren](#7-endgültige-auswahl-exportieren)
- [Einschränkungen & Hinweise](#einschränkungen--hinweise)
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

---

## Funktionen

- **Mehrere Eingabequellen**
  - **CSV-Datei** hochladen (beliebige Spalten, z. B. Menge, Artikelnummer, Beschreibung).
  - **Conrad-Bestell-/Warenkorb-PDF** hochladen (OCR extrahiert automatisch Artikelnummern).
  - **Manuelle Eingabe** – Artikelnummern direkt im UI eintragen.

- **OCR-Unterstützung für PDFs**
  - Nutzt **Tesseract OCR** über `pytesseract`.
  - Wandelt PDF-Seiten mit `pdf2image` in Bilder um.
  - Konfigurierbare DPI und OCR-Sprache (Deutsch/Englisch).

- **Conrad-Produktsuche nach Artikelnummer**
  - Durchsucht `conrad.de` mit der Artikelnummer.
  - Parst Suchergebnisseiten und Produktseiten mit **BeautifulSoup**.
  - Extrahiert Produkt-URL, Titel, Artikelnummer und Preis (falls verfügbar).
  - Einfaches Relevanz-Ranking der Ergebnisse.

- **Websuche als Fallback (optional)**
  - Falls die direkte Conrad-Suche nichts findet, kann die App folgende Quellen nutzen:
    - **DuckDuckGo HTML-Suche** (kein API-Key nötig)
    - **Serper.dev** (Google Search API, kostenpflichtig)
    - **Bing Web Search** (Azure, kostenpflichtig)
  - Es werden nur Conrad-Produkt-URLs aus den Suchergebnissen übernommen.

- **Interaktive Benutzeroberfläche**
  - Entwickelt mit **Streamlit**.
  - Seitenleiste zur Konfiguration von OCR und Suchverhalten.
  - Pro Zeile ein ausklappbarer Bereich, um jedes Eingabelement zu prüfen.
  - Anzeige aller Kandidaten-Produkte pro Zeile – einfache Auswahl per Radiobutton.
  - Ausgewähltes Produkt kann in einem neuen Browser-Tab geöffnet werden.

- **Export der endgültigen Auswahl**
  - Nach der Produktauswahl wird eine finale CSV erstellt mit:
    - Ursprünglichen Daten (Menge, Artikelnummer, Beschreibung etc.)
    - Gewählter Conrad-URL
    - Gewählter Bestellnummer
    - Gewähltem Titel
    - Gewähltem Preis
    - Status (Gefunden / Nicht gefunden)
    - Quelle (Conrad direkt / Web-Fallback / API)

---

## Technologie-Stack

- **Python** 3.8+
- **Streamlit** – Web-Framework für die UI
- **Pandas** – Datenverarbeitung für CSV/Zeilen
- **Requests** – HTTP-Anfragen an Conrad und Websuche
- **BeautifulSoup (bs4)** – HTML-Parsing
- **pdf2image** – Konvertierung von PDF-Seiten in Bilder (für OCR)
- **pytesseract** – Schnittstelle zur Tesseract-OCR-Engine
- **Pillow (PIL)** – Bildverarbeitung
- **lxml** – Backend für HTML-Parsing (schneller)

Alle Python-Abhängigkeiten sind in `requirements.txt` aufgeführt.

---

## Projektstruktur

```text
.
├── app.py             # Hauptanwendung (Conrad Produktfinder)
├── requirements.txt   # Python-Abhängigkeiten
└── README.md          # Projektdokumentation (diese Datei)
```

---

## Installation

### Python-Abhängigkeiten

1. **Repository klonen** (oder Quellcode herunterladen):
   ```bash
   git clone https://github.com/<dein-benutzername>/conrad-product-finder.git
   cd conrad-product-finder
   ```

2. **Virtuelle Umgebung erstellen und aktivieren** (empfohlen):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Python-Pakete installieren**:
   ```bash
   pip install -r requirements.txt
   ```

   Die `requirements.txt` enthält:
   ```
   streamlit
   pandas
   requests
   beautifulsoup4
   lxml
   pdf2image
   pytesseract
   pillow
   ```

### Systemabhängigkeiten

Die App benötigt **Tesseract OCR** und **Poppler** (für PDF-zu-Bild-Konvertierung). Beide müssen separat installiert werden.

#### Tesseract OCR

- **Windows**:
  - Lade das Installationsprogramm von [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) herunter.
  - Installiere es an einem bekannten Ort (z. B. `C:\Program Files\Tesseract-OCR`).
  - Achte darauf, dass die Sprachpakete **Deutsch** und **Englisch** mitinstalliert werden (`.traineddata`-Dateien).
- **macOS**:
  ```bash
  brew install tesseract
  brew install tesseract-lang   # für zusätzliche Sprachen
  ```
- **Linux** (Debian/Ubuntu):
  ```bash
  sudo apt update
  sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng
  ```

#### Poppler

- **Windows**:
  - Lade das aktuelle Binary-Paket von [poppler für Windows](http://blog.alivate.com.au/poppler-windows/) herunter.
  - Entpacke es in einen Ordner (z. B. `C:\poppler\poppler-23.11.0\Library\bin`).
- **macOS**:
  ```bash
  brew install poppler
  ```
- **Linux**:
  ```bash
  sudo apt install poppler-utils
  ```

Nach der Installation notieren Sie sich die Pfade zu:
- `tesseract.exe` (oder dem ausführbaren Tesseract-Programm)
- Dem `tessdata`-Verzeichnis (enthält die `.traineddata`-Sprachdateien)
- Dem Poppler `bin`-Verzeichnis (enthält `pdftoppm.exe`)

Diese Pfade werden später in der Streamlit-Seitenleiste eingetragen (siehe [Konfiguration](#konfiguration)).

---

## Konfiguration

Die gesamte Konfiguration erfolgt über die **Seitenleiste** der Streamlit-App. Erweitern Sie die Seitenleiste (oben links), um auf die Einstellungen zuzugreifen.

### OCR-Konfiguration

- **Pfad zu Tesseract** – Vollständiger Pfad zur `tesseract.exe`.  
  *Standard (Windows):* `C:\Program Files\Tesseract-OCR\tesseract.exe`
- **Pfad zum tessdata-Ordner** – Pfad zum Ordner mit den Sprachdateien.  
  *Standard:* `C:\Program Files\Tesseract-OCR\tessdata`
- **Pfad zu Poppler** – Pfad zu den Poppler-Binaries (enthält `pdftoppm.exe`).  
  *Standard:* `C:\poppler\poppler-23.11.0\Library\bin`
- **OCR-Sprache** – Sprache(n) für die Texterkennung.  
  *Optionen:* `deu+eng`, `deu`, `eng` (empfohlen: `deu+eng` für deutsche PDFs).
- **OCR-DPI** – Auflösung für die Umwandlung von PDF-Seiten in Bilder. Höhere DPI verbessern die Erkennung, verlangsamen aber die Verarbeitung.  
  *Optionen:* 200–400 (Standard: 300).

### Such-Einstellungen

- **Verzögerung zwischen Suchanfragen (Sekunden)** – Um Ratenlimits zu vermeiden.  
  *Standard:* 2,0 Sekunden.
- **Maximale Suchergebnisse pro Produkt** – Anzahl der Kandidaten-Produkte pro Artikelnummer.  
  *Standard:* 5.

### Websuche-Fallback

- **Fallback-Suche aktivieren** – Schaltet die Websuche ein, falls die Conrad-Suche keine Ergebnisse liefert.
- **Suchanbieter** – Auswahl der Fallback-Suchmaschine:
  - **DuckDuckGo** (kein API-Key erforderlich)
  - **Serper.dev** (Google Search API) – erfordert API-Key
  - **Bing Web Search** (Azure) – erfordert API-Key
- **API-Keys** – Geben Sie den benötigten Key ein, wenn Sie Serper.dev oder Bing verwenden.

---

## Nutzung

### 1. App starten

Führen Sie im Projektverzeichnis (mit aktivierter virtueller Umgebung) aus:

```bash
streamlit run app.py
```

Die App öffnet sich in Ihrem Standard-Webbrowser (meist `http://localhost:8501`).

### 2. Datenquelle wählen

Wählen Sie oben in der App eine der folgenden Optionen (per Radiobutton):

- **CSV hochladen**
  - Laden Sie eine `.csv`-Datei hoch, die Artikelnummern (und optional Menge, Beschreibung) enthält.
  - Die App liest die CSV in einen DataFrame ein.

- **PDF hochladen (OCR)** (nur sichtbar, wenn OCR verfügbar ist)
  - Laden Sie eine Conrad-Bestell- oder Warenkorb-PDF hoch.
  - Die App führt eine OCR durch und extrahiert **Conrad-Artikelnummern** (Bestell-Nr. / Artikel-Nr.).
  - Es wird eine einfache Tabelle erstellt mit:
    - `Menge` = 1 (Standard)
    - `Artikel-Nr.` = extrahierte Nummer
    - `Beschreibung` = leer
  - Eine Erfolgsmeldung zeigt die Anzahl der extrahierten Artikelnummern.

- **Manuelle Eingabe**
  - Geben Sie die Anzahl der Produkte ein (max. 50).
  - Für jedes Produkt tragen Sie ein:
    - Menge
    - Artikelnummer
    - Optionale Beschreibung
  - Klicken Sie auf **„Produkte übernehmen“**, um sie zu speichern.

### 3. Extrahierte Daten ansehen

- Ein DataFrame zeigt alle extrahierten / manuell eingegebenen Zeilen.
- Die Gesamtzahl der Elemente wird angezeigt.

### 4. Spalten zuordnen (nur CSV)

Wenn Sie eine CSV hochgeladen haben, können Ihre Spaltennamen von den erwarteten Bezeichnungen (`Menge`, `Artikel-Nr.`, `Beschreibung`) abweichen. Weisen Sie mit den Dropdowns zu:

- **Menge**-Spalte
- **Conrad Artikel-Nr.**-Spalte
- **Beschreibung**-Spalte (optional)

Klicken Sie auf **„Übernehmen“**, um die Zuordnung zu speichern. Sie wird für die nachfolgenden Suchläufe verwendet.

### 5. Produkte suchen

Sie haben zwei Suchoptionen:

- **„Alle Positionen suchen“** – Führt eine Massensuche für alle Artikelnummern durch (unter Beachtung der eingestellten Verzögerung).
- **Einzelne Suche pro Zeile** – Klappen Sie eine Zeile aus (z. B. `Position 1: Artikelnr. 1234567`) und klicken Sie auf **„Diese Position suchen“**, um nur diese Artikelnummer zu durchsuchen.

Während der Suche:

- Die Artikelnummer wird bereinigt (Nicht-Ziffern und Suffixe werden entfernt).
- Die App fragt Conrad mit der Artikelnummer ab.
- Falls keine direkten Ergebnisse gefunden werden und der Fallback aktiviert ist, wird eine Websuche nach Conrad-Produktseiten gestartet.

Fortschrittsbalken und Statusmeldungen zeigen den aktuellen Suchfortschritt an.

### 6. Ergebnisse prüfen und auswählen

Nach der Suche erscheint für jede Zeile:

- Eine Liste von Kandidaten-Produkten als Radiobuttons. Jeder Kandidat zeigt:
  - Titel
  - Artikelnummer
  - Preis (falls verfügbar)
  - Quelle (z. B. `[Web-Fallback]`, `[Serper API]` usw.)
- Wählen Sie das richtige Produkt durch Anklicken des Radiobuttons aus.
- Eine Vorschau des ausgewählten Produkts erscheint mit:
  - Titel
  - Conrad-Artikelnummer
  - Preis
  - Quelle
  - Ein Button **„In neuem Tab öffnen“**, um die Produktseite direkt aufzurufen.

Ihre Auswahl wird in der Session gespeichert.

### 7. Endgültige Auswahl exportieren

Sobald Sie für einige (oder alle) Zeilen Produkte ausgewählt haben, erscheint der Abschnitt **„Finale Auswahl“**.

- Ein finaler DataFrame wird angezeigt, der enthält:
  - Alle ursprünglichen Spalten (aus CSV / manueller Eingabe)
  - **Gewählte Conrad URL** – die URL des ausgewählten Produkts
  - **Gewählte Bestell-Nr.** – die ausgewählte Artikelnummer
  - **Gewählter Titel** – Produkttitel
  - **Gewählter Preis** – Produktpreis
  - **Status** – „Gefunden“ oder „Nicht gefunden“
  - **Quelle** – Herkunft des Ergebnisses (z. B. `conrad_direkt`, `web_fallback` usw.)

- Klicken Sie auf den Link **„CSV herunterladen“**, um die finalen Daten als `conrad_bestellung.csv` zu speichern (UTF‑8 mit BOM für Excel-Kompatibilität).

---

## Einschränkungen & Hinweise

- Die App ist abhängig von der **HTML-Struktur** von `conrad.de` und der jeweiligen Suchmaschine. Bei Änderungen des Seitenaufbaus kann das Scraping fehlschlagen.
- **OCR-Qualität** hängt stark ab von:
  - Scan-Qualität des PDFs
  - DPI-Einstellung
  - Korrekter Tesseract-Installation und Vorhandensein der Sprachdateien
- **Netzwerkzugriff** ist erforderlich für:
  - Conrad-Suche
  - Websuche-Fallback (DuckDuckGo / Serper.dev / Bing)
- Die App zielt standardmäßig nur auf **Conrad Deutschland** (`conrad.de`) ab.
- Die Anwendung ist für die **nicht-kommerzielle Nutzung** gedacht. Bitte beachten Sie die Nutzungsbedingungen der durchsuchten Websites und setzen Sie angemessene Verzögerungen ein, um die Server nicht zu überlasten.

---

## Mitwirken

Beiträge sind herzlich willkommen! Ideen für Verbesserungen:

- Bessere Fehlerbehandlung und Logging.
- Robustere Parsing-Logik für Conrad-Seiten (mehr Selektoren).
- Unterstützung weiterer Exportformate (Excel, JSON).
- Mehrsprachigkeit der Benutzeroberfläche (Deutsch/Englisch umschaltbar).
- Verbessertes Relevanz-Ranking (z. B. Fuzzy-Matching von Titeln).

Bitte eröffnen Sie ein Issue oder reichen Sie einen Pull Request im [GitHub-Repository](https://github.com/<dein-benutzername>/conrad-product-finder) ein.

---

## Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert – siehe die Datei [LICENSE](LICENSE) für Details.

---

## Autor

**Amir Mobasheraghdam**  
Letztes Update: 2026-04-06 | Version 4.0
```
