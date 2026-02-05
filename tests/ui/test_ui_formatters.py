"""Tests for ui/formatters.py"""

from unittest.mock import patch
import pytest

from ui.formatters import (
    print_header,
    print_section,
    print_status,
    print_key_value,
    print_phase_status,
)
from ui.icons import Icons


class TestPrintHeader:
    """Tests for print_header function"""

    def test_print_header_basic(self, capsys):
        """Test print_header with basic title"""
        print_header("Test Title")

        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "║" in captured.out  # Box characters

    def test_print_header_with_subtitle(self, capsys):
        """Test print_header with subtitle"""
        print_header("Test Title", subtitle="This is a subtitle")

        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "This is a subtitle" in captured.out

    def test_print_header_with_icon(self, capsys):
        """Test print_header with icon"""
        print_header("Test Title", icon_tuple=Icons.SUCCESS)

        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        # Icon should be present

    def test_print_header_custom_width(self, capsys):
        """Test print_header with custom width"""
        print_header("Test Title", width=50)

        captured = capsys.readouterr()
        assert "Test Title" in captured.out


class TestPrintSection:
    """Tests for print_section function"""

    def test_print_section_basic(self, capsys):
        """Test print_section with basic title"""
        print_section("Section Title")

        captured = capsys.readouterr()
        assert "Section Title" in captured.out

    def test_print_section_with_icon(self, capsys):
        """Test print_section with icon"""
        print_section("Section Title", icon_tuple=Icons.INFO)

        captured = capsys.readouterr()
        assert "Section Title" in captured.out


class TestPrintStatus:
    """Tests for print_status function"""

    def test_print_status_success(self, capsys):
        """Test print_status with success status"""
        print_status("Operation completed", status="success")

        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_print_status_error(self, capsys):
        """Test print_status with error status"""
        print_status("Operation failed", status="error")

        captured = capsys.readouterr()
        assert "Operation failed" in captured.out

    def test_print_status_warning(self, capsys):
        """Test print_status with warning status"""
        print_status("Warning message", status="warning")

        captured = capsys.readouterr()
        assert "Warning message" in captured.out

    def test_print_status_info(self, capsys):
        """Test print_status with info status"""
        print_status("Info message", status="info")

        captured = capsys.readouterr()
        assert "Info message" in captured.out

    def test_print_status_pending(self, capsys):
        """Test print_status with pending status"""
        print_status("Pending operation", status="pending")

        captured = capsys.readouterr()
        assert "Pending operation" in captured.out

    def test_print_status_progress(self, capsys):
        """Test print_status with progress status"""
        print_status("In progress", status="progress")

        captured = capsys.readouterr()
        assert "In progress" in captured.out

    def test_print_status_custom_icon(self, capsys):
        """Test print_status with custom icon"""
        print_status("Custom status", icon_tuple=Icons.WARNING)

        captured = capsys.readouterr()
        assert "Custom status" in captured.out


class TestPrintKeyValue:
    """Tests for print_key_value function"""

    def test_print_key_value_basic(self, capsys):
        """Test print_key_value with basic key-value"""
        print_key_value("Name", "John Doe")

        captured = capsys.readouterr()
        assert "Name:" in captured.out
        assert "John Doe" in captured.out

    def test_print_key_value_custom_indent(self, capsys):
        """Test print_key_value with custom indent"""
        print_key_value("Key", "Value", indent=4)

        captured = capsys.readouterr()
        assert "Key:" in captured.out
        assert "Value" in captured.out


class TestPrintPhaseStatus:
    """Tests for print_phase_status function"""

    def test_print_phase_status_complete(self, capsys):
        """Test print_phase_status with complete status"""
        print_phase_status("Planning", 5, 5, status="complete")

        captured = capsys.readouterr()
        assert "Planning" in captured.out
        assert "5/5" in captured.out

    def test_print_phase_status_in_progress(self, capsys):
        """Test print_phase_status with in_progress status"""
        print_phase_status("Coding", 2, 5, status="in_progress")

        captured = capsys.readouterr()
        assert "Coding" in captured.out
        assert "2/5" in captured.out

    def test_print_phase_status_pending(self, capsys):
        """Test print_phase_status with pending status"""
        print_phase_status("QA", 0, 3, status="pending")

        captured = capsys.readouterr()
        assert "QA" in captured.out
        assert "0/3" in captured.out

    def test_print_phase_status_blocked(self, capsys):
        """Test print_phase_status with blocked status"""
        print_phase_status("Review", 1, 2, status="blocked")

        captured = capsys.readouterr()
        assert "Review" in captured.out
        assert "1/2" in captured.out
