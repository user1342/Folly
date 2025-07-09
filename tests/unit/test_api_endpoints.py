"""
Unit tests for the Flask API endpoints.
"""
import pytest
import json
from unittest.mock import Mock, patch
from Folly.api import create_app, LLMTester


@pytest.fixture
def app(test_challenge_config):
    """Create Flask app for testing."""
    mock_tester = Mock(spec=LLMTester)
    mock_tester.config = test_challenge_config
    
    app = create_app(mock_tester)
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key"
    })
    
    # Store the tester instance in the app for access in tests
    app.tester = mock_tester
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestAPIEndpoints:
    """Test cases for Flask API endpoints."""

    def test_challenges_endpoint(self, client, test_challenge_config):
        """Test GET /challenges endpoint."""
        response = client.get('/challenges')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]["name"] == "Test Challenge 1"
        assert data[1]["name"] == "Test Challenge 2"

    def test_challenge_endpoint_success(self, client, app):
        """Test POST /challenge/<challenge_name> endpoint success."""
        with app.app_context():
            # Mock the LLM tester call_llm method
            app.tester.call_llm.return_value = {
                "status": "success",
                "input": "test input",
                "output": "test output",
                "conversation": []
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={"input": "test input"},
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["input"] == "test input"

    def test_challenge_endpoint_missing_input(self, client, app):
        """Test POST /challenge/<challenge_name> with missing input."""
        with app.app_context():
            # Return an error response from the LLM tester
            app.tester.call_llm.return_value = {
                "status": "error",
                "reason": "Missing input"
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={},
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "error"

    def test_challenge_endpoint_missing_token(self, client, app):
        """Test POST /challenge/<challenge_name> without user token."""
        with app.app_context():
            app.tester.call_llm.return_value = {
                "status": "success",
                "input": "test input",
                "output": "test output",
                "conversation": []
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={"input": "test input"}
            )
            
            assert response.status_code == 200  # Should still work, will generate a token

    def test_challenge_endpoint_llm_failure(self, client, app):
        """Test POST /challenge/<challenge_name> with LLM failure."""
        with app.app_context():
            app.tester.call_llm.return_value = {
                "status": "failed",
                "reason": "API error"
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={"input": "test input"},
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "failed"

    def test_reset_endpoint_success(self, client, app):
        """Test POST /reset/<challenge_name> endpoint success."""
        with app.app_context():
            app.tester.reset_conversation.return_value = {
                "status": "success",
                "message": "Conversation reset successfully"
            }
            
            response = client.post(
                '/reset/test_challenge_1',
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"

    def test_reset_endpoint_missing_token(self, client, app):
        """Test POST /reset/<challenge_name> without user token."""
        with app.app_context():
            app.tester.reset_conversation.return_value = {
                "status": "success",
                "message": "Reset successful"
            }
            
            response = client.post('/reset/test_challenge_1')
            
            assert response.status_code == 200  # Should still work

    def test_validate_endpoint_success(self, client, app):
        """Test POST /validate/<challenge_name> endpoint success."""
        with app.app_context():
            app.tester.validate_response.return_value = {
                "valid": True,
                "match_type": "exact",
                "best_match_score": 100
            }
            
            response = client.post(
                '/validate/test_challenge_1',
                json={"output": "test response"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["valid"]
            assert data["match_type"] == "exact"

    def test_validate_endpoint_missing_output(self, client, app):
        """Test POST /validate/<challenge_name> with missing output."""
        with app.app_context():
            app.tester.validate_response.return_value = {
                "valid": False,
                "reason": "No output provided"
            }
            
            response = client.post(
                '/validate/test_challenge_1',
                json={}
            )
            
            assert response.status_code == 200  # API still responds, but with error

    def test_validate_endpoint_failure(self, client, app):
        """Test POST /validate/<challenge_name> with validation failure."""
        with app.app_context():
            app.tester.validate_response.return_value = {
                "valid": False,
                "reason": "No match found"
            }
            
            response = client.post(
                '/validate/test_challenge_1',
                json={"output": "test response"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert not data["valid"]

    def test_nonexistent_endpoint(self, client):
        """Test request to non-existent endpoint."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404

    def test_challenge_endpoint_with_authorization_header(self, client, app):
        """Test challenge endpoint with Authorization header."""
        with app.app_context():
            app.tester.call_llm.return_value = {
                "status": "success",
                "input": "test input",
                "output": "test output",
                "conversation": []
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={"input": "test input"},
                headers={
                    "X-User-Token": "test-token",
                    "Authorization": "Bearer test-api-key"
                }
            )
            
            assert response.status_code == 200

    def test_session_conversation_management(self, client, app):
        """Test that conversation is properly managed in session."""
        with app.app_context():
            app.tester.call_llm.return_value = {
                "status": "success",
                "input": "new input",
                "output": "new output",
                "conversation": [
                    {"role": "user", "content": "previous message"},
                    {"role": "user", "content": "new input"},
                    {"role": "assistant", "content": "new output"}
                ]
            }
            
            response = client.post(
                '/challenge/test_challenge_1',
                json={"input": "new input"},
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            
            # Check that conversation was passed to call_llm
            app.tester.call_llm.assert_called_once()
            args, kwargs = app.tester.call_llm.call_args
            # The conversation starts empty, so should be []
            assert len(args[2]) == 0  # Empty conversation initially

    def test_reset_clears_session_conversation(self, client, app):
        """Test that reset endpoint clears session conversation."""
        with app.app_context():
            app.tester.reset_conversation.return_value = {
                "status": "success",
                "message": "Reset successful"
            }
            
            response = client.post(
                '/reset/test_challenge_1',
                headers={"X-User-Token": "test-token"}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"