"""Tests for task_logger/ansi.py"""

import pytest

from task_logger.ansi import (
    strip_ansi_codes,
    ANSI_CSI_PATTERN,
    ANSI_OSC_BEL_PATTERN,
    ANSI_OSC_ST_PATTERN,
)


class TestStripAnsiCodes:
    """Tests for strip_ansi_codes function"""

    def test_strip_ansi_codes_empty_string(self):
        """Test strip_ansi_codes with empty string"""
        result = strip_ansi_codes("")
        assert result == ""

    def test_strip_ansi_codes_none(self):
        """Test strip_ansi_codes with None"""
        result = strip_ansi_codes(None)
        assert result == ""

    def test_strip_ansi_codes_no_ansi(self):
        """Test strip_ansi_codes with plain text"""
        text = "This is plain text"
        result = strip_ansi_codes(text)
        assert result == "This is plain text"

    def test_strip_ansi_codes_basic_color(self):
        """Test strip_ansi_codes removes basic color codes"""
        text = "\x1b[31mRed text\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Red text"

    def test_strip_ansi_codes_multiple_colors(self):
        """Test strip_ansi_codes removes multiple color codes"""
        text = "\x1b[31m\x1b[1mBold red\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Bold red"

    def test_strip_ansi_codes_debug_format(self):
        """Test strip_ansi_codes with debug formatting"""
        text = "\x1b[90m[21:40:22.196]\x1b[0m \x1b[36m[DEBUG]\x1b[0m Message"
        result = strip_ansi_codes(text)
        assert result == "[21:40:22.196] [DEBUG] Message"

    def test_strip_ansi_codes_various_colors(self):
        """Test strip_ansi_codes removes various color codes"""
        test_cases = [
            ("\x1b[30mBlack\x1b[0m", "Black"),
            ("\x1b[31mRed\x1b[0m", "Red"),
            ("\x1b[32mGreen\x1b[0m", "Green"),
            ("\x1b[33mYellow\x1b[0m", "Yellow"),
            ("\x1b[34mBlue\x1b[0m", "Blue"),
            ("\x1b[35mMagenta\x1b[0m", "Magenta"),
            ("\x1b[36mCyan\x1b[0m", "Cyan"),
            ("\x1b[37mWhite\x1b[0m", "White"),
        ]

        for text, expected in test_cases:
            result = strip_ansi_codes(text)
            assert result == expected

    def test_strip_ansi_codes_bold_underline(self):
        """Test strip_ansi_codes removes style codes"""
        text = "\x1b[1mBold\x1b[0m \x1b[4mUnderline\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Bold Underline"

    def test_strip_ansi_codes_cursor_hide_show(self):
        """Test strip_ansi_codes removes cursor control codes"""
        text = "Text\x1b[?25lHidden\x1b[?25hShown"
        result = strip_ansi_codes(text)
        assert result == "TextHiddenShown"

    def test_strip_ansi_codes_bracketed_paste(self):
        """Test strip_ansi_codes removes bracketed paste codes"""
        text = "\x1b[200~content\x1b[201~"
        result = strip_ansi_codes(text)
        assert result == "content"

    def test_strip_ansi_codes_osc_bel_sequence(self):
        """Test strip_ansi_codes removes OSC sequences with BEL"""
        text = "Text\x1b]0;Window Title\x07More text"
        result = strip_ansi_codes(text)
        assert result == "TextMore text"

    def test_strip_ansi_codes_osc_st_sequence(self):
        """Test strip_ansi_codes removes OSC sequences with ST"""
        text = "Text\x1b]0;Window Title\x1b\\More text"
        result = strip_ansi_codes(text)
        assert result == "TextMore text"

    def test_strip_ansi_codes_mixed_sequences(self):
        """Test strip_ansi_codes removes mixed ANSI sequences"""
        text = "\x1b[31mRed\x1b[0m\x1b]0;Title\x07\x1b[1mBold\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "RedBold"

    def test_strip_ansi_codes_preserves_unicode(self):
        """Test strip_ansi_codes preserves Unicode characters"""
        text = "\x1b[31mEmoji: 🎉 中文 日本語 한글\x1b[0m"
        result = strip_ansi_codes(text)
        assert "🎉" in result
        assert "中文" in result
        assert "日本語" in result
        assert "한글" in result

    def test_strip_ansi_codes_preserves_line_breaks(self):
        """Test strip_ansi_codes preserves line breaks"""
        text = "\x1b[31mLine 1\nLine 2\r\nLine 3\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Line 1\nLine 2\r\nLine 3"

    def test_strip_ansi_codes_preserves_tabs(self):
        """Test strip_ansi_codes preserves tabs"""
        text = "\x1b[31mColumn1\tColumn2\tColumn3\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Column1\tColumn2\tColumn3"

    def test_strip_ansi_codes_complex_256_color(self):
        """Test strip_ansi_codes removes 256-color codes"""
        text = "\x1b[38;5;196mRed\x1b[0m \x1b[48;5;21mBG\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Red BG"

    def test_strip_ansi_codes_rgb_color(self):
        """Test strip_ansi_codes removes RGB color codes"""
        text = "\x1b[38;2;255;0;0mRGB Red\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "RGB Red"

    def test_strip_ansi_codes_sgr_parameters(self):
        """Test strip_ansi_codes removes various SGR parameters"""
        # SGR (Select Graphic Rendition) parameters
        # 0=reset, 1=bold, 2=dim, 3=italic, 4=underline, 5=blink, 7=inverse
        text = "\x1b[1mBold\x1b[0m \x1b[2mDim\x1b[0m \x1b[3mItalic\x1b[0m \x1b[4mUnder\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Bold Dim Italic Under"

    def test_strip_ansi_codes_long_sequence(self):
        """Test strip_ansi_codes handles long escape sequences"""
        # CSI sequence with many parameters
        text = "\x1b[38;2;255;128;0;48;2;0;0;255mStyled text\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Styled text"

    def test_strip_ansi_codes_multiple_sequences_in_row(self):
        """Test strip_ansi_codes handles multiple consecutive sequences"""
        text = "\x1b[31m\x1b[1m\x1b[4mText\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "Text"

    def test_strip_ansi_codes_real_terminal_output(self):
        """Test strip_ansi_codes with realistic terminal output"""
        # Simulates typical terminal output with colors and formatting
        text = (
            "\x1b[90m[2024-01-01 12:00:00]\x1b[0m "
            "\x1b[36mINFO\x1b[0m "
            "\x1b[1mProcessing file\x1b[0m "
            "\x1b[32m✓\x1b[0m Success"
        )
        result = strip_ansi_codes(text)
        assert "[2024-01-01 12:00:00]" in result
        assert "INFO" in result
        assert "Processing file" in result
        assert "Success" in result
        # No escape sequences should remain
        assert "\x1b" not in result

    def test_strip_ansi_codes_empty_after_stripping(self):
        """Test strip_ansi_codes returns empty when only ANSI codes"""
        text = "\x1b[31m\x1b[1m\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == ""

    def test_strip_ansi_codes_very_long_text(self):
        """Test strip_ansi_codes handles long text"""
        text = "\x1b[31m" + "A" * 10000 + "\x1b[0m"
        result = strip_ansi_codes(text)
        assert len(result) == 10000
        assert result == "A" * 10000


class TestAnsiPatterns:
    """Tests for ANSI pattern regexes"""

    def test_csi_pattern_matches_simple(self):
        """Test ANSI_CSI_PATTERN matches simple CSI sequences"""
        import re
        text = "\x1b[31m"
        match = ANSI_CSI_PATTERN.search(text)
        assert match is not None
        assert match.group() == "\x1b[31m"

    def test_csi_pattern_matches_complex(self):
        """Test ANSI_CSI_PATTERN matches complex CSI sequences"""
        import re
        text = "\x1b[38;5;196;1m"
        match = ANSI_CSI_PATTERN.search(text)
        assert match is not None
        assert match.group() == "\x1b[38;5;196;1m"

    def test_osc_bel_pattern_matches(self):
        """Test ANSI_OSC_BEL_PATTERN matches OSC sequences with BEL"""
        import re
        text = "\x1b]0;Window Title\x07"
        match = ANSI_OSC_BEL_PATTERN.search(text)
        assert match is not None
        assert match.group() == "\x1b]0;Window Title\x07"

    def test_osc_st_pattern_matches(self):
        """Test ANSI_OSC_ST_PATTERN matches OSC sequences with ST"""
        import re
        text = "\x1b]0;Window Title\x1b\\"
        match = ANSI_OSC_ST_PATTERN.search(text)
        assert match is not None
        assert match.group() == "\x1b]0;Window Title\x1b\\"


class TestEdgeCases:
    """Tests for edge cases"""

    def test_strip_ansi_codes_with_partial_sequence(self):
        """Test strip_ansi_codes handles partial/incomplete sequences"""
        # Incomplete CSI (missing final byte)
        # Note: The pattern \x1b[ will match, removing the escape and bracket
        text = "Text\x1b[31 more text"
        result = strip_ansi_codes(text)
        # Should not crash, partial sequence may be partially matched
        assert "Text" in result
        # The escape sequence part might be partially removed
        assert len(result) < len(text)  # Something was removed

    def test_strip_ansi_codes_with_escaped_escape(self):
        """Test strip_ansi_codes handles escaped escape characters"""
        # Literal backslash followed by escape sequence
        text = r"\x1b[31m not an escape"
        result = strip_ansi_codes(text)
        # String literal doesn't contain actual ESC byte
        assert "\\x1b[31m" in result or "x1b[31m" in result

    def test_strip_ansi_codes_preserves_whitespace(self):
        """Test strip_ansi_codes preserves all whitespace"""
        text = "  \x1b[31m  \n\t  \x1b[0m  "
        result = strip_ansi_codes(text)
        assert result == "    \n\t    "

    def test_strip_ansi_codes_numeric_only(self):
        """Test strip_ansi_codes handles text with only numbers"""
        text = "\x1b[31m12345\x1b[0m"
        result = strip_ansi_codes(text)
        assert result == "12345"
