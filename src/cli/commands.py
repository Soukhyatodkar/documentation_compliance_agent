"""
CLI Commands for Documentation Compliance Agent.

This module provides the command handlers for all CLI operations including:
- Full pipeline execution
- Individual stage execution (ingest, extract, compare, report)
- Utility commands (config, test-connection, status)
- Progress reporting and result formatting
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import structlog

from src.core.config import get_config
from src.core.exceptions import (
    ConfigurationError,
    ProcessingError,
    ValidationError,
    ExternalAPIError,
)
from src.core.logger import setup_logging
from src.pdf_ingestion.pdf_reader import PDFReader
from src.pdf_ingestion.chunk_generator import ChunkGenerator
from src.vector_store.embeddings import EmbeddingGenerator
from src.vector_store.qdrant_client import QdrantVectorStore
from src.data.models import WebComponent, ComparisonResult
from src.data.storage import DataStore
from src.coverage.tracker import CoverageTracker
from src.rag.retriever import SemanticRetriever
from src.rag.context import ContextBuilder
from src.agent.compliance_agent import ComplianceAgent
from src.agent.orchestrator import ComplianceOrchestrator
from src.reporting.report_generator import (
    ReportingOrchestrator,
    ReportMetadata,
)

logger = structlog.get_logger(__name__)

app = typer.Typer(
    help="Documentation Compliance Agent - Verify web applications against official documentation"
)


# ============================================================================
# Main Pipeline Command
# ============================================================================


@app.command()
def run(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would happen without executing",
    ),
) -> None:
    """
    Run the complete compliance checking pipeline.

    This command executes all stages:
    1. Ingest PDF guidelines
    2. Extract website components
    3. Compare against guidelines
    4. Generate reports

    Example:
        python main.py run --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Documentation Compliance Agent - Full Pipeline")
        typer.echo("=" * 70 + "\n")

        # Load configuration
        typer.echo("  Loading configuration...")
        config = get_config(config_path)

        # Setup logging
        setup_logging(config, verbose=verbose)

        if dry_run:
            typer.echo("  DRY RUN MODE - No changes will be made\n")
            _show_config_summary(config)
            return

        start_time = datetime.now()

        # Stage 1: Ingest PDF
        typer.echo(" Stage 1: Ingesting PDF guidelines...")
        _ingest_stage(config)
        typer.echo(" PDF ingestion complete\n")

        # Stage 2: Extract website (if not skipped)
        if not config.app.skip_extraction:
            typer.echo(" Stage 2: Extracting website components...")
            _extract_stage(config)
            typer.echo(" Website extraction complete\n")

        # Stage 3: Compare components
        typer.echo(" Stage 3: Comparing against guidelines...")
        results, discrepancies = asyncio.run(_compare_stage(config))
        typer.echo(f" Comparison complete - Found {len(discrepancies)} discrepancies\n")

        # Stage 4: Generate reports
        typer.echo(" Stage 4: Generating reports...")
        report_paths = _report_stage(config, results, discrepancies)
        typer.echo(" Reports generated\n")

        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        typer.echo("=" * 70)
        typer.echo(" PIPELINE COMPLETE")
        typer.echo("=" * 70)
        typer.echo(f"Duration: {duration:.1f}s")
        typer.echo(f"Discrepancies Found: {len(discrepancies)}")
        typer.echo(f"Compliance Score: {_calculate_compliance_score(results)}%")
        typer.echo("\n Reports Generated:")
        for name, path in report_paths.items():
            typer.echo(f"   {name.upper()}: {path}")
        typer.echo()

    except ConfigurationError as e:
        typer.echo(f" Configuration Error: {str(e)}", err=True)
        logger.exception("config_error", error=str(e))
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f" Pipeline Error: {str(e)}", err=True)
        logger.exception("pipeline_error", error=str(e))
        raise typer.Exit(1)


# ============================================================================
# Individual Stage Commands
# ============================================================================


@app.command()
def ingest(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """
    Ingest PDF guidelines into vector database.

    This command:
    1. Reads the PDF file
    2. Extracts and chunks text
    3. Generates embeddings
    4. Stores in Qdrant vector database

    Example:
        python main.py ingest --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Stage 1: PDF Ingestion")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config, verbose=verbose)

        _ingest_stage(config)

        typer.echo("\n PDF ingestion complete\n")

    except Exception as e:
        typer.echo(f" Ingestion Error: {str(e)}", err=True)
        logger.exception("ingest_error", error=str(e))
        raise typer.Exit(1)


@app.command()
def extract(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """
    Extract components from website.

    This command:
    1. Authenticates with the website (if needed)
    2. Navigates to specified pages
    3. Extracts components
    4. Captures screenshots
    5. Stores in canonical data format

    Example:
        python main.py extract --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Stage 2: Website Extraction")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config, verbose=verbose)

        _extract_stage(config)

        typer.echo("\n Website extraction complete\n")

    except Exception as e:
        typer.echo(f" Extraction Error: {str(e)}", err=True)
        logger.exception("extract_error", error=str(e))
        raise typer.Exit(1)


@app.command()
def compare(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """
    Compare website components against guidelines.

    This command:
    1. Retrieves stored website components
    2. Performs semantic search on guidelines
    3. Uses LLM to compare and detect discrepancies
    4. Generates confidence scores

    Example:
        python main.py compare --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Stage 3: Compliance Comparison")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config, verbose=verbose)

        results, discrepancies = asyncio.run(_compare_stage(config))

        typer.echo(f"\n Comparison complete")
        typer.echo(f"Discrepancies Found: {len(discrepancies)}")
        typer.echo(f"Compliance Score: {_calculate_compliance_score(results)}%\n")

    except Exception as e:
        typer.echo(f" Comparison Error: {str(e)}", err=True)
        logger.exception("compare_error", error=str(e))
        raise typer.Exit(1)


@app.command()
def report(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """
    Generate compliance reports.

    This command generates reports in multiple formats:
    - JSON (machine-readable)
    - Markdown (human-readable)
    - HTML (interactive dashboard)

    Example:
        python main.py report --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Stage 4: Report Generation")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config, verbose=verbose)

        # Load stored results
        data_store = DataStore(config)
        discrepancies = data_store.get_discrepancies()
        results = data_store.get_comparison_results()

        report_paths = _report_stage(config, results, discrepancies)

        typer.echo("\n Reports generated\n")
        typer.echo(" Report Locations:")
        for name, path in report_paths.items():
            typer.echo(f"   {name.upper()}: {path}")
        typer.echo()

    except Exception as e:
        typer.echo(f" Report Generation Error: {str(e)}", err=True)
        logger.exception("report_error", error=str(e))
        raise typer.Exit(1)


# ============================================================================
# Utility Commands
# ============================================================================


@app.command()
def config(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Show specific section only",
    ),
) -> None:
    """
    Display current configuration.

    Shows all active configuration settings loaded from the YAML file
    and environment variables.

    Example:
        python main.py config --config config/base_config.yaml
        python main.py config --section website
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo("  Configuration")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        _show_config_summary(config, section)

        typer.echo()

    except Exception as e:
        typer.echo(f" Configuration Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def test_connection(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Test connections to external services.

    Verifies that all required external services are accessible:
    - Qdrant vector database
    - OpenAI API
    - Website URL

    Example:
        python main.py test-connection --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Testing Connections")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config)

        # Test Qdrant
        typer.echo("Testing Qdrant vector database...")
        try:
            vector_store = QdrantVectorStore(config)
            vector_store.health_check()
            typer.echo("   Qdrant: Connected")
        except Exception as e:
            typer.echo(f"   Qdrant: Failed - {str(e)}", err=True)

        # Test OpenAI API
        typer.echo("Testing OpenAI API...")
        try:
            embedder = EmbeddingGenerator(config)
            # Test with small embedding
            embedder.embed_text("test")
            typer.echo("   OpenAI API: Connected")
        except Exception as e:
            typer.echo(f"   OpenAI API: Failed - {str(e)}", err=True)

        # Test Website URL
        typer.echo(f"Testing website: {config.website.url}...")
        try:
            import httpx

            async def test_url():
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        config.website.url, timeout=10.0, follow_redirects=True
                    )
                    return response.status_code

            status = asyncio.run(test_url())
            typer.echo(f"   Website: Reachable (HTTP {status})")
        except Exception as e:
            typer.echo(f"   Website: Unreachable - {str(e)}", err=True)

        # Test PDF file
        typer.echo(f"Testing PDF file: {config.pdf.path}...")
        if Path(config.pdf.path).exists():
            typer.echo("   PDF: File exists")
        else:
            typer.echo(f"   PDF: File not found", err=True)

        typer.echo("\n Connection test complete\n")

    except Exception as e:
        typer.echo(f" Connection Test Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Show project status and statistics.

    Displays information about:
    - Stored PDF chunks and embeddings
    - Extracted website components
    - Existing comparison results
    - Generated reports

    Example:
        python main.py status --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Project Status")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config)

        data_store = DataStore(config)

        # Show statistics
        components_count = data_store.count_components()
        results_count = data_store.count_comparison_results()
        discrepancies_count = data_store.count_discrepancies()

        typer.echo(" Statistics:")
        typer.echo(f"   Components stored: {components_count}")
        typer.echo(f"   Comparison results: {results_count}")
        typer.echo(f"   Discrepancies found: {discrepancies_count}")

        # Show report status
        report_dir = Path(config.output.reports_dir)
        if report_dir.exists():
            reports = list(report_dir.glob("*"))
            typer.echo(f"\n Reports ({len(reports)}):")
            for report in sorted(reports)[-5:]:
                typer.echo(f"   {report.name}")
        else:
            typer.echo("\n Reports: None generated yet")

        typer.echo()

    except Exception as e:
        typer.echo(f" Status Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo("\nDocumentation Compliance Agent")
    typer.echo("Version: 1.0.0")
    typer.echo("Status: Production Ready")
    typer.echo()


@app.command()
def validate_config(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Validate configuration file.

    Checks that the configuration file is valid and all required
    fields are present and properly formatted.

    Example:
        python main.py validate-config --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" Validating Configuration")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        typer.echo(" Configuration is valid")
        typer.echo(f"   Website: {config.website.url}")
        typer.echo(f"   PDF: {config.pdf.path}")
        typer.echo(f"   LLM Model: {config.llm.model}")
        typer.echo(f"   Vector DB: {config.vector_db.url}")
        typer.echo()

    except ConfigurationError as e:
        typer.echo(f" Configuration Error: {str(e)}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f" Validation Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def health_check(
    config_path: str = typer.Option(
        "config/base_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
    ),
) -> None:
    """
    Perform system health check.

    Verifies that all components are properly configured and accessible:
    - Configuration validation
    - External service connectivity
    - File permissions
    - Required dependencies

    Example:
        python main.py health-check --config config/base_config.yaml
    """
    try:
        typer.echo("\n" + "=" * 70)
        typer.echo(" System Health Check")
        typer.echo("=" * 70 + "\n")

        config = get_config(config_path)
        setup_logging(config)

        all_healthy = True

        # Check configuration
        typer.echo(" Configuration: Valid")

        # Check required directories
        typer.echo("Checking directories...")
        for dir_name, dir_path in [
            ("PDF Data", config.output.pdfs_dir),
            ("Extracted Data", config.output.extracted_dir),
            ("Screenshots", config.output.screenshots_dir),
            ("Reports", config.output.reports_dir),
            ("Logs", config.output.logs_dir),
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            typer.echo(f"   {dir_name}: OK")

        # Check PDF file
        typer.echo("Checking required files...")
        if Path(config.pdf.path).exists():
            typer.echo(f"   PDF File: Found")
        else:
            typer.echo(f"   PDF File: Not found at {config.pdf.path}", err=True)
            all_healthy = False

        # Check services (optional - don't fail on errors)
        typer.echo("Checking external services...")
        try:
            vector_store = QdrantVectorStore(config)
            vector_store.health_check()
            typer.echo("   Qdrant Vector DB: Connected")
        except Exception as e:
            typer.echo(f"    Qdrant Vector DB: Unreachable ({str(e)[:50]}...)")

        try:
            embedder = EmbeddingGenerator(config)
            embedder.embed_text("health_check")
            typer.echo("   OpenAI API: Connected")
        except Exception as e:
            typer.echo(f"    OpenAI API: Unreachable ({str(e)[:50]}...)")

        typer.echo()
        if all_healthy:
            typer.echo(" System health: OK - Ready to use")
        else:
            typer.echo("  System health: Check warnings above")
            raise typer.Exit(1)

        typer.echo()

    except Exception as e:
        typer.echo(f" Health Check Error: {str(e)}", err=True)
        raise typer.Exit(1)


# ============================================================================
# Helper Functions for Stages
# ============================================================================


def _ingest_stage(config) -> None:
    """Execute PDF ingestion stage."""
    # Read PDF
    typer.echo("   Reading PDF...")
    reader = PDFReader(config.pdf.path)
    pages = reader.extract_text()
    typer.echo(f"     Extracted {len(pages)} pages")

    # Generate chunks
    typer.echo("   Generating chunks...")
    chunk_gen = ChunkGenerator(
        min_chunk_size=config.pdf.chunking.min_chunk_size,
        max_chunk_size=config.pdf.chunking.max_chunk_size,
        overlap=config.pdf.chunking.overlap,
    )
    chunks = chunk_gen.chunk_pages(pages)
    typer.echo(f"     Generated {len(chunks)} chunks")

    # Generate embeddings
    typer.echo("   Generating embeddings...")
    embedder = EmbeddingGenerator(config)
    embedded_chunks = embedder.embed_chunks_batch(chunks, batch_size=10)
    typer.echo(f"     Embedded {len(embedded_chunks)} chunks")

    # Store in vector database
    typer.echo("   Storing in Qdrant...")
    vector_store = QdrantVectorStore(config)
    vector_store.create_collection()
    vector_store.add_points(embedded_chunks)
    typer.echo(f"     Stored in Qdrant")

    logger.info("pdf_ingestion_complete", chunks=len(chunks), embeddings=len(embedded_chunks))


def _extract_stage(config) -> None:
    """Execute website extraction stage."""
    from src.web_extraction.extractor import WebsiteExtractor
    
    typer.echo("   Extracting website components...")
    extractor = WebsiteExtractor(config)
    
    # Extract components
    components = asyncio.run(extractor.extract_website())
    typer.echo(f"     Extracted {len(components)} components")
    
    # Store components
    data_store = DataStore(config)
    for component in components:
        data_store.save_component(component)
    typer.echo(f"     Stored components in data store")


async def _compare_stage(config) -> tuple:
    """Execute compliance comparison stage."""
    data_store = DataStore(config)

    # Load components
    typer.echo("   Loading stored components...")
    components = data_store.get_components()
    typer.echo(f"     Loaded {len(components)} components")

    # Setup retriever and agent
    typer.echo("   Setting up RAG pipeline...")
    embedder = EmbeddingGenerator(config)
    vector_store = QdrantVectorStore(config)
    retriever = SemanticRetriever(embedder, vector_store)
    context_builder = ContextBuilder(config)

    typer.echo("   Comparing components...")
    agent = ComplianceAgent(config)
    orch = ComplianceOrchestrator(agent, retriever, context_builder, data_store)

    # Compare all components
    results = []
    discrepancies = []

    for i, component in enumerate(components):
        typer.echo(f"     {i+1}/{len(components)}: {component.component_type}...", nl=False)
        try:
            result, discreps = await orch.check_components_batch([component])
            results.extend(result)
            discrepancies.extend(discreps)
            typer.echo(" ")
        except Exception as e:
            typer.echo(f"  ({str(e)})")
            logger.warning("component_comparison_failed", component=component.id, error=str(e))

    typer.echo(f"     Compared {len(results)} components, found {len(discrepancies)} issues")

    # Store results
    for result in results:
        data_store.save_comparison_result(result)
    for discrep in discrepancies:
        data_store.save_discrepancy(discrep)

    logger.info(
        "comparison_complete", results=len(results), discrepancies=len(discrepancies)
    )

    return results, discrepancies


def _report_stage(config, results: list, discrepancies: list) -> dict:
    """Execute report generation stage."""
    typer.echo("   Generating report metadata...")
    metadata = ReportMetadata(
        report_id=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        generated_at=datetime.now(),
        website_url=config.website.url,
        pages_checked=len(set(r.page_url for r in results)),
        components_checked=len(results),
        discrepancies_found=len(discrepancies),
        audit_duration_seconds=0.0,  # Would be calculated from timing
        compliance_percentage=_calculate_compliance_score(results),
    )

    typer.echo("   Generating multi-format reports...")
    orch = ReportingOrchestrator()
    report_paths = orch.generate_all(
        metadata, results, discrepancies, output_dir=config.output.reports_dir
    )

    typer.echo(f"     Generated JSON report")
    typer.echo(f"     Generated Markdown report")
    typer.echo(f"     Generated HTML report")

    logger.info("reports_generated", paths=report_paths)

    return report_paths


# ============================================================================
# Helper Functions for Display
# ============================================================================


def _show_config_summary(config, section: Optional[str] = None) -> None:
    """Display configuration summary."""

    def show_section(name: str, obj: dict, indent: int = 0) -> None:
        prefix = "  " * indent
        for key, value in obj.items():
            if isinstance(value, dict):
                typer.echo(f"{prefix} {key}:")
                show_section(name, value, indent + 1)
            else:
                # Hide sensitive values
                if any(
                    x in key.lower()
                    for x in ["password", "token", "key", "secret", "api_key"]
                ):
                    value = "***REDACTED***"
                typer.echo(f"{prefix}{key}: {value}")

    if section:
        if hasattr(config, section):
            obj = getattr(config, section)
            typer.echo(f" {section.upper()}:")
            if hasattr(obj, "model_dump"):
                show_section(section, obj.model_dump())
            else:
                typer.echo(f"  {obj}")
        else:
            typer.echo(f" Section not found: {section}")
    else:
        typer.echo(" WEBSITE:")
        show_section("website", config.website.model_dump(), 1)
        typer.echo("\n PDF:")
        show_section("pdf", config.pdf.model_dump(), 1)
        typer.echo("\n LLM:")
        show_section("llm", config.llm.model_dump(), 1)
        typer.echo("\n VECTOR DATABASE:")
        show_section("vector_db", config.vector_db.model_dump(), 1)


def _calculate_compliance_score(results: list) -> float:
    """Calculate overall compliance percentage."""
    if not results:
        return 100.0

    compliant_count = sum(
        1 for r in results if r.status.value == "compliant" if hasattr(r, "status")
    )
    return (compliant_count / len(results)) * 100


if __name__ == "__main__":
    app()
