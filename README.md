# 🏛️ UAE Corporate Intelligence Hub

A multi-agent system for comprehensive company profiling using DFM and ADX data.

## 🚀 Features

- Identity Resolution: Fuzzy company name/ticker matching
- Smart Caching: ChromaDB vector storage with freshness validation
- Parallel Extraction: Async scraping from exchange endpoints
- LLM Synthesis: AI-powered insights and risk analysis
- Professional UI: Gradio dashboard with real-time progress
- LangGraph Orchestration: Multi-agent workflow management

## 🏗️ Architecture

```
CorporateIntelligenceX/
├── intelligence_hub/          # Main package
│   ├── agents/                # Workflow agents
│   ├── config/                # Configuration
│   ├── models/                # Data models
│   ├── prompts/               # LLM templates
│   ├── scrapers/              # Web scrapers
│   ├── ui/                    # Gradio UI
│   └── utils/                 # Helpers
├── tests/                     # Unit tests
├── scripts/                   # Utility scripts
├── main.py                    # Entry point
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
   source venv/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with API keys
   ```

5. Initialize database
   ```bash
   python scripts/init_db.py
   ```

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| SCRAPINGBEE_API_KEY | Web scraping API key | Required |
| MARKET_DATA_TTL | Cache TTL in hours | 24 |
| LLM_MODEL | AI model (gpt-4o/gemini-2.0-flash) | gpt-4o |
| VECTOR_DB_PATH | ChromaDB path | ./data/chroma_store |
| DEFAULT_TIMEFRAME_QTR | Quarterly timeframe | 12 |
| LOG_LEVEL | Logging level | INFO |

## 🚀 Usage

```bash
python main.py
```

Access dashboard at http://localhost:7860

### Investigation Process

1. Enter company name or ticker
2. Click "Launch Investigation"
3. Monitor progress through workflow steps
4. View financial, governance, and risk insights

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

## 🧠 Workflow

1. **Identity Resolution** → Map input to canonical name/ticker
2. **Cache Audit** → Validate data freshness
3. **Market Deep-Dive** → Parallel data extraction
4. **Financial Synthesis** → AI-generated insights & risks

## 🧪 Testing

```bash
pytest tests/
```

## 📄 License

Proprietary software for corporate intelligence applications

## 🆘 Support

Contact development team for support
