"""Comprehensive tests for merge/prompts.py"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from merge.prompts import (
    build_timeline_merge_prompt,
    build_simple_merge_prompt,
    build_conflict_only_prompt,
    parse_conflict_markers,
    reassemble_with_resolutions,
    extract_conflict_resolutions,
    optimize_prompt_for_length,
)

from merge.timeline_models import (
    BranchPoint,
    MainBranchEvent,
    MergeContext,
    TaskIntent,
)


class TestBuildTimelineMergePrompt:
    """Tests for build_timeline_merge_prompt function"""

    def test_build_timeline_merge_prompt_basic(self):
        """Test basic prompt building with MergeContext"""
        context = MergeContext(
            file_path="src/App.tsx",
            task_id="task-001",
            task_intent=TaskIntent(title="Add auth", description="Add authentication"),
            task_branch_point=BranchPoint(
                commit_hash="abc123",
                content="export default function App() {}",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="export default function App() { auth() }",
            current_main_content="export default function App() {}",
            current_main_commit="def456",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        assert "MERGING: src/App.tsx" in result
        assert "TASK: task-001" in result
        assert "Add auth" in result
        assert "Branched from commit: abc123" in result
        assert "PRESERVE all changes from main branch" in result

    def test_build_timeline_merge_prompt_with_main_evolution(self):
        """Test prompt with main branch evolution events"""
        now = datetime.now()
        context = MergeContext(
            file_path="test.py",
            task_id="task-001",
            task_intent=TaskIntent(title="Feature", description="A feature"),
            task_branch_point=BranchPoint(
                commit_hash="abc123",
                content="old",
                timestamp=now,
            ),
            main_evolution=[
                MainBranchEvent(
                    commit_hash="def456",
                    timestamp=now,
                    content="new1",
                    source="human",
                    commit_message="Human commit",
                ),
                MainBranchEvent(
                    commit_hash="789012",
                    timestamp=now,
                    content="new2",
                    source="merged_task",
                    commit_message="Merged task-002",
                    merged_from_task="task-002",
                ),
            ],
            task_worktree_content="task content",
            current_main_content="main content",
            current_main_commit="789012",
            other_pending_tasks=[],
            total_commits_behind=2,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        assert "MAIN BRANCH EVOLUTION (2 commits since task branched)" in result
        assert "MERGED FROM task-002" in result
        assert "Human commit" in result

    def test_build_timeline_merge_prompt_with_main_evolution_with_diff_summary(self):
        """Test prompt with main branch evolution events with diff_summary"""
        now = datetime.now()
        context = MergeContext(
            file_path="test.py",
            task_id="task-001",
            task_intent=TaskIntent(title="Feature", description="A feature"),
            task_branch_point=BranchPoint(
                commit_hash="abc123",
                content="old",
                timestamp=now,
            ),
            main_evolution=[
                MainBranchEvent(
                    commit_hash="def456",
                    timestamp=now,
                    content="new1",
                    source="human",
                    commit_message="Human commit",
                    diff_summary="+15 -3 lines",  # Cover line 123
                ),
            ],
            task_worktree_content="task content",
            current_main_content="main content",
            current_main_commit="def456",
            other_pending_tasks=[],
            total_commits_behind=1,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        assert "MAIN BRANCH EVOLUTION (1 commits since task branched)" in result
        assert "Changes: +15 -3 lines" in result

    def test_build_timeline_merge_prompt_with_main_evolution_without_diff_summary(self):
        """Test prompt with main branch evolution events without diff_summary"""
        now = datetime.now()
        context = MergeContext(
            file_path="test.py",
            task_id="task-001",
            task_intent=TaskIntent(title="Feature", description="A feature"),
            task_branch_point=BranchPoint(
                commit_hash="abc123",
                content="old",
                timestamp=now,
            ),
            main_evolution=[
                MainBranchEvent(
                    commit_hash="def456",
                    timestamp=now,
                    content="new1",
                    source="human",
                    commit_message="Human commit",
                    diff_summary=None,  # Cover line 125
                ),
            ],
            task_worktree_content="task content",
            current_main_content="main content",
            current_main_commit="def456",
            other_pending_tasks=[],
            total_commits_behind=1,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        assert "Changes: See content evolution below" in result

    def test_build_timeline_merge_prompt_with_pending_tasks(self):
        """Test prompt with other pending tasks"""
        context = MergeContext(
            file_path="file.ts",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description="Task 1"),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[
                {"task_id": "task-002", "intent": "Add logging", "branch_point": "xyz", "commits_behind": 3},
                {"task_id": "task-003", "intent": "Fix bug", "branch_point": "uvw", "commits_behind": 1},
            ],
            total_commits_behind=0,
            total_pending_tasks=2,
        )

        result = build_timeline_merge_prompt(context)

        assert "OTHER TASKS ALSO MODIFYING THIS FILE" in result
        assert "task-002" in result
        assert "Add logging" in result
        assert "task-003" in result
        assert "Fix bug" in result
        assert "2 other task(s) will merge after this" in result

    def test_build_timeline_merge_prompt_with_pending_tasks_no_intent(self):
        """Test prompt with pending tasks that have no intent (cover line 176)"""
        context = MergeContext(
            file_path="file.ts",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description="Task 1"),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[
                {"task_id": "task-002", "intent": "", "branch_point": "xyz", "commits_behind": 3},  # Empty intent
                {"task_id": "task-003", "intent": "Fix bug", "branch_point": "uvw", "commits_behind": 1},
            ],
            total_commits_behind=0,
            total_pending_tasks=2,
        )

        result = build_timeline_merge_prompt(context)

        # Should include task-002 without intent description
        assert "task-002" in result
        assert "task-003" in result

    def test_build_timeline_merge_prompt_no_pending_tasks(self):
        """Test prompt with no other pending tasks"""
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        assert "No other tasks are pending for this file" in result
        assert "No other tasks pending for this file" in result

    def test_build_timeline_merge_prompt_empty_description(self):
        """Test prompt with empty task intent description"""
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),  # Empty description
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = build_timeline_merge_prompt(context)

        # Should use title when description is empty
        assert "T1" in result


class TestBuildSimpleMergePrompt:
    """Tests for build_simple_merge_prompt function"""

    def test_build_simple_merge_prompt_basic(self):
        """Test simple merge prompt without task intent"""
        result = build_simple_merge_prompt(
            file_path="test.py",
            main_content="main version",
            worktree_content="feature version",
            base_content="base version",
            spec_name="feature-branch",
            language="python",
            task_intent=None,
        )

        assert "FILE: test.py" in result
        assert "main version" in result
        assert "feature version" in result
        assert "base version" in result
        assert "feature-branch" in result
        assert "syntactically valid python" in result

    def test_build_simple_merge_prompt_with_task_intent(self):
        """Test simple merge prompt with task intent"""
        task_intent = {
            "title": "Add authentication",
            "description": "Add OAuth login flow",
            "spec_summary": "Implement login with Google",
        }

        result = build_simple_merge_prompt(
            file_path="App.tsx",
            main_content="main",
            worktree_content="feature",
            base_content="base",
            spec_name="auth-feature",
            language="typescript",
            task_intent=task_intent,
        )

        assert "FEATURE BRANCH INTENT (auth-feature)" in result
        assert "Add authentication" in result
        assert "Add OAuth login flow" in result
        assert "Implement login with Google" in result

    def test_build_simple_merge_prompt_no_base_content(self):
        """Test simple merge prompt when base content is None"""
        result = build_simple_merge_prompt(
            file_path="new_file.py",
            main_content="main content",
            worktree_content="feature content",
            base_content=None,
            spec_name="new-feature",
            language="python",
        )

        assert "(File did not exist in common ancestor)" in result

    def test_build_simple_merge_prompt_empty_base(self):
        """Test simple merge prompt with empty base content"""
        result = build_simple_merge_prompt(
            file_path="test.js",
            main_content="main",
            worktree_content="feature",
            base_content="",
            spec_name="feature",
            language="javascript",
        )

        assert "=== COMMON ANCESTOR (base) ===" in result


class TestBuildConflictOnlyPrompt:
    """Tests for build_conflict_only_prompt function"""

    def test_build_conflict_only_prompt_single_conflict(self):
        """Test conflict-only prompt with single conflict"""
        conflicts = [
            {
                "id": "CONFLICT_1",
                "main_lines": "function foo() { return 1; }",
                "worktree_lines": "function foo() { return 2; }",
                "context_before": "Before function",
                "context_after": "After function",
            }
        ]

        result = build_conflict_only_prompt(
            file_path="test.js",
            conflicts=conflicts,
            spec_name="feature-branch",
            language="javascript",
            task_intent=None,
        )

        assert "1 conflict(s) in test.js" in result
        assert "--- CONFLICT_1 ---" in result
        assert "function foo() { return 1; }" in result
        assert "function foo() { return 2; }" in result
        assert "CONTEXT BEFORE:" in result
        assert "CONTEXT AFTER:" in result

    def test_build_conflict_only_prompt_multiple_conflicts(self):
        """Test conflict-only prompt with multiple conflicts"""
        conflicts = [
            {
                "id": "CONFLICT_1",
                "main_lines": "line1",
                "worktree_lines": "line1a",
                "context_before": "",
                "context_after": "",
            },
            {
                "id": "CONFLICT_2",
                "main_lines": "line2",
                "worktree_lines": "line2a",
                "context_before": "",
                "context_after": "",
            },
        ]

        result = build_conflict_only_prompt(
            file_path="file.py",
            conflicts=conflicts,
            spec_name="task-001",
            language="python",
            task_intent=None,
        )

        assert "2 conflict(s) in file.py" in result
        assert "--- CONFLICT_1 ---" in result
        assert "--- CONFLICT_2 ---" in result
        assert "--- CONFLICT_2 RESOLVED ---" in result
        assert "(continue for each conflict)" in result

    def test_build_conflict_only_prompt_with_task_intent(self):
        """Test conflict-only prompt with task intent"""
        conflicts = [
            {
                "id": "CONFLICT_1",
                "main_lines": "main",
                "worktree_lines": "feature",
                "context_before": "",
                "context_after": "",
            }
        ]

        task_intent = {
            "title": "Refactor code",
            "description": "Clean up implementation",
        }

        result = build_conflict_only_prompt(
            file_path="code.ts",
            conflicts=conflicts,
            spec_name="refactor",
            language="typescript",
            task_intent=task_intent,
        )

        assert "FEATURE INTENT: Refactor code" in result
        assert "Clean up implementation" in result


class TestParseConflictMarkers:
    """Tests for parse_conflict_markers function"""

    def test_parse_single_conflict(self):
        """Test parsing a single conflict region"""
        content = """before
<<<<<<< HEAD
main content
=======
feature content
>>>>>>> feature-branch
after"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert conflicts[0]["id"] == "CONFLICT_1"
        assert conflicts[0]["main_lines"] == "main content"
        assert conflicts[0]["worktree_lines"] == "feature content"
        assert len(clean_sections) == 2
        assert clean_sections[0] == "before\n"
        assert clean_sections[1] == "after"

    def test_parse_multiple_conflicts(self):
        """Test parsing multiple conflict regions"""
        content = """start
<<<<<<< HEAD
main1
=======
feature1
>>>>>>> branch1
middle
<<<<<<< HEAD
main2
=======
feature2
>>>>>>> branch2
end"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 2
        assert conflicts[0]["id"] == "CONFLICT_1"
        assert conflicts[1]["id"] == "CONFLICT_2"
        assert conflicts[0]["main_lines"] == "main1"
        assert conflicts[1]["main_lines"] == "main2"
        assert len(clean_sections) == 3

    def test_parse_conflicts_with_context(self):
        """Test that context is extracted before and after conflicts"""
        content = """line1
line2
line3
<<<<<<< HEAD
main
=======
feature
>>>>>>> branch
line4
line5
line6"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        # Should have last 3 lines before conflict as context
        assert "line1" in conflicts[0]["context_before"]
        assert "line2" in conflicts[0]["context_before"]
        assert "line3" in conflicts[0]["context_before"]
        # Should have first 3 lines after conflict as context
        assert "line4" in conflicts[0]["context_after"]
        assert "line5" in conflicts[0]["context_after"]
        assert "line6" in conflicts[0]["context_after"]

    def test_parse_no_conflicts(self):
        """Test parsing content without conflicts"""
        content = "clean content\nno conflicts here"

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 0
        assert len(clean_sections) == 1
        assert clean_sections[0] == content

    def test_parse_conflict_with_multiline_content(self):
        """Test parsing conflicts with multiline content"""
        content = """before
<<<<<<< HEAD
def function1():
    pass

def function2():
    pass
=======
def functionA():
    return 1
>>>>>>> branch
after"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert "def function1():" in conflicts[0]["main_lines"]
        assert "def function2():" in conflicts[0]["main_lines"]
        assert "def functionA():" in conflicts[0]["worktree_lines"]

    def test_parse_conflict_markers_variations(self):
        """Test parsing different conflict marker formats"""
        # Test with different branch names
        content = """<<<<<<< main
main
=======
feature
>>>>>>> feature
"""

        conflicts, _ = parse_conflict_markers(content)

        assert len(conflicts) == 1

    def test_parse_conflict_at_start(self):
        """Test parsing conflict at the very start of content"""
        content = """<<<<<<< HEAD
main
=======
feature
>>>>>>> branch
after"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert conflicts[0]["main_lines"] == "main"
        # First clean section should be empty
        assert clean_sections[0] == ""

    def test_parse_conflict_at_end(self):
        """Test parsing conflict at the very end of content"""
        content = """before
<<<<<<< HEAD
main
=======
feature
>>>>>>> branch"""

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        # Last clean section should be empty or just newline
        # When conflict is at end with no trailing newline, there's only 1 clean section
        assert len(clean_sections) >= 1

    def test_parse_conflict_with_empty_sections(self):
        """Test parsing conflict with empty main or worktree sections"""
        content = """before
<<<<<<< HEAD

=======
feature
>>>>>>> branch
after"""

        conflicts, _ = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert conflicts[0]["main_lines"] == ""
        assert conflicts[0]["worktree_lines"] == "feature"

    def test_parse_conflict_with_newlines_in_markers(self):
        """Test conflict markers without trailing newlines"""
        content = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts, clean_sections = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert conflicts[0]["main_lines"] == "main"
        assert conflicts[0]["worktree_lines"] == "feature"

    def test_parse_conflict_with_special_characters(self):
        """Test parsing conflicts with special characters in content"""
        content = r"""before
<<<<<<< HEAD
const x = "quotes";
const y = `backticks`;
const regex = /\d+/;
=======
const x = 'single quotes';
const y = "double quotes";
>>>>>>> branch
after"""

        conflicts, _ = parse_conflict_markers(content)

        assert len(conflicts) == 1
        assert "quotes" in conflicts[0]["main_lines"]
        assert "backticks" in conflicts[0]["main_lines"]
        assert "single quotes" in conflicts[0]["worktree_lines"]

    def test_parse_conflict_long_content_context_limit(self):
        """Test that context extraction handles limited lines correctly"""
        # Only 1 line before conflict
        content = """single
<<<<<<< HEAD
main
=======
feature
>>>>>>> branch
after"""

        conflicts, _ = parse_conflict_markers(content)

        assert len(conflicts) == 1
        # Should have context_before with just "single"
        assert conflicts[0]["context_before"] == "single"

    def test_parse_conflict_very_short_after_context(self):
        """Test context after when file ends shortly after conflict"""
        content = """before
<<<<<<< HEAD
main
=======
feature
>>>>>>> branch
end"""

        conflicts, _ = parse_conflict_markers(content)

        assert len(conflicts) == 1
        # context_after should handle short content
        assert "end" in conflicts[0]["context_after"] or conflicts[0]["context_after"] == ""


class TestReassembleWithResolutions:
    """Tests for reassemble_with_resolutions function"""

    def test_reassemble_single_conflict(self):
        """Test reassembling file with one resolved conflict"""
        original = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 7,
                "end": 56,  # Position after \n of >>>>>>> branch
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {"CONFLICT_1": "resolved content"}

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "before\n" in result
        assert "resolved content" in result
        assert "after" in result
        assert "<<<<<<<" not in result
        assert "=======" not in result
        assert ">>>>>>>" not in result

    def test_reassemble_multiple_conflicts(self):
        """Test reassembling file with multiple resolved conflicts"""
        original = """start
<<<<<<< HEAD
main1
=======
feature1
>>>>>>> branch1
middle
<<<<<<< HEAD
main2
=======
feature2
>>>>>>> branch2
end"""

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 6,
                "end": 57,
                "main_lines": "main1",
                "worktree_lines": "feature1",
            },
            {
                "id": "CONFLICT_2",
                "start": 64,
                "end": 116,
                "main_lines": "main2",
                "worktree_lines": "feature2",
            }
        ]

        resolutions = {
            "CONFLICT_1": "resolved1",
            "CONFLICT_2": "resolved2",
        }

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "start" in result
        assert "resolved1" in result
        assert "middle" in result
        assert "resolved2" in result
        assert "end" in result

    def test_reassemble_fallback_to_worktree(self):
        """Test fallback to worktree content when no resolution provided"""
        original = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 7,
                "end": 56,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {}  # No resolution provided

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "before\n" in result
        assert "feature" in result  # Should use worktree content
        assert "after" in result

    def test_reassemble_preserves_unsorted_conflicts(self):
        """Test that conflicts are sorted by position even if provided unsorted"""
        original = """start
<<<<<<<
first
=======
second
>>>>>>> end
middle
<<<<<<<
third
=======
fourth
>>>>>>> end
end"""

        conflicts = [
            {
                "id": "CONFLICT_2",
                "start": 40,  # Later position
                "end": 70,
                "main_lines": "third",
                "worktree_lines": "fourth",
                "context_before": "",
                "context_after": "",
            },
            {
                "id": "CONFLICT_1",
                "start": 6,  # Earlier position
                "end": 35,
                "main_lines": "first",
                "worktree_lines": "second",
                "context_before": "",
                "context_after": "",
            }
        ]

        resolutions = {
            "CONFLICT_1": "R1",
            "CONFLICT_2": "R2",
        }

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        # Should be in correct order despite unsorted input
        assert result.index("R1") < result.index("R2")

    def test_reassemble_partial_resolutions(self):
        """Test reassembling when only some conflicts have resolutions"""
        original = """start
<<<<<<< HEAD
main1
=======
feature1
>>>>>>> branch1
middle
<<<<<<< HEAD
main2
=======
feature2
>>>>>>> branch2
end"""

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 6,
                "end": 57,
                "main_lines": "main1",
                "worktree_lines": "feature1",
            },
            {
                "id": "CONFLICT_2",
                "start": 64,
                "end": 116,
                "main_lines": "main2",
                "worktree_lines": "feature2",
            }
        ]

        # Only resolve first conflict
        resolutions = {
            "CONFLICT_1": "resolved1",
            # CONFLICT_2 not provided - should fall back to worktree
        }

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "resolved1" in result
        assert "feature2" in result  # Should use worktree content

    def test_reassemble_empty_resolutions(self):
        """Test reassembling with all empty resolutions"""
        original = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 7,
                "end": 56,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {"CONFLICT_1": ""}  # Empty resolution

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        # Empty resolution should still be applied
        assert "before\n" in result
        assert "after" in result
        assert "<<<<<<<" not in result

    def test_reassemble_multiline_resolution(self):
        """Test reassembling with multiline resolved content"""
        original = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 7,
                "end": 56,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {
            "CONFLICT_1": "line1\nline2\nline3"
        }

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_reassemble_conflict_at_start(self):
        """Test reassembling when conflict is at the start"""
        original = "<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch\nafter"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 0,
                "end": 49,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {"CONFLICT_1": "resolved"}

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert result.startswith("resolved")
        assert "after" in result

    def test_reassemble_conflict_at_end(self):
        """Test reassembling when conflict is at the end"""
        original = "before\n<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 7,
                "end": 56,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {"CONFLICT_1": "resolved"}

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert "before\n" in result
        assert result.endswith("resolved") or result.rstrip().endswith("resolved")

    def test_reassemble_no_clean_sections(self):
        """Test reassembling when entire file is one conflict"""
        original = "<<<<<<< HEAD\nmain\n=======\nfeature\n>>>>>>> branch"

        conflicts = [
            {
                "id": "CONFLICT_1",
                "start": 0,
                "end": 49,
                "main_lines": "main",
                "worktree_lines": "feature",
            }
        ]

        resolutions = {"CONFLICT_1": "resolved"}

        result = reassemble_with_resolutions(original, conflicts, resolutions)

        assert result == "resolved"


class TestExtractConflictResolutions:
    """Tests for extract_conflict_resolutions function"""

    def test_extract_single_resolution(self):
        """Test extracting a single resolution"""
        response = """Some text

--- CONFLICT_1 RESOLVED ---
```python
def merged():
    pass
```

More text"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions
        assert "def merged():" in resolutions["CONFLICT_1"]
        assert "pass" in resolutions["CONFLICT_1"]

    def test_extract_multiple_resolutions(self):
        """Test extracting multiple resolutions"""
        response = """--- CONFLICT_1 RESOLVED ---
```python
resolution1
```

--- CONFLICT_2 RESOLVED ---
```python
resolution2
```"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""},
            {"id": "CONFLICT_2", "main_lines": "", "worktree_lines": ""},
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert len(resolutions) == 2
        assert "resolution1" in resolutions["CONFLICT_1"]
        assert "resolution2" in resolutions["CONFLICT_2"]

    def test_extract_case_insensitive(self):
        """Test that marker matching is case-insensitive"""
        response = """--- conflict_1 resolved ---
```python
content
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions

    def test_extract_fallback_single_code_block(self):
        """Test fallback to single code block when no markers found"""
        response = """Here's the merged code:

```python
def merged():
    return "merged"
```"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions
        assert "def merged():" in resolutions["CONFLICT_1"]

    def test_extract_no_resolution(self):
        """Test when no resolution can be extracted"""
        response = "I couldn't resolve this conflict"

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert len(resolutions) == 0

    def test_extract_with_language_in_marker(self):
        """Test extraction when language is in code block marker"""
        response = """--- CONFLICT_1 RESOLVED ---
```javascript
function merged() {}
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "javascript")

        assert "function merged()" in resolutions["CONFLICT_1"]

    def test_extract_with_no_language_marker(self):
        """Test extraction when code block has no language marker"""
        response = """--- CONFLICT_1 RESOLVED ---
```
def merged():
    pass
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "def merged():" in resolutions["CONFLICT_1"]

    def test_extract_multiline_resolution(self):
        """Test extracting multiline resolution content"""
        response = """--- CONFLICT_1 RESOLVED ---
```python
def function1():
    pass

def function2():
    return 1
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "def function1():" in resolutions["CONFLICT_1"]
        assert "def function2():" in resolutions["CONFLICT_1"]

    def test_extract_with_extra_whitespace(self):
        """Test extraction with extra whitespace in markers"""
        response = """---  CONFLICT_1  RESOLVED  ---
```python
content
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions
        assert "content" in resolutions["CONFLICT_1"]

    def test_extract_partial_resolutions(self):
        """Test when only some conflicts have resolutions"""
        response = """--- CONFLICT_1 RESOLVED ---
```python
resolved1
```

--- CONFLICT_3 RESOLVED ---
```python
resolved3
```"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""},
            {"id": "CONFLICT_2", "main_lines": "", "worktree_lines": ""},  # No resolution
            {"id": "CONFLICT_3", "main_lines": "", "worktree_lines": ""},
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert len(resolutions) == 2
        assert "CONFLICT_1" in resolutions
        assert "CONFLICT_2" not in resolutions
        assert "CONFLICT_3" in resolutions

    def test_extract_fallback_multiple_code_blocks_single_conflict(self):
        """Test that fallback uses first code block when multiple exist"""
        response = """Here's some context:

```python
first block
```

Some explanation:

```python
second block
```"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions
        # Should use the first code block
        assert "first block" in resolutions["CONFLICT_1"]

    def test_extract_empty_resolution(self):
        """Test extracting empty resolution"""
        response = """--- CONFLICT_1 RESOLVED ---
```python

```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "CONFLICT_1" in resolutions
        assert resolutions["CONFLICT_1"] == ""

    def test_extract_with_special_characters(self):
        """Test extraction with special characters in code"""
        response = r"""--- CONFLICT_1 RESOLVED ---
```python
const x = "quotes";
const y = `backticks`;
const regex = /\d+/;
```"""

        conflicts = [{"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""}]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        assert "quotes" in resolutions["CONFLICT_1"]
        assert "backticks" in resolutions["CONFLICT_1"]

    def test_extract_order_preserved(self):
        """Test that extraction order matches conflict order"""
        response = """--- CONFLICT_2 RESOLVED ---
```python
resolution2
```

--- CONFLICT_1 RESOLVED ---
```python
resolution1
```"""

        conflicts = [
            {"id": "CONFLICT_1", "main_lines": "", "worktree_lines": ""},
            {"id": "CONFLICT_2", "main_lines": "", "worktree_lines": ""},
        ]

        resolutions = extract_conflict_resolutions(response, conflicts, "python")

        # Both should be extracted regardless of order in response
        assert len(resolutions) == 2
        assert "CONFLICT_1" in resolutions
        assert "CONFLICT_2" in resolutions


class TestOptimizePromptForLength:
    """Tests for optimize_prompt_for_length function"""

    def test_optimize_no_trimming_needed(self):
        """Test when content is already within limits"""
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="short",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="short",
            current_main_content="short",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_content_chars=1000)

        assert result.task_branch_point.content == "short"
        assert result.task_worktree_content == "short"
        assert result.current_main_content == "short"

    def test_optimize_trim_content(self):
        """Test trimming long content"""
        long_content = "x" * 1000

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content=long_content,
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content=long_content,
            current_main_content=long_content,
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_content_chars=500)

        # Should be trimmed with omission marker
        assert len(result.task_branch_point.content) < 1000
        assert "omitted" in result.task_branch_point.content.lower()

    def test_optimize_trim_evolution_events(self):
        """Test trimming too many evolution events"""
        now = datetime.now()
        events = [
            MainBranchEvent(
                commit_hash=f"commit{i}",
                timestamp=now,
                content=f"content{i}",
                source="human",
                commit_message=f"Commit {i}",
            )
            for i in range(20)  # More than max_evolution_events default
        ]

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=now,
            ),
            main_evolution=events,
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_evolution_events=10)

        # Should have placeholder
        assert len(result.main_evolution) <= 11  # 10 + placeholder
        assert any("omitted" in str(e.commit_message).lower() or "omitted" in str(e.content).lower()
                   for e in result.main_evolution)

    def test_optimize_custom_limits(self):
        """Test with custom max limits"""
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="x" * 100,
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="y" * 100,
            current_main_content="z" * 100,
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(
            context,
            max_content_chars=50,
            max_evolution_events=5,
        )

        # Content should be trimmed
        assert len(result.task_branch_point.content) < 100
        assert "omitted" in result.task_branch_point.content.lower()

    def test_optimize_preserves_essential_info(self):
        """Test that optimization preserves essential merge info"""
        context = MergeContext(
            file_path="important.py",
            task_id="critical-task",
            task_intent=TaskIntent(title="Critical", description="Fix bug"),
            task_branch_point=BranchPoint(
                commit_hash="abc123",
                content="original",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="fixed",
            current_main_content="current",
            current_main_commit="def456",
            other_pending_tasks=[
                {"task_id": "other", "intent": "Other change", "branch_point": "xyz", "commits_behind": 1}
            ],
            total_commits_behind=0,
            total_pending_tasks=1,
        )

        result = optimize_prompt_for_length(context)

        # Essential fields should be preserved
        assert result.file_path == "important.py"
        assert result.task_id == "critical-task"
        assert result.task_intent.title == "Critical"
        assert result.task_branch_point.commit_hash == "abc123"
        assert len(result.other_pending_tasks) == 1

    def test_optimize_evolution_placeholder_message(self):
        """Test that evolution placeholder contains correct message"""
        now = datetime.now()
        events = [
            MainBranchEvent(
                commit_hash=f"commit{i}",
                timestamp=now,
                content=f"content{i}",
                source="human",
                commit_message=f"Commit {i}",
            )
            for i in range(15)
        ]

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=now,
            ),
            main_evolution=events,
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_evolution_events=10)

        # Find placeholder event
        placeholder = next(
            (e for e in result.main_evolution if e.commit_hash == "..."),
            None
        )
        assert placeholder is not None
        assert "5 commits omitted" in placeholder.commit_message  # 15 - 10 = 5

    def test_optimize_returns_modified_context(self):
        """Test that optimization returns the modified context (not a copy)"""
        now = datetime.now()
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="x" * 1000,
                timestamp=now,
            ),
            main_evolution=[],
            task_worktree_content="y" * 1000,
            current_main_content="z" * 1000,
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        original_content_len = len(context.task_branch_point.content)
        result = optimize_prompt_for_length(context, max_content_chars=100)

        # Result should be the modified same object
        assert result is context
        # Content should be modified in place
        assert len(result.task_branch_point.content) < original_content_len

    def test_optimize_exact_limit_no_trim(self):
        """Test when content is exactly at the limit"""
        exact_content = "x" * 500

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content=exact_content,
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content=exact_content,
            current_main_content=exact_content,
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_content_chars=500)

        # Should not be trimmed since it's exactly at limit
        assert result.task_branch_point.content == exact_content
        assert "omitted" not in result.task_branch_point.content.lower()

    def test_optimize_evolution_with_mixed_sources(self):
        """Test evolution trimming with mixed event sources"""
        now = datetime.now()
        events = []
        for i in range(15):
            source = "human" if i % 2 == 0 else "merged_task"
            events.append(
                MainBranchEvent(
                    commit_hash=f"commit{i}",
                    timestamp=now,
                    content=f"content{i}",
                    source=source,
                    commit_message=f"Commit {i}",
                    merged_from_task=f"task-{i}" if source == "merged_task" else None,
                )
            )

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=now,
            ),
            main_evolution=events,
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = optimize_prompt_for_length(context, max_evolution_events=8)

        # Should have first 4, placeholder, last 4
        assert len(result.main_evolution) == 9  # 8 + placeholder
        # First and last events should be preserved
        assert result.main_evolution[0].commit_hash == "commit0"
        assert result.main_evolution[-1].commit_hash == "commit14"


class TestBuildMainEvolutionSection:
    """Tests for _build_main_evolution_section helper function"""

    def test_build_main_evolution_no_events(self):
        """Test building main evolution section with no events"""
        from merge.prompts import _build_main_evolution_section

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = _build_main_evolution_section(context)

        assert "0 commits since task branched" in result
        assert "No changes have been made" in result

    def test_build_main_evolution_with_diff_summary(self):
        """Test building main evolution with diff summary"""
        from merge.prompts import _build_main_evolution_section

        now = datetime.now()
        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=now,
            ),
            main_evolution=[
                MainBranchEvent(
                    commit_hash="def456",
                    timestamp=now,
                    content="new",
                    source="human",
                    commit_message="Fix bug",
                    diff_summary="+10 -5 lines",
                ),
            ],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def456",
            other_pending_tasks=[],
            total_commits_behind=1,
            total_pending_tasks=0,
        )

        result = _build_main_evolution_section(context)

        assert "1 commits since task branched" in result
        assert "Changes: +10 -5 lines" in result


class TestBuildPendingTasksSection:
    """Tests for _build_pending_tasks_section helper function"""

    def test_build_pending_tasks_no_tasks(self):
        """Test building pending tasks section with no tasks"""
        from merge.prompts import _build_pending_tasks_section

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = _build_pending_tasks_section(context)

        assert "No other tasks are pending" in result

    def test_build_pending_tasks_with_missing_fields(self):
        """Test building pending tasks with missing optional fields"""
        from merge.prompts import _build_pending_tasks_section

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[
                {"task_id": "task-002"},  # Missing intent, branch_point, commits_behind
            ],
            total_commits_behind=0,
            total_pending_tasks=1,
        )

        result = _build_pending_tasks_section(context)

        assert "task-002" in result
        assert "unknown" in result  # Default for missing fields


class TestBuildCompatibilityInstructions:
    """Tests for _build_compatibility_instructions helper function"""

    def test_build_compatibility_no_pending(self):
        """Test building compatibility instructions with no pending tasks"""
        from merge.prompts import _build_compatibility_instructions

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[],
            total_commits_behind=0,
            total_pending_tasks=0,
        )

        result = _build_compatibility_instructions(context)

        assert "No other tasks pending for this file" in result

    def test_build_compatibility_with_tasks(self):
        """Test building compatibility instructions with pending tasks"""
        from merge.prompts import _build_compatibility_instructions

        context = MergeContext(
            file_path="file.py",
            task_id="task-001",
            task_intent=TaskIntent(title="T1", description=""),
            task_branch_point=BranchPoint(
                commit_hash="abc",
                content="",
                timestamp=datetime.now(),
            ),
            main_evolution=[],
            task_worktree_content="",
            current_main_content="",
            current_main_commit="def",
            other_pending_tasks=[
                {"task_id": "task-002", "intent": "Add feature X", "branch_point": "xyz", "commits_behind": 2},
                {"task_id": "task-003", "intent": "Fix bug Y", "branch_point": "uvw", "commits_behind": 1},
            ],
            total_commits_behind=0,
            total_pending_tasks=2,
        )

        result = _build_compatibility_instructions(context)

        assert "2 other task(s) will merge after this" in result
        assert "task-002: Add feature X" in result
        assert "task-003: Fix bug Y" in result
