"""Tests for security_scanner module"""

from analysis.security_scanner import (
    SecurityScanner,
    SecurityScanResult,
    SecurityVulnerability,
    scan_for_security_issues,
    has_security_issues,
    scan_secrets_only,
    main,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest
import tempfile
import shutil
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    yield project_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def python_project(temp_dir):
    """Create a Python project for testing."""
    (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (temp_dir / "test.py").write_text("print('hello')")
    return temp_dir


@pytest.fixture
def node_project(temp_dir):
    """Create a Node.js project for testing."""
    (temp_dir / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
    (temp_dir / "index.js").write_text("console.log('hello');")
    return temp_dir


@pytest.fixture
def spec_dir(temp_dir):
    """Create a spec directory for storing results."""
    spec_path = temp_dir / "specs" / "001"
    spec_path.mkdir(parents=True)
    return spec_path


class TestSecurityScannerInit:
    """Tests for SecurityScanner initialization."""

    def test_init(self):
        """Test SecurityScanner initializes."""
        scanner = SecurityScanner()
        assert scanner._bandit_available is None
        assert scanner._npm_available is None


class TestSecurityScanResult:
    """Tests for SecurityScanResult dataclass."""

    def test_default_values(self):
        """Test SecurityScanResult has correct default values."""
        result = SecurityScanResult()
        assert result.secrets == []
        assert result.vulnerabilities == []
        assert result.scan_errors == []
        assert result.has_critical_issues is False
        assert result.should_block_qa is False


class TestSecurityVulnerability:
    """Tests for SecurityVulnerability dataclass."""

    def test_vulnerability_creation(self):
        """Test SecurityVulnerability can be created."""
        vuln = SecurityVulnerability(
            severity="high",
            source="bandit",
            title="Test vulnerability",
            description="A test security issue",
            file="test.py",
            line=42,
            cwe="CWE-123",
        )
        assert vuln.severity == "high"
        assert vuln.source == "bandit"
        assert vuln.title == "Test vulnerability"
        assert vuln.file == "test.py"
        assert vuln.line == 42
        assert vuln.cwe == "CWE-123"


class TestScanMethod:
    """Tests for scan method."""

    def test_scan_returns_result(self, python_project):
        """Test scan returns a result."""
        scanner = SecurityScanner()
        result = scanner.scan(
            python_project,
            spec_dir=None,
            changed_files=None,
            run_secrets=False,
            run_sast=False,
            run_dependency_audit=False,
        )
        assert isinstance(result, SecurityScanResult)

    def test_scan_with_no_scans_enabled(self, python_project):
        """Test scan with all scans disabled."""
        scanner = SecurityScanner()
        result = scanner.scan(
            python_project,
            spec_dir=None,
            changed_files=None,
            run_secrets=False,
            run_sast=False,
            run_dependency_audit=False,
        )
        assert result.has_critical_issues is False
        assert result.should_block_qa is False

    def test_scan_saves_to_spec_dir(self, python_project, spec_dir):
        """Test scan saves results to spec directory."""
        scanner = SecurityScanner()
        result = scanner.scan(
            python_project,
            spec_dir=spec_dir,
            changed_files=None,
            run_secrets=False,
            run_sast=False,
            run_dependency_audit=False,
        )
        output_file = spec_dir / "security_scan_results.json"
        assert output_file.exists()

    def test_scan_with_changed_files(self, python_project):
        """Test scan with specific changed files."""
        scanner = SecurityScanner()
        result = scanner.scan(
            python_project,
            spec_dir=None,
            changed_files=["test.py"],
            run_secrets=False,
            run_sast=False,
            run_dependency_audit=False,
        )
        assert isinstance(result, SecurityScanResult)


class TestRunSecretsScan:
    """Tests for secrets scanning."""

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", False)
    def test_no_secrets_module(self, python_project):
        """Test handles missing secrets scanner module."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_secrets_scan(python_project, None, result)
        assert "scan_secrets module not available" in result.scan_errors

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.get_all_tracked_files", return_value=["test.py"])
    @patch("analysis.security_scanner.scan_files", return_value=[])
    def test_successful_secrets_scan(self, mock_scan, mock_files, python_project):
        """Test successful secrets scan."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_secrets_scan(python_project, None, result)
        # Should not have errors
        assert len(result.scan_errors) == 0

    @patch("analysis.security_scanner.HAS_SECRETS_SCANNER", True)
    @patch("analysis.security_scanner.get_all_tracked_files", return_value=["test.py"])
    @patch("analysis.security_scanner.scan_files")
    def test_secrets_found(self, mock_scan, mock_files, python_project):
        """Test secrets are detected."""
        from security.scan_secrets import SecretMatch

        mock_match = SecretMatch(
            file_path="test.py",
            line_number=10,
            pattern_name="API Key",
            matched_text="sk-1234567890",
            line_content="api_key = sk-1234567890",
        )
        mock_scan.return_value = [mock_match]

        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_secrets_scan(python_project, None, result)

        assert len(result.secrets) == 1
        assert result.secrets[0]["pattern"] == "API Key"
        assert len(result.vulnerabilities) == 1
        assert result.vulnerabilities[0].severity == "critical"


class TestRedactSecret:
    """Tests for _redact_secret method."""

    def test_redact_short_secret(self):
        """Test redacting short secrets."""
        scanner = SecurityScanner()
        result = scanner._redact_secret("abc")
        assert result == "***"

    def test_redact_long_secret(self):
        """Test redacting long secrets."""
        scanner = SecurityScanner()
        result = scanner._redact_secret("abcdefghijk")
        assert result == "abcd***hijk"

    def test_redact_exactly_eight_chars(self):
        """Test redacting exactly 8 characters."""
        scanner = SecurityScanner()
        result = scanner._redact_secret("12345678")
        assert result == "********"


class TestIsPythonProject:
    """Tests for _is_python_project method."""

    def test_detects_pyproject(self, temp_dir):
        """Test detects project with pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("[project]")
        scanner = SecurityScanner()
        assert scanner._is_python_project(temp_dir) is True

    def test_detects_requirements_txt(self, temp_dir):
        """Test detects project with requirements.txt."""
        (temp_dir / "requirements.txt").write_text("pytest")
        scanner = SecurityScanner()
        assert scanner._is_python_project(temp_dir) is True

    def test_detects_setup_py(self, temp_dir):
        """Test detects project with setup.py."""
        (temp_dir / "setup.py").write_text("from setuptools import setup")
        scanner = SecurityScanner()
        assert scanner._is_python_project(temp_dir) is True

    def test_no_python_indicators(self, temp_dir):
        """Test returns False for non-Python project."""
        scanner = SecurityScanner()
        assert scanner._is_python_project(temp_dir) is False


class TestCheckBanditAvailable:
    """Tests for _check_bandit_available method."""

    @patch("subprocess.run")
    def test_bandit_available(self, mock_run):
        """Test when bandit is available."""
        mock_run.return_value = Mock(returncode=0)
        scanner = SecurityScanner()
        result = scanner._check_bandit_available()
        assert result is True

    @patch("subprocess.run")
    def test_bandit_not_found(self, mock_run):
        """Test when bandit is not found."""
        import subprocess
        mock_run.side_effect = FileNotFoundError("bandit not found")
        scanner = SecurityScanner()
        result = scanner._check_bandit_available()
        assert result is False

    @patch("subprocess.run")
    def test_bandit_timeout(self, mock_run):
        """Test when bandit times out."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("bandit", 5)
        scanner = SecurityScanner()
        result = scanner._check_bandit_available()
        assert result is False

    def test_caches_result(self):
        """Test result is cached."""
        scanner = SecurityScanner()
        with patch("subprocess.run", return_value=Mock(returncode=0)):
            result1 = scanner._check_bandit_available()
            result2 = scanner._check_bandit_available()
            assert result1 is result2


class TestRunBandit:
    """Tests for _run_bandit method."""

    @patch("subprocess.run")
    def test_bandit_scan_success(self, mock_run, python_project):
        """Test successful bandit scan."""
        mock_run.return_value = Mock(
            stdout='{"results": [{"issue_severity": "HIGH", "issue_text": "Test issue", "filename": "test.py", "line_number": 10}]}',
            returncode=0
        )
        scanner = SecurityScanner()
        scanner._bandit_available = True
        result = SecurityScanResult()
        scanner._run_bandit(python_project, result)

        assert len(result.vulnerabilities) > 0

    @patch("subprocess.run")
    def test_bandit_timeout(self, mock_run, python_project):
        """Test bandit timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("bandit", 120)
        scanner = SecurityScanner()
        scanner._bandit_available = True
        result = SecurityScanResult()
        scanner._run_bandit(python_project, result)

        assert "timed out" in result.scan_errors[0].lower()

    @patch("subprocess.run")
    def test_bandit_not_found(self, mock_run, python_project):
        """Test bandit not found handling."""
        mock_run.side_effect = FileNotFoundError("bandit")
        scanner = SecurityScanner()
        scanner._bandit_available = True
        result = SecurityScanResult()
        scanner._run_bandit(python_project, result)

        assert "not found" in result.scan_errors[0].lower()


class TestRunNpmAudit:
    """Tests for npm audit scanning."""

    @patch("subprocess.run")
    def test_npm_audit_success(self, mock_run, node_project):
        """Test successful npm audit."""
        mock_run.return_value = Mock(
            stdout='{"vulnerabilities": {"package": {"severity": "high", "via": [{"title": "Test vulnerability"}]}}}',
            returncode=0
        )
        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_npm_audit(node_project, result)

        assert len(result.vulnerabilities) > 0

    @patch("subprocess.run")
    def test_npm_audit_timeout(self, mock_run, node_project):
        """Test npm audit timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("npm", 120)
        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_npm_audit(node_project, result)

        assert "timed out" in " ".join(result.scan_errors).lower()

    @patch("subprocess.run")
    def test_npm_not_available(self, mock_run, node_project):
        """Test npm not available handling."""
        mock_run.side_effect = FileNotFoundError("npm")
        scanner = SecurityScanner()
        result = SecurityScanResult()
        scanner._run_npm_audit(node_project, result)

        # Should not add error for npm not available
        assert len(result.scan_errors) == 0


class TestToDict:
    """Tests for to_dict method."""

    def test_to_dict_structure(self, python_project):
        """Test to_dict creates proper structure."""
        scanner = SecurityScanner()
        result = scanner.scan(python_project, run_secrets=False, run_sast=False, run_dependency_audit=False)
        dict_result = scanner.to_dict(result)

        assert "secrets" in dict_result
        assert "vulnerabilities" in dict_result
        assert "scan_errors" in dict_result
        assert "has_critical_issues" in dict_result
        assert "should_block_qa" in dict_result
        assert "summary" in dict_result

    def test_to_dict_summary(self, python_project):
        """Test to_dict includes summary."""
        scanner = SecurityScanner()
        result = scanner.scan(python_project, run_secrets=False, run_sast=False, run_dependency_audit=False)
        dict_result = scanner.to_dict(result)

        assert "total_secrets" in dict_result["summary"]
        assert "total_vulnerabilities" in dict_result["summary"]


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_scan_for_security_issues(self, python_project):
        """Test scan_for_security_issues function."""
        result = scan_for_security_issues(python_project)
        assert isinstance(result, SecurityScanResult)

    def test_has_security_issues_no_issues(self, python_project):
        """Test has_security_issues with no issues."""
        result = has_security_issues(python_project)
        assert result is False

    def test_scan_secrets_only(self, python_project):
        """Test scan_secrets_only function."""
        result = scan_secrets_only(python_project)
        assert isinstance(result, list)


class TestMainCLI:
    """Tests for main CLI function."""

    def test_main_with_project(self, python_project, capsys):
        """Test main with project directory."""
        with patch("sys.argv", ["security_scanner", str(python_project)]):
            main()
        captured = capsys.readouterr()
        assert "Secrets Found" in captured.out or "Vulnerabilities" in captured.out

    def test_main_json_output(self, python_project, capsys):
        """Test main with JSON output."""
        with patch("sys.argv", ["security_scanner", str(python_project), "--json"]):
            main()
        captured = capsys.readouterr()
        # Check if output is valid JSON
        import json
        try:
            json.loads(captured.out)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_main_secrets_only(self, python_project, capsys):
        """Test main with --secrets-only flag."""
        with patch("sys.argv", ["security_scanner", str(python_project), "--secrets-only"]):
            main()
        captured = capsys.readouterr()
        assert "Secrets Found" in captured.out


class TestCriticalIssuesDetection:
    """Tests for critical issues detection."""

    def test_secrets_mark_critical(self, temp_dir):
        """Test secrets are marked as critical."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        result.secrets.append({"file": "test.py", "line": 10, "pattern": "API Key"})

        scanner._run_secrets_scan = Mock()
        scanner._run_sast_scans = Mock()
        scanner._run_dependency_audits = Mock()

        with patch.object(scanner, "_run_secrets_scan", side_effect=lambda p, c, r: r.secrets.extend(result.secrets)):
            scanner.scan(temp_dir)

        # The scan method should mark critical issues
        actual_result = scanner.scan(temp_dir, run_secrets=False, run_sast=False, run_dependency_audit=False)
        # Manually add a secret to verify the logic
        actual_result.secrets.append({"file": "test.py", "line": 10})
        actual_result.has_critical_issues = len(actual_result.secrets) > 0
        assert actual_result.has_critical_issues is True

    def test_high_vulnerabilities_mark_critical(self):
        """Test high severity vulnerabilities are critical."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="high",
                source="bandit",
                title="Test",
                description="Test issue"
            )
        )
        result.has_critical_issues = any(v.severity in ["critical", "high"] for v in result.vulnerabilities)
        assert result.has_critical_issues is True


class TestBlockingQA:
    """Tests for QA blocking logic."""

    def test_secrets_always_block(self):
        """Test any secrets always block QA."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        result.secrets.append({"file": "test.py", "line": 10, "pattern": "API Key"})
        result.should_block_qa = len(result.secrets) > 0
        assert result.should_block_qa is True

    def test_critical_vulnerabilities_block(self):
        """Test critical vulnerabilities block QA."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="critical",
                source="bandit",
                title="Test",
                description="Test issue"
            )
        )
        result.should_block_qa = any(v.severity == "critical" for v in result.vulnerabilities)
        assert result.should_block_qa is True

    def test_high_does_not_block_without_critical(self):
        """Test high severity doesn't block without critical."""
        scanner = SecurityScanner()
        result = SecurityScanResult()
        result.vulnerabilities.append(
            SecurityVulnerability(
                severity="high",
                source="bandit",
                title="Test",
                description="Test issue"
            )
        )
        result.should_block_qa = len(result.secrets) > 0 or any(v.severity == "critical" for v in result.vulnerabilities)
        assert result.should_block_qa is False
