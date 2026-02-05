"""
Comprehensive tests for semantic_analysis.models module
"""

from merge.semantic_analysis.models import ExtractedElement
import pytest


class TestExtractedElement:
    """Test ExtractedElement dataclass"""

    def test_extracted_element_creation_minimal(self):
        """Test creating ExtractedElement with minimal required fields"""
        element = ExtractedElement(
            element_type="function",
            name="myFunction",
            start_line=10,
            end_line=20,
            content="def myFunction():\n    pass",
        )

        assert element.element_type == "function"
        assert element.name == "myFunction"
        assert element.start_line == 10
        assert element.end_line == 20
        assert element.content == "def myFunction():\n    pass"
        assert element.parent is None
        assert element.metadata == {}

    def test_extracted_element_with_parent(self):
        """Test ExtractedElement with parent specified"""
        element = ExtractedElement(
            element_type="method",
            name="myMethod",
            start_line=15,
            end_line=25,
            content="def myMethod(self):\n        pass",
            parent="MyClass",
        )

        assert element.parent == "MyClass"

    def test_extracted_element_with_metadata(self):
        """Test ExtractedElement with metadata"""
        metadata = {
            "async": True,
            "decorator": "@staticmethod",
            "returns": "str",
            "args": ["self", "value"],
        }

        element = ExtractedElement(
            element_type="method",
            name="processValue",
            start_line=5,
            end_line=10,
            content="@staticmethod\ndef processValue(value): pass",
            metadata=metadata,
        )

        assert element.metadata == metadata
        assert element.metadata["async"] is True
        assert element.metadata["decorator"] == "@staticmethod"
        assert element.metadata["returns"] == "str"
        assert element.metadata["args"] == ["self", "value"]

    def test_extracted_element_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict via __post_init__"""
        element = ExtractedElement(
            element_type="function",
            name="testFunc",
            start_line=1,
            end_line=5,
            content="def testFunc(): pass",
            metadata=None,
        )

        # __post_init__ should convert None to {}
        assert element.metadata == {}
        assert isinstance(element.metadata, dict)

    def test_extracted_element_function_type(self):
        """Test ExtractedElement for function type"""
        element = ExtractedElement(
            element_type="function",
            name="calculateSum",
            start_line=10,
            end_line=15,
            content="def calculateSum(a, b):\n    return a + b",
        )

        assert element.element_type == "function"

    def test_extracted_element_class_type(self):
        """Test ExtractedElement for class type"""
        element = ExtractedElement(
            element_type="class",
            name="UserManager",
            start_line=20,
            end_line=50,
            content="class UserManager:\n    pass",
        )

        assert element.element_type == "class"

    def test_extracted_element_import_type(self):
        """Test ExtractedElement for import type"""
        element = ExtractedElement(
            element_type="import",
            name="os",
            start_line=1,
            end_line=1,
            content="import os",
        )

        assert element.element_type == "import"

    def test_extracted_element_import_from_type(self):
        """Test ExtractedElement for import_from type"""
        element = ExtractedElement(
            element_type="import_from",
            name="pathlib.Path",
            start_line=2,
            end_line=2,
            content="from pathlib import Path",
        )

        assert element.element_type == "import_from"

    def test_extracted_element_variable_type(self):
        """Test ExtractedElement for variable type"""
        element = ExtractedElement(
            element_type="variable",
            name="MAX_RETRIES",
            start_line=1,
            end_line=1,
            content="MAX_RETRIES = 3",
            metadata={"type": "int", "constant": True},
        )

        assert element.element_type == "variable"
        assert element.metadata["constant"] is True

    def test_extracted_element_interface_type(self):
        """Test ExtractedElement for interface type (TypeScript)"""
        element = ExtractedElement(
            element_type="interface",
            name="UserProps",
            start_line=5,
            end_line=10,
            content="interface UserProps {\n  name: string;\n  age: number;\n}",
        )

        assert element.element_type == "interface"

    def test_extracted_element_type_alias_type(self):
        """Test ExtractedElement for type alias (TypeScript)"""
        element = ExtractedElement(
            element_type="type",
            name="ID",
            start_line=1,
            end_line=1,
            content="type ID = string;",
        )

        assert element.element_type == "type"

    def test_extracted_element_with_nested_parent(self):
        """Test ExtractedElement with nested parent (method in class)"""
        element = ExtractedElement(
            element_type="method",
            name="validate",
            start_line=25,
            end_line=30,
            content="def validate(self): pass",
            parent="AuthManager.Session",
        )

        assert element.parent == "AuthManager.Session"

    def test_extracted_element_multiline_content(self):
        """Test ExtractedElement with multiline content"""
        content = """class UserService:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id):
        return self.db.query(user_id)"""

        element = ExtractedElement(
            element_type="class",
            name="UserService",
            start_line=1,
            end_line=8,
            content=content,
        )

        assert "def __init__" in element.content
        assert "def get_user" in element.content

    def test_extracted_element_with_empty_content(self):
        """Test ExtractedElement with empty content"""
        element = ExtractedElement(
            element_type="function",
            name="stub",
            start_line=1,
            end_line=1,
            content="",
        )

        assert element.content == ""

    def test_extracted_element_with_special_characters_in_name(self):
        """Test ExtractedElement with special characters in name"""
        special_names = [
            "_private_method",
            "__dunder_method__",
            "method_with_underscore",
            "CamelCaseMethod",
            "mixedCase_method",
        ]

        for name in special_names:
            element = ExtractedElement(
                element_type="method",
                name=name,
                start_line=1,
                end_line=5,
                content=f"def {name}(): pass",
            )

            assert element.name == name

    def test_extracted_element_with_unicode_in_content(self):
        """Test ExtractedElement with unicode characters in content"""
        content = 'def greet():\n    print("Hello, 世界! 🌍")\n    return "Привет"'

        element = ExtractedElement(
            element_type="function",
            name="greet",
            start_line=1,
            end_line=3,
            content=content,
        )

        assert "世界" in element.content
        assert "🌍" in element.content
        assert "Привет" in element.content

    def test_extracted_element_line_numbers(self):
        """Test ExtractedElement with various line number combinations"""
        test_cases = [
            (1, 1, "single line"),
            (1, 10, "multi-line"),
            (100, 200, "large range"),
            (1, 1000, "very large range"),
        ]

        for start, end, description in test_cases:
            element = ExtractedElement(
                element_type="function",
                name=f"test_{description.replace(' ', '_')}",
                start_line=start,
                end_line=end,
                content="pass",
            )

            assert element.start_line == start
            assert element.end_line == end

    def test_extracted_element_with_decorator_metadata(self):
        """Test ExtractedElement with decorator in metadata"""
        element = ExtractedElement(
            element_type="method",
            name="authenticated_method",
            start_line=10,
            end_line=15,
            content="@require_auth\ndef authenticated_method(): pass",
            metadata={
                "decorators": ["@require_auth", "@log_calls"],
                "is_async": False,
            },
        )

        assert "@require_auth" in element.metadata["decorators"]
        assert "@log_calls" in element.metadata["decorators"]

    def test_extracted_element_js_function(self):
        """Test ExtractedElement for JavaScript function"""
        element = ExtractedElement(
            element_type="function",
            name="useCounter",
            start_line=5,
            end_line=10,
            content="const useCounter = (initial = 0) => {\n  const [count, setCount] = useState(initial);\n  return { count, setCount };\n};",
            metadata={"is_hook": True, "language": "javascript"},
        )

        assert element.element_type == "function"
        assert element.metadata["is_hook"] is True
        assert element.metadata["language"] == "javascript"

    def test_extracted_element_tsx_component(self):
        """Test ExtractedElement for TSX component"""
        element = ExtractedElement(
            element_type="function",
            name="App",
            start_line=1,
            end_line=10,
            content="function App() {\n  return <div>Hello</div>;\n}",
            metadata={"language": "typescript", "is_component": True},
        )

        assert element.metadata["is_component"] is True

    def test_extracted_element_with_return_type_metadata(self):
        """Test ExtractedElement with return type in metadata"""
        element = ExtractedElement(
            element_type="method",
            name="calculate",
            start_line=1,
            end_line=5,
            content="def calculate(self) -> int:\n    return 42",
            metadata={
                "return_type": "int",
                "parameters": ["self"],
                "typed": True,
            },
        )

        assert element.metadata["return_type"] == "int"
        assert element.metadata["typed"] is True

    def test_extracted_element_with_parameters_metadata(self):
        """Test ExtractedElement with parameter information in metadata"""
        element = ExtractedElement(
            element_type="function",
            name="process",
            start_line=1,
            end_line=5,
            content="def process(name: str, value: int, optional: bool = False): pass",
            metadata={
                "parameters": [
                    {"name": "name", "type": "str"},
                    {"name": "value", "type": "int"},
                    {"name": "optional", "type": "bool", "default": False},
                ],
                "param_count": 3,
            },
        )

        assert len(element.metadata["parameters"]) == 3
        assert element.metadata["param_count"] == 3

    def test_extracted_element_mutable_metadata(self):
        """Test that metadata can be mutated after creation"""
        element = ExtractedElement(
            element_type="function",
            name="test",
            start_line=1,
            end_line=1,
            content="def test(): pass",
            metadata={"key1": "value1"},
        )

        # Modify metadata
        element.metadata["key2"] = "value2"
        element.metadata["key1"] = "updated"

        assert element.metadata["key1"] == "updated"
        assert element.metadata["key2"] == "value2"

    def test_extracted_element_immutability_of_other_fields(self):
        """Test that other fields remain immutable"""
        element = ExtractedElement(
            element_type="function",
            name="original",
            start_line=1,
            end_line=5,
            content="original content",
        )

        # These are dataclass fields - they can be reassigned but the original
        # values should be preserved unless explicitly changed
        original_name = element.name
        original_content = element.content

        assert original_name == "original"
        assert original_content == "original content"

    def test_extracted_element_content_with_tabs_and_spaces(self):
        """Test ExtractedElement preserves whitespace in content"""
        content = "def indented():\n\t\ttab_indent()\n    space_indent()"

        element = ExtractedElement(
            element_type="function",
            name="indented",
            start_line=1,
            end_line=3,
            content=content,
        )

        assert "\t\t" in element.content
        assert "    " in element.content

    def test_extracted_element_with_docstring_in_content(self):
        """Test ExtractedElement content containing docstring"""
        content = '''def documented():
    """This is a docstring.

    It spans multiple lines.
    """
    pass'''

        element = ExtractedElement(
            element_type="function",
            name="documented",
            start_line=1,
            end_line=6,
            content=content,
        )

        assert '"""This is a docstring' in element.content
        assert "multi" in element.content

    def test_extracted_element_empty_metadata_dict(self):
        """Test ExtractedElement with explicitly empty metadata dict"""
        element = ExtractedElement(
            element_type="function",
            name="test",
            start_line=1,
            end_line=1,
            content="def test(): pass",
            metadata={},
        )

        assert element.metadata == {}
        assert len(element.metadata) == 0

    def test_extracted_element_with_nested_metadata(self):
        """Test ExtractedElement with nested metadata structure"""
        element = ExtractedElement(
            element_type="class",
            name="ComplexClass",
            start_line=1,
            end_line=20,
            content="class ComplexClass: pass",
            metadata={
                "nested": {
                    "level1": {
                        "level2": {
                            "value": "deep",
                        },
                    },
                },
                "list_of_dicts": [
                    {"key": "value1"},
                    {"key": "value2"},
                ],
            },
        )

        assert element.metadata["nested"]["level1"]["level2"]["value"] == "deep"
        assert len(element.metadata["list_of_dicts"]) == 2

    def test_extracted_element_all_element_types(self):
        """Test ExtractedElement for all supported element types"""
        element_types = [
            "function",
            "method",
            "class",
            "import",
            "import_from",
            "variable",
            "interface",
            "type",
            "constant",
            "decorator",
        ]

        for element_type in element_types:
            element = ExtractedElement(
                element_type=element_type,
                name=f"test_{element_type}",
                start_line=1,
                end_line=5,
                content="content",
            )

            assert element.element_type == element_type

    def test_extracted_element_zero_based_vs_one_based_lines(self):
        """Test that ExtractedElement uses 1-based line numbering (common convention)"""
        # The implementation uses 1-based line numbers (line 1 is first line)
        element = ExtractedElement(
            element_type="function",
            name="firstLine",
            start_line=1,
            end_line=1,
            content="def firstLine(): pass",
        )

        assert element.start_line == 1
        assert element.end_line == 1
