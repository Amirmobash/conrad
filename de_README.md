
em Poppler bin-Verzeichnis (enthält pdftoppm.exe)

Diese Pfade werden später in der Streamlit-Seitenleiste eingetragen (siehe Konfiguration).

Konfiguration
Die gesamte Konfiguration erfolgt über die Seitenleiste der Streamlit-App. Erweitern Sie die Seitenleiste (oben links), um auf die Einstellungen zuzugreifen.

OCR-Konfiguration
Pfad zu Tesseract – Vollständiger Pfad zur tesseract.exe.
Standard (Windows): C:\Program Files\Tesseract-OCR\tesseract.exe

Pfad zum tessdata-Ordner – Pfad zum Ordner mit den Sprachdateien.
Standard: C:\Program Files\Tesseract-OCR\tessdata

Pfad zu Poppler – Pfad zu den Poppler-Binaries (enthält pdftoppm.exe).
Standard: C:\poppler\poppler-23.11.0\Library\bin

OCR-Sprache – Sprache(n) für die Texterkennung.
Optionen: deu+eng, deu, eng (empfohlen: deu+eng für deutsche PDFs).

OCR-DPI – Auflösung für die Umwandlung von PDF-Seiten in Bilder. Höhere DPI verbessern die Erkennung, verlangsamen aber die Verarbeitung.
Optionen: 200–400 (Standard: 300).

Such-Einstellungen
Verzögerung zwischen Suchanfragen (Sekunden) – Um Ratenlimits zu vermeiden.
Standard: 2,0 Sekunden.

Maximale Suchergebnisse pro Produkt – Anzahl der Kandidaten-Produkte pro Artikelnummer.
Standard: 5.

Websuche-Fallback
Fallback-Suche aktivieren – Schaltet die Websuche ein, falls die Conrad-Suche keine Ergebnisse liefert.

Suchanbieter – Auswahl der Fallback-Suchmaschine:

DuckDuckGo (kein API-Key erforderlich)

Serper.dev (Google Search API) – erfordert API-Key

Bing Web Search (Azure) – erfordert API-Key

API-Keys – Geben Sie den benötigten Key ein, wenn Sie Serper.dev oder Bing verwenden.

Nutzung
1. App starten
Führen Sie im Projektverzeichnis (mit aktivierter virtueller Umgebung) aus:

bash
streamlit run app.py
Die App öffnet sich in Ihrem Standard-Webbrowser (meist http://localhost:8501).

2. Datenquelle wählen
Wählen Sie oben in der App eine der folgenden Optionen (per Radiobutton):

CSV hochladen

Laden Sie eine .csv-Datei hoch, die Artikelnummern (und optional Menge, Beschreibung) enthält.

Die App liest die CSV in einen DataFrame ein.

PDF hochladen (OCR) (nur sichtbar, wenn OCR verfügbar ist)

Laden Sie eine Conrad-Bestell- oder Warenkorb-PDF hoch.

Die App führt eine OCR durch und extrahiert Conrad-Artikelnummern (Bestell-Nr. / Artikel-Nr.).

Es wird eine einfache Tabelle erstellt mit:

Menge = 1 (Standard)

Artikel-Nr. = extrahierte Nummer

Beschreibung = leer

Eine Erfolgsmeldung zeigt die Anzahl der extrahierten Artikelnummern.

Manuelle Eingabe

Geben Sie die Anzahl der Produkte ein (max. 50).

Für jedes Produkt tragen Sie ein:

Menge

Artikelnummer

Optionale Beschreibung

Klicken Sie auf „Produkte übernehmen“, um sie zu speichern.

3. Extrahierte Daten ansehen
Ein DataFrame zeigt alle extrahierten / manuell eingegebenen Zeilen.

Die Gesamtzahl der Elemente wird angezeigt.

4. Spalten zuordnen (nur CSV)
Wenn Sie eine CSV hochgeladen haben, können Ihre Spaltennamen von den erwarteten Bezeichnungen (Menge, Artikel-Nr., Beschreibung) abweichen. Weisen Sie mit den Dropdowns zu:

Menge-Spalte

Conrad Artikel-Nr.-Spalte

Beschreibung-Spalte (optional)

Klicken Sie auf „Übernehmen“, um die Zuordnung zu speichern. Sie wird für die nachfolgenden Suchläufe verwendet.

5. Produkte suchen
Sie haben zwei Suchoptionen:

„Alle Positionen suchen“ – Führt eine Massensuche für alle Artikelnummern durch (unter Beachtung der eingestellten Verzögerung).

Einzelne Suche pro Zeile – Klappen Sie eine Zeile aus (z. B. Position 1: Artikelnr. 1234567) und klicken Sie auf „Diese Position suchen“, um nur diese Artikelnummer zu durchsuchen.

Während der Suche:

Die Artikelnummer wird bereinigt (Nicht-Ziffern und Suffixe werden entfernt).

Die App fragt Conrad mit der Artikelnummer ab.

Falls keine direkten Ergebnisse gefunden werden und der Fallback aktiviert ist, wird eine Websuche nach Conrad-Produktseiten gestartet.

Fortschrittsbalken und Statusmeldungen zeigen den aktuellen Suchfortschritt an.

6. Ergebnisse prüfen und auswählen
Nach der Suche erscheint für jede Zeile:

