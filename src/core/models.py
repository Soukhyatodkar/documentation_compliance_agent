"""
Pydantic models for configuration validation.

These models define the complete configuration schema with validation
for all 80+ configuration options.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum


class AuthType(str, Enum):
    """Authentication types."""

    NONE = "none"
    BASIC = "basic"
    FORM = "form"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class BrowserType(str, Enum):
    """Browser types supported by Playwright."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log format options."""

    SIMPLE = "simple"
    JSON = "json"
    STRUCTURED = "structured"


class ScrollBehavior(str, Enum):
    """Scroll behavior options."""

    NONE = "none"
    AUTO = "auto"
    FULL = "full"
    LAZY = "lazy"


class PDFStrategy(str, Enum):
    """PDF extraction strategies."""

    SIMPLE = "simple"
    SMART = "smart"
    SEMANTIC = "semantic"


# ============================================================================
# LLM Configuration
# ============================================================================


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4", description="LLM model name")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature (0-1)")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum tokens")
    api_key: Optional[str] = Field(default=None, description="API key for provider")
    timeout: int = Field(default=60, gt=0, description="Request timeout (seconds)")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries")

    class Config:
        use_enum_values = False


# ============================================================================
# Embedding Configuration
# ============================================================================


class EmbeddingsConfig(BaseModel):
    """Embeddings provider configuration."""

    provider: str = Field(default="openai", description="Embeddings provider")
    model: str = Field(default="text-embedding-3-small", description="Embeddings model")
    dimensions: int = Field(default=1536, gt=0, description="Embedding dimensions")
    api_key: Optional[str] = Field(default=None, description="API key")
    batch_size: int = Field(default=50, gt=0, description="Batch size for embeddings")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_hours: int = Field(default=24, ge=0, description="Cache TTL in hours")

    class Config:
        use_enum_values = False


# ============================================================================
# Vector Database Configuration
# ============================================================================


class VectorDBConfig(BaseModel):
    """Vector database configuration."""

    type: str = Field(default="qdrant", description="Vector DB type")
    url: str = Field(default="http://localhost:6333", description="Database URL")
    api_key: Optional[str] = Field(default=None, description="API key")
    collection_name: str = Field(default="guidelines", description="Collection name")
    vector_size: int = Field(default=1536, gt=0, description="Vector size")
    distance_metric: str = Field(default="cosine", description="Distance metric")
    timeout: int = Field(default=30, gt=0, description="Timeout in seconds")
    chunk_size: int = Field(default=500, gt=0, description="Chunk size")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Similarity threshold"
    )

    class Config:
        use_enum_values = False


# ============================================================================
# Authentication Configuration
# ============================================================================


class AuthenticationConfig(BaseModel):
    """Authentication configuration."""

    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    cookie_name: Optional[str] = Field(default=None, description="Session cookie name")
    token_header: str = Field(default="Authorization", description="Token header name")
    token_value: Optional[str] = Field(default=None, description="Token value")
    session_timeout_minutes: int = Field(default=30, gt=0, description="Session timeout")

    class Config:
        use_enum_values = True


# ============================================================================
# Website Crawling Configuration
# ============================================================================


class CrawlingConfig(BaseModel):
    """Website crawling configuration."""

    max_pages: int = Field(default=100, gt=0, description="Maximum pages to crawl")
    max_links: int = Field(default=500, gt=0, description="Maximum links to follow")
    skip_urls: List[str] = Field(default_factory=list, description="URL patterns to skip")
    allowed_url_patterns: List[str] = Field(
        default_factory=list, description="Allowed URL patterns"
    )
    follow_external_links: bool = Field(default=False, description="Follow external links")

    class Config:
        use_enum_values = False


# ============================================================================
# Website Extraction Configuration
# ============================================================================


class ExtractionConfig(BaseModel):
    """Website extraction configuration."""

    wait_for_selectors: List[str] = Field(
        default_factory=list, description="CSS selectors to wait for"
    )
    execute_js: Optional[str] = Field(default=None, description="JavaScript to execute")
    scroll_behavior: ScrollBehavior = Field(
        default=ScrollBehavior.FULL, description="Scroll behavior"
    )

    class Config:
        use_enum_values = True


# ============================================================================
# Website Configuration
# ============================================================================


class WebsiteConfig(BaseModel):
    """Website configuration."""

    url: str = Field(description="Website URL")
    username: Optional[str] = Field(default=None, description="Login username")
    password: Optional[str] = Field(default=None, description="Login password")
    login_url: Optional[str] = Field(default=None, description="Login URL")
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    crawling: CrawlingConfig = Field(default_factory=CrawlingConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)

    class Config:
        use_enum_values = False


# ============================================================================
# Browser Configuration
# ============================================================================


class ViewportConfig(BaseModel):
    """Viewport configuration."""

    width: int = Field(default=1280, gt=0, description="Viewport width")
    height: int = Field(default=720, gt=0, description="Viewport height")

    class Config:
        use_enum_values = False


class TimeoutsConfig(BaseModel):
    """Timeouts configuration."""

    page_load: int = Field(default=30000, gt=0, description="Page load timeout (ms)")
    element_wait: int = Field(default=10000, gt=0, description="Element wait timeout (ms)")
    navigation: int = Field(default=30000, gt=0, description="Navigation timeout (ms)")

    class Config:
        use_enum_values = False


class ScreenshotsConfig(BaseModel):
    """Screenshots configuration."""

    enabled: bool = Field(default=True, description="Enable screenshots")
    full_page: bool = Field(default=True, description="Full page screenshots")
    element_screenshots: bool = Field(default=True, description="Element screenshots")
    quality: int = Field(default=90, ge=1, le=100, description="Screenshot quality")
    format: str = Field(default="png", description="Screenshot format")
    directory: str = Field(default="./data/screenshots", description="Screenshot directory")

    class Config:
        use_enum_values = False


class BrowserConfig(BaseModel):
    """Browser configuration."""

    type: BrowserType = Field(default=BrowserType.CHROMIUM, description="Browser type")
    headless: bool = Field(default=True, description="Run headless")
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    screenshots: ScreenshotsConfig = Field(default_factory=ScreenshotsConfig)
    js_enabled: bool = Field(default=True, description="Enable JavaScript")
    user_agent: Optional[str] = Field(default=None, description="Custom user agent")
    proxy: Optional[str] = Field(default=None, description="Proxy URL")
    disable_images: bool = Field(default=False, description="Disable image loading")

    class Config:
        use_enum_values = True


# ============================================================================
# PDF Configuration
# ============================================================================


class ChunkingConfig(BaseModel):
    """PDF chunking configuration."""

    min_chunk_size: int = Field(default=100, gt=0, description="Minimum chunk size")
    max_chunk_size: int = Field(default=1000, gt=0, description="Maximum chunk size")
    overlap: int = Field(default=100, ge=0, description="Chunk overlap")
    preserve_headings: bool = Field(default=True, description="Preserve headings")
    preserve_metadata: bool = Field(default=True, description="Preserve metadata")

    class Config:
        use_enum_values = False


class PDFConfig(BaseModel):
    """PDF configuration."""

    path: str = Field(description="Path to PDF file")
    strategy: PDFStrategy = Field(default=PDFStrategy.SEMANTIC, description="Extraction strategy")
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    extract_tables: bool = Field(default=True, description="Extract tables")
    extract_images: bool = Field(default=False, description="Extract images")
    extract_metadata: bool = Field(default=True, description="Extract metadata")

    class Config:
        use_enum_values = True


# ============================================================================
# Retry Configuration
# ============================================================================


class RetryConfig(BaseModel):
    """Retry configuration."""

    max_retries: int = Field(default=3, ge=0, description="Maximum retries")
    initial_delay_ms: int = Field(default=1000, gt=0, description="Initial delay (ms)")
    backoff_multiplier: float = Field(default=2.0, gt=1.0, description="Backoff multiplier")
    max_delay_ms: int = Field(default=30000, gt=0, description="Maximum delay (ms)")
    exponential: bool = Field(default=True, description="Use exponential backoff")
    jitter: bool = Field(default=True, description="Add jitter to delays")

    class Config:
        use_enum_values = False


# ============================================================================
# Coverage Configuration
# ============================================================================


class CoverageConfig(BaseModel):
    """Coverage tracking configuration."""

    min_coverage_percentage: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Minimum coverage"
    )
    track_failed_pages: bool = Field(default=True, description="Track failed pages")
    track_auth_failures: bool = Field(default=True, description="Track auth failures")
    track_extraction_failures: bool = Field(default=True, description="Track extraction failures")

    class Config:
        use_enum_values = False


# ============================================================================
# Output Configuration
# ============================================================================


class OutputConfig(BaseModel):
    """Output configuration."""

    base_dir: str = Field(default="./data", description="Base output directory")
    reports_dir: str = Field(default="./data/reports", description="Reports directory")
    screenshots_dir: str = Field(default="./data/screenshots", description="Screenshots directory")
    extracted_dir: str = Field(default="./data/extracted", description="Extracted data directory")

    class Config:
        use_enum_values = False


# ============================================================================
# Report Configuration
# ============================================================================


class MarkdownReportConfig(BaseModel):
    """Markdown report configuration."""

    enabled: bool = Field(default=True, description="Generate Markdown report")
    include_table_of_contents: bool = Field(default=True, description="Include TOC")
    include_screenshots: bool = Field(default=True, description="Include screenshots")
    include_timestamps: bool = Field(default=True, description="Include timestamps")

    class Config:
        use_enum_values = False


class JSONReportConfig(BaseModel):
    """JSON report configuration."""

    enabled: bool = Field(default=True, description="Generate JSON report")
    pretty_print: bool = Field(default=True, description="Pretty print JSON")
    include_metadata: bool = Field(default=True, description="Include metadata")

    class Config:
        use_enum_values = False


class HTMLReportConfig(BaseModel):
    """HTML report configuration."""

    enabled: bool = Field(default=True, description="Generate HTML report")
    include_screenshots: bool = Field(default=True, description="Include screenshots")
    interactive_elements: bool = Field(default=True, description="Interactive elements")
    theme: str = Field(default="light", description="Theme (light/dark)")

    class Config:
        use_enum_values = False


class CommonReportConfig(BaseModel):
    """Common report configuration."""

    min_confidence_score: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum confidence"
    )
    group_by_severity: bool = Field(default=True, description="Group by severity")
    include_coverage_report: bool = Field(default=True, description="Include coverage")
    timestamp_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Timestamp format")

    class Config:
        use_enum_values = False


class ReportingConfig(BaseModel):
    """Reporting configuration."""

    markdown: MarkdownReportConfig = Field(default_factory=MarkdownReportConfig)
    json: JSONReportConfig = Field(default_factory=JSONReportConfig)
    html: HTMLReportConfig = Field(default_factory=HTMLReportConfig)
    common: CommonReportConfig = Field(default_factory=CommonReportConfig)

    class Config:
        use_enum_values = False


# ============================================================================
# Logging Configuration
# ============================================================================


class RotationConfig(BaseModel):
    """Log rotation configuration."""

    enabled: bool = Field(default=True, description="Enable log rotation")
    max_size_mb: int = Field(default=10, gt=0, description="Max size in MB")
    backup_count: int = Field(default=5, ge=0, description="Number of backups")

    class Config:
        use_enum_values = False


class IncludeConfig(BaseModel):
    """What to include in logs."""

    sql_queries: bool = Field(default=False, description="Log SQL queries")
    http_requests: bool = Field(default=False, description="Log HTTP requests")
    embeddings: bool = Field(default=False, description="Log embeddings")
    detailed_extraction: bool = Field(default=False, description="Detailed extraction logs")

    class Config:
        use_enum_values = False


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    format: LogFormat = Field(default=LogFormat.STRUCTURED, description="Log format")
    file: str = Field(default="./logs/agent.log", description="Log file path")
    rotation: RotationConfig = Field(default_factory=RotationConfig)
    include: IncludeConfig = Field(default_factory=IncludeConfig)

    class Config:
        use_enum_values = True


# ============================================================================
# Performance Configuration
# ============================================================================


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    concurrent_workers: int = Field(default=3, gt=0, description="Concurrent workers")
    embedding_batch_size: int = Field(default=50, gt=0, description="Embedding batch size")
    use_embedding_cache: bool = Field(default=True, description="Use embedding cache")
    cache_ttl_hours: int = Field(default=24, ge=0, description="Cache TTL in hours")

    class Config:
        use_enum_values = False


# ============================================================================
# Advanced Configuration
# ============================================================================


class AdvancedConfig(BaseModel):
    """Advanced configuration options."""

    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    monitoring_port: int = Field(default=8000, gt=0, le=65535, description="Monitoring port")
    test_mode: bool = Field(default=False, description="Test mode")
    use_mock_data: bool = Field(default=False, description="Use mock data")
    mock_data_file: str = Field(default="./tests/fixtures/mock_data.json", description="Mock data")

    class Config:
        use_enum_values = False


# ============================================================================
# Application Configuration
# ============================================================================


class AppConfig(BaseModel):
    """Application metadata."""

    name: str = Field(default="Documentation Compliance Agent", description="App name")
    version: str = Field(default="1.0.0", description="App version")
    description: str = Field(default="", description="App description")
    debug: bool = Field(default=False, description="Debug mode")
    dry_run: bool = Field(default=False, description="Dry run mode")
    strict_mode: bool = Field(default=False, description="Strict mode")

    class Config:
        use_enum_values = False


# ============================================================================
# Root Configuration
# ============================================================================


class Config(BaseModel):
    """Complete application configuration."""

    app: AppConfig = Field(default_factory=AppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    website: WebsiteConfig
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    pdf: PDFConfig
    retry: RetryConfig = Field(default_factory=RetryConfig)
    coverage: CoverageConfig = Field(default_factory=CoverageConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    class Config:
        use_enum_values = False

    @validator("retry")
    def validate_retry_delays(cls, v):
        """Validate retry delay configuration."""
        if v.initial_delay_ms > v.max_delay_ms:
            raise ValueError("initial_delay_ms cannot be greater than max_delay_ms")
        return v

    @validator("pdf")
    def validate_pdf_chunking(cls, v):
        """Validate PDF chunking configuration."""
        if v.chunking.min_chunk_size > v.chunking.max_chunk_size:
            raise ValueError("min_chunk_size cannot be greater than max_chunk_size")
        return v
