"""
LLM prompt templates for compliance comparison.

Provides prompt templates for various comparison tasks.
"""

import logging
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class PromptTemplate:
    """Base prompt template."""

    def __init__(self, name: str, template: str):
        """Initialize template."""
        self.name = name
        self.template = template

    def format(self, **kwargs) -> str:
        """Format template with variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise


class CompliancePrompts:
    """Compliance comparison prompt templates."""

    COMPARISON_PROMPT = PromptTemplate(
        "comparison",
        """Analyze if the following web component complies with the provided guidelines.

**Component Information:**
- Type: {component_type}
- Text: {component_text}
- Selector: {component_selector}

**Relevant Guidelines:**
{guidelines}

**Your Task:**
1. Determine if the component complies with the guidelines
2. Identify any discrepancies
3. Provide confidence score (0-1)
4. Suggest remediation if needed

**Format your response as:**
Compliant: [YES/NO]
Confidence: [0-1]
Reason: [explanation]
Issues: [list of issues if any]
Recommendation: [suggestions for fixes]
""",
    )

    DISCREPANCY_PROMPT = PromptTemplate(
        "discrepancy",
        """Identify compliance discrepancies for this component.

**Component:**
{component_text}

**Guidelines:**
{guidelines}

**List all discrepancies found:**
1. [Issue 1]
2. [Issue 2]
...

For each discrepancy, specify:
- Type (missing/incorrect/extra)
- Severity (critical/warning/info)
- Affected guideline section
""",
    )

    CONFIDENCE_PROMPT = PromptTemplate(
        "confidence",
        """Evaluate your confidence in the compliance assessment.

**Component**: {component_text}
**Assessment**: {assessment}
**Guidelines**: {guidelines}

Provide confidence score (0-1) with justification.
Consider:
- Clarity of guidelines
- Ambiguity in component
- Completeness of information
""",
    )

    RECOMMENDATION_PROMPT = PromptTemplate(
        "recommendation",
        """Generate remediation recommendations.

**Current State**: {actual_content}
**Expected State**: {expected_content}
**Guideline**: {guideline}

Provide specific, actionable recommendations to achieve compliance.
""",
    )

    SUMMARY_PROMPT = PromptTemplate(
        "summary",
        """Summarize compliance assessment for this page.

**Page**: {page_url}
**Components Checked**: {component_count}
**Compliant**: {compliant_count}
**Non-Compliant**: {non_compliant_count}

Provide executive summary (2-3 sentences) of key findings.
""",
    )

    @staticmethod
    def get_prompt(name: str) -> Optional[PromptTemplate]:
        """Get prompt template by name."""
        prompts = {
            "comparison": CompliancePrompts.COMPARISON_PROMPT,
            "discrepancy": CompliancePrompts.DISCREPANCY_PROMPT,
            "confidence": CompliancePrompts.CONFIDENCE_PROMPT,
            "recommendation": CompliancePrompts.RECOMMENDATION_PROMPT,
            "summary": CompliancePrompts.SUMMARY_PROMPT,
        }
        return prompts.get(name)


class ContextualPrompts:
    """Context-aware prompt templates."""

    BUTTON_PROMPT = """Analyze this button for compliance with UI/UX guidelines.

**Button Text**: {text}
**Button Type**: {type}
**Button Location**: {location}

**Guidelines**: {guidelines}

Check for:
- Clear, actionable text
- Proper accessibility attributes
- Correct button type (primary/secondary/danger)
- Color contrast requirements
"""

    FORM_PROMPT = """Analyze this form for compliance with data collection guidelines.

**Form Fields**: {fields}
**Form Type**: {form_type}
**Required Fields**: {required}

**Guidelines**: {guidelines}

Check for:
- Required field indicators
- Proper field labels
- Accessibility compliance
- Error handling
- Data validation rules
"""

    NAVIGATION_PROMPT = """Analyze this navigation for compliance with information architecture guidelines.

**Navigation Items**: {items}
**Navigation Type**: {nav_type}

**Guidelines**: {guidelines}

Check for:
- Clear hierarchy
- Consistent labeling
- Mobile responsiveness
- Accessibility (ARIA labels)
"""

    @staticmethod
    def get_contextual_prompt(component_type: str) -> Optional[str]:
        """Get contextual prompt for component type."""
        prompts = {
            "button": ContextualPrompts.BUTTON_PROMPT,
            "form": ContextualPrompts.FORM_PROMPT,
            "navigation": ContextualPrompts.NAVIGATION_PROMPT,
        }
        return prompts.get(component_type.lower())


class FewShotPrompts:
    """Few-shot example prompts for better accuracy."""

    COMPLIANCE_EXAMPLES = """Examples of compliance assessment:

Example 1:
Component: <button>Submit</button>
Guidelines: Buttons should use action verbs and be primary or secondary type
Assessment:
- Compliant: YES
- Confidence: 0.95
- Reason: Clear action verb "Submit" with standard semantics
- Issues: None
- Recommendation: Good as is

Example 2:
Component: <input type="text" placeholder="Enter your name">
Guidelines: Required fields must have labels, not just placeholders
Assessment:
- Compliant: NO
- Confidence: 0.85
- Reason: Uses placeholder instead of proper label element
- Issues: Missing <label> element, violates accessibility guidelines
- Recommendation: Add <label for="name">Your Name</label> and required attribute
"""

    @staticmethod
    def add_examples_to_prompt(base_prompt: str, include_examples: bool = True) -> str:
        """Add few-shot examples to prompt."""
        if include_examples:
            return FewShotPrompts.COMPLIANCE_EXAMPLES + "\n\n" + base_prompt
        return base_prompt


logger.info("Prompt templates initialized")
