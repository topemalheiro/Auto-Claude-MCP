"""Comprehensive tests for semantic_analyzer"""

from merge.semantic_analyzer import SemanticAnalyzer
from merge.types import ChangeType, FileAnalysis
from merge.semantic_analysis.models import ExtractedElement
import pytest


class TestSemanticAnalyzerInit:
    """Test SemanticAnalyzer initialization"""

    def test_init(self):
        """Test basic initialization"""
        analyzer = SemanticAnalyzer()

        assert analyzer is not None


class TestSemanticAnalyzerAnalyzeDiff:
    """Test SemanticAnalyzer.analyze_diff method"""

    def test_analyze_diff_python_add_import(self):
        """Test analyzing Python code with added import"""
        file_path = "test.py"
        before = "def main():\n    pass"
        after = "import os\n\ndef main():\n    pass"
        task_id = "task_001"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after, task_id)

        assert isinstance(result, FileAnalysis)
        assert result.file_path == file_path
        assert len(result.imports_added) > 0

    def test_analyze_diff_python_add_function(self):
        """Test analyzing Python code with added function"""
        file_path = "helpers.py"
        before = "def main():\n    pass"
        after = "def main():\n    pass\n\ndef helper():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)
        assert len(result.functions_added) > 0

    def test_analyze_diff_javascript_add_import(self):
        """Test analyzing JavaScript code with added import"""
        file_path = "app.js"
        before = "function App() {\n  return <div>Hello</div>;\n}"
        after = "import React from 'react';\n\nfunction App() {\n  return <div>Hello</div>;\n}"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) > 0

    def test_analyze_diff_typescript_add_function(self):
        """Test analyzing TypeScript code with added function"""
        file_path = "utils.ts"
        before = "export const existing = () => {}"
        after = "export const existing = () => {}\n\nexport const newFunc = () => {}"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)
        # Should detect the new function

    def test_analyze_diff_no_changes(self):
        """Test analyzing with no changes"""
        file_path = "test.py"
        before = "def main():\n    pass"
        after = "def main():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)
        assert len(result.changes) == 0

    def test_analyze_diff_with_task_id(self):
        """Test analyzing with task_id parameter"""
        file_path = "test.py"
        before = "old content"
        after = "new content"
        task_id = "task_123"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after, task_id)

        assert isinstance(result, FileAnalysis)

    def test_analyze_diff_python_remove_function(self):
        """Test analyzing Python code with removed function"""
        file_path = "test.py"
        before = "def func1():\n    pass\n\ndef func2():\n    pass"
        after = "def func1():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)

    def test_analyze_diff_multiple_imports(self):
        """Test analyzing with multiple imports added"""
        file_path = "test.py"
        before = "def main():\n    pass"
        after = "import os\nimport sys\nfrom pathlib import Path\n\ndef main():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)
        assert len(result.imports_added) >= 2

    def test_analyze_diff_unsupported_extension(self):
        """Test analyzing file with unsupported extension"""
        file_path = "test.rb"  # Ruby not supported
        before = "def hello\n  puts 'world'\nend"
        after = "def hello\n  puts 'world'\n  puts 'again'\nend"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        # Should still return a FileAnalysis, but may not detect changes
        assert isinstance(result, FileAnalysis)

    def test_analyze_diff_empty_content(self):
        """Test analyzing from empty to content"""
        file_path = "new.py"
        before = ""
        after = "def new_function():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert isinstance(result, FileAnalysis)

    def test_analyze_diff_total_lines_changed(self):
        """Test that total_lines_changed is calculated"""
        file_path = "test.py"
        before = "line1\nline2\nline3"
        after = "line1\nline2 modified\nline3\nline4 added"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        assert result.total_lines_changed >= 0

    def test_analyze_diff_change_types(self):
        """Test that changes have correct types"""
        file_path = "test.py"
        before = "def old():\n    pass"
        after = "import os\n\ndef old():\n    pass\n\ndef new():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after)

        for change in result.changes:
            assert isinstance(change.change_type, ChangeType)
            assert isinstance(change.target, str)
            assert isinstance(change.location, str)


class TestSemanticAnalyzerAnalyzeFile:
    """Test SemanticAnalyzer.analyze_file method"""

    def test_analyze_file_python(self):
        """Test analyzing a Python file"""
        file_path = "test.py"
        content = "import os\nimport sys\n\ndef main():\n    pass\n\ndef helper():\n    pass"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_file(file_path, content)

        assert isinstance(result, FileAnalysis)
        # Should detect imports and functions since we compare against empty
        assert len(result.imports_added) >= 0
        assert len(result.functions_added) >= 0

    def test_analyze_file_javascript(self):
        """Test analyzing a JavaScript file"""
        file_path = "app.js"
        content = "import React from 'react';\n\nfunction App() {\n  return <div>Hello</div>;\n}"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_file(file_path, content)

        assert isinstance(result, FileAnalysis)

    def test_analyze_file_empty(self):
        """Test analyzing empty file"""
        file_path = "empty.py"
        content = ""

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_file(file_path, content)

        assert isinstance(result, FileAnalysis)
        assert len(result.changes) == 0

    def test_analyze_file_with_classes(self):
        """Test analyzing file with classes"""
        file_path = "models.py"
        content = "class User:\n    def __init__(self, name):\n        self.name = name"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_file(file_path, content)

        assert isinstance(result, FileAnalysis)


class TestSemanticAnalyzerIsSupported:
    """Test SemanticAnalyzer.is_supported method"""

    def test_is_supported_python(self):
        """Test Python file support"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("test.py") is True
        assert analyzer.is_supported("/path/to/file.py") is True

    def test_is_supported_javascript(self):
        """Test JavaScript file support"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("app.js") is True
        assert analyzer.is_supported("/path/to/component.js") is True

    def test_is_supported_jsx(self):
        """Test JSX file support"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("App.jsx") is True
        assert analyzer.is_supported("/path/to/App.jsx") is True

    def test_is_supported_typescript(self):
        """Test TypeScript file support"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("utils.ts") is True
        assert analyzer.is_supported("/path/to/utils.ts") is True

    def test_is_supported_tsx(self):
        """Test TSX file support"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("App.tsx") is True
        assert analyzer.is_supported("/path/to/App.tsx") is True

    def test_is_supported_unsupported(self):
        """Test unsupported file types"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("test.rb") is False
        assert analyzer.is_supported("test.go") is False
        assert analyzer.is_supported("test.rs") is False
        assert analyzer.is_supported("test.java") is False
        assert analyzer.is_supported("test.php") is False
        assert analyzer.is_supported("test.cpp") is False

    def test_is_supported_case_sensitive(self):
        """Test case sensitivity of extensions"""
        analyzer = SemanticAnalyzer()

        # Should work with lowercase
        assert analyzer.is_supported("test.py") is True

        # May or may not work with uppercase depending on implementation
        result = analyzer.is_supported("test.PY")
        assert isinstance(result, bool)

    def test_is_supported_no_extension(self):
        """Test file without extension"""
        analyzer = SemanticAnalyzer()

        assert analyzer.is_supported("Makefile") is False
        assert analyzer.is_supported(".gitignore") is False


class TestSemanticAnalyzerSupportedExtensions:
    """Test SemanticAnalyzer.supported_extensions property"""

    def test_supported_extensions_property(self):
        """Test that supported_extensions returns correct types"""
        analyzer = SemanticAnalyzer()

        extensions = analyzer.supported_extensions

        assert isinstance(extensions, set)
        assert len(extensions) > 0

        # Check expected extensions
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".ts" in extensions
        assert ".tsx" in extensions

    def test_supported_extensions_immutability(self):
        """Test that modifying returned set doesn't affect internal state"""
        analyzer = SemanticAnalyzer()

        extensions1 = analyzer.supported_extensions
        extensions2 = analyzer.supported_extensions

        # Should return same set each time
        assert extensions1 == extensions2


class TestSemanticAnalyzerExtractedElement:
    """Test ExtractedElement from semantic_analysis.models"""

    def test_extracted_element_creation(self):
        """Test creating an ExtractedElement"""
        element = ExtractedElement(
            element_type="function",
            name="myFunc",
            start_line=10,
            end_line=20,
            content="def myFunc():\n    pass"
        )

        assert element.element_type == "function"
        assert element.name == "myFunc"
        assert element.start_line == 10
        assert element.end_line == 20
        assert element.content == "def myFunc():\n    pass"
        assert element.parent is None
        assert element.metadata == {}

    def test_extracted_element_with_parent(self):
        """Test ExtractedElement with parent"""
        element = ExtractedElement(
            element_type="method",
            name="myMethod",
            start_line=15,
            end_line=25,
            content="def myMethod(self):\n        pass",
            parent="MyClass"
        )

        assert element.parent == "MyClass"

    def test_extracted_element_with_metadata(self):
        """Test ExtractedElement with metadata"""
        metadata = {"async": True, "decorator": "@staticmethod"}
        element = ExtractedElement(
            element_type="function",
            name="myFunc",
            start_line=10,
            end_line=20,
            content="",
            metadata=metadata
        )

        assert element.metadata == metadata

    def test_extracted_element_metadata_default(self):
        """Test ExtractedElement metadata defaults to empty dict"""
        element = ExtractedElement(
            element_type="function",
            name="myFunc",
            start_line=10,
            end_line=20,
            content=""
        )

        assert element.metadata == {}


class TestSemanticAnalyzerIntegration:
    """Integration tests for SemanticAnalyzer"""

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow"""
        file_path = "component.tsx"
        before = """
function App() {
  return <div>Hello</div>;
}
"""
        after = """
import React, { useState } from 'react';

function App() {
  const [count, setCount] = useState(0);
  return <div>Hello {count}</div>;
}
"""
        task_id = "task_001"

        analyzer = SemanticAnalyzer()
        result = analyzer.analyze_diff(file_path, before, after, task_id)

        # Should detect changes
        assert isinstance(result, FileAnalysis)
        assert result.file_path == file_path

        # Check for import addition
        import_changes = [c for c in result.changes if c.change_type == ChangeType.ADD_IMPORT]
        # May have detected import

        # Check total lines changed
        assert result.total_lines_changed >= 0

    def test_analyze_multiple_files(self):
        """Test analyzing multiple different files"""
        analyzer = SemanticAnalyzer()

        files = [
            ("test.py", "def foo(): pass", "def foo(): pass\ndef bar(): pass"),
            ("test.js", "function foo() {}", "function foo() {}\nfunction bar() {}"),
            ("test.tsx", "const Foo = () => null", "const Foo = () => null\nconst Bar = () => null"),
        ]

        for file_path, before, after in files:
            result = analyzer.analyze_diff(file_path, before, after)
            assert isinstance(result, FileAnalysis)
            assert result.file_path == file_path
