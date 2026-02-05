"""Tests for spec_document_validator"""

from spec.validate_pkg.validators.spec_document_validator import SpecDocumentValidator
from spec.validate_pkg.models import ValidationResult
from spec.validate_pkg.schemas import SPEC_REQUIRED_SECTIONS, SPEC_RECOMMENDED_SECTIONS
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_SpecDocumentValidator___init__():
    """Test SpecDocumentValidator.__init__"""

    # Arrange
    spec_dir = Path("/tmp/test")

    # Act
    validator = SpecDocumentValidator(spec_dir)

    # Assert
    assert validator.spec_dir == spec_dir


def test_SpecDocumentValidator_validate_missing_file(tmp_path):
    """Test SpecDocumentValidator.validate when spec.md is missing"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    # No spec.md created

    validator = SpecDocumentValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert "not found" in result.errors[0].lower()
    assert result.checkpoint == "spec"


def test_SpecDocumentValidator_validate_valid_spec(tmp_path):
    """Test SpecDocumentValidator.validate with valid spec.md"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    spec_file = spec_dir / "spec.md"

    # Create spec with required sections
    content = ""
    for section in SPEC_REQUIRED_SECTIONS:
        content += f"## {section}\n\nContent here\n\n"
    spec_file.write_text(content, encoding="utf-8")

    validator = SpecDocumentValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert isinstance(result, ValidationResult)
    assert result.checkpoint == "spec"


def test_SpecDocumentValidator_validate_missing_required_sections(tmp_path):
    """Test SpecDocumentValidator.validate with missing required sections"""

    # Arrange
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    spec_file = spec_dir / "spec.md"
    spec_file.write_text("# Some content\n\nWithout required sections\n", encoding="utf-8")

    validator = SpecDocumentValidator(spec_dir)

    # Act
    result = validator.validate()

    # Assert
    assert result.valid is False
    assert len(result.errors) > 0
    assert any("Missing required section" in e for e in result.errors)


class TestSpecDocumentValidatorRequiredSections:
    """Tests for required section validation."""

    def test_all_required_sections_present(self, tmp_path):
        """Test validation passes when all required sections are present."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"## {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_overview_section(self, tmp_path):
        """Test validation detects missing Overview section."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            if section != "Overview":
                content += f"## {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Overview" in e for e in result.errors)

    def test_missing_workflow_type_section(self, tmp_path):
        """Test validation detects missing Workflow Type section."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            if section != "Workflow Type":
                content += f"## {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        assert any("Workflow Type" in e for e in result.errors)

    def test_missing_multiple_required_sections(self, tmp_path):
        """Test validation detects multiple missing required sections."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Title\n\nSome content\n", encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        # Should have errors for each missing section
        assert len([e for e in result.errors if "Missing required section" in e]) == len(SPEC_REQUIRED_SECTIONS)

    def test_section_with_single_hash(self, tmp_path):
        """Test that # (single hash) headings are recognized."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"# {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Single hash headings should be recognized
        assert result.valid is True

    def test_section_with_case_insensitive_match(self, tmp_path):
        """Test that section matching is case-insensitive."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            # Use random case
            content += f"## {section.lower()}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_section_with_extra_whitespace(self, tmp_path):
        """Test that sections with extra whitespace are recognized."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = "##   Overview  \n\nContent here\n\n"
        content += "##\tWorkflow Type\t\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Extra whitespace should still match
        assert "Overview" not in " ".join(result.errors)


class TestSpecDocumentValidatorRecommendedSections:
    """Tests for recommended section validation."""

    def test_all_recommended_sections_present(self, tmp_path):
        """Test no warnings when all recommended sections are present."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS + SPEC_RECOMMENDED_SECTIONS:
            content += f"## {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        # No warnings for recommended sections
        assert not any("Missing recommended section" in w for w in result.warnings)

    def test_missing_recommended_sections_generate_warnings(self, tmp_path):
        """Test that missing recommended sections generate warnings."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        # Only include required sections
        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"## {section}\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Should be valid (required sections present)
        assert result.valid is True
        # Should have warnings for missing recommended sections
        # Filter to only recommended section warnings
        rec_warnings = [w for w in result.warnings if "Missing recommended section" in w]
        assert len(rec_warnings) > 0

    def test_warnings_dont_affect_validity(self, tmp_path):
        """Test that recommended section warnings don't make spec invalid."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        # Only required sections
        content = "## Overview\n\nContent\n\n"
        content += "## Workflow Type\n\nContent\n\n"
        content += "## Task Scope\n\nContent\n\n"
        content += "## Success Criteria\n\nContent\n\n"
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True  # Still valid despite warnings
        assert len(result.warnings) > 0  # Has warnings


class TestSpecDocumentValidatorContentLength:
    """Tests for content length validation."""

    def test_very_short_spec_warning(self, tmp_path):
        """Test warning for very short spec (< 500 chars)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"## {section}\n\nBrief\n\n"
        # Make sure total is under 500 chars
        content = content[:400]

        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Should still be valid but with warning
        assert any("too short" in w.lower() for w in result.warnings)

    def test_minimum_length_spec(self, tmp_path):
        """Test spec at exactly 500 characters."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"## {section}\n\n"
        # Pad to exactly 500 chars
        content += "a" * (500 - len(content))

        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # At exactly 500 chars, no warning
        assert not any("too short" in w.lower() for w in result.warnings)

    def test_long_spec_no_warning(self, tmp_path):
        """Test no warning for long spec (> 500 chars)."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = ""
        for section in SPEC_REQUIRED_SECTIONS:
            content += f"## {section}\n\n"
            content += "This is detailed content that makes the spec longer. " * 10
            content += "\n\n"

        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Long content shouldn't generate shortness warning
        assert not any("too short" in w.lower() for w in result.warnings)

    def test_empty_spec_file(self, tmp_path):
        """Test validation of completely empty spec file."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("", encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        # Should have errors for missing required sections
        assert len(result.errors) >= len(SPEC_REQUIRED_SECTIONS)


class TestSpecDocumentValidatorEdgeCases:
    """Tests for edge cases and unusual content."""

    def test_spec_with_markdown_formatting(self, tmp_path):
        """Test spec with various markdown formatting."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """## Overview

This spec has **bold**, *italic*, and `code` formatting.

### Subsection

- List item 1
- List item 2

```python
def example():
    pass
```

## Workflow Type

More content with [links](https://example.com).

## Task Scope

Scope details.

## Success Criteria

1. Criterion 1
2. Criterion 2
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_spec_with_unicode_characters(self, tmp_path):
        """Test spec with unicode and emoji characters."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """## Overview

Spec with émojis 🎉 and special chars: café, naïve

## Workflow Type

Implementation details

## Task Scope

Scope with unicode: 中文, 日本語

## Success Criteria

✓ Criteria 1
✓ Criteria 2
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_spec_with_alternative_section_name(self, tmp_path):
        """Test that similar but not exact section names are not matched."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """## Overview (Detailed)

Content here.

## Workflow

Different name.

## Scoping

Not quite right.

## Success

Incomplete name.
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Should fail - section names don't match exactly
        assert result.valid is False

    def test_spec_with_line_continuations(self, tmp_path):
        """Test spec with various line continuation patterns."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = "## Overview\nContent with\nline breaks\n\n"
        content += "## Workflow Type\n\r\nWindows line endings\r\n\r\n"
        content += "## Task Scope\nContent\n\n"
        content += "## Success Criteria\nContent\n\n"

        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_spec_sections_in_different_order(self, tmp_path):
        """Test that section order doesn't matter."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        # Sections in reverse order
        content = "## Success Criteria\n\nContent\n\n"
        content += "## Task Scope\n\nContent\n\n"
        content += "## Workflow Type\n\nContent\n\n"
        content += "## Overview\n\nContent\n\n"

        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Order shouldn't matter
        assert result.valid is True

    def test_spec_with_comments(self, tmp_path):
        """Test spec with HTML comments or other annotations."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """<!-- This is a comment -->

## Overview

Content here.

## Workflow Type

Details.

## Task Scope

Scope.

## Success Criteria

Criteria.
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True

    def test_spec_with_horizontal_rules(self, tmp_path):
        """Test spec with horizontal rules."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """## Overview

---

Content above and below rule.

---

## Workflow Type

Details.

## Task Scope

Scope.

## Success Criteria

Criteria.
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True


class TestSpecDocumentValidatorFixSuggestions:
    """Tests for suggested fix messages."""

    def test_fix_includes_add_section_command(self, tmp_path):
        """Test that fix suggestions include section addition commands."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Title\n\nNo sections\n", encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is False
        # Fixes should suggest adding sections
        assert any("Add" in fix and "##" in fix for fix in result.fixes)

    def test_fix_for_missing_file(self, tmp_path):
        """Test fix suggestion when spec.md is missing."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        # No spec.md

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert "not found" in result.errors[0].lower()
        # Fix should suggest creating the file
        assert len(result.fixes) > 0


class TestSpecDocumentValidatorIntegration:
    """Integration tests with complete spec documents."""

    def test_complete_valid_spec(self, tmp_path):
        """Test validation of a complete, well-formed spec."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """# Feature Specification: User Authentication

## Overview

Implement OAuth2 authentication with support for multiple providers including Google and GitHub. This feature will allow users to sign in securely using their existing accounts.

## Workflow Type

feature

## Task Scope

- Implement OAuth2 flow for Google and GitHub
- Add user session management
- Create authentication UI components
- Add token refresh logic

## Success Criteria

- Users can authenticate with Google OAuth
- Users can authenticate with GitHub OAuth
- Sessions persist across page refreshes
- Tokens automatically refresh when expired

## Files to Modify

- apps/backend/auth/oauth.py
- apps/frontend/src/components/Auth.tsx

## Files to Reference

- apps/backend/auth/base.py
- shared/types/auth.ts
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        assert result.valid is True
        assert len(result.errors) == 0
        # May have warnings but no errors

    def test_spec_with_only_required_minimal(self, tmp_path):
        """Test minimal valid spec with only required sections."""

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"

        content = """## Overview

A feature.

## Workflow Type

feature

## Task Scope

Do the work.

## Success Criteria

It works.
"""
        spec_file.write_text(content, encoding="utf-8")

        validator = SpecDocumentValidator(spec_dir)
        result = validator.validate()

        # Minimal spec should be valid
        assert result.valid is True
        # But may have length warning
        assert len(result.errors) == 0
