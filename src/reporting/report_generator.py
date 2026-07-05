"""
Report Generation - Convert compliance checking results into human-readable and machine-readable formats.

This module provides comprehensive report generation capabilities for compliance audit results,
including JSON, HTML, and Markdown formats with statistics, visualizations, and evidence.

Features:
- JSON structured reports
- HTML interactive dashboards
- Markdown human-readable reports
- Statistics aggregation
- Evidence attachment
- Screenshot embedding
- Summary generation
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import base64

from pydantic import BaseModel, Field
import structlog

from src.core.exceptions import ReportGenerationError
from src.data.models import (
    Discrepancy,
    ComparisonResult,
    SeverityLevel,
    ComponentType,
    DiscrepancyType,
)


logger = structlog.get_logger(__name__)


class ReportMetadata(BaseModel):
    """Metadata for generated report."""

    report_id: str = Field(description="Unique report identifier")
    generated_at: datetime = Field(description="Report generation timestamp")
    website_url: str = Field(description="Website URL being audited")
    pages_checked: int = Field(description="Number of pages checked")
    components_checked: int = Field(description="Total components checked")
    discrepancies_found: int = Field(description="Total discrepancies")
    audit_duration_seconds: float = Field(description="Total audit duration")
    compliance_percentage: float = Field(ge=0.0, le=100.0, description="Overall compliance %")


class JSONReportGenerator:
    """Generate JSON format compliance reports."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize JSON report generator.

        Args:
            config: Configuration dictionary
        """
        self._config = config or {}
        logger.info("JSON report generator initialized")

    def generate(
        self,
        metadata: ReportMetadata,
        results: List[ComparisonResult],
        discrepancies: List[Discrepancy],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate JSON report.

        Args:
            metadata: Report metadata
            results: Comparison results
            discrepancies: Detected discrepancies
            output_path: Optional path to save report

        Returns:
            Report as dictionary
        """
        try:
            # Aggregate statistics
            stats = self._aggregate_statistics(results, discrepancies)

            # Build report structure
            report = {
                "metadata": {
                    "report_id": metadata.report_id,
                    "generated_at": metadata.generated_at.isoformat(),
                    "website_url": metadata.website_url,
                    "pages_checked": metadata.pages_checked,
                    "components_checked": metadata.components_checked,
                    "discrepancies_found": metadata.discrepancies_found,
                    "audit_duration_seconds": metadata.audit_duration_seconds,
                    "compliance_percentage": metadata.compliance_percentage,
                },
                "summary": {
                    "compliant_pages": stats["compliant_pages"],
                    "non_compliant_pages": stats["non_compliant_pages"],
                    "compliant_components": stats["compliant_components"],
                    "non_compliant_components": stats["non_compliant_components"],
                    "critical_issues": stats["critical_count"],
                    "warnings": stats["warning_count"],
                    "info_issues": stats["info_count"],
                },
                "discrepancies": [
                    self._format_discrepancy(d) for d in discrepancies
                ],
                "statistics": stats,
                "recommendations": self._generate_recommendations(discrepancies),
            }

            # Save if path provided
            if output_path:
                self._save_json(report, output_path)

            logger.info(
                "JSON report generated",
                report_id=metadata.report_id,
                discrepancy_count=len(discrepancies),
            )

            return report

        except Exception as e:
            logger.error("JSON report generation failed", error=str(e))
            raise ReportGenerationError(f"Failed to generate JSON report: {e}") from e

    def _format_discrepancy(self, d: Discrepancy) -> Dict[str, Any]:
        """Format discrepancy for JSON report."""
        component_type_val = d.component_type.value if hasattr(d.component_type, 'value') else str(d.component_type)
        return {
            "id": d.discrepancy_id,
            "page_url": d.page_url,
            "component_id": d.component_id,
            "component_type": component_type_val,
            "component_selector": d.component_selector,
            "actual": d.actual_content,
            "expected": d.expected_content,
            "guideline": d.guideline_chunk_id,
            "guideline_section": d.guideline_section,
            "severity": d.severity.value if hasattr(d.severity, 'value') else str(d.severity),
            "confidence": d.confidence_score,
            "reason": d.reason,
            "suggestion": d.remediation_suggestion,
            "detected_at": d.detected_at,
        }

    def _aggregate_statistics(
        self, results: List[ComparisonResult], discrepancies: List[Discrepancy]
    ) -> Dict[str, Any]:
        """Aggregate statistics from results."""
        critical = sum(1 for d in discrepancies if d.severity == SeverityLevel.CRITICAL)
        warning = sum(1 for d in discrepancies if d.severity == SeverityLevel.WARNING)
        info = sum(1 for d in discrepancies if d.severity == SeverityLevel.INFO)

        by_component = {}
        for d in discrepancies:
            key = d.component_type.value if hasattr(d.component_type, 'value') else str(d.component_type)
            by_component[key] = by_component.get(key, 0) + 1

        return {
            "compliant_pages": len([r for r in results if r.total_components == 0 or r.compliant_components == r.total_components]),
            "non_compliant_pages": len([r for r in results if r.total_components > 0 and r.compliant_components < r.total_components]),
            "compliant_components": sum(r.compliant_components for r in results) if results else 0,
            "non_compliant_components": sum(r.non_compliant_components for r in results) if results else 0,
            "critical_count": critical,
            "warning_count": warning,
            "info_count": info,
            "by_severity": {
                "critical": critical,
                "warning": warning,
                "info": info,
            },
            "by_component_type": by_component,
        }

    def _generate_recommendations(self, discrepancies: List[Discrepancy]) -> List[str]:
        """Generate high-level recommendations."""
        recommendations = []

        critical_count = sum(1 for d in discrepancies if d.severity == SeverityLevel.CRITICAL)
        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical issues immediately as they impact core functionality"
            )

        missing_count = sum(1 for d in discrepancies if "missing" in d.reason.lower() or "absent" in d.reason.lower())
        if missing_count > 0:
            recommendations.append(
                f"Add {missing_count} missing components/attributes to comply with guidelines"
            )

        incorrect_count = sum(1 for d in discrepancies if "incorrect" in d.reason.lower() or "wrong" in d.reason.lower())
        if incorrect_count > 0:
            recommendations.append(
                f"Correct {incorrect_count} incorrect implementations to match guidelines"
            )

        return recommendations

    def _save_json(self, report: Dict[str, Any], path: str) -> None:
        """Save JSON report to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("JSON report saved", path=path)


class MarkdownReportGenerator:
    """Generate Markdown format compliance reports."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Markdown report generator."""
        self._config = config or {}
        logger.info("Markdown report generator initialized")

    def generate(
        self,
        metadata: ReportMetadata,
        results: List[ComparisonResult],
        discrepancies: List[Discrepancy],
        output_path: Optional[str] = None,
    ) -> str:
        """Generate Markdown report."""
        try:
            md = []

            # Header
            md.append(f"# Compliance Audit Report")
            md.append(f"\n**Generated:** {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            md.append(f"**Website:** {metadata.website_url}")
            md.append(f"**Report ID:** {metadata.report_id}\n")

            # Executive Summary
            md.append("## Executive Summary\n")
            md.append(f"- **Overall Compliance:** {metadata.compliance_percentage:.1f}%")
            md.append(f"- **Pages Audited:** {metadata.pages_checked}")
            md.append(f"- **Components Checked:** {metadata.components_checked}")
            md.append(f"- **Issues Found:** {metadata.discrepancies_found}")
            md.append(f"- **Audit Duration:** {metadata.audit_duration_seconds:.1f} seconds\n")

            # Issue Summary by Severity
            md.append("## Issues by Severity\n")
            critical = sum(1 for d in discrepancies if d.severity == SeverityLevel.CRITICAL)
            warning = sum(1 for d in discrepancies if d.severity == SeverityLevel.WARNING)
            info = sum(1 for d in discrepancies if d.severity == SeverityLevel.INFO)

            md.append(f"- **🔴 Critical:** {critical}")
            md.append(f"- **🟡 Warning:** {warning}")
            md.append(f"- **🔵 Info:** {info}\n")

            # Detailed Findings
            md.append("## Detailed Findings\n")
            if not discrepancies:
                md.append("✅ No compliance issues found!\n")
            else:
                # Group by page
                by_page: Dict[str, List[Discrepancy]] = {}
                for d in discrepancies:
                    if d.page_url not in by_page:
                        by_page[d.page_url] = []
                    by_page[d.page_url].append(d)

                for page_url, page_discrepancies in sorted(by_page.items()):
                    md.append(f"### {page_url}\n")
                    for d in sorted(page_discrepancies, key=lambda x: x.severity.value, reverse=True):
                        severity_icon = self._get_severity_icon(d.severity)
                        md.append(
                            f"{severity_icon} **DISCREPANCY** "
                            f"({d.component_type.value}): {d.reason}"
                        )
                        md.append(f"  - *Expected:* {d.expected_content}")
                        md.append(f"  - *Actual:* {d.actual_content}")
                        md.append(f"  - *Guideline:* {d.guideline_section}")
                        md.append(f"  - *Fix:* {d.remediation_suggestion}")
                        md.append("")

            # Save if path provided
            report_text = "\n".join(md)
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(report_text)
                logger.info("Markdown report saved", path=output_path)

            return report_text

        except Exception as e:
            logger.error("Markdown report generation failed", error=str(e))
            raise ReportGenerationError(f"Failed to generate Markdown report: {e}") from e

    def _get_severity_icon(self, severity: SeverityLevel) -> str:
        """Get emoji icon for severity level."""
        icons = {
            SeverityLevel.CRITICAL: "🔴",
            SeverityLevel.WARNING: "🟡",
            SeverityLevel.INFO: "🔵",
            SeverityLevel.NOTE: "⚪",
        }
        return icons.get(severity, "⚪")


class HTMLReportGenerator:
    """Generate HTML format compliance reports."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize HTML report generator."""
        self._config = config or {}
        logger.info("HTML report generator initialized")

    def generate(
        self,
        metadata: ReportMetadata,
        results: List[ComparisonResult],
        discrepancies: List[Discrepancy],
        output_path: Optional[str] = None,
    ) -> str:
        """Generate HTML report."""
        try:
            html = self._build_html(metadata, results, discrepancies)

            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(html)
                logger.info("HTML report saved", path=output_path)

            return html

        except Exception as e:
            logger.error("HTML report generation failed", error=str(e))
            raise ReportGenerationError(f"Failed to generate HTML report: {e}") from e

    def _build_html(
        self,
        metadata: ReportMetadata,
        results: List[ComparisonResult],
        discrepancies: List[Discrepancy],
    ) -> str:
        """Build HTML report."""
        critical = sum(1 for d in discrepancies if d.severity == SeverityLevel.CRITICAL)
        warning = sum(1 for d in discrepancies if d.severity == SeverityLevel.WARNING)
        info = sum(1 for d in discrepancies if d.severity == SeverityLevel.INFO)

        discrepancy_rows = "\n".join(
            self._build_discrepancy_row(d) for d in discrepancies
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Audit Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metadata {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 4px; border-left: 4px solid #007bff; }}
        .summary-card h3 {{ margin: 0; color: #666; font-size: 12px; text-transform: uppercase; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; color: #333; }}
        .severity-critical {{ border-left-color: #dc3545; }}
        .severity-warning {{ border-left-color: #ffc107; }}
        .severity-info {{ border-left-color: #17a2b8; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #007bff; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .severity-badge {{ padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }}
        .badge-critical {{ background: #dc3545; color: white; }}
        .badge-warning {{ background: #ffc107; color: black; }}
        .badge-info {{ background: #17a2b8; color: white; }}
        .recommendation {{ background: #d4edda; padding: 15px; border-radius: 4px; margin: 10px 0; border-left: 4px solid #28a745; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Compliance Audit Report</h1>
        
        <div class="metadata">
            <p><strong>Website:</strong> {metadata.website_url}</p>
            <p><strong>Generated:</strong> {metadata.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Report ID:</strong> {metadata.report_id}</p>
        </div>

        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Overall Compliance</h3>
                <div class="value">{metadata.compliance_percentage:.1f}%</div>
            </div>
            <div class="summary-card severity-critical">
                <h3>Critical Issues</h3>
                <div class="value">{critical}</div>
            </div>
            <div class="summary-card severity-warning">
                <h3>Warnings</h3>
                <div class="value">{warning}</div>
            </div>
            <div class="summary-card severity-info">
                <h3>Info Issues</h3>
                <div class="value">{info}</div>
            </div>
        </div>

        <h2>Findings</h2>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Type</th>
                    <th>Page</th>
                    <th>Component</th>
                    <th>Issue</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {discrepancy_rows if discrepancy_rows else '<tr><td colspan="6">✅ No issues found</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            <p>This report was automatically generated by the Documentation Compliance Agent.</p>
            <p>For questions, please refer to the detailed findings above or contact your compliance team.</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _build_discrepancy_row(self, d: Discrepancy) -> str:
        """Build HTML table row for discrepancy."""
        severity_class = f"badge-{d.severity.value}"
        return f"""<tr>
            <td><span class="severity-badge {severity_class}">{d.severity.value.upper()}</span></td>
            <td>Discrepancy</td>
            <td>{d.page_url}</td>
            <td>{d.component_type.value}</td>
            <td>{d.reason}</td>
            <td>{d.remediation_suggestion}</td>
        </tr>"""


class ReportingOrchestrator:
    """Orchestrate report generation in multiple formats."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize reporting orchestrator."""
        self._config = config or {}
        self._json_generator = JSONReportGenerator(config)
        self._markdown_generator = MarkdownReportGenerator(config)
        self._html_generator = HTMLReportGenerator(config)
        logger.info("Reporting orchestrator initialized")

    def generate_all(
        self,
        metadata: ReportMetadata,
        results: List[ComparisonResult],
        discrepancies: List[Discrepancy],
        output_dir: str,
    ) -> Dict[str, str]:
        """
        Generate all report formats.

        Args:
            metadata: Report metadata
            results: Comparison results
            discrepancies: Detected discrepancies
            output_dir: Directory to save reports

        Returns:
            Dictionary with paths to generated reports
        """
        try:
            json_path = f"{output_dir}/{metadata.report_id}.json"
            markdown_path = f"{output_dir}/{metadata.report_id}.md"
            html_path = f"{output_dir}/{metadata.report_id}.html"

            self._json_generator.generate(metadata, results, discrepancies, json_path)
            self._markdown_generator.generate(metadata, results, discrepancies, markdown_path)
            self._html_generator.generate(metadata, results, discrepancies, html_path)

            logger.info(
                "All reports generated",
                report_id=metadata.report_id,
                json_path=json_path,
                markdown_path=markdown_path,
                html_path=html_path,
            )

            return {
                "json": json_path,
                "markdown": markdown_path,
                "html": html_path,
            }

        except Exception as e:
            logger.error("Report generation failed", error=str(e))
            raise ReportGenerationError(f"Failed to generate reports: {e}") from e


logger.info("Report generation module loaded")
