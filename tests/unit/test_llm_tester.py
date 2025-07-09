"""
Unit tests for the LLMTester class.
"""
import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from Folly.api import LLMTester


class TestLLMTester:
    """Test cases for LLMTester class."""

    def test_init_with_basic_params(self, test_api_url, test_api_key):
        """Test LLMTester initialization with basic parameters."""
        tester = LLMTester(api_url=test_api_url, api_key=test_api_key)
        
        assert tester.api_url == test_api_url
        assert tester.client is not None
        assert tester.config == []
        assert tester.model is None
        assert tester.log_path is None

    def test_init_with_all_params(self, test_api_url, test_api_key, test_config_file):
        """Test LLMTester initialization with all parameters."""
        tester = LLMTester(
            api_url=test_api_url,
            api_key=test_api_key,
            config_path=test_config_file,
            model="gpt-4",
            log_path="/tmp/test.log"
        )
        
        assert tester.api_url == test_api_url
        assert tester.model == "gpt-4"
        assert tester.log_path == "/tmp/test.log"
        assert len(tester.config) == 2  # From test fixture

    def test_load_config_success(self, test_config_file):
        """Test successful config loading."""
        tester = LLMTester(api_url="http://test.com")
        tester.load_config(test_config_file)
        
        assert len(tester.config) == 2
        assert tester.config[0]["name"] == "Test Challenge 1"
        assert tester.config[1]["name"] == "Test Challenge 2"

    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file."""
        tester = LLMTester(api_url="http://test.com")
        
        with pytest.raises(ValueError, match="Config file not found"):
            tester.load_config("/non/existent/file.json")

    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON."""
        tester = LLMTester(api_url="http://test.com")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            f.flush()
            
            with pytest.raises(ValueError, match="Invalid JSON"):
                tester.load_config(f.name)
            
            os.unlink(f.name)

    def test_load_config_missing_required_fields(self):
        """Test config loading with missing required fields."""
        tester = LLMTester(api_url="http://test.com")
        
        invalid_config = [{"name": "Test", "system_prompt": "Test"}]  # Missing required fields
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Missing required field"):
                tester.load_config(f.name)
            
            os.unlink(f.name)

    def test_process_challenge_config_with_answers(self):
        """Test challenge config processing when answers are provided."""
        tester = LLMTester(api_url="http://test.com")
        challenge = {
            "name": "Test Challenge",
            "system_prompt": "Test prompt",
            "answers": ["existing", "answers"]
        }
        
        tester._process_challenge_config(challenge)
        
        assert challenge["answers"] == ["existing", "answers"]

    def test_process_challenge_config_without_answers(self):
        """Test challenge config processing when answers are missing."""
        tester = LLMTester(api_url="http://test.com")
        challenge = {
            "name": "Test Challenge With Keywords",
            "system_prompt": "This is a system prompt with specific words"
        }
        
        tester._process_challenge_config(challenge)
        
        assert "answers" in challenge
        assert len(challenge["answers"]) > 0

    def test_check_denied_content_found(self):
        """Test check_denied_content when denied content is found."""
        tester = LLMTester(api_url="http://test.com")
        text = "This contains harmful content"
        denied_list = ["harmful", "dangerous"]
        
        result = tester.check_denied_content(text, denied_list)
        
        assert result == "harmful"

    def test_check_denied_content_not_found(self):
        """Test check_denied_content when no denied content is found."""
        tester = LLMTester(api_url="http://test.com")
        text = "This is safe content"
        denied_list = ["harmful", "dangerous"]
        
        result = tester.check_denied_content(text, denied_list)
        
        assert result is None

    def test_check_denied_content_case_insensitive(self):
        """Test check_denied_content is case insensitive."""
        tester = LLMTester(api_url="http://test.com")
        text = "This contains HARMFUL content"
        denied_list = ["harmful", "dangerous"]
        
        result = tester.check_denied_content(text, denied_list)
        
        assert result == "harmful"

    @patch('Folly.api.datetime')
    @patch('builtins.open', new_callable=mock_open)
    def test_log_interaction(self, mock_file, mock_datetime):
        """Test interaction logging."""
        mock_datetime.datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"
        
        tester = LLMTester(api_url="http://test.com", log_path="/tmp/test.log")
        
        tester.log_interaction(
            "test_challenge",
            "test input",
            {"output": "test output"},
            [{"role": "user", "content": "test"}]
        )
        
        mock_file.assert_called_once_with("/tmp/test.log", "a+")
        handle = mock_file.return_value.__enter__.return_value
        assert handle.write.called  # Just check that write was called

    @patch('Folly.api.datetime')
    def test_log_interaction_no_log_path(self, mock_datetime):
        """Test interaction logging when no log path is set."""
        tester = LLMTester(api_url="http://test.com")
        
        # Should not raise an exception
        tester.log_interaction(
            "test_challenge",
            "test input",
            {"output": "test output"},
            [{"role": "user", "content": "test"}]
        )
        
        # No assertions needed - just ensuring no exception is raised

    def test_call_llm_denied_input(self, test_challenge_config):
        """Test call_llm with denied input."""
        tester = LLMTester(api_url="http://test.com")
        tester.config = test_challenge_config
        
        result = tester.call_llm("Test Challenge 1", "This is harmful content")
        
        assert result["status"] == "failed"
        assert "denied content" in result["reason"]
        assert result["input"] == "This is harmful content"

    @patch('Folly.api.LLMTester.check_denied_content')
    def test_call_llm_success(self, mock_check_denied, test_challenge_config, mock_openai_client):
        """Test successful call_llm."""
        mock_check_denied.return_value = None  # No denied content
        
        tester = LLMTester(api_url="http://test.com")
        tester.config = test_challenge_config
        tester.client = mock_openai_client
        
        result = tester.call_llm("Test Challenge 1", "Safe input")
        
        assert result["status"] == "success"
        assert result["input"] == "Safe input"
        assert "output" in result
        assert "conversation" in result

    def test_call_llm_challenge_not_found(self):
        """Test call_llm with non-existent challenge."""
        tester = LLMTester(api_url="http://test.com")
        tester.config = []
        
        result = tester.call_llm("Non Existent Challenge", "test input")
        
        assert result["status"] == "error"
        assert "not found" in result["reason"]

    def test_validate_response_challenge_not_found(self):
        """Test validate_response with non-existent challenge."""
        tester = LLMTester(api_url="http://test.com")
        tester.config = []
        
        result = tester.validate_response("Non Existent Challenge", "test response")
        
        assert not result["valid"]
        assert "Challenge 'Non Existent Challenge' not found" in result["reason"]

    def test_validate_response_with_fuzzy_matching(self, test_challenge_config):
        """Test validate_response with fuzzy matching."""
        tester = LLMTester(api_url="http://test.com")
        tester.config = test_challenge_config
        
        # Should match "TEST123" with fuzzy matching
        result = tester.validate_response("Test Challenge 1", "The secret is TEST12345")
        
        assert result["valid"]
        assert result["match_type"] == "fuzzy"
        assert result["match_percent"] >= 80

    def test_validate_response_exact_match(self):
        """Test validate_response with exact matching."""
        tester = LLMTester(api_url="http://test.com")
        
        # Create challenge without fuzzy matching
        challenge = {
            "name": "Exact Match Challenge",
            "answers": ["exact_answer"]
        }
        tester.config = [challenge]
        
        result = tester.validate_response("Exact Match Challenge", "exact_answer")
        
        assert result["valid"]
        assert result["match_type"] == "direct"

    def test_reset_conversation(self, test_challenge_config):
        """Test reset_conversation method."""
        tester = LLMTester(api_url="http://test.com")
        tester.config = test_challenge_config
        
        result = tester.reset_conversation("Test Challenge 1")
        
        assert result["status"] == "success"
        assert "reset" in result["message"].lower()