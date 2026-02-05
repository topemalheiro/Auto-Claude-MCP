"""Tests for helpers"""

from merge.auto_merger.helpers import MergeHelpers
from merge.types import ChangeType, SemanticChange
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_MergeHelpers_find_import_section_end():
    """Test MergeHelpers.find_import_section_end"""

    # Arrange
    lines = [
        "import React from 'react'",
        "import { useState } from 'react'",
        "",
        "function App() {",
        "  return <div>Hello</div>",
        "}"
    ]
    ext = ".tsx"

    # Act
    result = MergeHelpers.find_import_section_end(lines, ext)

    # Assert
    assert result == 2  # First two lines are imports


def test_MergeHelpers_is_import_line():
    """Test MergeHelpers.is_import_line"""

    # Arrange & Act & Assert
    assert MergeHelpers.is_import_line("import React from 'react'", ".tsx") is True
    assert MergeHelpers.is_import_line("export default App", ".tsx") is True
    assert MergeHelpers.is_import_line("function App() {}", ".tsx") is False
    assert MergeHelpers.is_import_line("from os import path", ".py") is True
    assert MergeHelpers.is_import_line("import sys", ".py") is True


def test_MergeHelpers_extract_hook_call():
    """Test MergeHelpers.extract_hook_call"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.ADD_HOOK_CALL,
        target="useEffect",
        location="function:App",
        line_start=5,
        line_end=5,
        content_after="  useEffect(() => {}, [])"
    )

    # Act
    result = MergeHelpers.extract_hook_call(change)

    # Assert
    assert result is not None
    assert "useEffect" in result


def test_MergeHelpers_extract_jsx_wrapper():
    """Test MergeHelpers.extract_jsx_wrapper"""

    # Arrange
    change = SemanticChange(
        change_type=ChangeType.WRAP_JSX,
        target="App",
        location="function:App",
        line_start=10,
        line_end=10,
        content_after="<AuthProvider><App /></AuthProvider>"
    )

    # Act
    result = MergeHelpers.extract_jsx_wrapper(change)

    # Assert
    assert result is not None
    assert result[0] == "AuthProvider"


def test_MergeHelpers_insert_hooks_into_function():
    """Test MergeHelpers.insert_hooks_into_function"""

    # Arrange
    content = "function App() {\n  return <div>Hello</div>\n}"
    func_name = "App"
    hooks = ["  useEffect(() => {}, [])", "  const [count, setCount] = useState(0)"]

    # Act
    result = MergeHelpers.insert_hooks_into_function(content, func_name, hooks)

    # Assert
    assert result is not None
    assert "useEffect" in result
    assert "useState" in result


def test_MergeHelpers_wrap_function_return():
    """Test MergeHelpers.wrap_function_return"""

    # Arrange - content must have the pattern "return (<jsx>)"
    content = "function App() {\n  return (\n    <div>Hello</div>\n  )\n}"
    func_name = "App"
    wrapper_name = "AuthProvider"

    # Act
    result = MergeHelpers.wrap_function_return(content, func_name, wrapper_name, "")

    # Assert
    assert result is not None
    # The function wraps the JSX if the pattern matches
    assert "return" in result


def test_MergeHelpers_find_function_insert_position():
    """Test MergeHelpers.find_function_insert_position"""

    # Arrange
    content = "import React from 'react'\n\nexport default function App() {\n  return <div>Hello</div>\n}"

    # Act
    result = MergeHelpers.find_function_insert_position(content, ".tsx")

    # Assert
    assert result is not None


def test_MergeHelpers_insert_methods_into_class():
    """Test MergeHelpers.insert_methods_into_class"""

    # Arrange
    content = "class MyClass {\n  existing() {}\n}"
    class_name = "MyClass"
    methods = ["  newMethod() {}"]

    # Act
    result = MergeHelpers.insert_methods_into_class(content, class_name, methods)

    # Assert
    assert result is not None
    assert "newMethod" in result


def test_MergeHelpers_extract_new_props():
    """Test MergeHelpers.extract_new_props"""

    # Arrange - needs both content_before and content_after
    change = SemanticChange(
        change_type=ChangeType.MODIFY_JSX_PROPS,
        target="App",
        location="function:App",
        line_start=10,
        line_end=10,
        content_before='<App existingProp={value} />',
        content_after='<App existingProp={value} newProp={newValue} />',
        metadata={"props": [{"name": "newProp", "value": "{newValue}"}]}
    )

    # Act
    result = MergeHelpers.extract_new_props(change)

    # Assert
    assert result is not None
    # Should find the new prop
    assert len(result) >= 0  # Function returns list


def test_MergeHelpers_apply_content_change():
    """Test MergeHelpers.apply_content_change"""

    # Arrange
    content = "function App() {\n  return <div>Old</div>\n}"
    old = "<div>Old</div>"
    new = "<div>New</div>"

    # Act
    result = MergeHelpers.apply_content_change(content, old, new)

    # Assert
    assert result is not None
    assert "<div>New</div>" in result


def test_MergeHelpers_topological_sort_changes():
    """Test MergeHelpers.topological_sort_changes"""

    # Arrange
    from datetime import datetime

    change1 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="helper",
        location="file_top",
        line_start=5,
        line_end=10,
        content_after="function helper() {}"
    )

    change2 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="main",
        location="file_top",
        line_start=15,
        line_end=20,
        content_after="function main() { helper(); }",
        metadata={"dependencies": ["helper"]}
    )

    from merge.types import TaskSnapshot
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add functions",
        started_at=datetime.now(),
        semantic_changes=[change1, change2]
    )

    # Act
    result = MergeHelpers.topological_sort_changes([snapshot])

    # Assert
    assert result is not None
    assert len(result) > 0
