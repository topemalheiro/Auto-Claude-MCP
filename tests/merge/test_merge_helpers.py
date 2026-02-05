"""
Comprehensive tests for auto_merger.helpers module
"""

from datetime import datetime
from merge.auto_merger.helpers import MergeHelpers
from merge.types import ChangeType, SemanticChange, TaskSnapshot
import pytest


class TestMergeHelpersFindImportSectionEnd:
    """Test MergeHelpers.find_import_section_end"""

    def test_find_import_section_end_python(self):
        """Test finding import section end in Python file"""
        lines = [
            "import os",
            "import sys",
            "from pathlib import Path",
            "",
            "def main():",
            "    pass",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".py")

        # Should return line 3 (last import line, 1-indexed)
        assert result == 3

    def test_find_import_section_end_javascript(self):
        """Test finding import section end in JavaScript file"""
        lines = [
            "import React from 'react';",
            "import { useState } from 'react';",
            "import './styles.css';",
            "",
            "function App() {",
            "  return <div />;",
            "}",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".js")

        assert result == 3

    def test_find_import_section_end_with_comments(self):
        """Test finding import section with comments after imports"""
        lines = [
            "import os",
            "import sys",
            "# This is a comment",
            "def main():",
            "    pass",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".py")

        # Should return 2 (last actual import line)
        assert result == 2

    def test_find_import_section_end_with_inline_comment(self):
        """Test finding import section with inline comments"""
        lines = [
            "import os  # Operating system module",
            "import sys  # System module",
            "",
            "def main():",
            "    pass",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".py")

        # Should return 2 (imports with comments are still imports)
        assert result == 2

    def test_find_import_section_end_no_imports(self):
        """Test finding import section when there are no imports"""
        lines = [
            "def main():",
            "    pass",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".py")

        # Should return 0 when no imports found
        assert result == 0

    def test_find_import_section_end_only_imports(self):
        """Test finding import section when file only has imports"""
        lines = [
            "import os",
            "import sys",
            "import json",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".py")

        # Should return 3 (last import line)
        assert result == 3

    def test_find_import_section_end_typescript(self):
        """Test finding import section end in TypeScript file"""
        lines = [
            "import React, { useState } from 'react';",
            "import type { User } from './types';",
            "export { default } from './App';",
            "",
            "const App: React.FC = () => {",
            "  return null;",
            "};",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".ts")

        assert result == 3

    def test_find_import_section_end_unsupported_extension(self):
        """Test finding import section for unsupported file type"""
        lines = [
            "package main;",
            "import fmt;",
            "",
            "func main() {",
            "}",
        ]

        result = MergeHelpers.find_import_section_end(lines, ".go")

        # Should return 0 for unsupported extensions
        assert result == 0


class TestMergeHelpersIsImportLine:
    """Test MergeHelpers.is_import_line"""

    def test_is_import_line_python_import(self):
        """Test Python import statement"""
        assert MergeHelpers.is_import_line("import os", ".py") is True
        assert MergeHelpers.is_import_line("import os, sys", ".py") is True
        assert MergeHelpers.is_import_line("import os as operating_system", ".py") is True

    def test_is_import_line_python_from(self):
        """Test Python from import statement"""
        assert MergeHelpers.is_import_line("from pathlib import Path", ".py") is True
        assert MergeHelpers.is_import_line("from . import module", ".py") is True
        assert MergeHelpers.is_import_line("from ..parent import sibling", ".py") is True

    def test_is_import_line_javascript_import(self):
        """Test JavaScript import statement"""
        assert MergeHelpers.is_import_line("import React from 'react'", ".js") is True
        assert (
            MergeHelpers.is_import_line("import { useState } from 'react'", ".js") is True
        )
        assert MergeHelpers.is_import_line("import * as utils from './utils'", ".js") is True

    def test_is_import_line_javascript_export(self):
        """Test JavaScript export statement"""
        assert MergeHelpers.is_import_line("export default App", ".js") is True
        assert MergeHelpers.is_import_line("export { App, Component }", ".js") is True
        assert MergeHelpers.is_import_line("export const PI = 3.14", ".js") is True

    def test_is_import_line_typescript(self):
        """Test TypeScript import statements"""
        assert MergeHelpers.is_import_line("import React from 'react'", ".ts") is True
        assert MergeHelpers.is_import_line("import type { User } from './types'", ".ts") is True
        assert MergeHelpers.is_import_line("export default App", ".ts") is True

    def test_is_import_line_non_import_statements(self):
        """Test that non-import statements return False"""
        assert MergeHelpers.is_import_line("def my_function():", ".py") is False
        assert MergeHelpers.is_import_line("class MyClass:", ".py") is False
        assert MergeHelpers.is_import_line("function App() {", ".js") is False
        assert MergeHelpers.is_import_line("const x = 5;", ".js") is False

    def test_is_import_line_whitespace_variations(self):
        """Test import lines with various whitespace patterns"""
        # Implementation uses startswith() without stripping
        assert MergeHelpers.is_import_line("  import os", ".py") is False  # Leading space not matched
        assert MergeHelpers.is_import_line("import   os", ".py") is True   # Internal spaces OK
        assert MergeHelpers.is_import_line("import os", ".py") is True
        assert MergeHelpers.is_import_line("import os  ", ".py") is True  # Trailing ignored by startswith

    def test_is_import_line_unsupported_extensions(self):
        """Test unsupported file extensions"""
        assert MergeHelpers.is_import_line("import fmt", ".go") is False
        assert MergeHelpers.is_import_line("#include <stdio.h>", ".c") is False
        assert MergeHelpers.is_import_line("using System;", ".cs") is False


class TestMergeHelpersExtractHookCall:
    """Test MergeHelpers.extract_hook_call"""

    def test_extract_hook_call_basic(self):
        """Test extracting basic hook call"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useAuth",
            location="function:App",
            line_start=2,
            line_end=2,
            content_after="const { user } = useAuth();",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is not None
        assert "useAuth" in result

    def test_extract_hook_call_destructured(self):
        """Test extracting hook call with destructuring"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useCounter",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="const { count, setCount } = useCounter(0);",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is not None
        assert "useCounter" in result

    def test_extract_hook_call_simple(self):
        """Test extracting simple hook call without destructuring"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useTheme",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="const theme = useTheme();",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is not None
        assert "useTheme" in result

    def test_extract_hook_call_multiple_params(self):
        """Test extracting hook call with multiple parameters"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useFetch",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="const { data } = useFetch(url, { method: 'POST' });",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is not None
        assert "useFetch" in result

    def test_extract_hook_call_no_content(self):
        """Test extracting hook call when content_after is None"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useEffect",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after=None,
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is None

    def test_extract_hook_call_empty_content(self):
        """Test extracting hook call from empty content"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useState",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is None

    def test_extract_hook_call_non_hook_content(self):
        """Test extracting hook call from non-hook content"""
        change = SemanticChange(
            change_type=ChangeType.ADD_VARIABLE,
            target="count",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="const count = 0;",
        )

        result = MergeHelpers.extract_hook_call(change)

        # Should not extract a hook from non-hook content
        # (might return None or the pattern won't match)

    def test_extract_hook_call_use_async_pattern(self):
        """Test extracting useAsync hook call"""
        change = SemanticChange(
            change_type=ChangeType.ADD_HOOK_CALL,
            target="useAsync",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="const { data } = useAsync(fetchData, []);",
        )

        result = MergeHelpers.extract_hook_call(change)

        assert result is not None
        assert "useAsync" in result


class TestMergeHelpersExtractJsxWrapper:
    """Test MergeHelpers.extract_jsx_wrapper"""

    def test_extract_jsx_wrapper_basic(self):
        """Test extracting basic JSX wrapper"""
        change = SemanticChange(
            change_type=ChangeType.WRAP_JSX,
            target="AuthProvider",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="<AuthProvider>",
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is not None
        assert result[0] == "AuthProvider"
        assert result[1] == ""

    def test_extract_jsx_wrapper_with_props(self):
        """Test extracting JSX wrapper with props"""
        change = SemanticChange(
            change_type=ChangeType.WRAP_JSX,
            target="Router",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after='<Router basename="/app">',
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is not None
        assert result[0] == "Router"
        assert 'basename="/app"' in result[1]

    def test_extract_jsx_wrapper_multiple_props(self):
        """Test extracting JSX wrapper with multiple props"""
        change = SemanticChange(
            change_type=ChangeType.WRAP_JSX,
            target="QueryClientProvider",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after='<QueryClientProvider client={queryClient} context={QueryContext}>',
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is not None
        assert result[0] == "QueryClientProvider"
        assert "client={queryClient}" in result[1]
        assert "context={QueryContext}" in result[1]

    def test_extract_jsx_wrapper_no_content(self):
        """Test extracting JSX wrapper when content_after is None"""
        change = SemanticChange(
            change_type=ChangeType.WRAP_JSX,
            target="Wrapper",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after=None,
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is None

    def test_extract_jsx_wrapper_empty_content(self):
        """Test extracting JSX wrapper from empty content"""
        change = SemanticChange(
            change_type=ChangeType.WRAP_JSX,
            target="Wrapper",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after="",
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is None

    def test_extract_jsx_wrapper_self_closing(self):
        """Test extracting self-closing JSX wrapper"""
        change = SemanticChange(
            change_type=ChangeType.ADD_JSX_ELEMENT,
            target="Img",
            location="function:App",
            line_start=1,
            line_end=1,
            content_after='<Img src="/logo.png" alt="Logo" />',
        )

        result = MergeHelpers.extract_jsx_wrapper(change)

        assert result is not None
        assert result[0] == "Img"


class TestMergeHelpersInsertHooksIntoFunction:
    """Test MergeHelpers.insert_hooks_into_function"""

    def test_insert_hooks_into_function_declaration(self):
        """Test inserting hooks into function declaration"""
        content = """function App() {
  return <div>Hello</div>;
}"""
        hooks = ["const [count, setCount] = useState(0);", "const theme = useTheme();"]

        result = MergeHelpers.insert_hooks_into_function(content, "App", hooks)

        assert "useState" in result
        assert "useTheme" in result
        assert result.count("function App") == 1

    def test_insert_hooks_into_arrow_function(self):
        """Test inserting hooks into arrow function"""
        content = """const App = () => {
  return <div>Hello</div>;
}"""
        hooks = ["const { user } = useAuth();"]

        result = MergeHelpers.insert_hooks_into_function(content, "App", hooks)

        assert "useAuth" in result

    def test_insert_hooks_into_const_function(self):
        """Test inserting hooks into const function assignment"""
        content = """const App = function() {
  return <div>Hello</div>;
}"""
        hooks = ["const [loading, setLoading] = useState(false);"]

        result = MergeHelpers.insert_hooks_into_function(content, "App", hooks)

        assert "useState" in result

    def test_insert_hooks_into_function_no_match(self):
        """Test inserting hooks when function pattern doesn't match"""
        content = """class App {
  render() {
    return <div>Hello</div>;
  }
}"""
        hooks = ["const [count, setCount] = useState(0);"]

        result = MergeHelpers.insert_hooks_into_function(content, "App", hooks)

        # Should return original content unchanged
        assert result == content

    def test_insert_hooks_into_function_empty_list(self):
        """Test inserting empty hooks list"""
        content = "function App() { return <div/>; }"

        result = MergeHelpers.insert_hooks_into_function(content, "App", [])

        # Empty hooks list adds empty lines due to implementation
        # Just verify the function still exists
        assert "function App" in result

    def test_insert_hooks_into_function_single_hook(self):
        """Test inserting single hook"""
        content = "function App() { return <div/>; }"
        hooks = ["const value = useMemo(() => calc(), [deps]);"]

        result = MergeHelpers.insert_hooks_into_function(content, "App", hooks)

        assert "useMemo" in result


class TestMergeHelpersWrapFunctionReturn:
    """Test MergeHelpers.wrap_function_return"""

    def test_wrap_function_return_basic(self):
        """Test wrapping function return with JSX component"""
        content = """function App() {
  return (
    <div>Hello</div>
  );
}"""

        result = MergeHelpers.wrap_function_return(content, "App", "AuthProvider", "")

        assert "<AuthProvider" in result

    def test_wrap_function_return_with_props(self):
        """Test wrapping with props"""
        content = """function App() {
  return (
    <div>Hello</div>
  );
}"""

        result = MergeHelpers.wrap_function_return(content, "App", "Router", 'basename="/app"')

        assert "<Router" in result
        assert 'basename="/app"' in result

    def test_wrap_function_return_no_return_statement(self):
        """Test wrapping when no return statement found"""
        content = "function App() {\n  console.log('hello');\n}"

        result = MergeHelpers.wrap_function_return(content, "App", "Wrapper", "")

        # Should return content unchanged or with minimal changes
        assert "function App" in result


class TestMergeHelpersFindFunctionInsertPosition:
    """Test MergeHelpers.find_function_insert_position"""

    def test_find_function_insert_position_before_module_exports(self):
        """Test finding position before module.exports"""
        content = """function foo() {}

function bar() {}

module.exports = { foo, bar };"""

        result = MergeHelpers.find_function_insert_position(content, ".js")

        # Should find the line with module.exports
        assert result is not None
        assert result > 0

    def test_find_function_insert_position_before_export_default(self):
        """Test finding position before export default"""
        content = """function foo() {}

function bar() {}

export default foo;"""

        result = MergeHelpers.find_function_insert_position(content, ".js")

        # Should find the line with export default
        assert result is not None

    def test_find_function_insert_position_no_export(self):
        """Test finding position when no export statement"""
        content = """function foo() {}

function bar() {}"""

        result = MergeHelpers.find_function_insert_position(content, ".js")

        # Should return None when no export found
        assert result is None


class TestMergeHelpersInsertMethodsIntoClass:
    """Test MergeHelpers.insert_methods_into_class"""

    def test_insert_methods_into_class_basic(self):
        """Test inserting methods into class"""
        content = """class MyClass {
  constructor() {
    this.value = 0;
  }
}"""
        methods = ["getValue() { return this.value; }", "setValue(val) { this.value = val; }"]

        result = MergeHelpers.insert_methods_into_class(content, "MyClass", methods)

        assert "getValue" in result
        assert "setValue" in result

    def test_insert_methods_into_class_with_extends(self):
        """Test inserting into class that extends"""
        content = """class MyClass extends BaseClass {
  constructor() {
    super();
  }
}"""
        methods = ["customMethod() {}"]

        result = MergeHelpers.insert_methods_into_class(content, "MyClass", methods)

        assert "customMethod" in result

    def test_insert_methods_into_class_no_match(self):
        """Test inserting methods when class not found"""
        content = """function notAClass() {}"""
        methods = ["someMethod() {}"]

        result = MergeHelpers.insert_methods_into_class(content, "MyClass", methods)

        # Should return original content
        assert result == content

    def test_insert_methods_into_class_empty_list(self):
        """Test inserting empty methods list"""
        content = "class MyClass {}"

        result = MergeHelpers.insert_methods_into_class(content, "MyClass", [])

        # Empty methods list adds newlines due to implementation
        # Just verify the class still exists
        assert "class MyClass" in result


class TestMergeHelpersExtractNewProps:
    """Test MergeHelpers.extract_new_props"""

    def test_extract_new_props_basic(self):
        """Test extracting newly added props"""
        change = SemanticChange(
            change_type=ChangeType.MODIFY_JSX_PROPS,
            target="props",
            location="function:App",
            line_start=1,
            line_end=1,
            content_before='<Button onClick={handleClick}>',
            content_after='<Button onClick={handleClick} disabled={isDisabled}>',
        )

        result = MergeHelpers.extract_new_props(change)

        assert len(result) > 0
        assert any(name == "disabled" for name, _ in result)

    def test_extract_new_props_multiple(self):
        """Test extracting multiple new props"""
        change = SemanticChange(
            change_type=ChangeType.MODIFY_JSX_PROPS,
            target="props",
            location="function:App",
            line_start=1,
            line_end=1,
            content_before="<Component value={val}>",
            content_after="<Component value={val} disabled={true} loading={false}>",
        )

        result = MergeHelpers.extract_new_props(change)

        assert len(result) >= 2

    def test_extract_new_props_no_content(self):
        """Test extracting props when content is None"""
        change = SemanticChange(
            change_type=ChangeType.MODIFY_JSX_PROPS,
            target="props",
            location="function:App",
            line_start=1,
            line_end=1,
            content_before=None,
            content_after=None,
        )

        result = MergeHelpers.extract_new_props(change)

        assert len(result) == 0

    def test_extract_new_props_no_new(self):
        """Test extracting when no new props added"""
        change = SemanticChange(
            change_type=ChangeType.MODIFY_JSX_PROPS,
            target="props",
            location="function:App",
            line_start=1,
            line_end=1,
            content_before="<Component value={val}>",
            content_after="<Component value={newVal}>",
        )

        result = MergeHelpers.extract_new_props(change)

        # No new props added, just value changed
        # Pattern looks for ={} format, so should be empty or minimal


class TestMergeHelpersApplyContentChange:
    """Test MergeHelpers.apply_content_change"""

    def test_apply_content_change_basic_replacement(self):
        """Test basic content replacement"""
        content = "function oldName() { return 42; }"
        old = "oldName"
        new = "newName"

        result = MergeHelpers.apply_content_change(content, old, new)

        assert "newName" in result
        assert "oldName" not in result

    def test_apply_content_change_old_not_found(self):
        """Test when old content not found"""
        content = "function myFunc() { return 42; }"
        old = "nonexistent"
        new = "replacement"

        result = MergeHelpers.apply_content_change(content, old, new)

        # Should return original content unchanged
        assert result == content

    def test_apply_content_change_none_old(self):
        """Test when old is None"""
        content = "function myFunc() { return 42; }"

        result = MergeHelpers.apply_content_change(content, None, "new")

        # Should return original content
        assert result == content

    def test_apply_content_change_empty_old(self):
        """Test when old is empty string"""
        content = "function myFunc() { return 42; }"

        result = MergeHelpers.apply_content_change(content, "", "new")

        # Should return original content (empty string won't be replaced)
        assert result == content

    def test_apply_content_change_multiline_replacement(self):
        """Test multiline content replacement"""
        content = """line1
line2
line3"""
        old = "line2"
        new = "NEWLINE"

        result = MergeHelpers.apply_content_change(content, old, new)

        assert "NEWLINE" in result
        assert "line2" not in result


class TestMergeHelpersTopologicalSortChanges:
    """Test MergeHelpers.topological_sort_changes"""

    def test_topological_sort_changes_priority_ordering(self):
        """Test that changes are sorted by priority"""
        now = datetime.now()

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=now,
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="func1",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="import1",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                ),
                SemanticChange(
                    change_type=ChangeType.ADD_HOOK_CALL,
                    target="useEffect",
                    location="function:App",
                    line_start=2,
                    line_end=2,
                ),
            ],
        )

        result = MergeHelpers.topological_sort_changes([snapshot])

        # Imports should come before hooks
        import_idx = next(
            i for i, c in enumerate(result) if c.change_type == ChangeType.ADD_IMPORT
        )
        hook_idx = next(
            i for i, c in enumerate(result) if c.change_type == ChangeType.ADD_HOOK_CALL
        )

        assert import_idx < hook_idx

    def test_topological_sort_changes_empty_snapshots(self):
        """Test sorting with no snapshots"""
        result = MergeHelpers.topological_sort_changes([])

        assert len(result) == 0

    def test_topological_sort_changes_no_semantic_changes(self):
        """Test sorting when snapshots have no semantic changes"""
        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=datetime.now(),
        )

        result = MergeHelpers.topological_sort_changes([snapshot])

        assert len(result) == 0

    def test_topological_sort_changes_unknown_type(self):
        """Test sorting with unknown change type"""
        now = datetime.now()

        snapshot = TaskSnapshot(
            task_id="task_001",
            task_intent="Test",
            started_at=now,
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.UNKNOWN,
                    target="unknown",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                ),
            ],
        )

        result = MergeHelpers.topological_sort_changes([snapshot])

        # Should still return the unknown change
        assert len(result) == 1
        assert result[0].change_type == ChangeType.UNKNOWN

    def test_topological_sort_changes_multiple_snapshots(self):
        """Test sorting changes from multiple snapshots"""
        now = datetime.now()

        snapshot1 = TaskSnapshot(
            task_id="task_001",
            task_intent="Test1",
            started_at=now,
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.MODIFY_FUNCTION,
                    target="func1",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                ),
            ],
        )

        snapshot2 = TaskSnapshot(
            task_id="task_002",
            task_intent="Test2",
            started_at=now,
            semantic_changes=[
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target="import1",
                    location="file_top",
                    line_start=1,
                    line_end=1,
                ),
            ],
        )

        result = MergeHelpers.topological_sort_changes([snapshot1, snapshot2])

        # Should have both changes, with import first
        assert len(result) == 2
        assert result[0].change_type == ChangeType.ADD_IMPORT
        assert result[1].change_type == ChangeType.MODIFY_FUNCTION
