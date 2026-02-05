"""Tests for analyzers"""

from runners.ai_analyzer.analyzers import (
    AnalyzerFactory,
    ArchitectureAnalyzer,
    BaseAnalyzer,
    BusinessLogicAnalyzer,
    CodeQualityAnalyzer,
    CodeRelationshipsAnalyzer,
    PerformanceAnalyzer,
    SecurityAnalyzer,
)
import pytest


def test_BaseAnalyzer___init__():
    """Test BaseAnalyzer.__init__"""
    # Arrange
    project_index = {"services": {"test_service": {}}}

    # Act
    instance = BaseAnalyzer(project_index)

    # Assert
    assert instance is not None
    assert instance.project_index == project_index


def test_BaseAnalyzer_get_services():
    """Test BaseAnalyzer.get_services"""
    # Arrange
    project_index = {"services": {"test_service": {"api": {}}}}
    instance = BaseAnalyzer(project_index)

    # Act
    result = instance.get_services()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "test_service" in result


def test_BaseAnalyzer_get_first_service():
    """Test BaseAnalyzer.get_first_service"""
    # Arrange
    project_index = {"services": {"test_service": {"api": {}}}}
    instance = BaseAnalyzer(project_index)

    # Act
    result = instance.get_first_service()

    # Assert
    assert result is not None
    assert isinstance(result, tuple)
    assert result[0] == "test_service"
    assert result[1] == {"api": {}}


def test_BaseAnalyzer_get_first_service_empty():
    """Test BaseAnalyzer.get_first_service with no services"""
    # Arrange
    project_index = {"services": {}}
    instance = BaseAnalyzer(project_index)

    # Act
    result = instance.get_first_service()

    # Assert
    assert result is None


def test_CodeRelationshipsAnalyzer_get_prompt():
    """Test CodeRelationshipsAnalyzer.get_prompt"""
    # Arrange
    project_index = {
        "services": {
            "test_service": {
                "api": {"routes": [{"methods": "GET", "path": "/api/test", "file": "test.py"}]},
                "database": {"models": {"User": {}, "Post": {}}},
            }
        }
    }
    instance = CodeRelationshipsAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "code relationships" in result.lower()
    assert "/api/test" in result


def test_CodeRelationshipsAnalyzer_get_default_result():
    """Test CodeRelationshipsAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = CodeRelationshipsAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["relationships"] == []


def test_BusinessLogicAnalyzer_get_prompt():
    """Test BusinessLogicAnalyzer.get_prompt"""
    # Arrange
    project_index = {"services": {}}
    instance = BusinessLogicAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "business logic" in result.lower()


def test_BusinessLogicAnalyzer_get_default_result():
    """Test BusinessLogicAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = BusinessLogicAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["workflows"] == []


def test_ArchitectureAnalyzer_get_prompt():
    """Test ArchitectureAnalyzer.get_prompt"""
    # Arrange
    project_index = {"services": {}}
    instance = ArchitectureAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "architecture" in result.lower()


def test_ArchitectureAnalyzer_get_default_result():
    """Test ArchitectureAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = ArchitectureAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["architecture_style"] == "unknown"


def test_SecurityAnalyzer_get_prompt():
    """Test SecurityAnalyzer.get_prompt"""
    # Arrange
    project_index = {"services": {}}
    instance = SecurityAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "security" in result.lower()


def test_SecurityAnalyzer_get_default_result():
    """Test SecurityAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = SecurityAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["vulnerabilities"] == []


def test_PerformanceAnalyzer_get_prompt():
    """Test PerformanceAnalyzer.get_prompt"""
    # Arrange
    project_index = {"services": {}}
    instance = PerformanceAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "performance" in result.lower()


def test_PerformanceAnalyzer_get_default_result():
    """Test PerformanceAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = PerformanceAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["bottlenecks"] == []


def test_CodeQualityAnalyzer_get_prompt():
    """Test CodeQualityAnalyzer.get_prompt"""
    # Arrange
    project_index = {"services": {}}
    instance = CodeQualityAnalyzer(project_index)

    # Act
    result = instance.get_prompt()

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "code quality" in result.lower()


def test_CodeQualityAnalyzer_get_default_result():
    """Test CodeQualityAnalyzer.get_default_result"""
    # Arrange
    project_index = {"services": {}}
    instance = CodeQualityAnalyzer(project_index)

    # Act
    result = instance.get_default_result()

    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["code_smells"] == []


def test_AnalyzerFactory_create():
    """Test AnalyzerFactory.create"""
    # Arrange
    analyzer_name = "code_relationships"
    project_index = {"services": {}}

    # Act
    result = AnalyzerFactory.create(analyzer_name, project_index)

    # Assert
    assert result is not None
    assert isinstance(result, CodeRelationshipsAnalyzer)


def test_AnalyzerFactory_create_unknown_analyzer():
    """Test AnalyzerFactory.create with unknown analyzer"""
    # Arrange
    analyzer_name = "unknown_analyzer"
    project_index = {"services": {}}

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown analyzer: unknown_analyzer"):
        AnalyzerFactory.create(analyzer_name, project_index)


def test_AnalyzerFactory_create_all_analyzer_types():
    """Test AnalyzerFactory.create for all analyzer types"""
    # Arrange
    project_index = {"services": {}}
    analyzer_classes = {
        "code_relationships": CodeRelationshipsAnalyzer,
        "business_logic": BusinessLogicAnalyzer,
        "architecture": ArchitectureAnalyzer,
        "security": SecurityAnalyzer,
        "performance": PerformanceAnalyzer,
        "code_quality": CodeQualityAnalyzer,
    }

    for analyzer_name, expected_class in analyzer_classes.items():
        # Act
        result = AnalyzerFactory.create(analyzer_name, project_index)

        # Assert
        assert isinstance(result, expected_class)
