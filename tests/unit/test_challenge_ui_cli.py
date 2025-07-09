"""
Unit tests for the ChallengeUICLI class.
"""
import pytest
import responses
import uuid
from unittest.mock import Mock, patch
from Folly.cli import ChallengeUICLI


class TestChallengeUICLI:
    """Test cases for ChallengeUICLI class."""

    @responses.activate
    def test_init_success(self, test_challenge_config, test_api_key):
        """Test ChallengeUICLI initialization with successful API call."""
        api_url = "http://test-api.com"
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            json=test_challenge_config,
            status=200
        )
        
        cli = ChallengeUICLI(api_url, test_api_key)
        
        assert cli.api_url == api_url
        assert cli.api_key == test_api_key
        assert len(cli.challenges) == 2
        assert cli.challenges[0]["name"] == "Test Challenge 1"
        assert cli.user_token is not None

    @responses.activate
    def test_init_without_api_key(self, test_challenge_config):
        """Test ChallengeUICLI initialization without API key."""
        api_url = "http://test-api.com"
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            json=test_challenge_config,
            status=200
        )
        
        cli = ChallengeUICLI(api_url)
        
        assert cli.api_url == api_url
        assert cli.api_key is None
        assert len(cli.challenges) == 2

    @responses.activate
    def test_init_api_failure(self):
        """Test ChallengeUICLI initialization with API failure."""
        api_url = "http://test-api.com"
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            status=500
        )
        
        cli = ChallengeUICLI(api_url)
        
        assert cli.api_url == api_url
        assert cli.challenges == []

    def test_api_url_normalization(self):
        """Test that API URL trailing slashes are normalized."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com/")
            assert cli.api_url == "http://test-api.com"

    def test_get_api_headers_with_api_key(self, test_api_key):
        """Test get_api_headers with API key."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com", test_api_key)
        
        headers = cli.get_api_headers()
        
        assert headers["Authorization"] == f"Bearer {test_api_key}"
        assert "X-User-Token" in headers

    def test_get_api_headers_without_api_key(self):
        """Test get_api_headers without API key."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com")
        
        headers = cli.get_api_headers()
        
        assert "Authorization" not in headers
        assert "X-User-Token" in headers

    def test_user_token_is_uuid(self):
        """Test that user_token is a valid UUID."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com")
        
        # Should be able to parse as UUID without exception
        uuid.UUID(cli.user_token)

    @responses.activate
    def test_fetch_challenges_success(self, test_challenge_config):
        """Test successful fetch_challenges."""
        api_url = "http://test-api.com"
        cli = ChallengeUICLI(api_url)
        
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            json=test_challenge_config,
            status=200
        )
        
        cli.fetch_challenges()
        
        assert len(cli.challenges) == 2
        assert cli.challenges[0]["name"] == "Test Challenge 1"

    @responses.activate
    def test_fetch_challenges_failure(self):
        """Test fetch_challenges with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url)
        
        responses.add(
            responses.GET,
            f"{api_url}/challenges",
            status=500
        )
        
        cli.fetch_challenges()
        
        assert cli.challenges == []

    def test_get_challenge_by_name_found(self, test_challenge_config):
        """Test get_challenge_by_name when challenge exists."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com")
            cli.challenges = test_challenge_config
        
        challenge = cli.get_challenge_by_name("test_challenge_1")
        
        assert challenge is not None
        assert challenge["name"] == "Test Challenge 1"

    def test_get_challenge_by_name_not_found(self, test_challenge_config):
        """Test get_challenge_by_name when challenge doesn't exist."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com")
            cli.challenges = test_challenge_config
        
        challenge = cli.get_challenge_by_name("non_existent_challenge")
        
        assert challenge is None

    def test_get_challenge_by_name_case_insensitive(self, test_challenge_config):
        """Test get_challenge_by_name is case insensitive."""
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI("http://test-api.com")
            cli.challenges = test_challenge_config
        
        challenge = cli.get_challenge_by_name("TEST_CHALLENGE_1")
        
        assert challenge is not None
        assert challenge["name"] == "Test Challenge 1"

    @responses.activate
    def test_submit_prompt_success(self, sample_llm_response, test_api_key):
        """Test successful submit_prompt."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url, test_api_key)
        
        responses.add(
            responses.POST,
            f"{api_url}/challenge/test_challenge",
            json=sample_llm_response,
            status=200
        )
        
        result = cli.submit_prompt("test_challenge", "test prompt")
        
        assert result["status"] == "success"
        assert result["input"] == "Test prompt"
        
        # Check that headers were sent
        request = responses.calls[0].request
        assert "Authorization" in request.headers
        assert "X-User-Token" in request.headers

    @responses.activate
    def test_submit_prompt_failure(self):
        """Test submit_prompt with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/challenge/test_challenge",
            status=500
        )
        
        result = cli.submit_prompt("test_challenge", "test prompt")
        
        assert "status" in result
        assert result["status"] == "error"

    @responses.activate
    def test_reset_challenge_success(self, test_api_key):
        """Test successful reset_challenge."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url, test_api_key)
        
        responses.add(
            responses.POST,
            f"{api_url}/reset/test_challenge",
            json={"status": "success", "message": "Reset successful"},
            status=200
        )
        
        result = cli.reset_challenge("test_challenge")
        
        assert result["status"] == "success"

    @responses.activate
    def test_reset_challenge_failure(self):
        """Test reset_challenge with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/reset/test_challenge",
            status=500
        )
        
        result = cli.reset_challenge("test_challenge")
        
        assert "status" in result
        assert result["status"] == "error"

    @responses.activate
    def test_validate_response_success(self, test_api_key):
        """Test successful validate_response."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url, test_api_key)
        
        responses.add(
            responses.POST,
            f"{api_url}/validate/test_challenge",
            json={"valid": True, "match_type": "exact"},
            status=200
        )
        
        result = cli.validate_response("test_challenge", "test response")
        
        assert result["valid"]
        assert result["match_type"] == "exact"

    @responses.activate
    def test_validate_response_failure(self):
        """Test validate_response with API failure."""
        api_url = "http://test-api.com"
        
        with patch.object(ChallengeUICLI, 'fetch_challenges'):
            cli = ChallengeUICLI(api_url)
        
        responses.add(
            responses.POST,
            f"{api_url}/validate/test_challenge",
            status=500
        )
        
        result = cli.validate_response("test_challenge", "test response")
        
        assert not result["valid"]
        assert result["validation_issue"]
        assert "Validation error" in result["reason"]