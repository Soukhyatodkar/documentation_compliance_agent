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
- **🌐 Modern web scraping** with Playwright
- **📊 Vector embeddings** for guideline comprehension
- **🎯 Zero hardcoding** – works with any website/PDF by changing config only

### What It Does

```
PDF Guideline → Extract & Embed → Vector Database
                                        ↓
Website URL → Playwright → Extract Components → Semantic Retrieval
                                        ↓
                        Compare with Guideline ← LLM Agent
                                        ↓
                    Generate Compliance Report
```

## Key Features

✅ **Generic & Configurable**
- No hardcoding – change config, not code
- Works with any website and any guideline PDF
- Tested with WaiverPro example, but fully generic

✅ **Comprehensive Web Extraction**
- JavaScript rendering
- Authentication handling
- Dynamic content capture
- Screenshot evidence
- Full page navigation

✅ **Smart Semantic Search**
- RAG-powered guideline retrieval
- Embeddings-based similarity matching
- Context-aware comparisons

✅ **Intelligent Compliance Checking**
- LLM-based reasoning
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
- Markdown (human-readable)
- JSON (machine-readable)
- HTML (interactive)

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
