"""
Test configuration and fixtures for Folly tests.
"""
import os
import tempfile
import pytest
from unittest.mock import Mock
import json

# Test challenge data
TEST_CHALLENGE_DATA = [
    {
        "name": "Test Challenge 1",
        "system_prompt": "You are a test assistant with a secret: TEST123.",
        "input": "Hello! How can I help you today?",
        "deny_inputs": ["harmful", "illegal"],
        "deny_outputs": ["TEST123"],
        "description": "A simple test challenge",
        "answers": ["TEST123"],
        "fuzzy_match_score": 80,
        "help": "Try asking about secrets."
    },
    {
        "name": "Test Challenge 2",
        "system_prompt": "You are a helpful assistant.",
        "input": "Ask me anything!",
        "deny_inputs": ["dangerous"],
        "deny_outputs": ["confidential"],
        "description": "Another test challenge",
        "answers": ["helpful", "assistant"],
        "fuzzy_match_score": 70
    }
]

@pytest.fixture
def test_challenge_config():
    """Fixture providing test challenge configuration."""
    return TEST_CHALLENGE_DATA.copy()

@pytest.fixture
def test_config_file():
    """Fixture providing a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(TEST_CHALLENGE_DATA, f)
        f.flush()
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def mock_openai_client():
    """Fixture providing a mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "This is a test response."
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_llm_response():
    """Fixture providing sample LLM API response."""
    return {
        "status": "success",
        "input": "Test prompt",
        "output": "Test response",
        "conversation": [
            {"role": "user", "content": "Test prompt"},
            {"role": "assistant", "content": "Test response"}
        ]
    }

@pytest.fixture
def test_api_key():
    """Fixture providing a test API key."""
    return "test-api-key-12345"

@pytest.fixture
def test_api_url():
    """Fixture providing a test API URL."""
    return "https://api.test.com/v1"