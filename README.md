# 🏛️ UAE Corporate Intelligence Hub

A multi-agent system for comprehensive company profiling using DFM and ADX data.

## 🚀 Features

- Identity Resolution: Fuzzy company name/ticker matching
- Smart Caching: ChromaDB vector storage with freshness validation
- Parallel Extraction: Async scraping from exchange endpoints
- LLM Synthesis: AI-powered insights and risk analysis
- Professional UI: Streamlit dashboard with real-time progress
- LangGraph Orchestration: Multi-agent workflow management

## 🏗️ Architecture

```
CorporateIntelligenceX/
├── intelligence_hub/          # Main package
│   ├── agents/                # Workflow agents (PDF, Chat, Scraper orchestration)
│   ├── config/                # Configuration
│   ├── connectors/            # External service connectors
│   ├── core/                  # Core logic and mock data
│   ├── graph/                 # LangGraph workflow definitions
│   ├── llm/                   # LLM connector and models
│   ├── prompts/               # LLM templates
│   ├── scrapers/              # ADX/DFM web scrapers
│   ├── storage/               # ChromaDB vector manager
│   ├── ui/                    # Streamlit UI components
│   └── utils/                 # Helpers and extractors
├── tests/                     # Unit and integration tests
├── data/                      # Scraped data and ChromaDB storage
├── streamlit_app.py           # Main UI entry point
├── intelx_cli.py              # Command-line interface
└── setup.py                   # Package setup
```

## 📋 Prerequisites

- Python 3.9+
- ScrapingBee API key
- OpenAI API key (GPT-4o) or Google API key (Gemini)

## 🛠️ Installation

1. Clone repository
   ```bash
   git clone <repo-url>
   cd CorporateIntelligenceX
   ```

2. Create virtual environment
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## ⚙️ Configuration

Edit `.env` file with the following variables:

| Variable | Description | Default |
|----------|-------------|---------|
| SCRAPINGBEE_API_KEY | ScrapingBee web scraping API key | Required |
| MARKET_DATA_TTL | Cache TTL in hours | 24 |
| LLM_MODEL | AI model (`gpt-4o` or `gemini-2.0-flash`) | gpt-4o |
| VECTOR_DB_PATH | ChromaDB path | ./data/chroma_store |
| DEFAULT_TIMEFRAME_QTR | Quarterly timeframe | 12 |
| LOG_LEVEL | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| UI_THEME | UI theme | corporate_blue |

## 🚀 Usage

### Web Dashboard (Streamlit)

```bash
streamlit run streamlit_app.py
```

Access dashboard at http://localhost:8501

### Command Line Interface

```bash
# Show overview of all tickers in ChromaDB
python intelx_cli.py summary

# Audit knowledge sources for a specific ticker
python intelx_cli.py audit EMAAR

# Semantic search query against a ticker's data
python intelx_cli.py query EMAAR "What are the revenue trends?"
```

### Database Inspection

```bash
# Inspect ChromaDB collections and contents
python inspect_db.py
```

### Investigation Process (Web UI)

1. Enter company name or ticker
2. Click "Launch Investigation"
3. Monitor progress through workflow steps
4. View financial, governance, and risk insights
5. Use the chat panel for follow-up questions

## 📊 Data Sources

### Abu Dhabi Securities Exchange (ADX)
- Company Profile
- Financial Results
- Disclosures
- Governance & Board

### Dubai Financial Market (DFM)
- Company Profile
- Reports
- Disclosures
- Ownership Structure
- Board of Directors

### Dubai Economic Department (DED)
- License Master data
- Trade Names
- License Activities
- License Partners

## 🧠 Workflow

1. **Identity Resolution** → Map input to canonical name/ticker
2. **Cache Audit** → Validate data freshness
3. **Market Deep-Dive** → Parallel data extraction from ADX/DFM
4. **Financial Synthesis** → AI-generated insights & risks
5. **Vector Storage** → Store extracted data in ChromaDB for RAG

## 🛠️ Utility Scripts

### DED Data Management

```bash
# Aggregate DED license data from CSV files
python aggregate_ded_extract.py

# Create ChromaDB collection from selected corporates
python create_ded_selected_db.py

# Append new entries to existing DED ChromaDB (incremental update)
python append_ded_selected_db.py
python append_ded_selected_db.py --dry-run  # Preview without changes
```

### Debug Tools

```bash
# Debug PDF analysis agent
python debug_pdf_agent.py

# Debug PDF image extraction
python debug_pdf_images.py

# Debug PDF text extraction
python debug_pdf_text.py
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test files
python tests/test_pipeline.py
python tests/verify_full_flow.py
python tests/verify_mock_fallback.py
python tests/verify_tickers_and_scrapers.py
```

## 📦 Development Installation

```bash
# Install with development dependencies
pip install -e ".[dev]"
```

## 📄 License

Proprietary software for corporate intelligence applications

## 🆘 Support

Contact development team for support
