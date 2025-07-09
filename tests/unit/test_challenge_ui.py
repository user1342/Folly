"""
Unit tests for the ChallengeUI class.
"""
import pytest
import responses
import uuid
from unittest.mock import Mock, patch
from Folly.ui_app import ChallengeUI


class TestChallengeUI:
    """Test cases for ChallengeUI class."""

    @responses.activate
    def test_init_success(self, test_challenge_config):
        """Test ChallengeUI initialization with successful API call."""
        api_url = "http://test-api.com"
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            json=test_challenge_config,
            status=200
        )
        
        ui = ChallengeUI(api_url)
        
        assert ui.api_url == api_url
        assert len(ui.challenges) == 2
        assert ui.challenges[0]["name"] == "Test Challenge 1"

    @responses.activate
    def test_init_api_failure(self):
        """Test ChallengeUI initialization with API failure."""
        api_url = "http://test-api.com"
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            status=500
        )
        
        ui = ChallengeUI(api_url)
        
        assert ui.api_url == api_url
        assert ui.challenges == []

    def test_api_url_normalization(self):
        """Test that API URL trailing slashes are normalized."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://test-api.com/")
            assert ui.api_url == "http://test-api.com"

    def test_get_effective_url_with_user_setting(self):
        """Test get_effective_url with user-specific API URL."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://default-api.com")
        
        mock_session = {"user_api_url": "http://user-api.com"}
        result = ui.get_effective_url(mock_session)
        
        assert result == "http://user-api.com"

    def test_get_effective_url_without_user_setting(self):
        """Test get_effective_url without user-specific API URL."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://default-api.com")
        
        mock_session = {}
        result = ui.get_effective_url(mock_session)
        
        assert result == "http://default-api.com"

    def test_get_api_headers_with_all_settings(self):
        """Test get_api_headers with all user settings."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://test-api.com")
        
        mock_session = {
            "user_api_key": "test-key-123",
            "user_token": "user-token-456"
        }
        
        headers = ui.get_api_headers(mock_session)
        
        assert headers["Authorization"] == "Bearer test-key-123"
        assert headers["X-User-Token"] == "user-token-456"

    def test_get_api_headers_empty_session(self):
        """Test get_api_headers with empty session."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://test-api.com")
        
        headers = ui.get_api_headers({})
        
        assert headers == {}

    @responses.activate
    def test_fetch_challenges_success(self, test_challenge_config):
        """Test successful fetch_challenges."""
        api_url = "http://test-api.com"
        ui = ChallengeUI(api_url)
        
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            json=test_challenge_config,
            status=200
        )
        
        ui.fetch_challenges()
        
        assert len(ui.challenges) == 2
        assert ui.challenges[0]["name"] == "Test Challenge 1"

    @responses.activate
    def test_fetch_challenges_failure(self):
        """Test fetch_challenges with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            status=500
        )
        
        ui.fetch_challenges()
        
        assert ui.challenges == []

    def test_get_challenge_by_name_found(self, test_challenge_config):
        """Test get_challenge_by_name when challenge exists."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://test-api.com")
            ui.challenges = test_challenge_config
        
        challenge = ui.get_challenge_by_name("test_challenge_1")
        
        assert challenge is not None
        assert challenge["name"] == "Test Challenge 1"

    def test_get_challenge_by_name_not_found(self, test_challenge_config):
        """Test get_challenge_by_name when challenge doesn't exist."""
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI("http://test-api.com")
            ui.challenges = test_challenge_config
        
        challenge = ui.get_challenge_by_name("non_existent_challenge")
        
        assert challenge is None

    @responses.activate
    def test_submit_prompt_success(self, sample_llm_response):
        """Test successful submit_prompt."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/challenge/test_challenge",
            json=sample_llm_response,
            status=200
        )
        
        result = ui.submit_prompt("test_challenge", "test prompt")
        
        assert result["status"] == "success"
        assert result["input"] == "Test prompt"

    @responses.activate
    def test_submit_prompt_with_session(self, sample_llm_response):
        """Test submit_prompt with session headers."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/challenge/test_challenge",
            json=sample_llm_response,
            status=200
        )
        
        mock_session = {
            "user_api_key": "test-key",
            "user_token": "test-token"
        }
        
        result = ui.submit_prompt("test_challenge", "test prompt", mock_session)
        
        assert result["status"] == "success"
        
        # Check that headers were sent
        request = responses.calls[0].request
        assert "Authorization" in request.headers
        assert "X-User-Token" in request.headers

    @responses.activate
    def test_submit_prompt_failure(self):
        """Test submit_prompt with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/challenge/test_challenge",
            status=500
        )
        
        result = ui.submit_prompt("test_challenge", "test prompt")
        
        assert "status" in result
        assert result["status"] == "error"

    @responses.activate
    def test_reset_challenge_success(self):
        """Test successful reset_challenge."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/reset/test_challenge",
            json={"status": "success", "message": "Reset successful"},
            status=200
        )
        
        result = ui.reset_challenge("test_challenge")
        
        assert result["status"] == "success"

    @responses.activate
    def test_reset_challenge_failure(self):
        """Test reset_challenge with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/reset/test_challenge",
            status=500
        )
        
        result = ui.reset_challenge("test_challenge")
        
        assert "status" in result
        assert result["status"] == "error"

    @responses.activate
    def test_validate_response_success(self):
        """Test successful validate_response."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/validate/test_challenge",
            json={"valid": True, "match_type": "exact"},
            status=200
        )
        
        result = ui.validate_response("test_challenge", "test response")
        
        assert result["valid"]
        assert result["match_type"] == "exact"

    @responses.activate
    def test_validate_response_failure(self):
        """Test validate_response with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUI, 'fetch_challenges'):
            ui = ChallengeUI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/validate/test_challenge",
            status=500
        )
        
        result = ui.validate_response("test_challenge", "test response")
        
        assert not result["valid"]
        assert result["validation_issue"]
        assert "Validation error" in result["reason"]