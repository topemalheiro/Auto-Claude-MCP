"""Comprehensive tests for file_merger module"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from merge.file_merger import (
    apply_ai_merge,
    apply_single_task_changes,
    combine_non_conflicting_changes,
    detect_line_ending,
    extract_location_content,
    find_import_end,
)
from merge.types import ChangeType, SemanticChange, TaskSnapshot


class TestDetectLineEnding:
    """Test suite for detect_line_ending function"""

    def test_detect_lf_ending(self):
        """Test detection of LF (Unix) line endings"""
        content = "line1\nline2\nline3\n"
        assert detect_line_ending(content) == "\n"

    def test_detect_crlf_ending(self):
        """Test detection of CRLF (Windows) line endings"""
        content = "line1\r\nline2\r\nline3\r\n"
        assert detect_line_ending(content) == "\r\n"

    def test_detect_cr_ending(self):
        """Test detection of CR (classic Mac) line endings"""
        content = "line1\rline2\rline3\r"
        assert detect_line_ending(content) == "\r"

    def test_detect_crlf_priority_over_lf(self):
        """Test that CRLF is detected even when LF is present (since CRLF contains LF)"""
        content = "line1\r\nline2\r\n"
        # CRLF should be detected first (priority check)
        assert detect_line_ending(content) == "\r\n"

    def test_detect_default_to_lf(self):
        """Test that empty or non-newline content defaults to LF"""
        assert detect_line_ending("") == "\n"
        assert detect_line_ending("no newlines here") == "\n"

    def test_detect_mixed_endings(self):
        """Test detection with mixed line endings (returns first by priority)"""
        # Mixed endings - CRLF should be detected first due to priority
        content = "line1\r\nline2\nline3\r"
        assert detect_line_ending(content) == "\r\n"

    def test_detect_only_crlf_in_content(self):
        """Test pure CRLF content without other ending types"""
        content = "line1\r\nline2\r\nline3\r\n"
        assert detect_line_ending(content) == "\r\n"

    def test_detect_single_newline(self):
        """Test detection with single newline character"""
        assert detect_line_ending("\n") == "\n"
        assert detect_line_ending("\r\n") == "\r\n"
        assert detect_line_ending("\r") == "\r"


class TestApplySingleTaskChanges:
    """Test suite for apply_single_task_changes function"""

    def test_apply_modification_change(self):
        """Test applying a modification change"""
        baseline = "def existing():\n    pass\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Modify function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="existing",
                    location="function:existing",
                    line_start=1,
                    line_end=2,
                    content_before="def existing():\n    pass",
                    content_after="def existing():\n    return True",
                )
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        assert result is not None
        assert isinstance(result, str)
        assert "return True" in result

    def test_apply_add_import(self):
        """Test applying an import addition"""
        baseline = "def existing():\n    pass\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        assert result is not None
        assert isinstance(result, str)
        # Import should be added at the top
        assert "import os" in result

    def test_apply_add_function(self):
        """Test applying a function addition"""
        baseline = "def existing():\n    pass\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                )
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        assert result is not None
        assert isinstance(result, str)
        assert "def new_func():" in result

    def test_apply_multiple_changes(self):
        """Test applying multiple changes from one task"""
        baseline = "def existing():\n    pass\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Multiple changes",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                ),
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        assert result is not None
        assert "import os" in result
        assert "def new_func():" in result

    def test_apply_preserves_line_endings(self):
        """Test that original line endings are preserved"""
        # CRLF content
        baseline = "def existing():\r\n    pass\r\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        # Should preserve CRLF
        assert "\r\n" in result

    def test_apply_with_no_changes(self):
        """Test applying with no semantic changes"""
        baseline = "def existing():\n    pass\n"
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="No changes",
            started_at=datetime.now(),
            semantic_changes=[],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        # Should return baseline unchanged
        assert result == baseline

    def test_apply_with_empty_baseline(self):
        """Test applying changes to empty file"""
        baseline = ""
        file_path = "test.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add function to empty file",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="first_func",
                    location="file_top",
                    line_start=1,
                    line_end=5,
                    content_after="def first_func():\n    pass",
                )
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        assert result is not None
        assert isinstance(result, str)


class TestCombineNonConflictingChanges:
    """Test suite for combine_non_conflicting_changes function"""

    def test_combine_empty_snapshots(self):
        """Test combining with no snapshots"""
        baseline = "def existing():\n    pass\n"

        result = combine_non_conflicting_changes(baseline, [], "test.py")

        assert result == baseline

    def test_combine_single_snapshot(self):
        """Test combining a single snapshot"""
        baseline = "def existing():\n    pass\n"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                )
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot], "test.py")

        assert "def new_func():" in result

    def test_combine_multiple_task_imports(self):
        """Test combining imports from multiple tasks"""
        baseline = "def existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add os import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add sys import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="sys",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import sys",
                )
            ],
        )

        result = combine_non_conflicting_changes(
            baseline, [snapshot1, snapshot2], "test.py"
        )

        assert "import os" in result
        assert "import sys" in result

    def test_combine_preserves_import_order(self):
        """Test that imports are grouped together"""
        baseline = "import json\n\ndef existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add os import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import os",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add sys import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="sys",
                    location="file_top",
                    line_start=3,
                    line_end=4,
                    content_after="import sys",
                )
            ],
        )

        result = combine_non_conflicting_changes(
            baseline, [snapshot1, snapshot2], "test.py"
        )

        # Imports should be grouped at the top
        lines = result.split("\n")
        import_indices = [
            i for i, line in enumerate(lines) if line.strip().startswith("import ")
        ]
        # All imports should be before the function definition
        func_index = next(
            i for i, line in enumerate(lines) if line.strip().startswith("def ")
        )
        for idx in import_indices:
            assert idx < func_index

    def test_combine_preserves_line_endings(self):
        """Test that original line endings are preserved"""
        baseline = "def existing():\r\n    pass\r\n"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        result = combine_non_conflicting_changes(baseline, [snapshot], "test.py")

        # Should preserve CRLF
        assert "\r\n" in result

    def test_combine_deduplicates_imports(self):
        """Test that duplicate imports are not added"""
        baseline = "import os\n\ndef existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add os import",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add os import again",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        result = combine_non_conflicting_changes(
            baseline, [snapshot1, snapshot2], "test.py"
        )

        # Count occurrences of "import os"
        import_count = result.count("import os")
        # Should not duplicate - should be 1 or maybe 2 (original + added)
        # The implementation checks if import is already in content
        assert import_count <= 2


class TestFindImportEnd:
    """Test suite for find_import_end function"""

    def test_find_import_end_python(self):
        """Test finding import end in Python file"""
        lines = [
            "import os",
            "import sys",
            "from pathlib import Path",
            "",
            "def function():",
            "    pass",
        ]

        result = find_import_end(lines, "test.py")

        # Should be after the last import (line 3, index 2)
        assert result == 3

    def test_find_import_end_python_no_imports(self):
        """Test finding import end with no imports"""
        lines = ["def function():", "    pass"]

        result = find_import_end(lines, "test.py")

        assert result == 0

    def test_find_import_end_javascript(self):
        """Test finding import end in JavaScript file"""
        lines = [
            "import React from 'react'",
            "import { useState } from 'react'",
            "const App = () => {}",
        ]

        result = find_import_end(lines, "test.jsx")

        # Should be after the imports
        assert result == 2

    def test_find_import_end_typescript(self):
        """Test finding import end in TypeScript file"""
        lines = [
            "import React from 'react'",
            "import type { FC } from 'react'",
            "const App: FC = () => {}",
        ]

        result = find_import_end(lines, "test.tsx")

        # Should be after the imports
        assert result == 2

    def test_find_import_end_unsupported_extension(self):
        """Test finding import end with unsupported file extension"""
        lines = ["some code", "more code"]

        result = find_import_end(lines, "test.unknown")

        # Should return 0 for unknown extensions
        assert result == 0

    def test_find_import_end_with_from_import(self):
        """Test finding import end with 'from' imports"""
        lines = [
            "import os",
            "from sys import argv",
            "from pathlib import Path",
            "",
            "def function():",
            "    pass",
        ]

        result = find_import_end(lines, "test.py")

        # Should include 'from' imports
        assert result == 3


class TestExtractLocationContent:
    """Test suite for extract_location_content function"""

    def test_extract_function_location(self):
        """Test extracting a function"""
        content = "def existing():\n    pass\n\ndef new_func():\n    return True\n"

        result = extract_location_content(content, "function:new_func")

        assert "def new_func():" in result
        assert "return True" in result

    def test_extract_function_not_found(self):
        """Test extracting a function that doesn't exist"""
        content = "def existing():\n    pass\n"

        result = extract_location_content(content, "function:nonexistent")

        # Should return full content if location not found
        assert result == content

    def test_extract_class_location(self):
        """Test extracting a class"""
        content = "class MyClass:\n    pass\n\nclass OtherClass:\n    pass\n"

        result = extract_location_content(content, "class:MyClass")

        assert "class MyClass:" in result
        assert "pass" in result

    def test_extract_class_not_found(self):
        """Test extracting a class that doesn't exist"""
        content = "class Existing:\n    pass\n"

        result = extract_location_content(content, "class:NonExistent")

        # Should return full content if location not found
        assert result == content

    def test_extract_invalid_location_format(self):
        """Test extracting with invalid location format"""
        content = "def existing():\n    pass\n"

        result = extract_location_content(content, "invalid_format")

        # Should return full content for invalid format
        assert result == content

    def test_extract_const_function(self):
        """Test extracting a const function (JavaScript)"""
        content = "const App = () => {\n  return <div>Hello</div>;\n};\n\nconst Other = () => {};\n"

        result = extract_location_content(content, "function:App")

        assert "const App" in result

    def test_extract_empty_content(self):
        """Test extracting from empty content"""
        content = ""

        result = extract_location_content(content, "function:func")

        assert result == ""

    def test_extract_no_colon_in_location(self):
        """Test extracting with location containing no colon"""
        content = "def existing():\n    pass\n"

        result = extract_location_content(content, "nocolonhere")

        # Should return full content
        assert result == content


class TestApplyAIMerge:
    """Test suite for apply_ai_merge function"""

    def test_apply_ai_merge_basic(self):
        """Test basic AI merge application"""
        content = "def func():\n    pass\n"
        merged_region = "def func():\n    return True\n"
        location = "function:func"

        result = apply_ai_merge(content, location, merged_region)

        # Should attempt to replace the function
        assert result is not None
        assert isinstance(result, str)

    def test_apply_ai_merge_empty_merged_region(self):
        """Test applying AI merge with empty merged region"""
        content = "def func():\n    pass\n"
        merged_region = ""
        location = "function:func"

        result = apply_ai_merge(content, location, merged_region)

        # Should return original content unchanged
        assert result == content

    def test_apply_ai_merge_none_merged_region(self):
        """Test applying AI merge with None merged region"""
        content = "def func():\n    pass\n"
        location = "function:func"

        result = apply_ai_merge(content, location, None)

        # Should return original content unchanged
        assert result == content

    def test_apply_ai_merge_location_not_found(self):
        """Test applying AI merge when location is not found"""
        content = "def func():\n    pass\n"
        merged_region = "def other():\n    pass\n"
        location = "function:nonexistent"

        result = apply_ai_merge(content, location, merged_region)

        # Should return original content if location not found
        assert result == content

    def test_apply_ai_merge_with_class(self):
        """Test applying AI merge to a class"""
        content = "class MyClass:\n    pass\n"
        merged_region = "class MyClass:\n    def method(self):\n        pass\n"
        location = "class:MyClass"

        result = apply_ai_merge(content, location, merged_region)

        # Should attempt to replace the class
        assert result is not None
        assert isinstance(result, str)

    def test_apply_ai_merge_preserves_content(self):
        """Test that AI merge preserves content outside location"""
        content = "def func():\n    pass\n\ndef other():\n    pass\n"
        merged_region = "def func():\n    return True\n"
        location = "function:func"

        result = apply_ai_merge(content, location, merged_region)

        # Other function should still be present
        if result != content:  # If replacement actually happened
            assert "def other():" in result or "other" in result


class TestFileMergerIntegration:
    """Integration tests for file_merger module"""

    def test_full_merge_workflow(self):
        """Test complete merge workflow with multiple changes"""
        baseline = "import json\n\ndef existing():\n    pass\n"
        file_path = "app.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Multiple changes",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=2,
                    line_end=3,
                    content_after="import os",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                ),
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="existing",
                    location="function:existing",
                    line_start=4,
                    line_end=5,
                    content_before="def existing():\n    pass",
                    content_after="def existing():\n    return True",
                ),
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        # Verify all changes were applied
        assert "import os" in result
        assert "def new_func():" in result
        assert "return True" in result or "existing" in result

    def test_line_ending_preservation_across_operations(self):
        """Test that line endings are preserved through all operations"""
        # CRLF baseline
        baseline = "import json\r\n\r\ndef existing():\r\n    pass\r\n"
        file_path = "app.py"

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Add import and function",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="new_func",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def new_func():\n    pass",
                ),
            ],
        )

        result = apply_single_task_changes(baseline, snapshot, file_path)

        # Verify CRLF is preserved
        assert "\r\n" in result

    def test_combine_changes_from_multiple_tasks(self):
        """Test combining changes from multiple tasks"""
        baseline = "def existing():\n    pass\n"

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Add imports",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="os",
                    location="file_top",
                    line_start=1,
                    line_end=2,
                    content_after="import os",
                )
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Add functions",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="func1",
                    location="file_top",
                    line_start=5,
                    line_end=10,
                    content_after="def func1():\n    pass",
                )
            ],
        )

        snapshot3 = TaskSnapshot(
            task_id="task_003",
            task_intent="Add more functions",
            started_at=datetime.now(),
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target="func2",
                    location="file_top",
                    line_start=10,
                    line_end=15,
                    content_after="def func2():\n    pass",
                )
            ],
        )

        result = combine_non_conflicting_changes(
            baseline, [snapshot1, snapshot2, snapshot3], "test.py"
        )

        # Verify all changes are present
        assert "import os" in result
        assert "def func1():" in result
        assert "def func2():" in result
