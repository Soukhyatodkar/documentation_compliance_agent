# System Architecture

> **Comprehensive design documentation for the Documentation Compliance Agent**

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Module Architecture](#module-architecture)
5. [Design Patterns](#design-patterns)
6. [Scalability Considerations](#scalability-considerations)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Performance Optimization](#performance-optimization)

---

## High-Level Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI Interface (Typer)                        │
│  Commands: run | ingest | extract | compare | report            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration System                          │
│  • YAML config files                                             │
│  • Environment variable substitution                             │
│  • Pydantic validation                                           │
│  • 80+ configuration options                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Pipeline Execution                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 1: PDF Ingestion                                  │  │
│  │ • Extract text from PDF (pdfplumber + pypdf)            │  │
│  │ • Parse structure and headings                          │  │
│  │ • Generate semantic chunks                              │  │
│  │ • Store metadata (page number, section, heading)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 2: Embedding Generation                           │  │
│  │ • Generate embeddings via OpenAI API                    │  │
│  │ • Batch process for efficiency                          │  │
│  │ • Store in Qdrant vector database                       │  │
│  │ • Preserve metadata for retrieval                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 3: Website Extraction (Playwright)                │  │
│  │ • Authenticate if required                              │  │
│  │ • Navigate website pages                                │  │
│  │ • Extract components (buttons, text, forms, etc)        │  │
│  │ • Capture screenshots                                   │  │
│  │ • Store in canonical data format                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 4: RAG Pipeline                                   │  │
│  │ • Query expansion via LLM                               │  │
│  │ • Semantic retrieval from vector DB                     │  │
│  │ • Build context with relevant chunks                    │  │
│  │ • Cache results for efficiency                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 5: Compliance Comparison (LLM Agent)              │  │
│  │ • Compare components against guidelines                 │  │
│  │ • Detect discrepancies                                  │  │
│  │ • Score confidence                                      │  │
│  │ • Generate reasoning & recommendations                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Stage 6: Report Generation                              │  │
│  │ • Aggregate findings                                    │  │
│  │ • Generate JSON (machine-readable)                      │  │
│  │ • Generate Markdown (human-readable)                    │  │
│  │ • Generate HTML (interactive dashboard)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Data Persistence Layer                         │
│ • JSON file storage (extracted data)                            │
│ • Qdrant vector database (embeddings)                           │
│ • File system (screenshots, reports)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. **Core Module** (`src/core/`)

Handles foundational system concerns.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `config.py` | Configuration loading & validation | `Config`, `ConfigValidator` |
| `logger.py` | Structured logging setup | `LoggerConfig`, `setup_logging()` |
| `exceptions.py` | Custom exception hierarchy | 17 exception types |
| `models.py` | Shared data types & enums | `ComponentType`, `SeverityLevel` |

**Example:**
```python
from src.core.config import get_config
from src.core.logger import setup_logging

config = get_config("config/base_config.yaml")
logger = setup_logging(config)
logger.info("System initialized")
```

---

### 2. **PDF Ingestion Module** (`src/pdf_ingestion/`)

Processes guideline documents.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `pdf_reader.py` | Extract text from PDFs | `PDFReader` |
| `text_processor.py` | Clean & normalize text | `TextProcessor` |
| `chunk_generator.py` | Semantic chunking | `ChunkGenerator` |

**Data Flow:**
```
PDF File
    ↓ (PDFReader)
    → Raw text pages + metadata
    ↓ (TextProcessor)
    → Cleaned text with structure
    ↓ (ChunkGenerator)
    → Semantic chunks (with overlap)
    ↓
Vector DB (via embeddings)
```

---

### 3. **Vector Storage Module** (`src/vector_store/`)

Manages embeddings and semantic search.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `embeddings.py` | OpenAI embedding integration | `EmbeddingGenerator` |
| `qdrant_client.py` | Qdrant database operations | `QdrantVectorStore` |

**Capabilities:**
- Batch embedding generation
- Collection management (create, delete, check)
- Semantic search via similarity
- Metadata filtering
- Point CRUD operations

**Example:**
```python
embedder = EmbeddingGenerator(config)
vector_store = QdrantVectorStore(config)

# Embed chunks
embedded_chunks = embedder.embed_chunks_batch(chunks)

# Store in Qdrant
vector_store.create_collection()
vector_store.add_points(embedded_chunks)

# Search
query_embedding = embedder.embed_text("search query")
results = vector_store.search(query_embedding, limit=5)
```

---

### 4. **Data Models & Storage** (`src/data/`)

Canonical data structure and persistence.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `models.py` | Canonical data models | 13 Pydantic models |
| `schema.py` | Schema validation & conversion | `SchemaValidator` |
| `storage.py` | Data persistence layer | `DataStore` |

**Data Models:**
- `WebComponent`: Extracted website component
- `Discrepancy`: Identified compliance issue
- `ComparisonResult`: Result of comparison
- `CoverageReport`: Coverage statistics

**Example:**
```python
from src.data.models import WebComponent, ComponentType
from src.data.storage import DataStore

component = WebComponent(
    page_url="https://example.com",
    component_type=ComponentType.HEADING,
    text_content="Welcome"
)

store = DataStore(config)
store.save_component(component)

# Retrieve
retrieved = store.get_component(component.id)
```

---

### 5. **Web Extraction Module** (`src/web_extraction/`)

Extracts components from live websites.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `extractor.py` | Main extraction orchestrator | `WebsiteExtractor` |
| `navigator.py` | Page navigation logic | `WebNavigator` |
| `component_extractor.py` | Component detection & extraction | `ComponentExtractor` |
| `auth_handler.py` | Authentication handling | `AuthenticationHandler` |

**Features:**
- Playwright for modern JS rendering
- Multiple authentication types
- Screenshot capture
- Dynamic content wait handling
- Retry mechanisms

---

### 6. **RAG Module** (`src/rag/`)

Retrieval-Augmented Generation pipeline.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `retriever.py` | Semantic search | `SemanticRetriever` |
| `context.py` | Context building | `ContextBuilder` |
| `query_expander.py` | Query enhancement | `QueryExpander` |

**RAG Pipeline:**
```
User Query
    ↓ (Query Expander)
    → Multiple semantic variations
    ↓ (SemanticRetriever)
    → Top-K relevant chunks from vector DB
    ↓ (ContextBuilder)
    → Formatted context for LLM
    ↓
LLM Agent (receives grounded context)
```

---

### 7. **Compliance Agent** (`src/agent/`)

LLM-powered comparison engine.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `compliance_agent.py` | Component comparison logic | `ComplianceAgent` |
| `orchestrator.py` | Pipeline orchestration | `ComplianceOrchestrator` |

**Workflow:**
```python
agent = ComplianceAgent(config)

# For each extracted component:
assessment = agent.assess_compliance(
    component=web_component,
    guideline_chunks=retrieved_chunks,
    context=retrieval_context
)

# Returns:
# {
#   "matches_guideline": bool,
#   "severity": SeverityLevel,
#   "confidence": float,
#   "discrepancies": List[str],
#   "reasoning": str,
#   "remediation": str
# }
```

---

### 8. **Reporting Module** (`src/reporting/`)

Generate compliance reports.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `report_generator.py` | Multi-format report generation | `JSONReportGenerator`, `MarkdownReportGenerator`, `HTMLReportGenerator`, `ReportingOrchestrator` |

**Report Formats:**

1. **JSON Report**
   - Machine-readable
   - Includes all raw data
   - Suitable for programmatic access

2. **Markdown Report**
   - Human-readable
   - Good for documentation
   - Easy to share & version control

3. **HTML Report**
   - Interactive dashboard
   - Visual statistics
   - Embedded screenshots

---

### 9. **Coverage Tracking** (`src/coverage/`)

Track audit progress and coverage.

**Components:**

| Component | Purpose | Key Class |
|-----------|---------|-----------|
| `models.py` | Coverage data models | `CoverageMetrics` |
| `tracker.py` | Real-time tracking | `CoverageTracker` |
| `storage.py` | Persistence | `CoverageStorage` |
| `reporter.py` | Report generation | `CoverageReporter` |

**Metrics Tracked:**
- Pages visited vs. total pages
- Components extracted vs. total
- Extraction failures & retry counts
- Comparison results & confidence scores

---

### 10. **CLI Module** (`src/cli/`)

Command-line interface.

**Components:**

| Component | Purpose | Command |
|-----------|---------|---------|
| `commands.py` | CLI command handlers | run, ingest, extract, compare, report, config, validate-config, health-check, test-connection, status, version |

---

## Data Flow

### PDF Ingestion Flow

```
PDF File (guidelines.pdf)
    ↓
PDFReader.extract_text()
    → pages: List[Dict]
    → {"page_number": 0, "text": "...", "headings": [...]}
    ↓
TextProcessor.process()
    → Normalize text
    → Clean whitespace
    → Preserve structure
    ↓
ChunkGenerator.chunk_pages()
    → chunks: List[PDFChunk]
    → Each chunk: {text, page_num, section, heading, chunk_id}
    ↓
EmbeddingGenerator.embed_chunks_batch()
    → embedded_chunks: List[PointData]
    → Each point: {id, vector: 1536-dim, payload: metadata}
    ↓
QdrantVectorStore.add_points()
    → Stored in Qdrant collection
    ↓
✓ Ready for semantic search
```

### Component Comparison Flow

```
Extracted WebComponent
    {page_url, component_type, text_content, selector, ...}
    ↓
SemanticRetriever.retrieve()
    → Query expansion via LLM
    → Vector similarity search
    → Top-5 relevant chunks from PDF
    ↓
ContextBuilder.build()
    → Format chunks for LLM
    → Add metadata
    → ~300-500 tokens
    ↓
ComplianceAgent.assess_compliance()
    → Pass component + context to LLM
    → LLM compares and detects discrepancies
    → Returns assessment with reasoning
    ↓
ComparisonResult
    {
        "page_url": "...",
        "component": {...},
        "discrepancies": [...],
        "severity": CRITICAL|WARNING|INFO,
        "confidence": 0.95,
        "reasoning": "...",
        "guideline_citation": "Section 2.1"
    }
    ↓
DataStore.save_comparison_result()
    → Store for report generation
```

### Full Pipeline Flow

```
User Command: python main.py run --config config/waiverpo_config.yaml
    ↓
1. Load Configuration (YAML + environment variables)
    ↓
2. Setup Logging (structured, multi-level)
    ↓
3. PDF Ingestion Stage
    • Read PDF
    • Chunk text
    • Generate embeddings
    • Store in Qdrant
    ↓
4. Website Extraction Stage (optional)
    • Authenticate
    • Navigate pages
    • Extract components
    • Capture screenshots
    • Store in DataStore
    ↓
5. Comparison Stage
    For each component:
        • Retrieve relevant guidelines
        • Compare using LLM
        • Detect discrepancies
        • Store result
    ↓
6. Report Generation Stage
    • Aggregate all discrepancies
    • Generate JSON report
    • Generate Markdown report
    • Generate HTML report
    • Save to disk
    ↓
✓ Pipeline Complete
Output: 3 report files + 1 discrepancy summary
```

---

## Module Architecture

### Dependency Graph

```
CLI (commands.py)
    ↓
Core (config, logger, exceptions)
    ↓
    ├─→ PDF Ingestion (reader, processor, chunker)
    │       ↓
    │   Vector Store (embeddings)
    │       ↓
    │   Data Storage (canonical schema)
    │       ↓
    │   Qdrant Vector DB
    │
    ├─→ Web Extraction (extractor, navigator, auth)
    │       ↓
    │   Data Storage (canonical schema)
    │       ↓
    │   Coverage Tracking
    │
    ├─→ RAG Pipeline (retriever, context, query_expander)
    │       ↓
    │   Vector Store (search)
    │       ↓
    │   Qdrant Vector DB
    │
    ├─→ Compliance Agent (orchestrator, comparison)
    │       ↓
    │   RAG Pipeline (retrieve context)
    │       ↓
    │   OpenAI LLM API
    │       ↓
    │   Data Storage (save results)
    │
    └─→ Reporting (generators, orchestrator)
            ↓
        Data Storage (retrieve results)
```

### Module Separation & Interfaces

**Each module has:**
- Clear entry points
- Dependency injection
- Minimal coupling
- Comprehensive error handling
- Structured logging

**Example:**
```python
# Module: src/agent/compliance_agent.py

class ComplianceAgent:
    """Core compliance checking logic."""
    
    def __init__(self, config: Dict[str, Any]):
        """Inject configuration."""
        self.config = config
        self.llm_client = OpenAI(api_key=config["llm"]["api_key"])
        self.logger = structlog.get_logger(__name__)
    
    async def assess_compliance(
        self,
        component: WebComponent,
        guideline_chunks: List[PDFChunk],
        context: str
    ) -> ComparisonAssessment:
        """Public interface for comparison."""
        try:
            # Implementation
            return assessment
        except Exception as e:
            self.logger.exception("assess_compliance_failed", error=str(e))
            raise ComplianceCheckError(str(e)) from e
```

---

## Design Patterns

### 1. **Configuration Pattern**

```python
# Single source of truth
config = get_config("config/base_config.yaml")

# Environment variable substitution
website_username = config.website.authentication.username
# If env var exists: ${WEBSITE_USERNAME}
# Falls back to YAML value

# Pydantic validation
try:
    config = Config(**config_dict)
except ValidationError as e:
    raise ConfigurationError(f"Invalid config: {e}")
```

### 2. **Dependency Injection Pattern**

```python
# Pass dependencies, don't create them
class ComplianceAgent:
    def __init__(self, config: Dict, llm_client=None, logger=None):
        self.config = config
        self.llm = llm_client or OpenAI(**config["llm"])
        self.logger = logger or structlog.get_logger(__name__)

# Testing: Easy to mock
mock_llm = Mock()
agent = ComplianceAgent(config, llm_client=mock_llm)
```

### 3. **Repository Pattern**

```python
# Abstract data access
class DataStore:
    def save_component(self, component: WebComponent) -> None:
        """Save to storage."""
    
    def get_component(self, id: str) -> Optional[WebComponent]:
        """Retrieve from storage."""
    
    def query_components(self, filters: Dict) -> List[WebComponent]:
        """Query with filters."""

# Implementation-agnostic
# Can swap JSON for database later
```

### 4. **Pipeline Pattern**

```python
# Chain operations
pipeline = (
    PDFReader(config)
    .extract_text()
    .pipe(TextProcessor(config).process)
    .pipe(ChunkGenerator(config).chunk_pages)
    .pipe(EmbeddingGenerator(config).embed_chunks_batch)
)

result = pipeline.execute()
```

### 5. **Strategy Pattern**

```python
# Different embedding models
embedders = {
    "openai": OpenAIEmbedder(config),
    "local": LocalEmbedder(config),
    "huggingface": HuggingFaceEmbedder(config)
}

embedder_strategy = embedders[config.embeddings.model_type]
embeddings = embedder_strategy.embed_text(text)
```

---

## Scalability Considerations

### 1. **Horizontal Scalability**

**Current:** Single process

**Future:** Distributed processing

```python
# Queue-based task distribution
from celery import Celery

app = Celery('compliance_agent')

@app.task
def compare_component(component_id: str):
    """Task for worker pool."""
    component = DataStore.get_component(component_id)
    assessment = agent.assess_compliance(component)
    return assessment

# Distribute across workers
for component in components:
    compare_component.delay(component.id)
```

### 2. **Caching Strategy**

**Levels:**
1. Query result caching (RAG)
2. Embedding caching (avoid re-embedding)
3. Comparison result caching (same component + guidelines)

```python
@lru_cache(maxsize=1000)
def cached_assess_compliance(
    component_hash: str,
    guideline_hash: str
) -> ComparisonAssessment:
    return agent.assess_compliance(component, guidelines)
```

### 3. **Database Scaling**

**Current:** File-based JSON

**Scalable Options:**
- PostgreSQL for structured data
- MongoDB for flexible schemas
- Time-series DB for metrics
- S3 for large files (screenshots)

---

## Error Handling Strategy

### Exception Hierarchy

```
Exception
├── ComplianceAgentError (base)
│   ├── ConfigurationError
│   ├── ProcessingError
│   ├── ValidationError
│   ├── ExternalAPIError
│   ├── ComplianceCheckError
│   ├── ExtractionError
│   ├── ReportGenerationError
│   └── ... (17 total)
```

### Error Recovery Strategies

**1. Retry with Exponential Backoff**
```python
@retry(
    max_attempts=3,
    backoff_factor=2,  # 1s, 2s, 4s
    exceptions=(NetworkError, TimeoutError)
)
def fetch_from_api():
    pass
```

**2. Graceful Degradation**
```python
try:
    screenshots = extractor.capture_screenshots()
except ScreenshotError as e:
    logger.warning("Screenshot capture failed, continuing without", error=e)
    screenshots = []  # Continue with empty
```

**3. Circuit Breaker**
```python
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=300  # Open circuit for 5 minutes
)

if circuit_breaker.is_open():
    raise CircuitOpenError("Service temporarily unavailable")
```

---

## Performance Optimization

### 1. **Concurrent Processing**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Parallel component comparison
async def compare_all_components(components):
    tasks = [
        agent.assess_compliance(component)
        for component in components
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 2. **Batch Processing**

```python
# Batch embeddings for efficiency
embeddings = embedder.embed_chunks_batch(
    chunks,
    batch_size=50  # Process 50 at a time
)
```

### 3. **Lazy Evaluation**

```python
# Don't extract until needed
@lazy_property
def expensive_screenshots(self):
    return self.extractor.capture_all_screenshots()
```

---

## Security Considerations

### 1. **Secret Management**

```yaml
# .env (never committed)
OPENAI_API_KEY=sk-...
WEBSITE_PASSWORD=secret

# config.yaml (substitute at runtime)
llm:
  api_key: ${OPENAI_API_KEY}
```

### 2. **Input Validation**

```python
from pydantic import BaseModel, Field

class WebComponent(BaseModel):
    url: str = Field(pattern=r"^https?://")
    selector: str = Field(min_length=1, max_length=500)
```

### 3. **Rate Limiting**

```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=100, period=60)
def call_llm_api():
    pass
```

---

## Related Documentation

- [CONFIGURATION.md](CONFIGURATION.md) - All config options
- [LLM_USAGE.md](LLM_USAGE.md) - AI/LLM integration details
- [README.md](../README.md) - Getting started

---

**Architecture Version:** 1.0  
**Last Updated:** December 2024  
**Status:** Production Ready

