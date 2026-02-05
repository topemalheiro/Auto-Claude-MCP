"""Tests for merge/types.py"""

from datetime import datetime
from merge.types import (
    ChangeType,
    ConflictSeverity,
    MergeStrategy,
    MergeDecision,
    SemanticChange,
    FileAnalysis,
    ConflictRegion,
    TaskSnapshot,
    FileEvolution,
    MergeResult,
    compute_content_hash,
    sanitize_path_for_storage,
)


# =============================================================================
# Tests for ChangeType Enum
# =============================================================================


def test_ChangeType_import_values():
    """Test import-related ChangeType values."""
    assert ChangeType.ADD_IMPORT.value == "add_import"
    assert ChangeType.REMOVE_IMPORT.value == "remove_import"
    assert ChangeType.MODIFY_IMPORT.value == "modify_import"


def test_ChangeType_function_values():
    """Test function-related ChangeType values."""
    assert ChangeType.ADD_FUNCTION.value == "add_function"
    assert ChangeType.REMOVE_FUNCTION.value == "remove_function"
    assert ChangeType.MODIFY_FUNCTION.value == "modify_function"
    assert ChangeType.RENAME_FUNCTION.value == "rename_function"


def test_ChangeType_react_values():
    """Test React/JSX-specific ChangeType values."""
    assert ChangeType.ADD_HOOK_CALL.value == "add_hook_call"
    assert ChangeType.REMOVE_HOOK_CALL.value == "remove_hook_call"
    assert ChangeType.WRAP_JSX.value == "wrap_jsx"
    assert ChangeType.UNWRAP_JSX.value == "unwrap_jsx"
    assert ChangeType.ADD_JSX_ELEMENT.value == "add_jsx_element"
    assert ChangeType.MODIFY_JSX_PROPS.value == "modify_jsx_props"


def test_ChangeType_variable_values():
    """Test variable/constant ChangeType values."""
    assert ChangeType.ADD_VARIABLE.value == "add_variable"
    assert ChangeType.REMOVE_VARIABLE.value == "remove_variable"
    assert ChangeType.MODIFY_VARIABLE.value == "modify_variable"
    assert ChangeType.ADD_CONSTANT.value == "add_constant"


def test_ChangeType_class_values():
    """Test class-related ChangeType values."""
    assert ChangeType.ADD_CLASS.value == "add_class"
    assert ChangeType.REMOVE_CLASS.value == "remove_class"
    assert ChangeType.MODIFY_CLASS.value == "modify_class"
    assert ChangeType.ADD_METHOD.value == "add_method"
    assert ChangeType.REMOVE_METHOD.value == "remove_method"
    assert ChangeType.MODIFY_METHOD.value == "modify_method"
    assert ChangeType.ADD_PROPERTY.value == "add_property"


def test_ChangeType_type_values():
    """Test TypeScript type-related ChangeType values."""
    assert ChangeType.ADD_TYPE.value == "add_type"
    assert ChangeType.MODIFY_TYPE.value == "modify_type"
    assert ChangeType.ADD_INTERFACE.value == "add_interface"
    assert ChangeType.MODIFY_INTERFACE.value == "modify_interface"


def test_ChangeType_python_values():
    """Test Python-specific ChangeType values."""
    assert ChangeType.ADD_DECORATOR.value == "add_decorator"
    assert ChangeType.REMOVE_DECORATOR.value == "remove_decorator"


def test_ChangeType_generic_values():
    """Test generic ChangeType values."""
    assert ChangeType.ADD_COMMENT.value == "add_comment"
    assert ChangeType.MODIFY_COMMENT.value == "modify_comment"
    assert ChangeType.FORMATTING_ONLY.value == "formatting_only"
    assert ChangeType.UNKNOWN.value == "unknown"


def test_ChangeType_from_string():
    """Test creating ChangeType from string values."""
    assert ChangeType("add_import") == ChangeType.ADD_IMPORT
    assert ChangeType("add_function") == ChangeType.ADD_FUNCTION
    assert ChangeType("modify_function") == ChangeType.MODIFY_FUNCTION
    assert ChangeType("unknown") == ChangeType.UNKNOWN


# =============================================================================
# Tests for ConflictSeverity Enum
# =============================================================================


def test_ConflictSeverity_values():
    """Test all ConflictSeverity enum values."""
    assert ConflictSeverity.NONE.value == "none"
    assert ConflictSeverity.LOW.value == "low"
    assert ConflictSeverity.MEDIUM.value == "medium"
    assert ConflictSeverity.HIGH.value == "high"
    assert ConflictSeverity.CRITICAL.value == "critical"


def test_ConflictSeverity_from_string():
    """Test creating ConflictSeverity from string values."""
    assert ConflictSeverity("none") == ConflictSeverity.NONE
    assert ConflictSeverity("low") == ConflictSeverity.LOW
    assert ConflictSeverity("medium") == ConflictSeverity.MEDIUM
    assert ConflictSeverity("high") == ConflictSeverity.HIGH
    assert ConflictSeverity("critical") == ConflictSeverity.CRITICAL


# =============================================================================
# Tests for MergeStrategy Enum
# =============================================================================


def test_MergeStrategy_import_values():
    """Test import-related MergeStrategy values."""
    assert MergeStrategy.COMBINE_IMPORTS.value == "combine_imports"


def test_MergeStrategy_function_body_values():
    """Test function body MergeStrategy values."""
    assert MergeStrategy.HOOKS_FIRST.value == "hooks_first"
    assert MergeStrategy.HOOKS_THEN_WRAP.value == "hooks_then_wrap"
    assert MergeStrategy.APPEND_STATEMENTS.value == "append_statements"


def test_MergeStrategy_structural_values():
    """Test structural MergeStrategy values."""
    assert MergeStrategy.APPEND_FUNCTIONS.value == "append_functions"
    assert MergeStrategy.APPEND_METHODS.value == "append_methods"
    assert MergeStrategy.COMBINE_PROPS.value == "combine_props"


def test_MergeStrategy_ordering_values():
    """Test ordering MergeStrategy values."""
    assert MergeStrategy.ORDER_BY_DEPENDENCY.value == "order_by_dependency"
    assert MergeStrategy.ORDER_BY_TIME.value == "order_by_time"


def test_MergeStrategy_fallback_values():
    """Test fallback MergeStrategy values."""
    assert MergeStrategy.AI_REQUIRED.value == "ai_required"
    assert MergeStrategy.HUMAN_REQUIRED.value == "human_required"


def test_MergeStrategy_from_string():
    """Test creating MergeStrategy from string values."""
    assert MergeStrategy("combine_imports") == MergeStrategy.COMBINE_IMPORTS
    assert MergeStrategy("hooks_first") == MergeStrategy.HOOKS_FIRST
    assert MergeStrategy("ai_required") == MergeStrategy.AI_REQUIRED
    assert MergeStrategy("human_required") == MergeStrategy.HUMAN_REQUIRED


# =============================================================================
# Tests for MergeDecision Enum
# =============================================================================


def test_MergeDecision_values():
    """Test all MergeDecision enum values."""
    assert MergeDecision.AUTO_MERGED.value == "auto_merged"
    assert MergeDecision.AI_MERGED.value == "ai_merged"
    assert MergeDecision.NEEDS_HUMAN_REVIEW.value == "needs_human_review"
    assert MergeDecision.FAILED.value == "failed"
    assert MergeDecision.DIRECT_COPY.value == "direct_copy"


def test_MergeDecision_from_string():
    """Test creating MergeDecision from string values."""
    assert MergeDecision("auto_merged") == MergeDecision.AUTO_MERGED
    assert MergeDecision("ai_merged") == MergeDecision.AI_MERGED
    assert MergeDecision("needs_human_review") == MergeDecision.NEEDS_HUMAN_REVIEW
    assert MergeDecision("failed") == MergeDecision.FAILED
    assert MergeDecision("direct_copy") == MergeDecision.DIRECT_COPY


# =============================================================================
# Tests for SemanticChange Dataclass
# =============================================================================


def test_SemanticChange_creation_minimal():
    """Test creating SemanticChange with minimal required fields."""
    change = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="myFunction",
        location="file_top",
        line_start=10,
        line_end=25,
    )
    assert change.change_type == ChangeType.ADD_FUNCTION
    assert change.target == "myFunction"
    assert change.location == "file_top"
    assert change.line_start == 10
    assert change.line_end == 25
    assert change.content_before is None
    assert change.content_after is None
    assert change.metadata == {}


def test_SemanticChange_creation_full():
    """Test creating SemanticChange with all fields."""
    change = SemanticChange(
        change_type=ChangeType.MODIFY_FUNCTION,
        target="myFunction",
        location="function:myFunction",
        line_start=10,
        line_end=25,
        content_before="old code",
        content_after="new code",
        metadata={"complexity": "high", "affects_tests": True},
    )
    assert change.change_type == ChangeType.MODIFY_FUNCTION
    assert change.content_before == "old code"
    assert change.content_after == "new code"
    assert change.metadata == {"complexity": "high", "affects_tests": True}


def test_SemanticChange_to_dict():
    """Test SemanticChange.to_dict method."""
    change = SemanticChange(
        change_type=ChangeType.ADD_IMPORT,
        target="useState",
        location="file_top",
        line_start=1,
        line_end=1,
        content_after='import { useState } from "react";',
        metadata={"react_hook": True},
    )
    result = change.to_dict()
    assert result["change_type"] == "add_import"
    assert result["target"] == "useState"
    assert result["location"] == "file_top"
    assert result["line_start"] == 1
    assert result["line_end"] == 1
    assert result["content_before"] is None
    assert result["content_after"] == 'import { useState } from "react";'
    assert result["metadata"] == {"react_hook": True}


def test_SemanticChange_from_dict():
    """Test SemanticChange.from_dict class method."""
    data = {
        "change_type": "add_hook_call",
        "target": "useAuth",
        "location": "function:App",
        "line_start": 15,
        "line_end": 15,
        "content_before": None,
        "content_after": "const auth = useAuth();",
        "metadata": {"hook_type": "custom"},
    }
    change = SemanticChange.from_dict(data)
    assert change.change_type == ChangeType.ADD_HOOK_CALL
    assert change.target == "useAuth"
    assert change.location == "function:App"
    assert change.line_start == 15
    assert change.line_end == 15
    assert change.content_before is None
    assert change.content_after == "const auth = useAuth();"
    assert change.metadata == {"hook_type": "custom"}


def test_SemanticChange_from_dict_missing_optional():
    """Test SemanticChange.from_dict with missing optional fields."""
    data = {
        "change_type": "add_function",
        "target": "newFunc",
        "location": "file_top",
        "line_start": 50,
        "line_end": 60,
    }
    change = SemanticChange.from_dict(data)
    assert change.change_type == ChangeType.ADD_FUNCTION
    assert change.content_before is None
    assert change.content_after is None
    assert change.metadata == {}


def test_SemanticChange_overlaps_with_same_location():
    """Test SemanticChange.overlaps_with with same location."""
    change1 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="func1",
        location="function:App",
        line_start=10,
        line_end=20,
    )
    change2 = SemanticChange(
        change_type=ChangeType.MODIFY_FUNCTION,
        target="func2",
        location="function:App",
        line_start=50,
        line_end=60,
    )
    assert change1.overlaps_with(change2) is True


def test_SemanticChange_overlaps_with_line_overlap():
    """Test SemanticChange.overlaps_with with line number overlap."""
    change1 = SemanticChange(
        change_type=ChangeType.ADD_VARIABLE,
        target="var1",
        location="function:helper",
        line_start=10,
        line_end=25,
    )
    change2 = SemanticChange(
        change_type=ChangeType.ADD_VARIABLE,
        target="var2",
        location="different_location",
        line_start=20,
        line_end=30,
    )
    assert change1.overlaps_with(change2) is True


def test_SemanticChange_overlaps_with_no_overlap():
    """Test SemanticChange.overlaps_with with no overlap."""
    change1 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="func1",
        location="file_top",
        line_start=10,
        line_end=20,
    )
    change2 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="func2",
        location="file_bottom",
        line_start=100,
        line_end=110,
    )
    assert change1.overlaps_with(change2) is False


def test_SemanticChange_overlaps_with_adjacent():
    """Test SemanticChange.overlaps_with with adjacent (non-overlapping) changes."""
    change1 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="func1",
        location="location_1",
        line_start=10,
        line_end=20,
    )
    change2 = SemanticChange(
        change_type=ChangeType.ADD_FUNCTION,
        target="func2",
        location="location_2",
        line_start=21,
        line_end=30,
    )
    # Adjacent lines don't overlap (change1 ends at 20, change2 starts at 21)
    assert change1.overlaps_with(change2) is False


def test_SemanticChange_is_additive_true():
    """Test SemanticChange.is_additive for additive changes."""
    additive_types = [
        ChangeType.ADD_IMPORT,
        ChangeType.ADD_FUNCTION,
        ChangeType.ADD_HOOK_CALL,
        ChangeType.ADD_VARIABLE,
        ChangeType.ADD_CONSTANT,
        ChangeType.ADD_CLASS,
        ChangeType.ADD_METHOD,
        ChangeType.ADD_PROPERTY,
        ChangeType.ADD_TYPE,
        ChangeType.ADD_INTERFACE,
        ChangeType.ADD_DECORATOR,
        ChangeType.ADD_JSX_ELEMENT,
        ChangeType.ADD_COMMENT,
    ]
    for ct in additive_types:
        change = SemanticChange(
            change_type=ct, target="test", location="test", line_start=1, line_end=5
        )
        assert change.is_additive is True, f"{ct} should be additive"


def test_SemanticChange_is_additive_false():
    """Test SemanticChange.is_additive for non-additive changes."""
    non_additive_types = [
        ChangeType.REMOVE_IMPORT,
        ChangeType.MODIFY_IMPORT,
        ChangeType.REMOVE_FUNCTION,
        ChangeType.MODIFY_FUNCTION,
        ChangeType.RENAME_FUNCTION,
        ChangeType.REMOVE_HOOK_CALL,
        ChangeType.WRAP_JSX,
        ChangeType.UNWRAP_JSX,
        ChangeType.MODIFY_JSX_PROPS,
        ChangeType.REMOVE_VARIABLE,
        ChangeType.MODIFY_VARIABLE,
        ChangeType.REMOVE_CLASS,
        ChangeType.MODIFY_CLASS,
        ChangeType.REMOVE_METHOD,
        ChangeType.MODIFY_METHOD,
        ChangeType.MODIFY_TYPE,
        ChangeType.MODIFY_INTERFACE,
        ChangeType.REMOVE_DECORATOR,
        ChangeType.MODIFY_COMMENT,
        ChangeType.FORMATTING_ONLY,
        ChangeType.UNKNOWN,
    ]
    for ct in non_additive_types:
        change = SemanticChange(
            change_type=ct, target="test", location="test", line_start=1, line_end=5
        )
        assert change.is_additive is False, f"{ct} should not be additive"


# =============================================================================
# Tests for FileAnalysis Dataclass
# =============================================================================


def test_FileAnalysis_creation_minimal():
    """Test creating FileAnalysis with minimal required fields."""
    analysis = FileAnalysis(file_path="src/App.tsx")
    assert analysis.file_path == "src/App.tsx"
    assert analysis.changes == []
    assert analysis.functions_modified == set()
    assert analysis.functions_added == set()
    assert analysis.imports_added == set()
    assert analysis.imports_removed == set()
    assert analysis.classes_modified == set()
    assert analysis.total_lines_changed == 0


def test_FileAnalysis_creation_full():
    """Test creating FileAnalysis with all fields."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="newFunc",
            location="file_top",
            line_start=10,
            line_end=20,
        )
    ]
    analysis = FileAnalysis(
        file_path="src/utils.ts",
        changes=changes,
        functions_modified={"oldFunc"},
        functions_added={"newFunc", "helperFunc"},
        imports_added={"lodash", "axios"},
        imports_removed={"moment"},
        classes_modified={"UserManager"},
        total_lines_changed=45,
    )
    assert analysis.file_path == "src/utils.ts"
    assert len(analysis.changes) == 1
    assert analysis.functions_modified == {"oldFunc"}
    assert analysis.functions_added == {"newFunc", "helperFunc"}
    assert analysis.imports_added == {"lodash", "axios"}
    assert analysis.imports_removed == {"moment"}
    assert analysis.classes_modified == {"UserManager"}
    assert analysis.total_lines_changed == 45


def test_FileAnalysis_to_dict():
    """Test FileAnalysis.to_dict method."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="useState",
            location="file_top",
            line_start=1,
            line_end=1,
        )
    ]
    analysis = FileAnalysis(
        file_path="src/App.tsx",
        changes=changes,
        functions_added={"useEffect"},
        imports_added={"react"},
        total_lines_changed=10,
    )
    result = analysis.to_dict()
    assert result["file_path"] == "src/App.tsx"
    assert len(result["changes"]) == 1
    assert result["changes"][0]["change_type"] == "add_import"
    assert result["functions_added"] == ["useEffect"]
    assert result["imports_added"] == ["react"]
    assert result["total_lines_changed"] == 10
    # Sets are converted to lists
    assert isinstance(result["functions_modified"], list)
    assert isinstance(result["functions_added"], list)


def test_FileAnalysis_from_dict():
    """Test FileAnalysis.from_dict class method."""
    data = {
        "file_path": "src/components/Button.tsx",
        "changes": [
            {
                "change_type": "add_jsx_element",
                "target": "Button",
                "location": "file_top",
                "line_start": 5,
                "line_end": 10,
                "content_before": None,
                "content_after": "<Button />",
                "metadata": {},
            }
        ],
        "functions_modified": ["handleClick"],
        "functions_added": [],
        "imports_added": [],
        "imports_removed": [],
        "classes_modified": [],
        "total_lines_changed": 15,
    }
    analysis = FileAnalysis.from_dict(data)
    assert analysis.file_path == "src/components/Button.tsx"
    assert len(analysis.changes) == 1
    assert analysis.changes[0].change_type == ChangeType.ADD_JSX_ELEMENT
    assert analysis.functions_modified == {"handleClick"}
    assert analysis.total_lines_changed == 15


def test_FileAnalysis_from_dict_empty():
    """Test FileAnalysis.from_dict with empty data."""
    data = {
        "file_path": "src/empty.ts",
        "changes": [],
        "functions_modified": [],
        "functions_added": [],
        "imports_added": [],
        "imports_removed": [],
        "classes_modified": [],
        "total_lines_changed": 0,
    }
    analysis = FileAnalysis.from_dict(data)
    assert analysis.file_path == "src/empty.ts"
    assert analysis.changes == []
    assert analysis.functions_modified == set()


def test_FileAnalysis_get_changes_at_location():
    """Test FileAnalysis.get_changes_at_location method."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="function:App",
            line_start=10,
            line_end=20,
        ),
        SemanticChange(
            change_type=ChangeType.ADD_VARIABLE,
            target="var1",
            location="function:App",
            line_start=15,
            line_end=15,
        ),
        SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="useState",
            location="file_top",
            line_start=1,
            line_end=1,
        ),
    ]
    analysis = FileAnalysis(file_path="test.ts", changes=changes)
    app_changes = analysis.get_changes_at_location("function:App")
    assert len(app_changes) == 2
    assert all(c.location == "function:App" for c in app_changes)


def test_FileAnalysis_is_additive_only_true():
    """Test FileAnalysis.is_additive_only when all changes are additive."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="file_top",
            line_start=10,
            line_end=20,
        ),
        SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="lodash",
            location="file_top",
            line_start=1,
            line_end=1,
        ),
    ]
    analysis = FileAnalysis(file_path="test.ts", changes=changes)
    assert analysis.is_additive_only is True


def test_FileAnalysis_is_additive_only_false():
    """Test FileAnalysis.is_additive_only when some changes are not additive."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="file_top",
            line_start=10,
            line_end=20,
        ),
        SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func2",
            location="file_top",
            line_start=25,
            line_end=35,
        ),
    ]
    analysis = FileAnalysis(file_path="test.ts", changes=changes)
    assert analysis.is_additive_only is False


def test_FileAnalysis_is_additive_only_empty():
    """Test FileAnalysis.is_additive_only with no changes."""
    analysis = FileAnalysis(file_path="test.ts")
    assert analysis.is_additive_only is True  # Empty list is vacuously true


def test_FileAnalysis_locations_changed():
    """Test FileAnalysis.locations_changed property."""
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="file_top",
            line_start=10,
            line_end=20,
        ),
        SemanticChange(
            change_type=ChangeType.ADD_VARIABLE,
            target="var1",
            location="function:helper",
            line_start=30,
            line_end=30,
        ),
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func2",
            location="file_top",
            line_start=21,
            line_end=30,
        ),
    ]
    analysis = FileAnalysis(file_path="test.ts", changes=changes)
    locations = analysis.locations_changed
    assert locations == {"file_top", "function:helper"}


# =============================================================================
# Tests for ConflictRegion Dataclass
# =============================================================================


def test_ConflictRegion_creation():
    """Test creating ConflictRegion."""
    region = ConflictRegion(
        file_path="src/App.tsx",
        location="function:App",
        tasks_involved=["task_001", "task_002"],
        change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.ADD_VARIABLE],
        severity=ConflictSeverity.LOW,
        can_auto_merge=True,
        merge_strategy=MergeStrategy.HOOKS_FIRST,
        reason="Both tasks added independent hooks",
    )
    assert region.file_path == "src/App.tsx"
    assert region.location == "function:App"
    assert region.tasks_involved == ["task_001", "task_002"]
    assert len(region.change_types) == 2
    assert region.severity == ConflictSeverity.LOW
    assert region.can_auto_merge is True
    assert region.merge_strategy == MergeStrategy.HOOKS_FIRST
    assert region.reason == "Both tasks added independent hooks"


def test_ConflictRegion_creation_no_strategy():
    """Test creating ConflictRegion without merge strategy."""
    region = ConflictRegion(
        file_path="src/utils.ts",
        location="function:helper",
        tasks_involved=["task_001"],
        change_types=[ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.HIGH,
        can_auto_merge=False,
        reason="Complex modification requiring AI",
    )
    assert region.merge_strategy is None


def test_ConflictRegion_to_dict():
    """Test ConflictRegion.to_dict method."""
    region = ConflictRegion(
        file_path="src/App.tsx",
        location="function:App",
        tasks_involved=["task_001", "task_002"],
        change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.ADD_VARIABLE],
        severity=ConflictSeverity.LOW,
        can_auto_merge=True,
        merge_strategy=MergeStrategy.HOOKS_FIRST,
        reason="Both tasks added independent hooks",
    )
    result = region.to_dict()
    assert result["file_path"] == "src/App.tsx"
    assert result["location"] == "function:App"
    assert result["tasks_involved"] == ["task_001", "task_002"]
    assert result["change_types"] == ["add_hook_call", "add_variable"]
    assert result["severity"] == "low"
    assert result["can_auto_merge"] is True
    assert result["merge_strategy"] == "hooks_first"
    assert result["reason"] == "Both tasks added independent hooks"


def test_ConflictRegion_to_dict_no_strategy():
    """Test ConflictRegion.to_dict with no merge strategy."""
    region = ConflictRegion(
        file_path="src/utils.ts",
        location="function:helper",
        tasks_involved=["task_001"],
        change_types=[ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.HIGH,
        can_auto_merge=False,
    )
    result = region.to_dict()
    assert result["merge_strategy"] is None


def test_ConflictRegion_from_dict():
    """Test ConflictRegion.from_dict class method."""
    data = {
        "file_path": "src/components/Header.tsx",
        "location": "function:Header",
        "tasks_involved": ["task_003", "task_004"],
        "change_types": ["add_jsx_element", "modify_jsx_props"],
        "severity": "medium",
        "can_auto_merge": True,
        "merge_strategy": "combine_props",
        "reason": "Both tasks modified different props",
    }
    region = ConflictRegion.from_dict(data)
    assert region.file_path == "src/components/Header.tsx"
    assert region.tasks_involved == ["task_003", "task_004"]
    assert region.change_types == [
        ChangeType.ADD_JSX_ELEMENT,
        ChangeType.MODIFY_JSX_PROPS,
    ]
    assert region.severity == ConflictSeverity.MEDIUM
    assert region.can_auto_merge is True
    assert region.merge_strategy == MergeStrategy.COMBINE_PROPS


def test_ConflictRegion_from_dict_no_strategy():
    """Test ConflictRegion.from_dict without merge strategy."""
    data = {
        "file_path": "src/utils.ts",
        "location": "function:helper",
        "tasks_involved": ["task_001"],
        "change_types": ["modify_function"],
        "severity": "critical",
        "can_auto_merge": False,
    }
    region = ConflictRegion.from_dict(data)
    assert region.merge_strategy is None
    assert region.reason == ""


# =============================================================================
# Tests for TaskSnapshot Dataclass
# =============================================================================


def test_TaskSnapshot_creation_minimal():
    """Test creating TaskSnapshot with minimal required fields."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add authentication",
        started_at=started,
    )
    assert snapshot.task_id == "task_001"
    assert snapshot.task_intent == "Add authentication"
    assert snapshot.started_at == started
    assert snapshot.completed_at is None
    assert snapshot.content_hash_before == ""
    assert snapshot.content_hash_after == ""
    assert snapshot.semantic_changes == []
    assert snapshot.raw_diff is None


def test_TaskSnapshot_creation_full():
    """Test creating TaskSnapshot with all fields."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    completed = datetime(2024, 1, 1, 12, 30, 0)
    changes = [
        SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="authenticate",
            location="file_top",
            line_start=10,
            line_end=25,
        )
    ]
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add authentication",
        started_at=started,
        completed_at=completed,
        content_hash_before="abc123",
        content_hash_after="def456",
        semantic_changes=changes,
        raw_diff="@@ -10,0 +10,15 @@\n+def authenticate():\n+    pass",
    )
    assert snapshot.task_id == "task_001"
    assert snapshot.completed_at == completed
    assert snapshot.content_hash_before == "abc123"
    assert snapshot.content_hash_after == "def456"
    assert len(snapshot.semantic_changes) == 1
    assert snapshot.raw_diff is not None


def test_TaskSnapshot_to_dict():
    """Test TaskSnapshot.to_dict method."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    completed = datetime(2024, 1, 1, 12, 30, 0)
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Add feature",
        started_at=started,
        completed_at=completed,
        content_hash_before="abc123",
        content_hash_after="def456",
        raw_diff="+ new line",
    )
    result = snapshot.to_dict()
    assert result["task_id"] == "task_001"
    assert result["task_intent"] == "Add feature"
    assert result["started_at"] == "2024-01-01T12:00:00"
    assert result["completed_at"] == "2024-01-01T12:30:00"
    assert result["content_hash_before"] == "abc123"
    assert result["content_hash_after"] == "def456"
    assert result["raw_diff"] == "+ new line"


def test_TaskSnapshot_to_dict_no_completion():
    """Test TaskSnapshot.to_dict without completed_at."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="In progress",
        started_at=started,
    )
    result = snapshot.to_dict()
    assert result["completed_at"] is None


def test_TaskSnapshot_from_dict():
    """Test TaskSnapshot.from_dict class method."""
    data = {
        "task_id": "task_002",
        "task_intent": "Fix bug",
        "started_at": "2024-01-01T10:00:00",
        "completed_at": "2024-01-01T10:15:00",
        "content_hash_before": "old_hash",
        "content_hash_after": "new_hash",
        "semantic_changes": [
            {
                "change_type": "modify_function",
                "target": "buggyFunc",
                "location": "function:buggyFunc",
                "line_start": 50,
                "line_end": 60,
                "content_before": "old",
                "content_after": "new",
                "metadata": {},
            }
        ],
        "raw_diff": "-old\n+new",
    }
    snapshot = TaskSnapshot.from_dict(data)
    assert snapshot.task_id == "task_002"
    assert snapshot.task_intent == "Fix bug"
    assert snapshot.started_at == datetime(2024, 1, 1, 10, 0, 0)
    assert snapshot.completed_at == datetime(2024, 1, 1, 10, 15, 0)
    assert snapshot.content_hash_before == "old_hash"
    assert snapshot.content_hash_after == "new_hash"
    assert len(snapshot.semantic_changes) == 1
    assert snapshot.raw_diff == "-old\n+new"


def test_TaskSnapshot_from_dict_no_completion():
    """Test TaskSnapshot.from_dict without completed_at."""
    data = {
        "task_id": "task_003",
        "task_intent": "Running task",
        "started_at": "2024-01-01T12:00:00",
    }
    snapshot = TaskSnapshot.from_dict(data)
    assert snapshot.completed_at is None


def test_TaskSnapshot_has_modifications_true_semantic():
    """Test TaskSnapshot.has_modifications with semantic changes."""
    started = datetime.now()
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Test",
        started_at=started,
        semantic_changes=[
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="f",
                location="test",
                line_start=1,
                line_end=5,
            )
        ],
    )
    assert snapshot.has_modifications is True


def test_TaskSnapshot_has_modifications_true_new_file():
    """Test TaskSnapshot.has_modifications for new file."""
    started = datetime.now()
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Create file",
        started_at=started,
        content_hash_before="",
        content_hash_after="abc123",
    )
    assert snapshot.has_modifications is True


def test_TaskSnapshot_has_modifications_true_hash_change():
    """Test TaskSnapshot.has_modifications via hash comparison."""
    started = datetime.now()
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="Modify",
        started_at=started,
        content_hash_before="old_hash",
        content_hash_after="new_hash",
    )
    assert snapshot.has_modifications is True


def test_TaskSnapshot_has_modifications_false_same_hash():
    """Test TaskSnapshot.has_modifications with same hashes."""
    started = datetime.now()
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="No change",
        started_at=started,
        content_hash_before="same_hash",
        content_hash_after="same_hash",
    )
    assert snapshot.has_modifications is False


def test_TaskSnapshot_has_modifications_false_empty():
    """Test TaskSnapshot.has_modifications with no changes."""
    started = datetime.now()
    snapshot = TaskSnapshot(
        task_id="task_001",
        task_intent="No change",
        started_at=started,
    )
    assert snapshot.has_modifications is False


# =============================================================================
# Tests for FileEvolution Dataclass
# =============================================================================


def test_FileEvolution_creation():
    """Test creating FileEvolution."""
    captured = datetime(2024, 1, 1, 12, 0, 0)
    evolution = FileEvolution(
        file_path="src/App.tsx",
        baseline_commit="abc123def",
        baseline_captured_at=captured,
        baseline_content_hash="hash123",
        baseline_snapshot_path="/snapshots/App.tsx.baseline",
    )
    assert evolution.file_path == "src/App.tsx"
    assert evolution.baseline_commit == "abc123def"
    assert evolution.baseline_captured_at == captured
    assert evolution.baseline_content_hash == "hash123"
    assert evolution.baseline_snapshot_path == "/snapshots/App.tsx.baseline"
    assert evolution.task_snapshots == []


def test_FileEvolution_creation_with_snapshots():
    """Test creating FileEvolution with task snapshots."""
    captured = datetime(2024, 1, 1, 12, 0, 0)
    task1 = TaskSnapshot(
        task_id="task_001", task_intent="First", started_at=captured
    )
    task2 = TaskSnapshot(
        task_id="task_002", task_intent="Second", started_at=captured
    )
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="base_hash",
        baseline_snapshot_path="/snapshots/test.baseline",
        task_snapshots=[task1, task2],
    )
    assert len(evolution.task_snapshots) == 2


def test_FileEvolution_to_dict():
    """Test FileEvolution.to_dict method."""
    captured = datetime(2024, 1, 1, 12, 0, 0)
    task = TaskSnapshot(
        task_id="task_001", task_intent="Test", started_at=captured
    )
    evolution = FileEvolution(
        file_path="src/test.ts",
        baseline_commit="abc123",
        baseline_captured_at=captured,
        baseline_content_hash="hash123",
        baseline_snapshot_path="/snapshots/test.ts",
        task_snapshots=[task],
    )
    result = evolution.to_dict()
    assert result["file_path"] == "src/test.ts"
    assert result["baseline_commit"] == "abc123"
    assert result["baseline_captured_at"] == "2024-01-01T12:00:00"
    assert result["baseline_content_hash"] == "hash123"
    assert result["baseline_snapshot_path"] == "/snapshots/test.ts"
    assert len(result["task_snapshots"]) == 1


def test_FileEvolution_from_dict():
    """Test FileEvolution.from_dict class method."""
    data = {
        "file_path": "src/App.tsx",
        "baseline_commit": "def456",
        "baseline_captured_at": "2024-01-01T12:00:00",
        "baseline_content_hash": "content_hash",
        "baseline_snapshot_path": "/snapshots/App.tsx.baseline",
        "task_snapshots": [
            {
                "task_id": "task_001",
                "task_intent": "Test task",
                "started_at": "2024-01-01T12:30:00",
                "completed_at": None,
                "content_hash_before": "",
                "content_hash_after": "",
                "semantic_changes": [],
                "raw_diff": None,
            }
        ],
    }
    evolution = FileEvolution.from_dict(data)
    assert evolution.file_path == "src/App.tsx"
    assert evolution.baseline_commit == "def456"
    assert evolution.baseline_captured_at == datetime(2024, 1, 1, 12, 0, 0)
    assert len(evolution.task_snapshots) == 1


def test_FileEvolution_get_task_snapshot_found():
    """Test FileEvolution.get_task_snapshot when task exists."""
    captured = datetime.now()
    task = TaskSnapshot(
        task_id="task_001", task_intent="Test", started_at=captured
    )
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
        task_snapshots=[task],
    )
    result = evolution.get_task_snapshot("task_001")
    assert result is not None
    assert result.task_id == "task_001"


def test_FileEvolution_get_task_snapshot_not_found():
    """Test FileEvolution.get_task_snapshot when task doesn't exist."""
    captured = datetime.now()
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
    )
    result = evolution.get_task_snapshot("nonexistent")
    assert result is None


def test_FileEvolution_add_task_snapshot_new():
    """Test FileEvolution.add_task_snapshot adding new task."""
    captured = datetime.now()
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
    )
    task = TaskSnapshot(
        task_id="task_001", task_intent="Test", started_at=captured
    )
    evolution.add_task_snapshot(task)
    assert len(evolution.task_snapshots) == 1
    assert evolution.task_snapshots[0].task_id == "task_001"


def test_FileEvolution_add_task_snapshot_update():
    """Test FileEvolution.add_task_snapshot updating existing task."""
    captured = datetime.now()
    task1 = TaskSnapshot(
        task_id="task_001", task_intent="Original", started_at=captured
    )
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
        task_snapshots=[task1],
    )
    task2 = TaskSnapshot(
        task_id="task_001",
        task_intent="Updated",
        started_at=captured,
        content_hash_after="new_hash",
    )
    evolution.add_task_snapshot(task2)
    assert len(evolution.task_snapshots) == 1
    assert evolution.task_snapshots[0].task_intent == "Updated"
    assert evolution.task_snapshots[0].content_hash_after == "new_hash"


def test_FileEvolution_add_task_snapshot_sorting():
    """Test FileEvolution.add_task_snapshot maintains chronological order."""
    captured = datetime.now()
    task1 = TaskSnapshot(
        task_id="task_001", task_intent="First", started_at=captured
    )
    task2 = TaskSnapshot(
        task_id="task_002",
        task_intent="Second",
        started_at=datetime(2024, 1, 1, 11, 0, 0),
    )
    task3 = TaskSnapshot(
        task_id="task_003",
        task_intent="Third",
        started_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
    )
    evolution.add_task_snapshot(task1)
    evolution.add_task_snapshot(task2)
    evolution.add_task_snapshot(task3)
    # Should be sorted by started_at: task3 (10:00), task2 (11:00), task1 (12:00)
    assert evolution.task_snapshots[0].task_id == "task_003"
    assert evolution.task_snapshots[1].task_id == "task_002"
    assert evolution.task_snapshots[2].task_id == "task_001"


def test_FileEvolution_tasks_involved():
    """Test FileEvolution.tasks_involved property."""
    captured = datetime.now()
    task1 = TaskSnapshot(
        task_id="task_001", task_intent="First", started_at=captured
    )
    task2 = TaskSnapshot(
        task_id="task_002", task_intent="Second", started_at=captured
    )
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
        task_snapshots=[task1, task2],
    )
    tasks = evolution.tasks_involved
    assert tasks == ["task_001", "task_002"]


def test_FileEvolution_tasks_involved_empty():
    """Test FileEvolution.tasks_involved with no tasks."""
    captured = datetime.now()
    evolution = FileEvolution(
        file_path="test.ts",
        baseline_commit="base",
        baseline_captured_at=captured,
        baseline_content_hash="hash",
        baseline_snapshot_path="/path",
    )
    assert evolution.tasks_involved == []


# =============================================================================
# Tests for MergeResult Dataclass
# =============================================================================


def test_MergeResult_creation_minimal():
    """Test creating MergeResult with minimal required fields."""
    result = MergeResult(
        decision=MergeDecision.AUTO_MERGED, file_path="src/App.tsx"
    )
    assert result.decision == MergeDecision.AUTO_MERGED
    assert result.file_path == "src/App.tsx"
    assert result.merged_content is None
    assert result.conflicts_resolved == []
    assert result.conflicts_remaining == []
    assert result.ai_calls_made == 0
    assert result.tokens_used == 0
    assert result.explanation == ""
    assert result.error is None


def test_MergeResult_creation_full():
    """Test creating MergeResult with all fields."""
    conflict = ConflictRegion(
        file_path="test.ts",
        location="function:main",
        tasks_involved=["task_001"],
        change_types=[ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.MEDIUM,
        can_auto_merge=False,
    )
    result = MergeResult(
        decision=MergeDecision.AI_MERGED,
        file_path="src/utils.ts",
        merged_content="// merged content",
        conflicts_resolved=[conflict],
        conflicts_remaining=[],
        ai_calls_made=2,
        tokens_used=1500,
        explanation="Successfully resolved conflicts",
    )
    assert result.decision == MergeDecision.AI_MERGED
    assert result.merged_content == "// merged content"
    assert len(result.conflicts_resolved) == 1
    assert result.ai_calls_made == 2
    assert result.tokens_used == 1500
    assert result.explanation == "Successfully resolved conflicts"


def test_MergeResult_to_dict():
    """Test MergeResult.to_dict method."""
    conflict = ConflictRegion(
        file_path="test.ts",
        location="function:main",
        tasks_involved=["task_001"],
        change_types=[ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.HIGH,
        can_auto_merge=False,
    )
    result = MergeResult(
        decision=MergeDecision.NEEDS_HUMAN_REVIEW,
        file_path="src/test.ts",
        conflicts_remaining=[conflict],
        explanation="Requires human intervention",
    )
    dict_result = result.to_dict()
    assert dict_result["decision"] == "needs_human_review"
    assert dict_result["file_path"] == "src/test.ts"
    assert dict_result["merged_content"] is None
    assert len(dict_result["conflicts_remaining"]) == 1
    assert dict_result["explanation"] == "Requires human intervention"
    assert dict_result["error"] is None


def test_MergeResult_success_auto_merged():
    """Test MergeResult.success for AUTO_MERGED."""
    result = MergeResult(
        decision=MergeDecision.AUTO_MERGED, file_path="test.ts"
    )
    assert result.success is True


def test_MergeResult_success_ai_merged():
    """Test MergeResult.success for AI_MERGED."""
    result = MergeResult(decision=MergeDecision.AI_MERGED, file_path="test.ts")
    assert result.success is True


def test_MergeResult_success_direct_copy():
    """Test MergeResult.success for DIRECT_COPY."""
    result = MergeResult(
        decision=MergeDecision.DIRECT_COPY, file_path="test.ts"
    )
    assert result.success is True


def test_MergeResult_success_needs_human_review():
    """Test MergeResult.success for NEEDS_HUMAN_REVIEW."""
    result = MergeResult(
        decision=MergeDecision.NEEDS_HUMAN_REVIEW, file_path="test.ts"
    )
    assert result.success is False


def test_MergeResult_success_failed():
    """Test MergeResult.success for FAILED."""
    result = MergeResult(decision=MergeDecision.FAILED, file_path="test.ts")
    assert result.success is False


def test_MergeResult_needs_human_review_true_by_decision():
    """Test MergeResult.needs_human_review when decision is NEEDS_HUMAN_REVIEW."""
    result = MergeResult(
        decision=MergeDecision.NEEDS_HUMAN_REVIEW, file_path="test.ts"
    )
    assert result.needs_human_review is True


def test_MergeResult_needs_human_review_true_by_conflicts():
    """Test MergeResult.needs_human_review when conflicts remain."""
    conflict = ConflictRegion(
        file_path="test.ts",
        location="test",
        tasks_involved=["task_001"],
        change_types=[],
        severity=ConflictSeverity.HIGH,
        can_auto_merge=False,
    )
    result = MergeResult(
        decision=MergeDecision.AUTO_MERGED,
        file_path="test.ts",
        conflicts_remaining=[conflict],
    )
    assert result.needs_human_review is True


def test_MergeResult_needs_human_review_false():
    """Test MergeResult.needs_human_review when no issues."""
    result = MergeResult(
        decision=MergeDecision.AUTO_MERGED,
        file_path="test.ts",
        merged_content="all good",
    )
    assert result.needs_human_review is False


# =============================================================================
# Tests for Utility Functions
# =============================================================================


def test_compute_content_hash_basic():
    """Test compute_content_hash with basic content."""
    content = "Hello, world!"
    hash_result = compute_content_hash(content)
    assert isinstance(hash_result, str)
    assert len(hash_result) == 16  # SHA-256 truncated to 16 chars


def test_compute_content_hash_consistency():
    """Test compute_content_hash returns same hash for same content."""
    content = "Consistent content"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)
    assert hash1 == hash2


def test_compute_content_hash_different_content():
    """Test compute_content_hash returns different hashes for different content."""
    hash1 = compute_content_hash("Content 1")
    hash2 = compute_content_hash("Content 2")
    assert hash1 != hash2


def test_compute_content_hash_empty_string():
    """Test compute_content_hash with empty string."""
    hash_result = compute_content_hash("")
    assert isinstance(hash_result, str)
    assert len(hash_result) == 16


def test_compute_content_hash_unicode():
    """Test compute_content_hash with unicode characters."""
    content = "Hello 世界 🌍"
    hash_result = compute_content_hash(content)
    assert isinstance(hash_result, str)
    assert len(hash_result) == 16


def test_compute_content_hash_multiline():
    """Test compute_content_hash with multiline content."""
    content = """Line 1
Line 2
Line 3"""
    hash_result = compute_content_hash(content)
    assert isinstance(hash_result, str)


def test_compute_content_hash_special_characters():
    """Test compute_content_hash with special characters."""
    content = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
    hash_result = compute_content_hash(content)
    assert isinstance(hash_result, str)


def test_sanitize_path_for_storage_unix():
    """Test sanitize_path_for_storage with Unix paths."""
    path = "src/components/App.tsx"
    result = sanitize_path_for_storage(path)
    assert result == "src_components_App_tsx"


def test_sanitize_path_for_storage_windows():
    """Test sanitize_path_for_storage with Windows paths."""
    path = "src\\components\\App.tsx"
    result = sanitize_path_for_storage(path)
    assert result == "src_components_App_tsx"


def test_sanitize_path_for_storage_mixed_separators():
    """Test sanitize_path_for_storage with mixed path separators."""
    path = "src\\components/utils/helper.ts"
    result = sanitize_path_for_storage(path)
    assert result == "src_components_utils_helper_ts"


def test_sanitize_path_for_storage_multiple_extensions():
    """Test sanitize_path_for_storage with files with multiple dots."""
    path = "archive.tar.gz"
    result = sanitize_path_for_storage(path)
    assert result == "archive_tar_gz"


def test_sanitize_path_for_storage_dots_in_path():
    """Test sanitize_path_for_storage with dots in directory names."""
    path = "src.v2/components/app.ts"
    result = sanitize_path_for_storage(path)
    assert result == "src_v2_components_app_ts"


def test_sanitize_path_for_storage_simple_filename():
    """Test sanitize_path_for_storage with simple filename."""
    path = "README.md"
    result = sanitize_path_for_storage(path)
    assert result == "README_md"


def test_sanitize_path_for_storage_deep_path():
    """Test sanitize_path_for_storage with deeply nested path."""
    path = "a/b/c/d/e/f/g/file.py"
    result = sanitize_path_for_storage(path)
    assert result == "a_b_c_d_e_f_g_file_py"


def test_sanitize_path_for_storage_empty_segments():
    """Test sanitize_path_for_storage with empty path segments."""
    path = "a//b///c"
    result = sanitize_path_for_storage(path)
    assert result == "a__b___c"


def test_sanitize_path_for_storage_leading_trailing_separators():
    """Test sanitize_path_for_storage with leading/trailing separators."""
    path = "/src/components/"
    result = sanitize_path_for_storage(path)
    assert result == "_src_components_"


def test_sanitize_path_for_storage_relative_path():
    """Test sanitize_path_for_storage with relative path."""
    path = "../src/utils/helper.ts"
    result = sanitize_path_for_storage(path)
    # ../ becomes ___ (.. becomes .. then / becomes _)
    assert result == "___src_utils_helper_ts"


def test_sanitize_path_for_storage_current_directory():
    """Test sanitize_path_for_storage with ./ prefix."""
    path = "./src/App.tsx"
    result = sanitize_path_for_storage(path)
    # ./ becomes __ (. becomes . then / becomes _)
    assert result == "__src_App_tsx"


def test_sanitize_path_for_storage_no_separators():
    """Test sanitize_path_for_storage with filename only."""
    path = "config"
    result = sanitize_path_for_storage(path)
    assert result == "config"


def test_sanitize_path_for_storage_special_windows_path():
    """Test sanitize_path_for_storage with Windows-style absolute path."""
    path = "C:\\Users\\Test\\App.tsx"
    result = sanitize_path_for_storage(path)
    # Note: the function only replaces /, \, and . with _
    # The colon : is NOT replaced, so C: stays as C:
    assert result == "C:_Users_Test_App_tsx"
