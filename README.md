# ⚖️ Gov_OCR — Cause List Extractor
**An Intelligent, High-Speed Legal Document Parser for the Indian Judicial System.**

Gov_OCR is a specialized tool designed to automate the extraction of case data from PDF and image-based cause lists. Built on a sophisticated **Adaptive AI Engine**, it balances processing speed with high-precision extraction for complex legal layouts.

---

## 🚀 Key Features

### 🧠 Adaptive Extraction Engine (v5.0)
Unlike standard OCR tools, Gov_OCR uses a two-phase intelligence model to handle diverse court layouts:
* **Phase 1 (Performance):** Processes clean, digital PDFs using `mistral-small` in 2-page batches for maximum speed.
* **Phase 2 (Precision):** Automatically detects messy or scanned layouts and upgrades to `mistral-large` with a secondary **Reconciliation Layer** to ensure no case number is missed.

### 🏛️ Universal Court Support
Optimized for the specific formatting nuances of:
* All **25 Indian High Courts** (e.g., Telangana, Delhi, Madras, Bombay).
* The **Supreme Court of India**.
* Both digital (searchable) and scanned (handwritten/stamped) documents.

### 🧹 Smart Data Cleaning
* **Regex-Validated:** Uses deep pattern matching to identify case numbers.
* **IA Filtering:** Automatically identifies and groups Interlocutory Applications (IAs) to keep the main case list clean.
* **Deduplication:** Ensures unique entries even when data spans across page breaks.

---

## 🛠️ Technology Stack
* **Framework:** [Streamlit](https://streamlit.io/)
* **OCR & Intelligence:** [Mistral AI](https://mistral.ai/) (`mistral-ocr-latest`, `mistral-large-latest`)
* **Data Processing:** Pandas, OpenPyXL, Regular Expressions (Re)
* **Styling:** Custom CSS for a "Dark Mode" premium legal interface.

---

## 📦 Getting Started

### Prerequisites
* Python 3.9+
* A Mistral AI API Key

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/IshaniArora1024/Gov_OCR.git](https://github.com/IshaniArora1024/Gov_OCR.git)
   cd Gov_OCR
Install dependencies:

Bash
pip install -r requirements.txt
Configure Secrets:
Create a folder .streamlit and a file secrets.toml:

Ini, TOML
MISTRAL_API_KEY = "your_mistral_api_key_here"
Run the Application:

Bash
streamlit run app.py
📥 Output Formats
Extract your data instantly in the following formats:

Excel (.xlsx) - Pre-formatted for legal clerks and advocates.

CSV - For integration with external database systems.

JSON - For developers and legal-tech integrations.

🛡️ Security & Privacy
This application is designed with security in mind:

Zero Persistence: Uploaded files are processed in-memory and not stored on the server.

Encrypted Secrets: API keys are managed via Streamlit's encrypted secrets management.

Developed by Ishani Arora | Empowering Legal Tech with AI
