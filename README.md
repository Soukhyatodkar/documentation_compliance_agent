# Documentation Compliance Agent

> **Production-quality automated compliance checking for web applications against their official documentation and guidelines**

[![CI/CD Pipeline](https://github.com/example/documentation-compliance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/example/documentation-compliance-agent/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The **Documentation Compliance Agent** is a sophisticated, production-ready system that automatically verifies whether live web applications comply with their official documentation and guidelines. It combines:

- **🤖 LLM-powered reasoning** for intelligent comparison
- **🔍 Semantic search** via RAG (Retrieval-Augmented Generation)
- **🌐 Modern web scraping** with Playwright (handles authentication, dynamic content)
- **📊 Vector embeddings** for guideline comprehension
- **🎯 Zero hardcoding** – works with any website/PDF by changing config only

### What It Does

```
PDF Guideline → Extract & Embed → Vector Database
                                        ↓
Website URL → Playwright → Extract Components → Semantic Retrieval
                   ↓ (Login, Dynamic Content, Screenshots)
                                        ↓
                        Compare with Guideline ← LLM Agent
                                        ↓
                    Generate Compliance Report
```

## Key Features

✅ **Generic & Configurable**
- No hardcoding – change config, not code
- Works with any website and any guideline PDF
- Tested with WaiverPro, but fully generic

✅ **Comprehensive Web Extraction** (Playwright)
- JavaScript rendering and dynamic content
- Authentication handling (form-based, basic)
- Component extraction (buttons, forms, text, navigation, etc.)
- Screenshot evidence capture
- Full page navigation with crawling
- Lazy loading and AJAX support

✅ **Smart Semantic Search**
- RAG-powered guideline retrieval
- Embeddings-based similarity matching
- Context-aware comparisons

✅ **Intelligent Compliance Checking**
- LLM-based reasoning (GPT-4)
- Multi-level verification
- Guideline citations in reports
- Confidence scoring

✅ **Production-Ready**
- Structured logging
- Comprehensive error handling
- Retry mechanisms
- Coverage tracking
- Docker support

✅ **Multiple Report Formats**
- JSON (machine-readable)
- Markdown (human-readable)
- HTML (interactive dashboard)

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/example/documentation-compliance-agent.git
cd documentation-compliance-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up Playwright browsers
playwright install chromium
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

**Required environment variables:**
```bash
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
QDRANT_URL=http://localhost:6333        # Qdrant server URL
```

### Start Qdrant Vector Database

```bash
# Option 1: Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant:v1.13.4

# Option 2: Use docker-compose
docker-compose -f docker/docker-compose.yml up -d qdrant
```

### WaiverPro Example Setup

```bash
# 1. Download guidelines PDF from:
# https://drive.google.com/drive/folders/1hklfhcLyDYZ9cFJlIzc0SWZcyqLMudim
# and save to: data/pdfs/waiverpo-guidelines.pdf

# 2. Create/update config for WaiverPro
cp config/template_config.yaml config/waiverpo_config.yaml
```

Edit `config/waiverpo_config.yaml`:
```yaml
website:
  url: https://white-cliff-0bca3ed00.1.azurestaticapps.net/
  username: admin@gmail.com
  password: password
  authentication:
    type: form
    login_url: https://white-cliff-0bca3ed00.1.azurestaticapps.net/

pdf:
  path: ./data/pdfs/waiverpo-guidelines.pdf
  strategy: semantic

llm:
  model: gpt-4
  temperature: 0.7
```

### Run the Agent

```bash
# Full pipeline: ingest PDF → extract website → compare → report
python main.py run --config config/waiverpo_config.yaml

# Or run individual stages
python main.py ingest --config config/waiverpo_config.yaml    # Ingest PDF
python main.py extract --config config/waiverpo_config.yaml   # Extract website
python main.py compare --config config/waiverpo_config.yaml   # Compare
python main.py report --config config/waiverpo_config.yaml    # Generate reports
```

## How It Works

### Step 1: PDF Ingestion
- Reads guideline PDF (WaiverPro User Guidelines)
- Extracts text, preserves structure and headings
- Creates semantic chunks with metadata
- Generates embeddings and stores in Qdrant

### Step 2: Website Extraction (Playwright)
- Navigates to website URL
- Authenticates (if credentials provided)
- Extracts all visible components:
  - Buttons, links, forms, text, images
  - Navigation elements, tables, modals
  - Headings, paragraphs, selects
- Captures full-page screenshots
- Tracks extraction progress and failures

### Step 3: Comparison (RAG + LLM Agent)
- Retrieves relevant guideline chunks from vector DB
- Uses semantic similarity to match components
- Sends to GPT-4 with structured comparison prompt
- Detects discrepancies:
  - Missing components
  - Extra components
  - Text mismatches
  - Functional differences
- Generates confidence scores

### Step 4: Report Generation
- Aggregates all findings
- Creates compliance percentage
- Generates JSON (structured), Markdown (human-readable), HTML (interactive)
- Includes screenshots as evidence
- Cites guideline sections

## Configuration

The system is entirely configuration-driven. All settings go in YAML files – no code changes needed.

### Configuration Files

- `config/base_config.yaml` – Default configuration
- `config/waiverpo_config.yaml` – WaiverPro example
- `config/template_config.yaml` – Template for new websites

### Key Configuration Sections

```yaml
website:
  url: https://your-site.com
  username: admin@gmail.com
  password: password
  authentication:
    type: form                   # none, basic, form, oauth2
  crawling:
    max_pages: 50               # Pages to crawl
    skip_urls: [logout, delete] # Patterns to skip

pdf:
  path: ./data/pdfs/guidelines.pdf
  strategy: semantic            # simple, smart, semantic

llm:
  model: gpt-4
  temperature: 0.7
  max_tokens: 2000

browser:
  type: chromium               # chromium, firefox, webkit
  headless: true
  screenshots:
    enabled: true
    full_page: true
  timeouts:
    navigation: 30000          # 30 seconds
    element_wait: 10000        # 10 seconds
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for all 80+ options.

## Architecture

### System Layers

```
┌─────────────────────────────────────────┐
│      CLI Interface (Typer)              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│   PDF Ingestion  │  Web Extraction      │
│   RAG Pipeline   │  Compliance Agent    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Vector DB (Qdrant)                 │
│      Canonical Data Store               │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│    Report Generation                    │
│    (JSON/Markdown/HTML)                 │
└─────────────────────────────────────────┘
```

### Data Flow

1. **PDF Ingestion**: Parse PDF → Extract text → Semantic chunking → Generate embeddings → Store in Qdrant
2. **Web Extraction**: Login → Navigate pages → Capture components → Screenshots → Structured JSON
3. **Comparison**: Retrieve guideline chunks → Compare components → LLM reasoning → Score confidence
4. **Reporting**: Collect discrepancies → Format reports → Generate evidence

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Usage Examples

### Basic Usage (WaiverPro)

```bash
# Full pipeline
python main.py run --config config/waiverpo_config.yaml

# Extract website only
python main.py extract --config config/waiverpo_config.yaml
# Output: data/extracted/waiverpo_extraction_*.json

# Generate reports
python main.py report --config config/waiverpo_config.yaml
# Output: data/reports/compliance_report.json
#         data/reports/compliance_report.md
#         data/reports/compliance_report.html
```

### Using with New Website

1. Copy the template:
   ```bash
   cp config/template_config.yaml config/mysite_config.yaml
   ```

2. Edit configuration:
   ```bash
   nano config/mysite_config.yaml
   # Update: website URL, PDF path, login credentials, etc.
   ```

3. Run the agent:
   ```bash
   python main.py run --config config/mysite_config.yaml
   ```

### Validate Configuration

```bash
python main.py validate-config --config config/mysite_config.yaml
```

## CLI Commands

```bash
python main.py --help                    # Show all commands

# Full pipeline
python main.py run --config CONFIG       # Run all stages

# Individual stages
python main.py ingest --config CONFIG    # Ingest PDF
python main.py extract --config CONFIG   # Extract website
python main.py compare --config CONFIG   # Run comparison
python main.py report --config CONFIG    # Generate reports

# Utilities
python main.py validate-config           # Validate configuration
python main.py test-connection           # Test external connections
python main.py health-check              # System health check
python main.py status                    # Project status
python main.py version                   # Version info
```

## Output

The agent generates comprehensive compliance reports:

### 1. JSON Report (Machine-Readable)
```json
{
  "summary": {
    "total_pages": 45,
    "pages_extracted": 42,
    "coverage": 93.3,
    "total_discrepancies": 7,
    "critical": 2,
    "warnings": 5
  },
  "discrepancies": [
    {
      "page_url": "https://example.com/features",
      "component": "header_title",
      "actual_text": "Our Amazing Features",
      "expected_text": "Features",
      "guideline_citation": "Section 2.1: Header Labels",
      "severity": "warning",
      "confidence": 0.92,
      "screenshot": "data/screenshots/screenshot_001.png"
    }
  ]
}
```

### 2. Markdown Report (Human-Readable)
- Executive summary
- Detailed findings by severity
- Screenshots as evidence
- Guideline citations
- Actionable recommendations

### 3. HTML Report (Interactive)
- Dashboard with compliance metrics
- Discrepancy table with sorting
- Screenshot evidence
- Severity breakdown
- Professional styling

## Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit                        # Unit tests only
pytest tests/integration                 # Integration tests
pytest -m "not slow"                     # Skip slow tests

# With coverage
pytest --cov=src --cov-report=html

# Watch mode (requires pytest-watch)
ptw
```

## Docker Deployment

### Single Container

```bash
docker build -f docker/Dockerfile -t compliance-agent .
docker run --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  compliance-agent
```

### Full Stack (Agent + Qdrant)

```bash
docker-compose -f docker/docker-compose.yml up
```

## Performance

**Typical execution times (WaiverPro example):**
- PDF ingestion (50 pages): 5-10 seconds
- Website extraction (50 pages): 2-5 minutes
- Comparison: 1-2 minutes
- Report generation: 10-30 seconds

**Resource requirements:**
- CPU: 2+ cores
- RAM: 4GB+
- Storage: 10GB+ (for screenshots and data)
- Network: Internet access for OpenAI API

## Troubleshooting

### Common Issues

**Qdrant connection fails**
```bash
# Check Qdrant is running
curl http://localhost:6333/health
# If not, start it: docker run -p 6333:6333 qdrant/qdrant:v1.13.4
```

**OpenAI API errors**
```bash
# Verify API key
echo $OPENAI_API_KEY
# Check rate limits: https://platform.openai.com/account/rate-limits
```

**Playwright browser issues**
```bash
# Reinstall browsers
playwright install chromium
```

**Authentication fails**
```bash
# Verify credentials in config
# Check login URL is correct
# Test credentials manually on the website
```

**Page extraction times out**
```bash
# Increase timeouts in config:
browser:
  timeouts:
    navigation: 60000  # 60 seconds
    element_wait: 20000  # 20 seconds
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more help.

## Project Structure

```
documentation-compliance-agent/
├── src/                          # Application code
│   ├── core/                     # Configuration, logging, exceptions
│   ├── pdf_ingestion/            # PDF processing
│   ├── vector_store/             # Embeddings & Qdrant integration
│   ├── web_extraction/           # Playwright-based scraping
│   ├── rag/                      # RAG pipeline
│   ├── agent/                    # Compliance agent logic
│   ├── reporting/                # Report generation
│   ├── coverage/                 # Coverage tracking
│   ├── data/                     # Data models and storage
│   └── utils/                    # Helpers and utilities
│
├── config/                       # Configuration files
│   ├── base_config.yaml
│   ├── waiverpo_config.yaml
│   └── template_config.yaml
│
├── tests/                        # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/                         # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   └── DEPLOYMENT.md
│
├── docker/                       # Docker files
├── data/                         # Output directories
│   ├── pdfs/                     # Input PDFs
│   ├── extracted/                # Extracted web data
│   ├── screenshots/              # Page screenshots
│   └── reports/                  # Generated reports
│
├── requirements.txt
├── README.md
└── setup.py
```

## Design Decisions

### Why Playwright?
- Handles modern JS frameworks (React, Vue, Angular)
- Built-in authentication support
- Excellent error handling and retry mechanisms
- Parallel execution via async/await
- Cross-browser support

### Why RAG (Retrieval-Augmented Generation)?
- Grounds comparisons in actual guideline content
- Reduces LLM hallucinations
- Provides citation trails for discrepancies
- Scalable to large PDFs (500+ pages)

### Why Qdrant?
- Fast semantic search via vector similarity
- Built-in filtering and metadata support
- Production-ready, no external dependencies
- Easy local deployment via Docker
- Efficient scaling

### Why Configuration Files?
- Zero hardcoding – true generalization
- Easy to version control and audit
- Different configs for different websites
- No code changes needed for new deployments
- Supports environment variable substitution

## Known Limitations

1. **Large PDFs**: Processing 500+ page PDFs may take longer
2. **Dynamic Content**: SPAs require explicit wait selectors  
3. **CAPTCHA**: Not handled – may need manual intervention
4. **JavaScript-heavy sites**: May need tuning of wait times
5. **Rate limiting**: Respects robots.txt but may hit API limits
6. **JavaScript Rendering**: Limited to Chromium (no native desktop apps)

## Future Improvements

- [ ] Support for more authentication types (SAML, SSO, MFA)
- [ ] Visual regression detection (pixel-perfect comparisons)
- [ ] Custom comparison rules via DSL
- [ ] Database caching for repeated comparisons
- [ ] Webhook integration for CI/CD
- [ ] Web UI dashboard
- [ ] Multi-language support
- [ ] Performance optimization for large-scale crawling

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run quality checks: `black . && isort . && flake8 src tests`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

## License

MIT License – see [LICENSE](LICENSE) for details

## Support

- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/example/documentation-compliance-agent/issues)
- 💬 [Discussions](https://github.com/example/documentation-compliance-agent/discussions)

## Citation

If you use this project in research, please cite:

```bibtex
@software{compliance_agent_2024,
  title={Documentation Compliance Agent},
  author={Documentation Compliance Team},
  year={2024},
  url={https://github.com/example/documentation-compliance-agent}
}
```

---

**Built with ❤️ for production software engineering**


## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/example/documentation-compliance-agent.git
cd documentation-compliance-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up Playwright browsers
playwright install chromium
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

**Required environment variables:**
```bash
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
QDRANT_URL=http://localhost:6333        # Qdrant server URL
WEBSITE_URL=https://example.com          # Target website
PDF_PATH=./data/pdfs/guidelines.pdf      # Guideline PDF
```

### Start Qdrant Vector Database

```bash
# Option 1: Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant:latest

# Option 2: Use docker-compose
docker-compose -f docker/docker-compose.yml up -d qdrant
```

### Run the Agent

```bash
# Full pipeline: ingest PDF → extract website → compare → report
python main.py run --config config/base_config.yaml

# Or run individual stages
python main.py ingest                    # Ingest PDF into vector DB
python main.py extract                   # Extract website components
python main.py compare                   # Compare with guidelines
python main.py report                    # Generate reports
```

## Configuration

The system is entirely configuration-driven. All settings go in YAML files – no code changes needed.

### Configuration Files

- `config/base_config.yaml` – Default configuration
- `config/waiverpo_config.yaml` – WaiverPro example
- `config/template_config.yaml` – Template for new websites

### Key Configuration Sections

```yaml
website:
  url: https://your-site.com
  authentication:
    type: form  # none, basic, form, oauth2
    username: ${WEBSITE_USERNAME}
    password: ${WEBSITE_PASSWORD}

pdf:
  path: ./data/pdfs/guidelines.pdf
  chunking:
    max_chunk_size: 1000
    overlap: 100

llm:
  model: gpt-4
  temperature: 0.7

vector_db:
  type: qdrant
  url: http://localhost:6333
  collection_name: guidelines
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for detailed options.

## Architecture

### System Layers

```
┌─────────────────────────────────────────┐
│      CLI Interface (Typer)              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│   PDF Ingestion  │  Web Extraction      │
│   RAG Pipeline   │  Compliance Agent    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Vector DB (Qdrant)                 │
│      Canonical Data Store               │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│    Report Generation                    │
│    (Markdown/JSON/HTML)                 │
└─────────────────────────────────────────┘
```

### Data Flow

1. **PDF Ingestion**: Parse PDF → Extract text → Semantic chunking → Generate embeddings → Store in Qdrant
2. **Web Extraction**: Login → Navigate pages → Capture components → Screenshots → Structured JSON
3. **Comparison**: Retrieve guideline chunks → Compare components → LLM reasoning → Score confidence
4. **Reporting**: Collect discrepancies → Format reports → Generate evidence

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Usage Examples

### Basic Usage

```bash
# Ingest guidelines
python main.py ingest --config config/waiverpo_config.yaml

# Extract website
python main.py extract --config config/waiverpo_config.yaml

# Run comparison
python main.py compare --config config/waiverpo_config.yaml

# Generate reports
python main.py report --config config/waiverpo_config.yaml
```

### Full Pipeline

```bash
# Run everything in one command
python main.py run --config config/waiverpo_config.yaml
```

### Using with New Website

1. Copy the template:
   ```bash
   cp config/template_config.yaml config/mysite_config.yaml
   ```

2. Edit configuration:
   ```bash
   nano config/mysite_config.yaml
   # Update: website URL, PDF path, login credentials, etc.
   ```

3. Run the agent:
   ```bash
   python main.py run --config config/mysite_config.yaml
   ```

## CLI Commands

```bash
python main.py --help                    # Show all commands

# Stage-by-stage execution
python main.py ingest                    # Ingest PDF
python main.py extract                   # Extract website
python main.py compare                   # Run comparison
python main.py report                    # Generate reports

# Full pipeline
python main.py run                       # Run all stages

# Utilities
python main.py validate-config           # Validate configuration
python main.py test-connection           # Test external connections
python main.py health-check              # System health check
```

## Output

The agent generates comprehensive compliance reports:

### 1. Discrepancy Report (JSON)
```json
{
  "summary": {
    "total_pages": 45,
    "pages_extracted": 42,
    "coverage": 93.3,
    "total_discrepancies": 7,
    "critical": 2,
    "warnings": 5
  },
  "discrepancies": [
    {
      "page_url": "https://example.com/features",
      "component": "header_title",
      "actual_text": "Our Amazing Features",
      "expected_text": "Features",
      "guideline_citation": "Section 2.1: Header Labels",
      "severity": "warning",
      "confidence": 0.92,
      "screenshot": "data/screenshots/page_1_header.png"
    }
  ]
}
```

### 2. HTML Report
Interactive report with:
- Dashboard with compliance metrics
- Discrepancy details with screenshots
- Guideline citations
- Coverage analysis
- Severity breakdown

### 3. Markdown Report
Human-readable format with:
- Executive summary
- Detailed findings
- Screenshots as evidence
- Actionable recommendations

## Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit                        # Unit tests only
pytest tests/integration                 # Integration tests
pytest -m "not slow"                     # Skip slow tests

# With coverage
pytest --cov=src --cov-report=html

# Watch mode (requires pytest-watch)
ptw
```

## Docker Deployment

### Single Container

```bash
docker build -f docker/Dockerfile -t compliance-agent .
docker run --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  compliance-agent
```

### Full Stack (Agent + Qdrant)

```bash
docker-compose -f docker/docker-compose.yml up
```

## Performance

**Typical execution times:**
- PDF ingestion (50 pages): 5-10 seconds
- Website extraction (50 pages): 2-5 minutes
- Comparison: 1-2 minutes
- Report generation: 10-30 seconds

**Resource requirements:**
- CPU: 2+ cores
- RAM: 4GB+
- Storage: 10GB+ (for screenshots and data)
- Network: Internet access for OpenAI API

## Troubleshooting

### Common Issues

**Qdrant connection fails**
```bash
# Check Qdrant is running
curl http://localhost:6333/health
# If not, start it: docker run -p 6333:6333 qdrant/qdrant:latest
```

**OpenAI API errors**
```bash
# Verify API key
echo $OPENAI_API_KEY
# Check rate limits: https://platform.openai.com/account/rate-limits
```

**Playwright browser issues**
```bash
# Reinstall browsers
playwright install chromium
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more help.

## Project Structure

```
documentation-compliance-agent/
├── src/                          # Application code
│   ├── core/                     # Configuration, logging, exceptions
│   ├── pdf_ingestion/            # PDF processing
│   ├── vector_store/             # Embeddings & Qdrant integration
│   ├── web_extraction/           # Playwright-based scraping
│   ├── rag/                      # RAG pipeline
│   ├── agent/                    # Compliance agent logic
│   ├── reporting/                # Report generation
│   └── utils/                    # Helpers and utilities
│
├── config/                       # Configuration files
│   ├── base_config.yaml
│   ├── waiverpo_config.yaml
│   └── template_config.yaml
│
├── tests/                        # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/                         # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   └── USAGE.md
│
├── docker/                       # Docker files
└── data/                         # Output directories
    ├── pdfs/                     # Input PDFs
    ├── extracted/                # Extracted web data
    ├── screenshots/              # Page screenshots
    └── reports/                  # Generated reports
```

## Design Decisions

### Why Qdrant?
- Fast semantic search via vector similarity
- Built-in filtering and metadata support
- Production-ready, no external dependencies
- Easy local deployment via Docker

### Why Playwright?
- Handles modern JS frameworks
- Built-in authentication support
- Parallel execution via async/await
- Excellent error handling

### Why RAG (Retrieval-Augmented Generation)?
- Grounds comparisons in actual guideline content
- Reduces hallucinations
- Provides citation trails
- Scalable to large PDFs

### Why Configuration Files?
- Zero hardcoding – true generalization
- Easy to version control and audit
- Different configs for different websites
- No code changes needed for new deployments

## Known Limitations

- The GitHub Actions documentation workflow assumes an MkDocs configuration, which is not included because the project uses a README-based documentation approach.
- The CI pipeline may require environment-specific adjustments for the Qdrant service container and platform-specific dependencies.
- The application has been developed and validated locally; CI configuration can be further refined for production use.

1. **Large PDFs**: Processing 500+ page PDFs may take longer
2. **Dynamic Content**: SPAs require explicit wait selectors
3. **CAPTCHA**: Not handled – may need manual intervention
4. **JavaScript-heavy sites**: May need tuning of wait times
5. **Rate limiting**: Respects robots.txt but may hit API limits

## Future Improvements

- [ ] Support for more authentication types (SAML, SSO)
- [ ] Visual regression detection (pixel-perfect comparisons)
- [ ] Custom comparison rules via DSL
- [ ] Database caching for repeated comparisons
- [ ] Webhook integration for CI/CD
- [ ] Web UI dashboard
- [ ] Multi-language support

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run quality checks: `black . && isort . && flake8 src tests`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

## License

MIT License – see [LICENSE](LICENSE) for details

## Support

- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/example/documentation-compliance-agent/issues)
- 💬 [Discussions](https://github.com/example/documentation-compliance-agent/discussions)
- 📧 [Contact](mailto:team@example.com)

## Citation

If you use this project in research, please cite:

```bibtex
@software{compliance_agent_2024,
  title={Documentation Compliance Agent},
  author={Documentation Compliance Team},
  year={2024},
  url={https://github.com/example/documentation-compliance-agent}
}
```

---

**Built with ❤️ for production software engineering**
