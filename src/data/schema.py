"""
Schema validation utilities for data models.

Provides functions for validating, converting, and managing
canonical data structures throughout the system.
"""

import json
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import hashlib
from src.data.models import (
    ComponentType,
    SeverityLevel,
    ComplianceStatus,
    WebComponent,
    WebPage,
    WebsiteExtraction,
    GuidelineChunk,
    Discrepancy,
    DiscrepancyReport,
    ComparisonContext,
    ComparisonResult,
    PageStats,
    ComponentStats,
    ComplianceStats,
)
from src.core.exceptions import ValidationError


class SchemaValidator:
    """Validates data against canonical schema."""

    @staticmethod
    def validate_component_type(value: Any) -> ComponentType:
        """Validate and convert value to ComponentType."""
        if isinstance(value, ComponentType):
            return value
        if isinstance(value, str):
            try:
                return ComponentType(value)
            except ValueError:
                raise ValidationError(
                    f"Invalid component type: {value}. "
                    f"Valid types: {[c.value for c in ComponentType]}"
                )
        raise ValidationError(f"Component type must be string or ComponentType, got {type(value)}")

    @staticmethod
    def validate_severity_level(value: Any) -> SeverityLevel:
        """Validate and convert value to SeverityLevel."""
        if isinstance(value, SeverityLevel):
            return value
        if isinstance(value, str):
            try:
                return SeverityLevel(value)
            except ValueError:
                raise ValidationError(
                    f"Invalid severity level: {value}. "
                    f"Valid levels: {[s.value for s in SeverityLevel]}"
                )
        raise ValidationError(f"Severity level must be string or SeverityLevel, got {type(value)}")

    @staticmethod
    def validate_compliance_status(value: Any) -> ComplianceStatus:
        """Validate and convert value to ComplianceStatus."""
        if isinstance(value, ComplianceStatus):
            return value
        if isinstance(value, str):
            try:
                return ComplianceStatus(value)
            except ValueError:
                raise ValidationError(
                    f"Invalid compliance status: {value}. "
                    f"Valid statuses: {[c.value for c in ComplianceStatus]}"
                )
        raise ValidationError(f"Compliance status must be string or ComplianceStatus, got {type(value)}")

    @staticmethod
    def validate_confidence_score(value: Any) -> float:
        """Validate confidence score is between 0 and 1."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Confidence score must be numeric, got {type(value)}")
        score = float(value)
        if not (0.0 <= score <= 1.0):
            raise ValidationError(f"Confidence score must be between 0 and 1, got {score}")
        return score

    @staticmethod
    def validate_compliance_percentage(value: Any) -> float:
        """Validate compliance percentage is between 0 and 100."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Compliance percentage must be numeric, got {type(value)}")
        percentage = float(value)
        if not (0.0 <= percentage <= 100.0):
            raise ValidationError(f"Compliance percentage must be between 0 and 100, got {percentage}")
        return percentage

    @staticmethod
    def validate_url(value: Any) -> str:
        """Validate URL format."""
        if not isinstance(value, str):
            raise ValidationError(f"URL must be string, got {type(value)}")
        if not value.strip():
            raise ValidationError("URL cannot be empty")
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValidationError(f"URL must start with http:// or https://, got {value}")
        return value

    @staticmethod
    def validate_embedding(value: Any, expected_dimensions: int = 1536) -> List[float]:
        """Validate embedding vector."""
        if not isinstance(value, list):
            raise ValidationError(f"Embedding must be list, got {type(value)}")
        if len(value) != expected_dimensions:
            raise ValidationError(
                f"Embedding must have {expected_dimensions} dimensions, got {len(value)}"
            )
        for i, elem in enumerate(value):
            if not isinstance(elem, (int, float)):
                raise ValidationError(f"Embedding element {i} must be numeric, got {type(elem)}")
        return value

    @staticmethod
    def validate_web_component(component: Dict[str, Any]) -> Dict[str, Any]:
        """Validate web component data."""
        required_fields = ["component_id", "component_type", "selector"]
        for field in required_fields:
            if field not in component:
                raise ValidationError(f"WebComponent missing required field: {field}")

        # Validate component type
        component["component_type"] = SchemaValidator.validate_component_type(
            component["component_type"]
        )

        # Validate optional position and attributes
        if "position" in component and component["position"]:
            if not isinstance(component["position"], dict):
                raise ValidationError("Position must be dictionary")

        if "attributes" in component and component["attributes"]:
            if not isinstance(component["attributes"], dict):
                raise ValidationError("Attributes must be dictionary")

        return component

    @staticmethod
    def validate_discrepancy(discrepancy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate discrepancy data."""
        required_fields = [
            "discrepancy_id",
            "page_url",
            "component_id",
            "component_type",
            "component_selector",
            "actual_content",
            "guideline_chunk_id",
            "severity",
            "confidence_score",
            "reason",
        ]
        for field in required_fields:
            if field not in discrepancy:
                raise ValidationError(f"Discrepancy missing required field: {field}")

        # Validate enums
        discrepancy["component_type"] = SchemaValidator.validate_component_type(
            discrepancy["component_type"]
        )
        discrepancy["severity"] = SchemaValidator.validate_severity_level(discrepancy["severity"])

        # Validate confidence score
        discrepancy["confidence_score"] = SchemaValidator.validate_confidence_score(
            discrepancy["confidence_score"]
        )

        # Validate URL
        discrepancy["page_url"] = SchemaValidator.validate_url(discrepancy["page_url"])

        return discrepancy


class SchemaConverter:
    """Convert between different data representations."""

    @staticmethod
    def component_to_dict(component: WebComponent) -> Dict[str, Any]:
        """Convert WebComponent to dictionary."""
        return component.dict()

    @staticmethod
    def component_from_dict(data: Dict[str, Any]) -> WebComponent:
        """Create WebComponent from dictionary."""
        SchemaValidator.validate_web_component(data)
        return WebComponent(**data)

    @staticmethod
    def discrepancy_to_dict(discrepancy: Discrepancy) -> Dict[str, Any]:
        """Convert Discrepancy to dictionary."""
        return discrepancy.dict()

    @staticmethod
    def discrepancy_from_dict(data: Dict[str, Any]) -> Discrepancy:
        """Create Discrepancy from dictionary."""
        SchemaValidator.validate_discrepancy(data)
        return Discrepancy(**data)

    @staticmethod
    def page_to_dict(page: WebPage) -> Dict[str, Any]:
        """Convert WebPage to dictionary."""
        data = page.dict()
        # Convert nested components
        data["components"] = [
            SchemaConverter.component_to_dict(comp) for comp in page.components
        ]
        return data

    @staticmethod
    def page_from_dict(data: Dict[str, Any]) -> WebPage:
        """Create WebPage from dictionary."""
        if "components" in data and data["components"]:
            data["components"] = [
                SchemaConverter.component_from_dict(comp) for comp in data["components"]
            ]
        return WebPage(**data)

    @staticmethod
    def extraction_to_dict(extraction: WebsiteExtraction) -> Dict[str, Any]:
        """Convert WebsiteExtraction to dictionary."""
        data = extraction.dict()
        # Convert nested pages
        data["pages"] = [SchemaConverter.page_to_dict(page) for page in extraction.pages]
        return data

    @staticmethod
    def extraction_from_dict(data: Dict[str, Any]) -> WebsiteExtraction:
        """Create WebsiteExtraction from dictionary."""
        if "pages" in data and data["pages"]:
            data["pages"] = [SchemaConverter.page_from_dict(page) for page in data["pages"]]
        return WebsiteExtraction(**data)

    @staticmethod
    def report_to_dict(report: DiscrepancyReport) -> Dict[str, Any]:
        """Convert DiscrepancyReport to dictionary."""
        data = report.dict()
        # Convert nested discrepancies
        data["discrepancies"] = [
            SchemaConverter.discrepancy_to_dict(disc) for disc in report.discrepancies
        ]
        return data

    @staticmethod
    def report_from_dict(data: Dict[str, Any]) -> DiscrepancyReport:
        """Create DiscrepancyReport from dictionary."""
        if "discrepancies" in data and data["discrepancies"]:
            data["discrepancies"] = [
                SchemaConverter.discrepancy_from_dict(disc) for disc in data["discrepancies"]
            ]
        return DiscrepancyReport(**data)

    @staticmethod
    def comparison_result_to_dict(result: ComparisonResult) -> Dict[str, Any]:
        """Convert ComparisonResult to dictionary."""
        return result.dict()

    @staticmethod
    def comparison_result_from_dict(data: Dict[str, Any]) -> ComparisonResult:
        """Create ComparisonResult from dictionary."""
        return ComparisonResult(**data)


class SchemaNormalizer:
    """Normalize and clean data according to schema rules."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL to standard form."""
        url = url.strip()
        # Ensure trailing slash for root URLs
        if url.endswith("/?") or url.endswith("?"):
            return url[:-1]
        return url

    @staticmethod
    def normalize_component_id(component_id: str) -> str:
        """Normalize component ID."""
        return component_id.strip().lower()

    @staticmethod
    def normalize_chunk_id(chunk_id: str) -> str:
        """Normalize chunk ID."""
        return chunk_id.strip().lower()

    @staticmethod
    def generate_component_id(component_type: ComponentType, selector: str, page_url: str) -> str:
        """Generate deterministic component ID."""
        combined = f"{component_type.value}:{selector}:{page_url}"
        return f"comp_{hashlib.md5(combined.encode()).hexdigest()[:12]}"

    @staticmethod
    def generate_discrepancy_id(
        page_url: str, component_id: str, guideline_chunk_id: str
    ) -> str:
        """Generate deterministic discrepancy ID."""
        combined = f"{page_url}:{component_id}:{guideline_chunk_id}"
        return f"disc_{hashlib.md5(combined.encode()).hexdigest()[:12]}"

    @staticmethod
    def generate_extraction_id(website_url: str, timestamp: Optional[str] = None) -> str:
        """Generate deterministic extraction ID."""
        ts = timestamp or datetime.now().isoformat()
        combined = f"{website_url}:{ts}"
        return f"ext_{hashlib.md5(combined.encode()).hexdigest()[:12]}"

    @staticmethod
    def generate_report_id(extraction_id: str, guideline_source: str) -> str:
        """Generate deterministic report ID."""
        combined = f"{extraction_id}:{guideline_source}"
        return f"report_{hashlib.md5(combined.encode()).hexdigest()[:12]}"

    @staticmethod
    def normalize_text_content(text: Optional[str]) -> Optional[str]:
        """Normalize text content."""
        if text is None:
            return None
        # Remove leading/trailing whitespace
        text = text.strip()
        # Collapse multiple spaces
        text = " ".join(text.split())
        return text if text else None

    @staticmethod
    def normalize_confidence_score(score: float) -> float:
        """Normalize confidence score to 2 decimal places."""
        return round(max(0.0, min(1.0, score)), 2)

    @staticmethod
    def normalize_compliance_percentage(percentage: float) -> float:
        """Normalize compliance percentage to 1 decimal place."""
        return round(max(0.0, min(100.0, percentage)), 1)


class SchemaStatistics:
    """Calculate statistics from schema objects."""

    @staticmethod
    def calculate_page_compliance(page: WebPage) -> float:
        """Calculate compliance percentage for a page."""
        if not page.components:
            return 100.0

        # This would need actual comparison results to calculate
        # For now, return placeholder
        return 100.0

    @staticmethod
    def calculate_report_statistics(report: DiscrepancyReport) -> Dict[str, Any]:
        """Calculate detailed statistics from report."""
        stats = {
            "total_pages": report.total_pages_checked,
            "pages_with_issues": report.pages_with_discrepancies,
            "pages_compliant": report.total_pages_checked - report.pages_with_discrepancies,
            "total_issues": report.total_discrepancies,
            "by_severity": {
                "critical": report.critical_count,
                "warning": report.warning_count,
                "info": report.info_count,
                "note": report.note_count,
            },
            "compliance_percentage": report.compliance_percentage,
            "average_issues_per_page": (
                report.total_discrepancies / report.total_pages_checked
                if report.total_pages_checked > 0
                else 0
            ),
        }
        return stats

    @staticmethod
    def get_severity_distribution(
        discrepancies: List[Discrepancy],
    ) -> Dict[str, int]:
        """Get distribution of discrepancies by severity."""
        distribution = {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "note": 0,
        }
        for disc in discrepancies:
            severity_key = disc.severity.value
            if severity_key in distribution:
                distribution[severity_key] += 1
        return distribution

    @staticmethod
    def get_component_type_distribution(
        discrepancies: List[Discrepancy],
    ) -> Dict[str, int]:
        """Get distribution of discrepancies by component type."""
        distribution = {}
        for disc in discrepancies:
            comp_type = disc.component_type.value
            distribution[comp_type] = distribution.get(comp_type, 0) + 1
        return distribution

    @staticmethod
    def get_page_distribution(discrepancies: List[Discrepancy]) -> Dict[str, int]:
        """Get distribution of discrepancies by page."""
        distribution = {}
        for disc in discrepancies:
            page_url = disc.page_url
            distribution[page_url] = distribution.get(page_url, 0) + 1
        return distribution


class SchemaExporter:
    """Export schema objects to various formats."""

    @staticmethod
    def to_json_string(obj: Any, indent: int = 2) -> str:
        """Convert object to JSON string."""
        if hasattr(obj, "dict"):
            data = obj.dict()
        else:
            data = obj
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def to_json_file(obj: Any, filepath: str) -> None:
        """Write object to JSON file."""
        json_str = SchemaExporter.to_json_string(obj)
        with open(filepath, "w") as f:
            f.write(json_str)

    @staticmethod
    def from_json_string(json_str: str, model_class: Type) -> Any:
        """Create object from JSON string."""
        data = json.loads(json_str)
        return model_class(**data)

    @staticmethod
    def from_json_file(filepath: str, model_class: Type) -> Any:
        """Create object from JSON file."""
        with open(filepath, "r") as f:
            json_str = f.read()
        return SchemaExporter.from_json_string(json_str, model_class)


class SchemaRegistry:
    """Registry of all schema classes for validation and conversion."""

    SCHEMA_CLASSES = {
        "ComponentType": ComponentType,
        "SeverityLevel": SeverityLevel,
        "ComplianceStatus": ComplianceStatus,
        "WebComponent": WebComponent,
        "WebPage": WebPage,
        "WebsiteExtraction": WebsiteExtraction,
        "GuidelineChunk": GuidelineChunk,
        "Discrepancy": Discrepancy,
        "DiscrepancyReport": DiscrepancyReport,
        "ComparisonContext": ComparisonContext,
        "ComparisonResult": ComparisonResult,
        "PageStats": PageStats,
        "ComponentStats": ComponentStats,
        "ComplianceStats": ComplianceStats,
    }

    @classmethod
    def get_schema_class(cls, name: str) -> Type:
        """Get schema class by name."""
        if name not in cls.SCHEMA_CLASSES:
            raise ValidationError(f"Unknown schema class: {name}")
        return cls.SCHEMA_CLASSES[name]

    @classmethod
    def list_schemas(cls) -> List[str]:
        """List all available schema classes."""
        return list(cls.SCHEMA_CLASSES.keys())

    @classmethod
    def get_schema_info(cls) -> Dict[str, str]:
        """Get information about all schemas."""
        return {name: cls_type.__doc__ or "" for name, cls_type in cls.SCHEMA_CLASSES.items()}
