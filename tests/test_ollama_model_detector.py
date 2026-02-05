"""Tests for ollama_model_detector"""

import json
import urllib.error
from ollama_model_detector import cmd_check_status, cmd_get_recommended_models, cmd_list_embedding_models, cmd_list_models, cmd_pull_model, fetch_ollama_api, get_embedding_description, get_embedding_dim, get_model_min_version, get_ollama_version, is_embedding_model, main, output_error, output_json, parse_version, version_gte
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import sys


def test_parse_version():
    """Test parse_version"""

    # Test valid version string
    result = parse_version("1.2.3")
    assert result == (1, 2, 3)

    # Test version with prerelease suffix
    result = parse_version("1.2.3-rc1")
    assert result == (1, 2, 3)

    # Test empty version
    result = parse_version(None)
    assert result == (0, 0, 0)

    # Test invalid version
    result = parse_version("invalid")
    assert result == (0, 0, 0)


def test_version_gte():
    """Test version_gte"""

    # Test greater version
    result = version_gte("1.2.3", "1.2.2")
    assert result is True

    # Test equal version
    result = version_gte("1.2.3", "1.2.3")
    assert result is True

    # Test lower version
    result = version_gte("1.2.3", "1.2.4")
    assert result is False

    # Test None version
    result = version_gte(None, "1.2.3")
    assert result is False


def test_output_json(capsys):
    """Test output_json"""

    # Mock sys.exit to prevent actual exit
    with patch("sys.exit"):
        # Test successful output with data
        output_json(True, {"key": "value"})

    captured = capsys.readouterr()
    assert '{"success": true, "data": {"key": "value"}}' in captured.out

    # Test output with error
    with patch("sys.exit"):
        output_json(False, error="Test error")

    captured = capsys.readouterr()
    assert '{"success": false, "error": "Test error"}' in captured.out


def test_output_error(capsys):
    """Test output_error"""

    # Mock sys.exit to prevent actual exit
    with patch("sys.exit"):
        output_error("Something went wrong")

    captured = capsys.readouterr()
    assert '{"success": false, "error": "Something went wrong"}' in captured.out


def test_fetch_ollama_api():
    """Test fetch_ollama_api"""

    # Mock successful API response
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = fetch_ollama_api("http://localhost:11434", "api/tags")
        assert result == {"status": "ok"}

    # Test URLError (line 181)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        result = fetch_ollama_api("http://localhost:11434", "api/tags")
        assert result is None

    # Test JSON decode error (line 182-183)
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"invalid json'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = fetch_ollama_api("http://localhost:11434", "api/tags")
        assert result is None

    # Test generic Exception (lines 184-185)
    with patch("urllib.request.urlopen", side_effect=Exception("Unexpected error")):
        result = fetch_ollama_api("http://localhost:11434", "api/tags")
        assert result is None


def test_get_ollama_version():
    """Test get_ollama_version"""

    # Mock successful version fetch
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        mock_fetch.return_value = {"version": "0.1.0"}
        result = get_ollama_version("http://localhost:11434")
        assert result == "0.1.0"

    # Test no version in response
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        mock_fetch.return_value = {}
        result = get_ollama_version("http://localhost:11434")
        assert result is None


def test_is_embedding_model():
    """Test is_embedding_model"""

    # Test known embedding models
    assert is_embedding_model("nomic-embed-text") is True
    assert is_embedding_model("embeddinggemma") is True
    assert is_embedding_model("qwen3-embedding") is True

    # Test models with embedding patterns
    assert is_embedding_model("bge-base-en") is True
    assert is_embedding_model("e5-large") is True
    assert is_embedding_model("all-minilm") is True

    # Test other embedding patterns (for coverage of line 208)
    assert is_embedding_model("arctic-embed") is True
    assert is_embedding_model("jina-embeddings-v2") is True
    assert is_embedding_model("mxbai-embed-large") is True
    assert is_embedding_model("paraphrase-multilingual") is True

    # Test non-embedding model
    assert is_embedding_model("llama3.1") is False
    assert is_embedding_model("mistral") is False


def test_get_embedding_dim():
    """Test get_embedding_dim"""

    # Test known embedding models
    assert get_embedding_dim("nomic-embed-text") == 768
    # qwen3-embedding:4b returns 1024 (qwen3-embedding base), not 2560
    assert get_embedding_dim("qwen3-embedding:4b") == 1024
    assert get_embedding_dim("bge-small-en") == 384

    # Test models with size patterns
    assert get_embedding_dim("my-large-embed") == 1024
    assert get_embedding_dim("my-base-embed") == 768
    assert get_embedding_dim("my-small-embed") == 384

    # Test unknown model
    assert get_embedding_dim("unknown-model") is None


def test_get_embedding_description():
    """Test get_embedding_description"""

    # Test known embedding models
    result = get_embedding_description("nomic-embed-text")
    assert "Nomic AI" in result

    result = get_embedding_description("qwen3-embedding")
    assert "Qwen3" in result

    # Test unknown model returns default
    result = get_embedding_description("unknown-embed")
    assert result == "Embedding model"


def test_get_model_min_version():
    """Test get_model_min_version"""

    # Test models with minimum version
    result = get_model_min_version("qwen3-embedding")
    assert result == "0.10.0"

    result = get_model_min_version("qwen3-embedding:4b")
    assert result == "0.10.0"

    # Test models without minimum version
    result = get_model_min_version("nomic-embed-text")
    assert result is None

    result = get_model_min_version("unknown-model")
    assert result is None


def test_cmd_check_status():
    """Test cmd_check_status"""

    # Mock arguments
    args = MagicMock()
    args.base_url = "http://localhost:11434"

    # Mock successful status check
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = {"version": "0.1.0"}
            cmd_check_status(args)

    # Test when version endpoint fails but tags endpoint works (lines 280-291)
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            # First call (version) returns None, second call (tags) returns data
            mock_fetch.side_effect = [None, {"models": []}]
            cmd_check_status(args)

    # Test when both endpoints fail
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = None
            cmd_check_status(args)

    # Test with unknown version
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = {}
            cmd_check_status(args)


def test_cmd_list_models():
    """Test cmd_list_models"""

    # Mock arguments
    args = MagicMock()
    args.base_url = "http://localhost:11434"

    # Mock successful list
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = {
                "models": [
                    {"name": "nomic-embed-text", "size": 274000000, "modified_at": "2024-01-01"},
                    {"name": "llama3.1", "size": 4000000000, "modified_at": "2024-01-01"}
                ]
            }
            cmd_list_models(args)

    # Test error handling when API fails (lines 308-309)
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = None
            cmd_list_models(args)


def test_cmd_list_embedding_models():
    """Test cmd_list_embedding_models"""

    # Mock arguments
    args = MagicMock()
    args.base_url = "http://localhost:11434"

    # Mock successful list
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = {
                "models": [
                    {"name": "nomic-embed-text", "size": 274000000, "modified_at": "2024-01-01"},
                    {"name": "llama3.1", "size": 4000000000, "modified_at": "2024-01-01"}
                ]
            }
            cmd_list_embedding_models(args)

    # Test error handling when API fails (lines 350-351)
    with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
        with patch("sys.exit"):
            mock_fetch.return_value = None
            cmd_list_embedding_models(args)


def test_cmd_get_recommended_models():
    """Test cmd_get_recommended_models"""

    # Mock arguments
    args = MagicMock()
    args.base_url = "http://localhost:11434"

    # Mock successful recommended list
    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
            with patch("sys.exit"):
                mock_version.return_value = "0.10.0"
                mock_fetch.return_value = {
                    "models": [
                        {"name": "nomic-embed-text", "size": 274000000, "modified_at": "2024-01-01"}
                    ]
                }
                cmd_get_recommended_models(args)

    # Test when Ollama version cannot be verified (line 419)
    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
            with patch("sys.exit"):
                mock_version.return_value = None
                mock_fetch.return_value = {"models": []}
                cmd_get_recommended_models(args)

    # Test when version is incompatible (lines 417, 419)
    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.fetch_ollama_api") as mock_fetch:
            with patch("sys.exit"):
                mock_version.return_value = "0.9.0"
                mock_fetch.return_value = {"models": []}
                cmd_get_recommended_models(args)


def test_cmd_pull_model():
    """Test cmd_pull_model"""

    # Mock arguments
    args = MagicMock()
    args.model = "nomic-embed-text"
    args.base_url = "http://localhost:11434"

    # Mock version check
    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_json"):
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                # Mock successful pull
                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_response = MagicMock()
                    mock_response.read.return_value = b'{"status": "success"}\n'
                    mock_response.__iter__ = MagicMock(return_value=iter([b'{"status": "success"}\n']))
                    mock_response.__enter__ = MagicMock(return_value=mock_response)
                    mock_response.__exit__ = MagicMock(return_value=False)
                    mock_urlopen.return_value = mock_response

                    cmd_pull_model(args)

    # Test missing model name error (lines 447-448)
    args_no_model = MagicMock()
    args_no_model.model = ""
    with patch("ollama_model_detector.output_error") as mock_error:
        cmd_pull_model(args_no_model)
        mock_error.assert_called()

    # Test version compatibility check failure (lines 455-461)
    args_compat = MagicMock()
    args_compat.model = "qwen3-embedding"
    args_compat.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_error") as mock_error:
                mock_version.return_value = "0.9.0"
                mock_min_version.return_value = "0.10.0"
                cmd_pull_model(args_compat)
                mock_error.assert_called()

    # Test streaming error handling (lines 479-490, 494, 508-509)
    args_stream = MagicMock()
    args_stream.model = "qwen3-embedding"
    args_stream.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_json") as mock_output:
                with patch("ollama_model_detector.output_error") as mock_error:
                    mock_version.return_value = "0.10.0"
                    mock_min_version.return_value = None

                    with patch("urllib.request.urlopen") as mock_urlopen:
                        # Mock streaming response with error
                        error_line = json.dumps({"error": "requires newer version of Ollama"}).encode("utf-8")
                        mock_response = MagicMock()
                        mock_response.__iter__ = MagicMock(return_value=iter([error_line]))
                        mock_response.__enter__ = MagicMock(return_value=mock_response)
                        mock_response.__exit__ = MagicMock(return_value=False)
                        mock_urlopen.return_value = mock_response

                        cmd_pull_model(args_stream)
                        mock_error.assert_called()

    # Test connection error handling (lines 520-525)
    args_error = MagicMock()
    args_error.model = "nomic-embed-text"
    args_error.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_error") as mock_error:
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                with patch("urllib.request.urlopen", side_effect=Exception("Connection failed")):
                    cmd_pull_model(args_error)
                    mock_error.assert_called()

    # Test progress streaming (line 494)
    args_progress = MagicMock()
    args_progress.model = "nomic-embed-text"
    args_progress.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_json") as mock_output:
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                # Mock streaming response with progress
                progress_line = json.dumps({"completed": 50, "total": 100, "status": "downloading"}).encode("utf-8")
                success_line = json.dumps({"status": "success"}).encode("utf-8")
                mock_response = MagicMock()
                mock_response.__iter__ = MagicMock(return_value=iter([progress_line, success_line]))
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)

                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_urlopen.return_value = mock_response
                    cmd_pull_model(args_progress)
                    mock_output.assert_called()

    # Test HTTP error (line 523)
    args_http_error = MagicMock()
    args_http_error.model = "nomic-embed-text"
    args_http_error.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("sys.exit"):
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None)):
                    cmd_pull_model(args_http_error)

    # Test URL error (line 521)
    args_url_error = MagicMock()
    args_url_error.model = "nomic-embed-text"
    args_url_error.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("sys.exit"):
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
                    cmd_pull_model(args_url_error)

    # Test JSON decode error during streaming (lines 508-509)
    args_json_error = MagicMock()
    args_json_error.model = "nomic-embed-text"
    args_json_error.base_url = "http://localhost:11434"

    with patch("ollama_model_detector.get_ollama_version") as mock_version:
        with patch("ollama_model_detector.get_model_min_version") as mock_min_version:
            with patch("ollama_model_detector.output_json") as mock_output:
                mock_version.return_value = "0.10.0"
                mock_min_version.return_value = None

                # Mock streaming response with invalid JSON followed by success
                invalid_line = b'{"invalid": json}'
                success_line = json.dumps({"status": "success"}).encode("utf-8")
                mock_response = MagicMock()
                mock_response.__iter__ = MagicMock(return_value=iter([invalid_line, success_line]))
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)

                with patch("urllib.request.urlopen") as mock_urlopen:
                    mock_urlopen.return_value = mock_response
                    cmd_pull_model(args_json_error)
                    mock_output.assert_called()


def test_main():
    """Test main with command-line arguments"""

    # Test with valid command
    with patch("sys.argv", ["ollama_model_detector.py", "check-status"]):
        with patch("ollama_model_detector.fetch_ollama_api", return_value={"version": "0.1.0"}):
            with patch("sys.exit"):
                main()

    # Test with no command (should show help)
    with patch("sys.argv", ["ollama_model_detector.py"]):
        with patch("sys.exit"):
            main()

    # Test with unknown command (line 590)
    with patch("sys.argv", ["ollama_model_detector.py", "invalid-command"]):
        with patch("sys.exit"):
            main()
