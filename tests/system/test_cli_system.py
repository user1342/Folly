"""
System tests for the Folly CLI application.

These tests verify command-line interface functionality.
"""
import pytest
import subprocess
import tempfile
import json
import os


@pytest.fixture
def test_challenges_file():
    """Create a temporary challenges file for testing."""
    challenges = [
        {
            "name": "CLI Test Challenge",
            "system_prompt": "You are a test assistant.",
            "input": "Hello! Test the CLI.",
            "deny_inputs": ["harmful"],
            "deny_outputs": ["secret"],
            "description": "A CLI test challenge",
            "answers": ["test"],
            "help": "Just enter 'test'."
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(challenges, f)
        f.flush()
        yield f.name
    
    os.unlink(f.name)


@pytest.mark.system
class TestCLISystemIntegration:
    """System tests for the CLI application."""

    def test_cli_help(self):
        """Test CLI help command."""
        result = subprocess.run(
            ['python', '-m', 'Folly.cli', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()
        assert "api_url" in result.stdout.lower()  # Positional argument

    def test_cli_version_info(self):
        """Test that CLI can be imported and run."""
        # Just test that the module can be imported without errors
        result = subprocess.run(
            ['python', '-c', 'import Folly.cli; print("CLI module imported successfully")'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        assert "imported successfully" in result.stdout

    def test_cli_invalid_api_url(self):
        """Test CLI with invalid API URL."""
        result = subprocess.run(
            ['python', '-m', 'Folly.cli', 'http://invalid-url'],
            capture_output=True,
            text=True,
            timeout=15,
            input='\nq\n'  # Quit immediately
        )
        
        # CLI should handle the error gracefully
        # Return code might be 1 due to connection error, which is expected
        assert "Error" in result.stdout or "error" in result.stderr.lower() or result.returncode != 0

    def test_cli_with_mock_server_url(self):
        """Test CLI with a mock server URL that doesn't exist."""
        # This tests the CLI's error handling when API is unavailable
        result = subprocess.run(
            ['python', '-m', 'Folly.cli', 'http://localhost:9999'],
            capture_output=True,
            text=True,
            timeout=15,
            input='q\n'  # Quit immediately
        )
        
        # Should handle connection error gracefully
        assert result.returncode in [0, 1]  # Either handles gracefully or exits with error

    def test_cli_argument_parsing(self):
        """Test CLI argument parsing."""
        # Test with valid arguments but immediate quit
        result = subprocess.run([
            'python', '-m', 'Folly.cli',
            'http://test.com',
            '--api-key', 'test-key'
        ], capture_output=True, text=True, timeout=15, input='q\n')
        
        # Should accept arguments without syntax error
        assert "unrecognized arguments" not in result.stderr.lower()

    def test_cli_challenge_parameter(self):
        """Test CLI with specific challenge parameter."""
        result = subprocess.run([
            'python', '-m', 'Folly.cli',
            'http://localhost:9999',
            '--challenge', 'test_challenge'
        ], capture_output=True, text=True, timeout=15, input='\nq\n')
        
        # Should handle the challenge parameter
        assert result.returncode in [0, 1]

    def test_cli_imports(self):
        """Test that all CLI dependencies can be imported."""
        import_test = """
try:
    from Folly.cli import ChallengeUICLI, main
    from rich.console import Console
    from rich.table import Table
    print("All imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)
"""
        
        result = subprocess.run(
            ['python', '-c', import_test],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        assert "All imports successful" in result.stdout

    def test_cli_rich_formatting(self):
        """Test that Rich formatting works."""
        rich_test = """
from rich.console import Console
from rich.table import Table

console = Console()
table = Table()
table.add_column("Test")
table.add_row("Value")

# Should not crash
with console.capture() as capture:
    console.print(table)

print("Rich formatting works")
"""
        
        result = subprocess.run(
            ['python', '-c', rich_test],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        assert "Rich formatting works" in result.stdout