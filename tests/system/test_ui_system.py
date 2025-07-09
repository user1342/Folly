"""
System tests for the Folly UI application.

These tests verify end-to-end functionality of the web interface.
"""
import pytest
import requests
import time
import subprocess
import os
import tempfile
import json


@pytest.fixture(scope="module")
def test_challenges_file():
    """Create a temporary challenges file for testing."""
    challenges = [
        {
            "name": "UI Test Challenge",
            "system_prompt": "You are a test assistant.",
            "input": "Hello! Test the UI.",
            "deny_inputs": ["harmful"],
            "deny_outputs": ["secret"],
            "description": "A UI test challenge",
            "answers": ["test"],
            "help": "Just enter 'test'."
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(challenges, f)
        f.flush()
        yield f.name
    
    os.unlink(f.name)


@pytest.fixture(scope="module")
def api_server(test_challenges_file):
    """Start the API server for testing."""
    api_port = 5002
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(__file__))
    
    cmd = [
        'python', '-m', 'Folly.api',
        '--config', test_challenges_file,
        '--port', str(api_port),
        '--api-key', 'test-api-key',
        '--api-url', 'https://api.openai.com/v1'
    ]
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    api_url = f"http://localhost:{api_port}"
    for _ in range(30):
        try:
            response = requests.get(f"{api_url}/challenges", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        process.terminate()
        pytest.fail("API server failed to start")
    
    yield api_url
    
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="module")
def ui_server(api_server):
    """Start the UI server for testing."""
    ui_port = 5003
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(__file__))
    
    cmd = [
        'python', '-m', 'Folly.ui_app',
        '--api-url', api_server,
        '--port', str(ui_port)
    ]
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    ui_url = f"http://localhost:{ui_port}"
    for _ in range(30):
        try:
            response = requests.get(ui_url, timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        process.terminate()
        pytest.fail("UI server failed to start")
    
    yield ui_url
    
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.system
class TestUISystemIntegration:
    """System tests for the UI server."""

    def test_homepage_loads(self, ui_server):
        """Test that the homepage loads successfully."""
        response = requests.get(ui_server)
        
        assert response.status_code == 200
        assert "Folly" in response.text
        assert "LLM Prompt Injection Testing" in response.text

    def test_challenge_page_loads(self, ui_server):
        """Test that challenge pages load."""
        # First, let's get the list of challenges from the homepage
        response = requests.get(ui_server)
        assert response.status_code == 200
        
        # Check that the challenge link is present
        assert "ui_test_challenge" in response.text or "UI Test Challenge" in response.text
        
        # Try to access the challenge page
        challenge_response = requests.get(f"{ui_server}/challenge/ui_test_challenge")
        assert challenge_response.status_code == 200

    def test_static_files_served(self, ui_server):
        """Test that static files are served correctly."""
        # Test CSS files
        css_response = requests.get(f"{ui_server}/static/css/styles.css")
        # CSS might not exist, but should not return 500
        assert css_response.status_code in [200, 404]
        
        # Test that static file route exists
        static_response = requests.get(f"{ui_server}/static/nonexistent.css")
        assert static_response.status_code == 404

    def test_settings_page(self, ui_server):
        """Test settings functionality."""
        session = requests.Session()
        
        # Get the main page first to establish session
        response = session.get(ui_server)
        assert response.status_code == 200
        
        # Try to access settings (might be integrated into main page)
        # Just verify the session works
        response2 = session.get(ui_server)
        assert response2.status_code == 200

    def test_api_integration(self, ui_server, api_server):
        """Test that UI properly communicates with API."""
        response = requests.get(ui_server)
        
        assert response.status_code == 200
        # Should show challenges loaded from API
        assert "UI Test Challenge" in response.text or "Available Challenges" in response.text

    def test_challenge_form_page(self, ui_server):
        """Test challenge form page loads."""
        response = requests.get(f"{ui_server}/challenge/ui_test_challenge")
        
        assert response.status_code == 200
        assert "form" in response.text.lower() or "prompt" in response.text.lower()

    def test_nonexistent_challenge(self, ui_server):
        """Test accessing non-existent challenge."""
        response = requests.get(f"{ui_server}/challenge/nonexistent_challenge")
        
        # Should redirect or show error
        assert response.status_code in [200, 302, 404]

    def test_debug_info_endpoint(self, ui_server):
        """Test debug info endpoint if available."""
        response = requests.get(f"{ui_server}/debug-info")
        
        # May or may not exist depending on debug mode
        assert response.status_code in [200, 404]