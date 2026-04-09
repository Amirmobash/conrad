# 🔍 Conrad Produktfinder – Bestellungen wiederfinden

Eine **Streamlit**-Webanwendung, die Ihnen hilft, **Conrad-Bestellungen zu rekonstruieren**, indem sie Conrad-Artikelnummern aus CSV‑, PDF‑Dokumenten oder per Webcam extrahiert und automatisch mit aktuellen Produktseiten auf [conrad.de](https://www.conrad.de) abgleicht.  
Die App unterstützt OCR für gescannte PDFs und kann optional auf Websuche zurückgreifen, wenn die direkte Conrad-Suche keine Ergebnisse liefert.

**Autor:** Amir Mobasheraghdam  
**Letztes Update:** 2026-04-09 | Version 7.0

---

## 📌 Inhaltsverzeichnis

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
  - [3. Automatische Suche](#3-automatische-suche)
  - [4. Ergebnisse prüfen und auswählen](#4-ergebnisse-prüfen-und-auswählen)
  - [5. Export der finalen Auswahl](#5-export-der-finalen-auswahl)
- [Einschränkungen & Hinweise](#einschränkungen--hinweise)
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

---

## ✨ Funktionen

- **Mehrere Eingabequellen**
  - **CSV-Datei** hochladen (beliebige Spalten, z. B. Menge, Artikelnummer, Beschreibung).
  - **Conrad-Bestell-/Warenkorb-PDF** hochladen – OCR extrahiert automatisch Artikelnummern.
  - **Manuelle Eingabe** – Artikelnummern direkt im UI eintragen.
  - **Webcam-Scanner** – Barcode oder gedruckte Artikelnummer erkennen und zur Liste hinzufügen.

- **OCR-Unterstützung für PDFs und Bilder**
  - Nutzt **Tesseract OCR** über `pytesseract`.
  - Wandelt PDF-Seiten mit `pdf2image` in Bilder um.
  - Konfigurierbare DPI und OCR-Sprache (Deutsch/Englisch).

- **Automatische Conrad-Produktsuche**
  - Durchsucht `conrad.de` mit der Artikelnummer.
  - Parst Suchergebnisseiten und Produktseiten mit **BeautifulSoup**.
  - Extrahiert Produkt-URL, Titel, Artikelnummer und Preis (falls verfügbar).
  - Intelligentes Relevanz-Ranking der Ergebnisse.

- **Websuche als Fallback (optional)**
  - Falls die direkte Conrad-Suche nichts findet, können folgende Quellen genutzt werden:
    - **DuckDuckGo HTML-Suche** (kein API-Key nötig)
    - **Serper.dev** (Google Search API, kostenpflichtig)
    - **Bing Web Search** (Azure, kostenpflichtig)
  - Es werden nur Conrad-Produkt-URLs aus den Suchergebnissen übernommen.

- **Vollautomatischer Ablauf**
  - Nach dem Hochladen einer Datei oder dem Scannen startet die Suche **sofort** – kein zusätzlicher Klick nötig.
  - Fortschrittsbalken und Statusmeldungen zeigen den aktuellen Suchfortschritt.

- **Interaktive Benutzeroberfläche**
  - Entwickelt mit **Streamlit**.
  - Seitenleiste zur Konfiguration von OCR, Suchverhalten und Fallback.
  - Pro Zeile ein ausklappbarer Bereich mit allen gefundenen Kandidaten.
  - Einfache Auswahl des richtigen Produkts per Radiobutton.
  - Direktes Öffnen der Produktseite in einem neuen Tab.

- **Export der endgültigen Auswahl**
  - Nach der Produktauswahl wird eine finale CSV erstellt mit:
    - Ursprünglichen Daten (Menge, Artikelnummer, Beschreibung etc.)
    - Gewählter Conrad-URL
    - Gewählter Bestellnummer
    - Gewähltem Titel
    - Gewähltem Preis
    - Status (Gefunden / Nicht gefunden)

---

## 🧰 Technologie-Stack

- **Python** 3.8+
- **Streamlit** – Web-Framework für die UI
- **Pandas** – Datenverarbeitung für CSV/Zeilen
- **aiohttp** – Asynchrone HTTP-Anfragen (schneller)
- **BeautifulSoup (bs4)** – HTML-Parsing
- **pdf2image** – Konvertierung von PDF-Seiten in Bilder (für OCR)
- **pytesseract** – Schnittstelle zur Tesseract-OCR-Engine
- **Pillow (PIL)** – Bildverarbeitung
- **pyzbar** – Barcode-Erkennung
- **PyPDF2** – Fallback für direkte Textextraktion aus PDFs

---

## 📁 Projektstruktur

```text
.
├── app.py                # Hauptanwendung (Conrad Produktfinder)
├── requirements.txt      # Python-Abhängigkeiten
└── README.md             # Projektdokumentation (diese Datei)
```

---

## 🛠 Installation

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
   aiohttp
   beautifulsoup4
   lxml
   pdf2image
   pytesseract
   pillow
   opencv-python
   pyzbar
   PyPDF2
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

## ⚙️ Konfiguration

Die gesamte Konfiguration erfolgt über die **Seitenleiste** der Streamlit-App.

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
  *Standard:* 0,5 Sekunden.
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

## 🚀 Nutzung

### 1. App starten

Führen Sie im Projektverzeichnis (mit aktivierter virtueller Umgebung) aus:

```bash
streamlit run app.py
```

Die App öffnet sich in Ihrem Standard-Webbrowser (meist `http://localhost:8501`).

### 2. Datenquelle wählen

Wählen Sie oben in der App eine der folgenden Optionen (per Radiobutton):

- **CSV hochladen** – Laden Sie eine `.csv`-Datei mit Artikelnummern hoch.
- **PDF hochladen (automatisch)** – Laden Sie eine Conrad-Bestell- oder Warenkorb-PDF hoch. Die App extrahiert alle Artikelnummern per OCR.
- **Manuelle Eingabe** – Geben Sie Menge und Artikelnummer direkt ein.
- **Webcam-Scanner** – Richten Sie die Kamera auf einen Barcode oder eine gedruckte Nummer. Klicken Sie auf „Foto aufnehmen“ – die erkannte Nummer wird zur Liste hinzugefügt.

### 3. Automatische Suche

- **Sobald die Daten geladen sind, startet die Suche automatisch für alle Artikelnummern.**
- Ein Fortschrittsbalken zeigt den Status jeder Zeile an.
- Die App fragt zuerst Conrad direkt ab; falls nichts gefunden wird und der Fallback aktiviert ist, folgt eine Websuche.
- Nach Abschluss erscheint die Meldung „Suche abgeschlossen“.

### 4. Ergebnisse prüfen und auswählen

- Für jede Zeile klappen Sie den Bereich aus.
- Sie sehen eine Liste von Kandidaten-Produkten (Titel, Artikelnummer, Preis, Quelle).
- Wählen Sie das richtige Produkt durch Anklicken des Radiobuttons aus.
- Eine Vorschau mit allen Details wird angezeigt, inklusive eines Buttons „In neuem Tab öffnen“.

### 5. Export der finalen Auswahl

- Sobald Sie für einige (oder alle) Zeilen Produkte ausgewählt haben, erscheint der Abschnitt **„Ausgewählte Produkte“**.
- Ein finaler DataFrame zeigt alle ursprünglichen Daten plus die gewählten Conrad-Informationen.
- Klicken Sie auf **„Ergebnis CSV herunterladen“**, um die finale Liste als `conrad_ergebnisse.csv` zu speichern (UTF‑8 mit BOM für Excel-Kompatibilität).

---

## ⚠️ Einschränkungen & Hinweise

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

## 🤝 Mitwirken

Beiträge sind herzlich willkommen! Ideen für Verbesserungen:

- Bessere Fehlerbehandlung und Logging.
- Robustere Parsing-Logik für Conrad-Seiten (mehr Selektoren).
- Unterstützung weiterer Exportformate (Excel, JSON).
- Mehrsprachigkeit der Benutzeroberfläche (Deutsch/Englisch umschaltbar).
- Verbessertes Relevanz-Ranking (z. B. Fuzzy-Matching von Titeln).

Bitte eröffnen Sie ein Issue oder reichen Sie einen Pull Request im [GitHub-Repository](https://github.com/<dein-benutzername>/conrad-product-finder) ein.

---

## 📄 Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert – siehe die Datei [LICENSE](LICENSE) für Details.

---

## 👤 Autor

**Amir Mobasheraghdam**  
Letztes Update: 2026-04-09 | Version 7.0
```
