
````markdown
# Conrad Product Finder 🔍

A Streamlit web application that helps you **reconstruct Conrad orders** by extracting Conrad article numbers from CSV or PDF documents and matching them to current product pages on conrad.de. It supports OCR for scanned PDFs and can optionally fall back to web search if the Conrad search returns no results. :contentReference[oaicite:0]{index=0}

Author: **Amir Mobasheraghdam**

---

## Features

- **Multiple input sources**
  - Upload a **CSV** file containing article numbers and other columns
  - Upload a **Conrad order/cart PDF** (OCR is used to extract article numbers)
  - **Manual entry**: enter article numbers directly in the UI

- **OCR support for PDFs**
  - Uses **Tesseract OCR** via `pytesseract`
  - Uses **pdf2image** to convert PDF pages to images
  - Configurable DPI and OCR language (German/English)

- **Conrad product search by article number**
  - Searches conrad.de with the article number
  - Parses the search result page and product pages using **BeautifulSoup**
  - Extracts product URL, title, article number, and price (if available)
  - Basic relevance scoring to rank results

- **Web search fallback (optional)**
  - If no direct result is found on Conrad, the app can use:
    - DuckDuckGo HTML search (no API key required)
    - Serper.dev (Google Search API)
    - Bing Web Search (Azure)
  - Only Conrad product URLs are kept from the web search

- **Interactive UI**
  - Built with **Streamlit**
  - Sidebar configuration for OCR and search behavior
  - Per-row expanders to review each input item
  - For each row, view all candidate products and select the correct one
  - Open selected product in a new browser tab

- **Export of final selection**
  - After selecting products, export a final CSV with:
    - Original row data
    - Selected Conrad URL
    - Selected article number
    - Selected title
    - Selected price
    - Status (Found / Not found)
    - Source (Conrad / Web fallback)

---

## Tech Stack

- **Python**
- **Streamlit** – web UI framework
- **Pandas** – data handling for CSV/rows
- **Requests** – HTTP requests for Conrad and web search
- **BeautifulSoup (bs4)** – HTML parsing
- **pdf2image** – convert PDF pages to images (for OCR)
- **pytesseract** – OCR engine interface
- **Pillow (PIL)** – image handling
- **fuzzywuzzy + python-Levenshtein** – (available for possible fuzzy matching)
- **lxml** – HTML parsing backend

All Python dependencies are listed in `requirements.txt`. :contentReference[oaicite:1]{index=1}

---

## Project Structure

```text
.
├── app.py             # Main Streamlit app (Conrad Product Finder)
├── requirements.txt   # Python dependencies
└── README.md          # Project documentation (this file)
````

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install system dependencies

The app uses **Tesseract OCR** and **Poppler** for PDF → image conversion.

#### Tesseract

* Download and install Tesseract (e.g. on Windows):

  * Typical path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
* Make sure you have the required language data files (`.traineddata`) in the `tessdata` folder
  (German and English if you use `deu`/`eng`).

#### Poppler

* Install Poppler for your OS (Windows / macOS / Linux).
* On Windows, a typical path for the binaries is something like:

  * `C:\poppler\poppler-23.11.0\Library\bin`

You can adjust these paths later in the Streamlit sidebar.

---

## Configuration (in the UI)

All configuration is done via the **sidebar** in the Streamlit app. 

### OCR Configuration

* **Tesseract path**
  Default:
  `C:\Program Files\Tesseract-OCR\tesseract.exe`

* **tessdata path**
  Default:
  `C:\Program Files\Tesseract-OCR\tessdata`

* **Poppler path**
  Default:
  `C:\poppler\poppler-23.11.0\Library\bin`

* **OCR Language**

  * Options: `deu+eng`, `deu`, `eng`
  * Recommended: `deu+eng` for German Conrad PDFs.

* **OCR DPI**

  * Options: 200, 250, 300, 350, 400
  * Higher DPI = better quality but slower.

### Search Settings

* **Delay between search requests (seconds)**

  * Prevents hitting rate limits or overloading Conrad / web search.
* **Max results per product**

  * How many candidate products to fetch per article number.

### Web Search Fallback

* **Enable Fallback**

  * Toggle web search if Conrad search returns no results.

* **Search Provider**

  * DuckDuckGo (no API key)
  * Serper.dev (Google Search API)
  * Bing Web Search (Azure)

* **API keys (if needed)**

  * Serper.dev API key
  * Bing Web Search API key

---

## Usage

### 1. Run the app

From the project directory:

```bash
streamlit run app.py
```

This will start the Streamlit server and open the app in your web browser.

### 2. Choose data source

At the top of the app, select one of:

* **CSV upload**

  * Upload a `.csv` file with article numbers (and optionally quantity, description, etc.)

* **PDF upload** (if OCR support is available)

  * Upload a Conrad order/cart PDF.
  * The app runs OCR to extract **Conrad article numbers** (Bestell-Nr / Artikel-Nr).
  * It creates a simple table with quantity (default 1), article number, and empty description.

* **Manual entry**

  * Choose how many products you want to enter.
  * For each product, type:

    * Quantity
    * Article number
    * Optional description
  * Click **“Apply products”** (or similar button) to store them.

### 3. Preview extracted data

* The app displays a dataframe with all extracted/entered items.
* You see how many items were found.

### 4. Map columns

If you uploaded a CSV, your column names might be different.

* In **Column Mapping**, assign:

  * **Quantity** column
  * **Conrad Article No.** column
  * **Description** column (optional)
* Click **“Apply mapping”** to save the mapping. 

### 5. Search for products

You can:

* **Search all rows at once**

  * Click **“Search all items”** to run a bulk search for every article number.
  * The app will respect the configured delay between requests.

* **Search a single row**

  * Expand a row (`Position #...`).
  * Click **“Search this item”** to run the search only for this article number.

The app:

* Cleans the article number (removing separators/suffixes).
* Searches Conrad by article number.
* If no result is found and fallback is enabled, runs a web search for conrad.de product pages.

### 6. Review and select candidates

For each row:

* Expand the row to see:

  * Original quantity
  * Article number
  * Optional description
* Candidate products are listed as radio buttons:

  * Title
  * Article number
  * Price (if available)
  * Source (Conrad / Web fallback / Serper / Bing)
* Select the correct product.
* You can open the product page in a new browser tab via the **“Open in new tab”** button.

### 7. Export final selection

* Once you have selected products for (some or all) rows:

  * A **“Final selection”** section appears.
  * A final dataframe is shown, including:

    * Original columns
    * Selected Conrad URL
    * Selected article number
    * Selected title
    * Selected price
    * Status & Source

* Click the download link (e.g. **“Download CSV”**) to save the final data as `conrad_bestellung.csv`.

---

## Limitations & Notes

* The app depends on the **HTML structure** of conrad.de and search engines; if the website layout changes, scraping may need updates.
* OCR quality strongly depends on:

  * PDF scan quality
  * DPI settings
  * Correct Tesseract configuration
* Network access is required for:

  * Conrad search
  * Web search fallback (DuckDuckGo / Serper.dev / Bing)
* Only Conrad Germany (`conrad.de`) URLs are targeted by default.

---

## How to Contribute

Suggestions for improvements:

* Better error handling and logging
* More robust parsing of Conrad pages
* Support for additional export formats (e.g. Excel)
* Internationalization of the UI

Pull requests and issues are welcome.

---

## License

Add your preferred license here (for example: MIT, Apache 2.0, etc.).

---

## Author

**Amir Mobasheraghdam**
