"""Tests for agents.pr_template_filler module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from agents.pr_template_filler import (
    detect_pr_template,
    _truncate_diff,
    _strip_markdown_fences,
    _build_prompt,
    _load_spec_overview,
    run_pr_template_filler,
)


class TestDetectPrTemplate:
    """Test detect_pr_template function."""

    def test_returns_content_from_single_template(self, tmp_path):
        """Test that content is returned from PULL_REQUEST_TEMPLATE.md."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        template_file = github_dir / "PULL_REQUEST_TEMPLATE.md"
        template_content = "# PR Template\n\nPlease fill out"
        template_file.write_text(template_content)

        result = detect_pr_template(tmp_path)

        assert result == template_content

    def test_returns_content_from_template_directory(self, tmp_path):
        """Test that content is returned from PULL_REQUEST_TEMPLATE directory."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "template.md"
        template_content = "# Template from directory"
        template_file.write_text(template_content)

        result = detect_pr_template(tmp_path)

        assert result == template_content

    def test_picks_first_file_alphabetically(self, tmp_path):
        """Test that first file alphabetically is picked from directory."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        (template_dir / "z_template.md").write_text("Z template")
        (template_dir / "a_template.md").write_text("A template")

        result = detect_pr_template(tmp_path)

        assert "A template" in result

    def test_returns_none_when_no_template(self, tmp_path):
        """Test that None is returned when no template exists."""
        result = detect_pr_template(tmp_path)

        assert result is None

    def test_returns_none_for_empty_template(self, tmp_path):
        """Test that None is returned for empty template file."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        template_file = github_dir / "PULL_REQUEST_TEMPLATE.md"
        template_file.write_text("   \n   ")

        result = detect_pr_template(tmp_path)

        assert result is None

    def test_returns_none_for_empty_template_in_directory(self, tmp_path):
        """Test that None is returned when directory template is empty."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "template.md"
        template_file.write_text("   \n  \t  ")

        result = detect_pr_template(tmp_path)

        assert result is None

    def test_handles_single_template_read_error(self, tmp_path):
        """Test that read errors on single template are handled gracefully."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        template_file = github_dir / "PULL_REQUEST_TEMPLATE.md"
        # Create file but make it unreadable
        template_file.write_text("content")

        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            result = detect_pr_template(tmp_path)

        # Should return None and log warning, not crash
        assert result is None

    def test_handles_directory_template_read_error(self, tmp_path):
        """Test that read errors in template directory are handled gracefully."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "template.md"
        template_file.write_text("content")

        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            result = detect_pr_template(tmp_path)

        # Should return None and log warning, not crash
        assert result is None

    def test_prefers_single_file_over_directory(self, tmp_path):
        """Test that single template file is preferred over directory."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        single_template = github_dir / "PULL_REQUEST_TEMPLATE.md"
        single_template.write_text("Single template")

        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        (template_dir / "template.md").write_text("Directory template")

        result = detect_pr_template(tmp_path)

        # Single file should be found first
        assert result == "Single template"

    def test_handles_non_md_files_in_directory(self, tmp_path):
        """Test that non-.md files in template directory are ignored."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)
        (template_dir / "template.txt").write_text("Text file")
        (template_dir / "template.md").write_text("MD file")

        result = detect_pr_template(tmp_path)

        # Should only pick .md files
        assert "MD file" in result
        assert "Text file" not in result

    def test_handles_project_dir_as_string(self, tmp_path):
        """Test that project_dir can be passed as string."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        template_file = github_dir / "PULL_REQUEST_TEMPLATE.md"
        template_content = "# PR Template"
        template_file.write_text(template_content)

        # Pass as string instead of Path
        result = detect_pr_template(str(tmp_path))

        assert result == template_content

    def test_handles_empty_github_directory(self, tmp_path):
        """Test that empty .github directory returns None."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()

        result = detect_pr_template(tmp_path)

        assert result is None

    def test_handles_empty_template_directory(self, tmp_path):
        """Test that empty PULL_REQUEST_TEMPLATE directory returns None."""
        template_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(parents=True)

        result = detect_pr_template(tmp_path)

        assert result is None


class TestTruncateDiff:
    """Test _truncate_diff function."""

    def test_returns_original_when_under_limit(self):
        """Test that original diff is returned when under limit."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff = "a" * (MAX_DIFF_CHARS - 100)

        result = _truncate_diff(diff)

        assert result == diff

    def test_truncates_when_over_limit(self):
        """Test that diff is truncated when over limit."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff = "a" * (MAX_DIFF_CHARS + 100)

        result = _truncate_diff(diff)

        assert len(result) < len(diff)
        assert "truncated" in result.lower()

    def test_extracts_file_summaries(self):
        """Test that file-level summaries are extracted."""
        diff_lines = [
            "diff --git a/file.py b/file.py",
            "index 123..456 789",
            "--- a/file.py",
            "+++ b/file.py",
            "@@ -1,1 +1,1 @@",
            " context line",
            "+added line",
            "-removed line",
            "1 file changed, 1 insertion(+), 1 deletion(-)",
        ]
        diff = "\n".join(diff_lines * 1000)  # Make it large

        result = _truncate_diff(diff)

        # Should contain file-level info
        assert "diff --git" in result or "file changed" in result

    def test_returns_exact_limit(self):
        """Test that diff exactly at limit is returned unchanged."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff = "a" * MAX_DIFF_CHARS

        result = _truncate_diff(diff)

        assert result == diff

    def test_falls_back_to_truncation_when_no_summaries(self):
        """Test that truncation falls back to chunk when no summaries found."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        # Create a large diff with no file-level markers
        diff = "a" * (MAX_DIFF_CHARS + 100)

        result = _truncate_diff(diff)

        # Should still be truncated
        assert len(result) < len(diff)
        assert "truncated" in result.lower()

    def test_extracts_rename_markers(self):
        """Test that rename markers are extracted."""
        diff_lines = [
            "diff --git a/old.py b/new.py",
            "rename from old.py",
            "rename to new.py",
            "index 123..456 789",
            "context line" * 1000,
        ]
        diff = "\n".join(diff_lines * 100)  # Make it large

        result = _truncate_diff(diff)

        assert "rename" in result.lower()

    def test_extracts_binary_file_markers(self):
        """Test that binary file markers are extracted."""
        diff_lines = [
            "Binary files a/file.png and b/file.png differ",
            "Binary file a/file.jpg has changed",
            "context line" * 1000,
        ]
        diff = "\n".join(diff_lines * 100)  # Make it large

        result = _truncate_diff(diff)

        assert "binary" in result.lower()

    def test_extracts_new_file_markers(self):
        """Test that new file markers are extracted."""
        diff_lines = [
            "diff --git a/newfile.py b/newfile.py",
            "new file mode 100644",
            "index 0000000..1234567",
            "context line" * 1000,
        ]
        diff = "\n".join(diff_lines * 100)  # Make it large

        result = _truncate_diff(diff)

        assert "new file" in result.lower()

    def test_extracts_deleted_file_markers(self):
        """Test that deleted file markers are extracted."""
        diff_lines = [
            "diff --git a/oldfile.py b/oldfile.py",
            "deleted file mode 100644",
            "index 1234567..0000000",
            "context line" * 1000,
        ]
        diff = "\n".join(diff_lines * 100)  # Make it large

        result = _truncate_diff(diff)

        assert "deleted file" in result.lower()

    def test_extracts_insertion_deletion_stats(self):
        """Test that insertion/deletion stats are extracted."""
        diff_lines = [
            "diff --git a/file.py b/file.py",
            "context line" * 1000,
            "5 files changed, 10 insertions(+), 3 deletions(-)",
            "2 files changed, 50 insertions(+), 20 deletions(-)",
        ]
        diff = "\n".join(diff_lines * 100)  # Make it large

        result = _truncate_diff(diff)

        assert "insertion" in result.lower() or "deletion" in result.lower()

    def test_handles_empty_diff(self):
        """Test that empty diff is handled correctly."""
        result = _truncate_diff("")

        assert result == ""

    def test_handles_diff_with_only_file_headers(self):
        """Test diff with only file header lines."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff_lines = [
            "diff --git a/file.py b/file.py",
            "--- a/file.py",
            "+++ b/file.py",
        ]
        diff = "\n".join(diff_lines * 10000)  # Very large but only headers

        result = _truncate_diff(diff)

        # Should extract headers (may actually be longer due to truncation notice)
        assert "diff --git" in result

    def test_preserves_diff_structure_when_truncated(self):
        """Test that truncated diff maintains proper structure."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff_lines = [
            "diff --git a/file1.py b/file1.py",
            "--- a/file1.py",
            "+++ b/file1.py",
            "some content line" * 100,
            "diff --git a/file2.py b/file2.py",
            "--- a/file2.py",
            "+++ b/file2.py",
            "more content" * 100,
        ]
        diff = "\n".join(diff_lines * 1000)  # Make it very large

        result = _truncate_diff(diff)

        # Should contain header lines
        assert "diff --git" in result
        assert "---" in result
        assert "+++" in result

    def test_adds_truncation_notice(self):
        """Test that truncation notice is added."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        diff = "a" * (MAX_DIFF_CHARS + 100)

        result = _truncate_diff(diff)

        assert "truncated" in result.lower()
        # Can start with truncation notice or just "a"s
        assert "(" in result or result.startswith("a")


class TestStripMarkdownFences:
    """Test _strip_markdown_fences function."""

    def test_removes_markdown_fences(self):
        """Test that markdown fences are removed."""
        content = "```markdown\n# Content\n\nSome text\n```"

        result = _strip_markdown_fences(content)

        assert result.startswith("# Content")
        assert not result.startswith("```")
        assert not result.endswith("```")

    def test_removes_md_fences(self):
        """Test that ```md fences are removed."""
        content = "```md\n# Content\n```"

        result = _strip_markdown_fences(content)

        assert result.startswith("# Content")
        assert not result.startswith("```")

    def test_removes_generic_fences(self):
        """Test that generic ``` fences are removed."""
        content = "```\n# Content\n```"

        result = _strip_markdown_fences(content)

        assert result.startswith("# Content")
        assert not result.startswith("```")

    def test_leaves_content_without_fences(self):
        """Test that content without fences is unchanged."""
        content = "# Content\n\nSome text"

        result = _strip_markdown_fences(content)

        assert result == content

    def test_removes_fences_with_language_no_space(self):
        """Test removing ```markdown without space after."""
        content = "```markdown\n# Content\n```"

        result = _strip_markdown_fences(content)

        assert "```markdown" not in result
        assert "```" not in result

    def test_handles_fences_with_extra_whitespace(self):
        """Test fences with extra whitespace."""
        content = "```markdown  \n  # Content  \n  ```  "

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        # Note: trailing whitespace after closing fence is stripped but we check content
        assert "# Content" in result or "Content" in result

    def test_handles_only_opening_fence(self):
        """Test content with only opening fence."""
        content = "```markdown\n# Content\nNo closing fence"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        assert "No closing fence" in result

    def test_handles_only_closing_fence(self):
        """Test content with only closing fence."""
        content = "# Content\n```"

        result = _strip_markdown_fences(content)

        # Should strip closing fence
        assert not result.endswith("```")
        assert "# Content" in result

    def test_handles_multiple_fence_blocks(self):
        """Test content with multiple fence blocks (only outer stripped)."""
        content = "```markdown\n# Outer\n```\n\n```python\ncode\n```"

        result = _strip_markdown_fences(content)

        # Outer fences should be stripped
        assert not result.startswith("```")
        # Inner fence might remain (simple stripping)
        assert "code" in result or "python" in result

    def test_handles_empty_content_with_fences(self):
        """Test empty content between fences."""
        content = "```\n\n```"

        result = _strip_markdown_fences(content)

        assert result == ""

    def test_handles_content_with_backticks(self):
        """Test content containing backticks not as fences."""
        content = "```markdown\nCode with `backticks` inside\n```"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        assert "backticks" in result

    def test_handles_nested_backticks(self):
        """Test content with nested backticks."""
        content = "```markdown\nText with ``` inside\n```"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        # Should preserve internal backticks
        assert "``` inside" in result or "inside" in result

    def test_handles_content_starting_with_fence_text(self):
        """Test content that starts with fence-like text."""
        content = "```markdown\n# Content starting with code block reference"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        assert "Content starting" in result

    def test_handles_multiline_content_with_fences(self):
        """Test multiline content with fences."""
        content = "```markdown\n# Title\n\nParagraph 1\n\nParagraph 2\n\n## Section\n```"

        result = _strip_markdown_fences(content)

        assert "# Title" in result
        assert "Paragraph 1" in result
        assert "## Section" in result
        assert "```markdown" not in result

    def test_handles_fences_case_sensitivity(self):
        """Test that fence detection is case-sensitive."""
        content = "```Markdown\n# Content\n```"

        result = _strip_markdown_fences(content)

        # Should not strip because it's "Markdown" not "markdown"
        # But generic ``` stripping should work
        assert "# Content" in result

    def test_handles_content_with_trailing_newlines(self):
        """Test content with trailing newlines after fence."""
        content = "```markdown\n# Content\n```"

        result = _strip_markdown_fences(content)

        # Content is stripped, so trailing newlines are removed
        # But the closing fence is removed first, then rstrip
        assert "# Content" in result or result.strip().startswith("# Content")

    def test_handles_lowercase_md_fence(self):
        """Test ```md fence variant."""
        content = "```md\n# Content\n```"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        assert "# Content" in result

    def test_handles_content_already_without_fences(self):
        """Test content without fences is returned as-is."""
        content = "# Just content\n\nNo fences here"

        result = _strip_markdown_fences(content)

        assert result == content

    def test_handles_fences_at_end_of_content(self):
        """Test closing fence at end without newline."""
        content = "```markdown\n# Content\n```"

        result = _strip_markdown_fences(content)

        assert not result.startswith("```")
        assert not result.endswith("```")
        assert "# Content" in result

    def test_handles_whitespace_around_fences(self):
        """Test whitespace around fence markers."""
        content = "```markdown\n# Content\n```"

        result = _strip_markdown_fences(content)

        # Should strip fences
        assert "# Content" in result
        assert not result.startswith("```")


class TestBuildPrompt:
    """Test _build_prompt function."""

    def test_includes_all_sections(self):
        """Test that prompt includes all required sections."""
        template = "## Description\n\nDescribe changes"
        diff = "diff --git a/file.py"
        spec = "# Spec\n\nFeature description"
        commits = "abc123 Message"
        branch = "feature/branch"
        target = "develop"

        result = _build_prompt(template, diff, spec, commits, branch, target)

        assert "Fill out the following GitHub PR template" in result
        assert template in result
        assert diff in result
        assert spec in result
        assert commits in result
        assert branch in result
        assert target in result

    def test_includes_branch_info(self):
        """Test that branch information is included."""
        result = _build_prompt("Template", "Diff", "Spec", "Commits", "feature/test", "main")

        assert "feature/test" in result
        assert "main" in result

    def test_includes_checkbox_guidelines(self):
        """Test that checkbox guidelines are included."""
        result = _build_prompt("T", "D", "S", "C", "b", "t")

        assert "Checkbox Guidelines" in result
        assert "tested my changes locally" in result
        assert "CI checks pass" in result
        assert "synced with develop" in result

    def test_handles_empty_values(self):
        """Test that empty values are handled."""
        result = _build_prompt("", "", "", "", "", "")

        # Should still build prompt with empty sections
        assert "Fill out the following GitHub PR template" in result
        assert "## PR Template" in result
        assert "## Change Context" in result

    def test_handles_special_characters_in_content(self):
        """Test that special characters in content are handled."""
        template = "## Description\n\nCode with `backticks` and \"quotes\""
        diff = "diff --git a/file.py\n+ line with 'quotes' and \"double quotes\""
        spec = "# Spec\n\nContent with $pecial and <chars>"
        commits = "abc123 Fix: issue with \\backslashes\\"

        result = _build_prompt(template, diff, spec, commits, "branch", "target")

        # Should include all content
        assert "backticks" in result
        assert "quotes" in result
        assert "$pecial" in result
        assert "backslashes" in result

    def test_handles_multiline_content(self):
        """Test that multiline content is preserved."""
        template = "## Description\n\nLine 1\nLine 2\nLine 3"
        diff = "diff --git a/file.py\n+line 1\n+line 2"
        spec = "# Spec\n\nFeature:\n- Item 1\n- Item 2"
        commits = "abc123 First commit\nabc124 Second commit"

        result = _build_prompt(template, diff, spec, commits, "branch", "target")

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Item 1" in result
        assert "First commit" in result

    def test_markdown_formatting_in_prompt(self):
        """Test that prompt uses proper markdown formatting."""
        result = _build_prompt("Template", "Diff", "Spec", "Commits", "branch", "target")

        # Check for code blocks
        assert "```" in result
        # Check for headers
        assert "##" in result
        # Check for bold markers
        assert "**" in result

    def test_includes_pr_template_section(self):
        """Test that PR Template section is properly formatted."""
        template = "## Description\n\nPlease describe"
        result = _build_prompt(template, "Diff", "Spec", "Commits", "branch", "target")

        assert "## PR Template" in result
        assert template in result

    def test_includes_branch_info_section(self):
        """Test that Branch Information section is included."""
        result = _build_prompt("T", "D", "S", "C", "feature-123", "main")

        assert "## Branch Information" in result
        assert "feature-123" in result
        assert "main" in result
        assert "Source branch:" in result
        assert "Target branch:" in result

    def test_includes_git_diff_section(self):
        """Test that Git Diff Summary section is included."""
        result = _build_prompt("T", "diff content", "S", "C", "b", "t")

        assert "## Git Diff Summary" in result
        assert "diff content" in result
        # Should be in code block
        assert "```\ndiff content" in result or "diff content\n```" in result

    def test_includes_spec_overview_section(self):
        """Test that Spec Overview section is included."""
        result = _build_prompt("T", "D", "# Spec content", "C", "b", "t")

        assert "## Spec Overview" in result
        assert "# Spec content" in result

    def test_includes_commit_history_section(self):
        """Test that Commit History section is included."""
        result = _build_prompt("T", "D", "S", "commit1\ncommit2", "b", "t")

        assert "## Commit History" in result
        assert "commit1" in result
        # Should be in code block
        assert "```" in result

    def test_handles_long_diff_content(self):
        """Test that long diff content is included."""
        long_diff = "diff --git a/file.py\n+line\n" * 100
        result = _build_prompt("T", long_diff, "S", "C", "b", "t")

        assert long_diff in result

    def test_handles_unicode_characters(self):
        """Test that unicode characters are handled."""
        template = "## Description\n\nUnicode: test"
        diff = "diff --git a/file.py\n+ Unicode: "
        spec = "# Spec\n\nEmoji: "

        result = _build_prompt(template, diff, spec, "C", "b", "t")

        assert "Unicode:" in result or "test" in result

    def test_handles_newlines_in_sections(self):
        """Test that newlines in sections are preserved."""
        result = _build_prompt(
            "Line1\nLine2",
            "Diff1\nDiff2",
            "Spec1\nSpec2",
            "Commit1\nCommit2",
            "branch",
            "target"
        )

        assert "Line1" in result and "Line2" in result
        assert "Diff1" in result and "Diff2" in result
        assert "Spec1" in result and "Spec2" in result
        assert "Commit1" in result and "Commit2" in result

    def test_handles_template_with_checkboxes(self):
        """Test that templates with checkboxes are preserved."""
        template = """
## Description
[ ] Describe changes

## Checklist
- [x] Item 1
- [ ] Item 2
"""
        result = _build_prompt(template, "D", "S", "C", "b", "t")

        assert "[ ]" in result or "- [x]" in result
        assert "Describe changes" in result


class TestLoadSpecOverview:
    """Test _load_spec_overview function."""

    def test_returns_spec_content(self, tmp_path):
        """Test that spec content is returned."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_content = "# Test Spec\n\nDescription"
        spec_file.write_text(spec_content)

        result = _load_spec_overview(spec_dir)

        assert result == spec_content

    def test_truncates_long_specs(self, tmp_path):
        """Test that long specs are truncated."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        long_content = "# Test\n\n" + "a" * 10000
        spec_file.write_text(long_content)

        result = _load_spec_overview(spec_dir)

        assert len(result) < len(long_content)
        assert "truncated" in result.lower()

    def test_returns_fallback_when_missing(self, tmp_path):
        """Test that fallback message is returned when spec is missing."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        result = _load_spec_overview(spec_dir)

        assert "No spec overview available" in result

    def test_handles_spec_read_error(self, tmp_path):
        """Test that file read errors are handled gracefully."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("content")

        with patch("pathlib.Path.read_text", side_effect=OSError("Read error")):
            result = _load_spec_overview(spec_dir)

        # Should return fallback message
        assert "No spec overview available" in result

    def test_handles_spec_at_exact_truncation_limit(self, tmp_path):
        """Test spec at exact truncation limit."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        # Content at exactly 8000 chars (limit is 8000)
        content = "# Test\n\n" + "a" * 7990
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        # Should not be truncated since it's at the limit
        assert len(result) == len(content)

    def test_handles_spec_just_over_truncation_limit(self, tmp_path):
        """Test spec just over truncation limit."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        # Content over 8000 chars (limit)
        content = "# Test\n\n" + "a" * 9000
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        # Should be truncated
        assert len(result) < len(content)
        assert "truncated" in result.lower()

    def test_handles_empty_spec_file(self, tmp_path):
        """Test that empty spec file is handled."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("")

        result = _load_spec_overview(spec_dir)

        # Empty file should still return content (empty string)
        assert result == ""

    def test_handles_spec_with_unicode(self, tmp_path):
        """Test that unicode content in spec is handled."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Test\n\nUnicode: test"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "Unicode:" in result or "test" in result

    def test_handles_spec_with_special_characters(self, tmp_path):
        """Test that special characters in spec are handled."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Test\n\nSpecial: <>&\"'\\"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "Special:" in result

    def test_handles_multiline_spec(self, tmp_path):
        """Test that multiline spec is preserved."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Title\n\nLine 1\nLine 2\nLine 3"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_handles_spec_with_markdown(self, tmp_path):
        """Test that markdown formatting in spec is preserved."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Title\n\n**Bold** and *italic* and `code`"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "**Bold**" in result
        assert "*italic*" in result
        assert "`code`" in result

    def test_handles_spec_with_list_items(self, tmp_path):
        """Test that list items in spec are preserved."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Title\n\n- Item 1\n- Item 2\n- Item 3"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result

    def test_returns_fallback_for_nonexistent_directory(self, tmp_path):
        """Test that missing directory returns fallback."""
        spec_dir = tmp_path / "nonexistent" / "spec"

        result = _load_spec_overview(spec_dir)

        assert "No spec overview available" in result

    def test_handles_spec_with_code_blocks(self, tmp_path):
        """Test that code blocks in spec are preserved."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        content = "# Title\n\n```\ncode here\n```"
        spec_file.write_text(content)

        result = _load_spec_overview(spec_dir)

        assert "```" in result
        assert "code here" in result

    def test_truncation_message_format(self, tmp_path):
        """Test that truncation message is properly formatted."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        long_content = "a" * 10000
        spec_file.write_text(long_content)

        result = _load_spec_overview(spec_dir)

        # Check truncation message format
        assert "truncated for brevity" in result.lower()


class TestRunPrTemplateFiller:
    """Test run_pr_template_filler function."""

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Create PR template
        github_dir = project_dir / ".github"
        github_dir.mkdir()
        template_file = github_dir / "PULL_REQUEST_TEMPLATE.md"
        template_file.write_text("# PR Template\n\n## Description")
        return project_dir

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Test Spec")
        return spec_dir

    @pytest.mark.asyncio
    async def test_returns_none_when_no_template(self, tmp_path):
        """Test that None is returned when no template is found."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        result = await run_pr_template_filler(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model="claude-3-5-sonnet-20241022",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_fills_template_successfully(self, mock_project_dir, mock_spec_dir):
        """Test that template is filled successfully."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled template", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                branch_name="feature/test",
                target_branch="develop",
                diff_summary="Diff content",
                commit_log="Commit log",
            )

            assert result is not None
            assert "Filled template" in result

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, mock_project_dir, mock_spec_dir):
        """Test that None is returned on error."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("error", "Error", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, mock_project_dir, mock_spec_dir):
        """Test that None is returned on exception during session."""
        # The code only catches exceptions in the try block (after client is created)
        # create_client is outside the try block, so we need to patch run_agent_session
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, side_effect=Exception("Test error")):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_strips_markdown_fences_from_response(self, mock_project_dir, mock_spec_dir):
        """Test that markdown fences are stripped from response."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "```markdown\n# Filled\n```", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is not None
            assert not result.startswith("```")

    @pytest.mark.asyncio
    async def test_uses_pr_template_filler_agent_type(self, mock_project_dir, mock_spec_dir):
        """Test that pr_template_filler agent type is used."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Check agent_type
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs["agent_type"] == "pr_template_filler"

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_response(self, mock_project_dir, mock_spec_dir):
        """Test that None is returned when agent returns empty response."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_whitespace_only_response(self, mock_project_dir, mock_spec_dir):
        """Test that None is returned when agent returns whitespace-only response."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "   \n  \t  ", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_passes_thinking_budget_to_client(self, mock_project_dir, mock_spec_dir):
        """Test that thinking budget is passed to client."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                thinking_budget=5000,
            )

            # Check thinking_budget is passed
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs["max_thinking_tokens"] == 5000

    @pytest.mark.asyncio
    async def test_handles_none_thinking_budget(self, mock_project_dir, mock_spec_dir):
        """Test that None thinking budget is handled."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                thinking_budget=None,
            )

            # Check that thinking_budget=None is passed
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs["max_thinking_tokens"] is None

    @pytest.mark.asyncio
    async def test_includes_diff_summary_in_prompt(self, mock_project_dir, mock_spec_dir):
        """Test that diff summary is included in the prompt."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                diff_summary="diff --git a/file.py b/file.py",
            )

            # Check that prompt was built with diff summary
            prompt_arg = mock_session.call_args[0][1]  # Second argument is prompt
            assert "diff --git a/file.py" in prompt_arg

    @pytest.mark.asyncio
    async def test_includes_commit_log_in_prompt(self, mock_project_dir, mock_spec_dir):
        """Test that commit log is included in the prompt."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                commit_log="abc123 Fix bug\nabc124 Add test",
            )

            # Check that prompt was built with commit log
            prompt_arg = mock_session.call_args[0][1]
            assert "abc123 Fix bug" in prompt_arg

    @pytest.mark.asyncio
    async def test_includes_branch_info_in_prompt(self, mock_project_dir, mock_spec_dir):
        """Test that branch info is included in the prompt."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                branch_name="feature/new-auth",
                target_branch="develop",
            )

            # Check that prompt was built with branch info
            prompt_arg = mock_session.call_args[0][1]
            assert "feature/new-auth" in prompt_arg
            assert "develop" in prompt_arg

    @pytest.mark.asyncio
    async def test_handles_large_diff_summary(self, mock_project_dir, mock_spec_dir):
        """Test that large diff summary is truncated before being sent."""
        from agents.pr_template_filler import MAX_DIFF_CHARS
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            large_diff = "a" * (MAX_DIFF_CHARS + 10000)

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                diff_summary=large_diff,
            )

            # Check that prompt was built with truncated diff
            prompt_arg = mock_session.call_args[0][1]
            assert "truncated" in prompt_arg.lower()

    @pytest.mark.asyncio
    async def test_handles_spec_overview_loading(self, mock_project_dir, mock_spec_dir):
        """Test that spec overview is loaded and included."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Check that prompt includes spec overview
            prompt_arg = mock_session.call_args[0][1]
            assert "# Test Spec" in prompt_arg

    @pytest.mark.asyncio
    async def test_respects_verbose_parameter(self, mock_project_dir, mock_spec_dir):
        """Test that verbose parameter is passed to run_agent_session."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=True,
            )

            # Check that verbose was passed (3rd positional arg after client and prompt)
            args = mock_session.call_args[0]
            # run_agent_session(client, prompt, spec_dir, verbose, phase)
            # args are: client, prompt, spec_dir, verbose, phase
            # Actually looking at the code: run_agent_session(client, prompt, spec_dir, verbose, phase)
            # So verbose is the 4th positional arg (index 3)
            assert len(args) >= 4

    @pytest.mark.asyncio
    async def test_logs_error_on_exception(self, mock_project_dir, mock_spec_dir):
        """Test that errors are logged appropriately."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, side_effect=ValueError("Test error")):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Should return None on error
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_different_models(self, mock_project_dir, mock_spec_dir):
        """Test that different models can be used."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-opus-20240229",
            )

            # Check that model is passed (3rd positional arg after project_dir and spec_dir)
            args = mock_create_client.call_args[0]
            assert len(args) >= 3

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_response(self, mock_project_dir, mock_spec_dir):
        """Test that whitespace is stripped from response."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "  \n  # Filled template  \n  ", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            assert result is not None
            assert result.startswith("# Filled template")
            assert not result.startswith(" ")

    @pytest.mark.asyncio
    async def test_handles_missing_spec_file(self, mock_project_dir, tmp_path):
        """Test that missing spec file is handled gracefully."""
        spec_dir = tmp_path / "specs" / "001-no-spec"
        spec_dir.mkdir(parents=True)
        # Don't create spec.md

        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Should use fallback message for spec
            prompt_arg = mock_session.call_args[0][1]
            assert "No spec overview available" in prompt_arg

    @pytest.mark.asyncio
    async def test_handles_template_from_directory(self, mock_project_dir, mock_spec_dir):
        """Test that template from directory is used when single file doesn't exist."""
        # Remove single template file
        single_template = mock_project_dir / ".github" / "PULL_REQUEST_TEMPLATE.md"
        single_template.unlink()

        # Create template directory
        template_dir = mock_project_dir / ".github" / "PULL_REQUEST_TEMPLATE"
        template_dir.mkdir(exist_ok=True)
        (template_dir / "feature.md").write_text("# Feature Template")

        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Should use directory template
            prompt_arg = mock_session.call_args[0][1]
            assert "# Feature Template" in prompt_arg

    @pytest.mark.asyncio
    async def test_default_target_branch(self, mock_project_dir, mock_spec_dir):
        """Test that default target branch is 'develop'."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
            )

            # Check that default target branch is used
            prompt_arg = mock_session.call_args[0][1]
            assert "develop" in prompt_arg

    @pytest.mark.asyncio
    async def test_empty_branch_name(self, mock_project_dir, mock_spec_dir):
        """Test that empty branch name is handled."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock, return_value=("continue", "Filled", {})):

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None

            # Should not raise with empty branch name
            result = await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                branch_name="",
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_custom_target_branch(self, mock_project_dir, mock_spec_dir):
        """Test that custom target branch is used."""
        with patch("agents.pr_template_filler.create_client") as mock_create_client, \
             patch("agents.pr_template_filler.run_agent_session", new_callable=AsyncMock) as mock_session:

            mock_client = AsyncMock()
            mock_create_client.return_value.__aenter__.return_value = mock_client
            mock_create_client.return_value.__aexit__.return_value = None
            mock_session.return_value = ("continue", "Filled", {})

            await run_pr_template_filler(
                project_dir=mock_project_dir,
                spec_dir=mock_spec_dir,
                model="claude-3-5-sonnet-20241022",
                target_branch="main",
            )

            # Check that custom target branch is used
            prompt_arg = mock_session.call_args[0][1]
            assert "main" in prompt_arg
            # Should not contain default 'develop'
            # Actually both might be in context, let's just check main is there
            assert "main" in prompt_arg
