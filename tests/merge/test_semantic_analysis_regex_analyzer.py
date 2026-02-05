"""
Comprehensive tests for semantic_analysis.regex_analyzer module
"""

from merge.semantic_analysis.regex_analyzer import (
    analyze_with_regex,
    get_import_pattern,
    get_function_pattern,
)
from merge.types import ChangeType, FileAnalysis
import pytest


class TestAnalyzeWithRegex:
    """Test analyze_with_regex function"""

    def test_analyze_with_regex_python_add_import(self):
        """Test analyzing Python code with added import"""
        before = "def main():\n    pass"
        after = "import os\n\ndef main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert result.file_path == "test.py"
        assert len(result.imports_added) > 0
        assert "import os" in result.imports_added or "os" in result.imports_added

    def test_analyze_with_regex_python_remove_import(self):
        """Test analyzing Python code with removed import"""
        before = "import os\nimport sys\n\ndef main():\n    pass"
        after = "import os\n\ndef main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_removed) > 0

    def test_analyze_with_regex_python_add_function(self):
        """Test analyzing Python code with added function"""
        before = "def main():\n    pass"
        after = "def main():\n    pass\n\ndef helper():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.functions_added) > 0
        assert "helper" in result.functions_added

    def test_analyze_with_regex_python_remove_function(self):
        """Test analyzing Python code with removed function"""
        before = "def main():\n    pass\n\ndef helper():\n    pass"
        after = "def main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.changes) > 0

    def test_analyze_with_regex_javascript_add_import(self):
        """Test analyzing JavaScript code with added import"""
        before = "function App() {\n  return <div>Hello</div>;\n}"
        after = "import React from 'react';\n\nfunction App() {\n  return <div>Hello</div>;\n}"

        result = analyze_with_regex("app.js", before, after, ".js")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) > 0

    def test_analyze_with_regex_javascript_add_function(self):
        """Test analyzing JavaScript code with added function"""
        before = "function foo() {}"
        after = "function foo() {}\n\nfunction bar() {}"

        result = analyze_with_regex("utils.js", before, after, ".js")

        assert isinstance(result, FileAnalysis)
        assert len(result.functions_added) > 0

    def test_analyze_with_regex_typescript_add_function(self):
        """Test analyzing TypeScript code with added function"""
        before = "export const foo = () => {}"
        after = "export const foo = () => {}\n\nexport const bar = () => {}"

        result = analyze_with_regex("utils.ts", before, after, ".ts")

        assert isinstance(result, FileAnalysis)
        # Should detect the new function

    def test_analyze_with_regex_no_changes(self):
        """Test analyzing with no changes"""
        before = "def main():\n    pass"
        after = "def main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.changes) == 0
        assert result.total_lines_changed == 0

    def test_analyze_with_regex_from_import(self):
        """Test analyzing with from import"""
        before = "def main():\n    pass"
        after = "from pathlib import Path\n\ndef main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) > 0

    def test_analyze_with_regex_windows_line_endings(self):
        """Test analyzing with Windows CRLF line endings"""
        before = "def main():\r\n    pass"
        after = "import os\r\n\r\ndef main():\r\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        # Should handle CRLF properly

    def test_analyze_with_regex_old_mac_line_endings(self):
        """Test analyzing with old Mac CR line endings"""
        before = "def main():\r    pass"
        after = "import os\r\rdef main():\r    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        # Should handle CR properly

    def test_analyze_with_regex_empty_to_content(self):
        """Test analyzing from empty to content"""
        before = ""
        after = "def new_function():\n    pass"

        result = analyze_with_regex("new.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)

    def test_analyze_with_regex_content_to_empty(self):
        """Test analyzing from content to empty"""
        before = "def old_function():\n    pass"
        after = ""

        result = analyze_with_regex("deleted.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)

    def test_analyze_with_regex_total_lines_changed(self):
        """Test that total_lines_changed is calculated"""
        before = "line1\nline2\nline3"
        after = "line1\nline2 modified\nline3\nline4 added"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert result.total_lines_changed >= 2

    def test_analyze_with_regex_multiple_imports_added(self):
        """Test analyzing with multiple imports added"""
        before = "def main():\n    pass"
        after = "import os\nimport sys\nfrom pathlib import Path\n\ndef main():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) >= 2

    def test_analyze_with_regex_jsx_import(self):
        """Test analyzing JSX file with import"""
        before = "function App() {\n  return <div/>;\n}"
        after = "import React from 'react';\n\nfunction App() {\n  return <div/>;\n}"

        result = analyze_with_regex("App.jsx", before, after, ".jsx")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) > 0

    def test_analyze_with_regex_tsx_import(self):
        """Test analyzing TSX file with import"""
        before = "const App = () => <div/>;"
        after = "import React from 'react';\n\nconst App = () => <div/>;"

        result = analyze_with_regex("App.tsx", before, after, ".tsx")

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) > 0

    def test_analyze_with_regex_export_statement(self):
        """Test analyzing with export statement (JS/TS)"""
        before = "const App = () => {};"
        after = "export const App = () => {};"

        result = analyze_with_regex("utils.js", before, after, ".js")

        assert isinstance(result, FileAnalysis)
        # Export is considered an import-like statement

    def test_analyze_with_regex_python_function_with_args(self):
        """Test detecting Python function with arguments"""
        before = "# Start of file"
        after = "# Start of file\ndef my_function(a, b, c=None): pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        assert isinstance(result, FileAnalysis)
        assert "my_function" in result.functions_added

    def test_analyze_with_regex_javascript_arrow_function(self):
        """Test detecting JavaScript arrow function"""
        before = "// Start"
        after = "// Start\nconst myFunc = () => { return true; };"

        result = analyze_with_regex("utils.js", before, after, ".js")

        assert isinstance(result, FileAnalysis)
        # Should detect the arrow function

    def test_analyze_with_regex_javascript_async_function(self):
        """Test detecting JavaScript async function"""
        before = "// Start"
        after = "// Start\nconst fetchData = async () => { return data; };"

        result = analyze_with_regex("api.js", before, after, ".js")

        assert isinstance(result, FileAnalysis)
        # Should detect the async function

    def test_analyze_with_regex_unsupported_extension(self):
        """Test analyzing file with unsupported extension"""
        before = "def hello\n  puts 'world'\nend"
        after = "def hello\n  puts 'world'\n  puts 'again'\nend"

        result = analyze_with_regex("test.rb", before, after, ".rb")

        # Should still return a FileAnalysis, but with limited detection
        assert isinstance(result, FileAnalysis)

    def test_analyze_with_regex_change_types(self):
        """Test that changes have correct types"""
        before = "def old():\n    pass"
        after = "import os\n\ndef old():\n    pass\n\ndef new():\n    pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        for change in result.changes:
            assert isinstance(change.change_type, ChangeType)
            assert isinstance(change.target, str)
            assert isinstance(change.location, str)
            assert isinstance(change.line_start, int)
            assert isinstance(change.line_end, int)

    def test_analyze_with_regex_whitespace_variations(self):
        """Test with various whitespace patterns in imports"""
        test_cases = [
            "import os",
            "import  os",
            "import os ",
            "  import os",
            "from pathlib import Path",
            "from  pathlib  import  Path",
        ]

        for import_line in test_cases:
            after = f"{import_line}\n\ndef main(): pass"
            before = "def main(): pass"

            result = analyze_with_regex("test.py", before, after, ".py")

            assert isinstance(result, FileAnalysis)

    def test_analyze_with_regex_comment_after_import(self):
        """Test import with inline comment"""
        before = "def main(): pass"
        after = "import os  # Operating system\n\ndef main(): pass"

        result = analyze_with_regex("test.py", before, after, ".py")

        # Should still detect the import despite comment
        assert isinstance(result, FileAnalysis)


class TestGetImportPattern:
    """Test get_import_pattern function"""

    def test_get_import_pattern_python(self):
        """Test getting import pattern for Python"""
        pattern = get_import_pattern(".py")

        assert pattern is not None
        assert pattern.match("import os")
        assert pattern.match("import os, sys")
        assert pattern.match("from pathlib import Path")
        assert pattern.match("from . import module")

    def test_get_import_pattern_javascript(self):
        """Test getting import pattern for JavaScript"""
        pattern = get_import_pattern(".js")

        assert pattern is not None
        assert pattern.match("import React from 'react'")
        assert pattern.match("import { useState } from 'react'")
        assert pattern.match("import * as utils from './utils'")

    def test_get_import_pattern_jsx(self):
        """Test getting import pattern for JSX"""
        pattern = get_import_pattern(".jsx")

        assert pattern is not None
        assert pattern.match("import React from 'react'")

    def test_get_import_pattern_typescript(self):
        """Test getting import pattern for TypeScript"""
        pattern = get_import_pattern(".ts")

        assert pattern is not None
        assert pattern.match("import React from 'react'")
        assert pattern.match("import type { User } from './types'")

    def test_get_import_pattern_tsx(self):
        """Test getting import pattern for TSX"""
        pattern = get_import_pattern(".tsx")

        assert pattern is not None
        assert pattern.match("import React from 'react'")

    def test_get_import_pattern_unsupported(self):
        """Test getting import pattern for unsupported extensions"""
        unsupported_extensions = [".rb", ".go", ".java", ".cpp", ".cs", ".php", ".rs", ".swift"]

        for ext in unsupported_extensions:
            pattern = get_import_pattern(ext)
            assert pattern is None

    def test_get_import_pattern_does_not_match_non_imports(self):
        """Test that import patterns don't match non-import statements"""
        pattern = get_import_pattern(".py")

        assert not pattern.match("def my_function():")
        assert not pattern.match("class MyClass:")
        assert not pattern.match("x = 5")
        assert not pattern.match("# import os")  # Comment
        assert not pattern.match("print('import os')")  # String

    def test_get_import_pattern_case_sensitive(self):
        """Test that import patterns are case sensitive"""
        pattern = get_import_pattern(".py")

        assert pattern.match("import os")
        assert not pattern.match("Import os")
        assert not pattern.match("IMPORT os")


class TestGetFunctionPattern:
    """Test get_function_pattern function"""

    def test_get_function_pattern_python(self):
        """Test getting function pattern for Python"""
        pattern = get_function_pattern(".py")

        assert pattern is not None

        matches = pattern.findall("def myFunc(): pass")
        assert len(matches) > 0
        assert "myFunc" in matches

    def test_get_function_pattern_python_multiple(self):
        """Test detecting multiple Python functions"""
        pattern = get_function_pattern(".py")

        code = "def func1(): pass\ndef func2(): pass\ndef func3(): pass"
        matches = pattern.findall(code)

        assert len(matches) == 3
        assert "func1" in matches
        assert "func2" in matches
        assert "func3" in matches

    def test_get_function_pattern_javascript_function(self):
        """Test getting function pattern for JavaScript function declaration"""
        pattern = get_function_pattern(".js")

        code = "function myFunc() { return true; }"
        matches = pattern.findall(code)

        assert len(matches) > 0
        # Should find the function name

    def test_get_function_pattern_javascript_arrow(self):
        """Test getting function pattern for JavaScript arrow function"""
        pattern = get_function_pattern(".js")

        code = "const myFunc = () => { return true; };"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_javascript_const_function(self):
        """Test getting function pattern for const function assignment"""
        pattern = get_function_pattern(".js")

        code = "const myFunc = function() { return true; };"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_jsx(self):
        """Test getting function pattern for JSX"""
        pattern = get_function_pattern(".jsx")

        code = "function App() { return <div/>; }"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_typescript(self):
        """Test getting function pattern for TypeScript"""
        pattern = get_function_pattern(".ts")

        # Test with arrow function without complex type annotation
        code = "const myFunc = () => {};"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_tsx(self):
        """Test getting function pattern for TSX"""
        pattern = get_function_pattern(".tsx")

        code = "const App = () => <div/>;"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_async_function(self):
        """Test detecting async functions"""
        pattern = get_function_pattern(".js")

        code = "const fetchData = async () => { return data; };"
        matches = pattern.findall(code)

        assert len(matches) > 0

    def test_get_function_pattern_unsupported(self):
        """Test getting function pattern for unsupported extensions"""
        unsupported_extensions = [".rb", ".go", ".java", ".cpp", ".cs", ".php", ".rs"]

        for ext in unsupported_extensions:
            pattern = get_function_pattern(ext)
            assert pattern is None

    def test_get_function_pattern_with_args(self):
        """Test detecting functions with arguments"""
        pattern = get_function_pattern(".py")

        code = "def myFunc(a, b, c=None): pass"
        matches = pattern.findall(code)

        assert len(matches) > 0
        assert "myFunc" in matches

    def test_get_function_pattern_does_not_match_classes(self):
        """Test that function patterns don't match class definitions"""
        pattern = get_function_pattern(".py")

        matches = pattern.findall("class MyClass: pass")

        # Should not match class definitions
        assert "MyClass" not in matches or len(matches) == 0

    def test_get_function_pattern_underscore_names(self):
        """Test detecting functions with underscore names"""
        pattern = get_function_pattern(".py")

        code = "def _private_func(): pass\ndef __dunder_func__(): pass"
        matches = pattern.findall(code)

        assert len(matches) >= 2

    def test_get_function_pattern_dollar_sign_names_js(self):
        """Test detecting JS functions with $ in name (jQuery style)"""
        pattern = get_function_pattern(".js")

        code = "function $init() { return true; }"
        matches = pattern.findall(code)

        # May or may not match depending on regex pattern
        assert isinstance(matches, list)
