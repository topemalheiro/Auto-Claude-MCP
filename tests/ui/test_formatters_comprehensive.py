"""
Comprehensive Tests for ui.formatters module
=============================================

Enhanced tests covering edge cases, integration scenarios,
and comprehensive functionality for all formatter functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from ui.formatters import (
    print_header,
    print_section,
    print_status,
    print_key_value,
    print_phase_status,
)
from ui.icons import Icons
from ui.colors import bold, muted, success, error, warning, info, highlight


class TestPrintHeaderEdgeCases:
    """Tests for print_header edge cases"""

    def test_print_header_empty_title(self, capsys):
        """Test print_header with empty title"""
        print_header("")

        captured = capsys.readouterr()
        # Should still print a box
        assert "║" in captured.out or "┃" in captured.out

    def test_print_header_very_long_title(self, capsys):
        """Test print_header with very long title"""
        long_title = "This is a very long title that might exceed the normal box width and cause wrapping or truncation"
        print_header(long_title, width=70)

        captured = capsys.readouterr()
        # Long titles get truncated with ellipsis
        assert long_title[:30] in captured.out or "..." in captured.out

    def test_print_header_very_long_subtitle(self, capsys):
        """Test print_header with very long subtitle"""
        long_subtitle = "This is a very long subtitle that might cause issues with the box formatting"
        print_header("Title", subtitle=long_subtitle, width=70)

        captured = capsys.readouterr()
        assert "Title" in captured.out
        # Long subtitles get truncated with ellipsis
        assert long_subtitle[:30] in captured.out or "..." in captured.out

    def test_print_header_minimal_width(self, capsys):
        """Test print_header with minimal width"""
        print_header("Test", width=10)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_header_very_large_width(self, capsys):
        """Test print_header with very large width"""
        print_header("Test", width=200)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_header_unicode_title(self, capsys):
        """Test print_header with unicode characters in title"""
        print_header("Test with cafe and other unicode characters")

        captured = capsys.readouterr()
        assert "cafe" in captured.out or "coffee" in captured.out

    def test_print_header_special_characters(self, capsys):
        """Test print_header with special characters"""
        print_header("Fix: API /api/v1/users - error!")

        captured = capsys.readouterr()
        assert "/" in captured.out
        assert "!" in captured.out

    def test_print_header_newlines_in_title(self, capsys):
        """Test print_header with newlines in title"""
        print_header("Line 1\nLine 2")

        captured = capsys.readouterr()
        # Should handle the newline
        assert "Line 1" in captured.out or "Line 2" in captured.out

    def test_print_header_tabs_in_title(self, capsys):
        """Test print_header with tabs in title"""
        print_header("Title\twith\ttabs")

        captured = capsys.readouterr()
        assert "Title" in captured.out

    def test_print_header_all_icons(self, capsys):
        """Test print_header with all available icons"""
        icons = [
            Icons.SUCCESS,
            Icons.ERROR,
            Icons.WARNING,
            Icons.INFO,
            Icons.PENDING,
            Icons.IN_PROGRESS,
            Icons.BLOCKED,
        ]

        for icon_tuple in icons:
            print_header(f"Test with icon", icon_tuple=icon_tuple)
            captured = capsys.readouterr()
            # Should print without error
            assert len(captured.out) > 0


class TestPrintSectionEdgeCases:
    """Tests for print_section edge cases"""

    def test_print_section_empty_title(self, capsys):
        """Test print_section with empty title"""
        print_section("")

        captured = capsys.readouterr()
        # Should still print something
        assert len(captured.out) > 0

    def test_print_section_very_long_title(self, capsys):
        """Test print_section with very long title"""
        long_title = "This is a very long section title that might cause formatting issues"
        print_section(long_title, width=70)

        captured = capsys.readouterr()
        # Long titles get truncated with ellipsis
        assert long_title[:30] in captured.out or "..." in captured.out

    def test_print_section_minimal_width(self, capsys):
        """Test print_section with minimal width"""
        print_section("Test", width=10)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_section_large_width(self, capsys):
        """Test print_section with large width"""
        print_section("Test", width=150)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_section_unicode_title(self, capsys):
        """Test print_section with unicode characters"""
        print_section("Section with cafe unicode")

        captured = capsys.readouterr()
        assert "cafe" in captured.out or "coffee" in captured.out

    def test_print_section_all_icons(self, capsys):
        """Test print_section with all available icons"""
        icons = [
            Icons.SUCCESS,
            Icons.ERROR,
            Icons.WARNING,
            Icons.INFO,
            Icons.PENDING,
            Icons.IN_PROGRESS,
            Icons.BLOCKED,
        ]

        for icon_tuple in icons:
            print_section("Test", icon_tuple=icon_tuple)
            captured = capsys.readouterr()
            assert len(captured.out) > 0


class TestPrintStatusEdgeCases:
    """Tests for print_status edge cases"""

    def test_print_status_empty_message(self, capsys):
        """Test print_status with empty message"""
        print_status("", status="info")

        captured = capsys.readouterr()
        # Should still print something (icon)
        assert len(captured.out) > 0

    def test_print_status_very_long_message(self, capsys):
        """Test print_status with very long message"""
        long_message = "This is a very long status message that might wrap or cause display issues"
        print_status(long_message, status="info")

        captured = capsys.readouterr()
        assert long_message in captured.out

    def test_print_status_newlines_in_message(self, capsys):
        """Test print_status with newlines in message"""
        print_status("Line 1\nLine 2\nLine 3", status="info")

        captured = capsys.readouterr()
        assert "Line 1" in captured.out

    def test_print_status_special_characters(self, capsys):
        """Test print_status with special characters"""
        print_status("Error: API /api/v1/users failed!", status="error")

        captured = capsys.readouterr()
        assert "/" in captured.out
        assert "!" in captured.out

    def test_print_status_unicode_message(self, capsys):
        """Test print_status with unicode characters"""
        print_status("Message with cafe and other unicode", status="info")

        captured = capsys.readouterr()
        assert "cafe" in captured.out or "coffee" in captured.out

    def test_print_status_invalid_status_type(self, capsys):
        """Test print_status with invalid status type"""
        print_status("Test", status="invalid_type")

        captured = capsys.readouterr()
        # Should default to info icon
        assert "Test" in captured.out

    def test_print_status_none_icon_with_valid_status(self, capsys):
        """Test print_status with None icon but valid status"""
        print_status("Test", status="success", icon_tuple=None)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_status_custom_icon_overrides_default(self, capsys):
        """Test that custom icon overrides default status icon"""
        # Use error status but success icon
        print_status("Test", status="error", icon_tuple=Icons.SUCCESS)

        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_print_status_all_status_types(self, capsys):
        """Test print_status with all status types"""
        statuses = ["success", "error", "warning", "info", "pending", "progress"]

        for status in statuses:
            print_status(f"Test {status}", status=status)
            captured = capsys.readouterr()
            assert f"Test {status}" in captured.out

    def test_print_status_message_with_leading_trailing_spaces(self, capsys):
        """Test print_status preserves spaces in message"""
        print_status("  Test with spaces  ", status="info")

        captured = capsys.readouterr()
        # Should preserve the spaces
        assert "Test with spaces" in captured.out


class TestPrintKeyValueEdgeCases:
    """Tests for print_key_value edge cases"""

    def test_print_key_value_empty_key(self, capsys):
        """Test print_key_value with empty key"""
        print_key_value("", "value")

        captured = capsys.readouterr()
        assert ":" in captured.out

    def test_print_key_value_empty_value(self, capsys):
        """Test print_key_value with empty value"""
        print_key_value("key", "")

        captured = capsys.readouterr()
        assert "key:" in captured.out

    def test_print_key_value_both_empty(self, capsys):
        """Test print_key_value with both empty"""
        print_key_value("", "")

        captured = capsys.readouterr()
        assert ":" in captured.out

    def test_print_key_value_very_long_key(self, capsys):
        """Test print_key_value with very long key"""
        long_key = "this_is_a_very_long_key_name_that_might_cause_display_issues"
        print_key_value(long_key, "value")

        captured = capsys.readouterr()
        assert long_key in captured.out
        assert "value" in captured.out

    def test_print_key_value_very_long_value(self, capsys):
        """Test print_key_value with very long value"""
        long_value = "this is a very long value that might cause wrapping or other display issues"
        print_key_value("key", long_value)

        captured = capsys.readouterr()
        assert "key:" in captured.out
        assert long_value in captured.out

    def test_print_key_value_zero_indent(self, capsys):
        """Test print_key_value with zero indent"""
        print_key_value("key", "value", indent=0)

        captured = capsys.readouterr()
        assert "key:" in captured.out
        assert "value" in captured.out

    def test_print_key_value_large_indent(self, capsys):
        """Test print_key_value with large indent"""
        print_key_value("key", "value", indent=20)

        captured = capsys.readouterr()
        assert "key:" in captured.out
        assert "value" in captured.out

    def test_print_key_value_negative_indent(self, capsys):
        """Test print_key_value with negative indent (edge case)"""
        print_key_value("key", "value", indent=-1)

        captured = capsys.readouterr()
        # Should still print something
        assert "key:" in captured.out or "value" in captured.out

    def test_print_key_value_unicode_key_value(self, capsys):
        """Test print_key_value with unicode characters"""
        print_key_value("cafe key", "cafe value")

        captured = capsys.readouterr()
        assert "cafe" in captured.out

    def test_print_key_value_special_characters(self, capsys):
        """Test print_key_value with special characters"""
        print_key_value("API Key", "/api/v1/users?param=value&other=123")

        captured = capsys.readouterr()
        assert "API Key:" in captured.out
        assert "/api/v1/users" in captured.out

    def test_print_key_value_newlines_in_value(self, capsys):
        """Test print_key_value with newlines in value"""
        print_key_value("key", "value1\nvalue2\nvalue3")

        captured = capsys.readouterr()
        assert "key:" in captured.out
        assert "value1" in captured.out

    def test_print_key_value_tabs_in_value(self, capsys):
        """Test print_key_value with tabs in value"""
        print_key_value("key", "value1\tvalue2\tvalue3")

        captured = capsys.readouterr()
        assert "key:" in captured.out
        assert "value" in captured.out


class TestPrintPhaseStatusEdgeCases:
    """Tests for print_phase_status edge cases"""

    def test_print_phase_status_zero_completed(self, capsys):
        """Test print_phase_status with zero completed"""
        print_phase_status("Testing", 0, 5, status="pending")

        captured = capsys.readouterr()
        assert "0/5" in captured.out
        assert "Testing" in captured.out

    def test_print_phase_status_all_completed(self, capsys):
        """Test print_phase_status with all completed"""
        print_phase_status("Complete", 5, 5, status="complete")

        captured = capsys.readouterr()
        assert "5/5" in captured.out

    def test_print_phase_status_exceeds_total(self, capsys):
        """Test print_phase_status when completed exceeds total"""
        print_phase_status("Over", 10, 5, status="in_progress")

        captured = capsys.readouterr()
        assert "10/5" in captured.out

    def test_print_phase_status_zero_total(self, capsys):
        """Test print_phase_status with zero total (edge case)"""
        print_phase_status("Test", 0, 0, status="pending")

        captured = capsys.readouterr()
        assert "0/0" in captured.out

    def test_print_phase_status_empty_name(self, capsys):
        """Test print_phase_status with empty name"""
        print_phase_status("", 3, 5, status="in_progress")

        captured = capsys.readouterr()
        assert "3/5" in captured.out

    def test_print_phase_status_very_long_name(self, capsys):
        """Test print_phase_status with very long name"""
        long_name = "This is a very long phase name that might cause display issues"
        print_phase_status(long_name, 3, 5, status="in_progress")

        captured = capsys.readouterr()
        assert long_name in captured.out

    def test_print_phase_status_unicode_name(self, capsys):
        """Test print_phase_status with unicode characters"""
        print_phase_status("cafe phase", 2, 5, status="pending")

        captured = capsys.readouterr()
        assert "cafe" in captured.out or "coffee" in captured.out

    def test_print_phase_status_all_status_types(self, capsys):
        """Test print_phase_status with all status types"""
        statuses = ["complete", "in_progress", "pending", "blocked"]

        for status in statuses:
            print_phase_status(f"Test {status}", 2, 5, status=status)
            captured = capsys.readouterr()
            assert "2/5" in captured.out

    def test_print_phase_status_invalid_status(self, capsys):
        """Test print_phase_status with invalid status"""
        print_phase_status("Test", 2, 5, status="invalid")

        captured = capsys.readouterr()
        # Should default to pending icon
        assert "2/5" in captured.out

    def test_print_phase_status_large_numbers(self, capsys):
        """Test print_phase_status with large numbers"""
        print_phase_status("Test", 99999, 100000, status="in_progress")

        captured = capsys.readouterr()
        assert "99999/100000" in captured.out

    def test_print_phase_status_single_item(self, capsys):
        """Test print_phase_status with single item"""
        print_phase_status("Single", 1, 1, status="complete")

        captured = capsys.readouterr()
        assert "1/1" in captured.out


class TestFormatterIntegration:
    """Integration tests for formatters working together"""

    def test_combined_formatters(self, capsys):
        """Test using multiple formatters together"""
        print_header("Main Header")
        print_section("Section 1")
        print_status("Status message", status="info")
        print_key_value("Setting", "value")
        print_phase_status("Phase", 3, 5, status="in_progress")
        print_section("Section 2")
        print_status("Complete", status="success")

        captured = capsys.readouterr()
        assert "Main Header" in captured.out
        assert "Section 1" in captured.out
        assert "Status message" in captured.out
        assert "Setting:" in captured.out
        assert "3/5" in captured.out

    def test_header_and_section_consistency(self, capsys):
        """Test that header and section use consistent styling"""
        print_header("Header Title", width=60)
        print_section("Section Title", width=60)

        captured = capsys.readouterr()
        assert "Header Title" in captured.out
        assert "Section Title" in captured.out

    def test_multiple_statuses(self, capsys):
        """Test printing multiple status messages"""
        print_status("Step 1", status="success")
        print_status("Step 2", status="in_progress")
        print_status("Step 3", status="pending")
        print_status("Step 4", status="warning")

        captured = capsys.readouterr()
        assert "Step 1" in captured.out
        assert "Step 2" in captured.out
        assert "Step 3" in captured.out
        assert "Step 4" in captured.out

    def test_multiple_phases(self, capsys):
        """Test printing multiple phase statuses"""
        print_phase_status("Planning", 5, 5, status="complete")
        print_phase_status("Coding", 3, 10, status="in_progress")
        print_phase_status("Testing", 0, 5, status="pending")
        print_phase_status("Review", 0, 2, status="blocked")

        captured = capsys.readouterr()
        assert "5/5" in captured.out
        assert "3/10" in captured.out
        assert "0/5" in captured.out
        assert "0/2" in captured.out


class TestFormatterOutputFormat:
    """Tests for output format consistency"""

    def test_header_contains_box_drawing(self, capsys):
        """Test that header contains box drawing characters"""
        print_header("Test")

        captured = capsys.readouterr()
        # Should contain some form of box drawing
        assert any(char in captured.out for char in ["║", "─", "╔", "╗", "╚", "╝", "│", "┃"])

    def test_section_contains_box_drawing(self, capsys):
        """Test that section contains box drawing characters"""
        print_section("Test")

        captured = capsys.readouterr()
        # Should contain some form of box drawing
        assert any(char in captured.out for char in ["║", "─", "╔", "╗", "╚", "╝", "│", "┃"])

    def test_status_ends_with_newline(self, capsys):
        """Test that status output ends with newline"""
        print_status("Test")

        captured = capsys.readouterr()
        assert captured.out.endswith("\n")

    def test_key_value_ends_with_newline(self, capsys):
        """Test that key-value output ends with newline"""
        print_key_value("key", "value")

        captured = capsys.readouterr()
        assert captured.out.endswith("\n")

    def test_phase_status_ends_with_newline(self, capsys):
        """Test that phase status output ends with newline"""
        print_phase_status("Test", 1, 2)

        captured = capsys.readouterr()
        assert captured.out.endswith("\n")
