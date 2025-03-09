#!/usr/bin/env python3
"""
LLM Challenge CLI

This module provides a command-line interface for interacting with the LLM Challenge API.
It handles challenge selection, conversation, and result display using Rich for pretty output.
"""
import argparse
import os
import requests
import uuid
import json
import time
import sys
from typing import Dict, List, Optional, Any, Union

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.box import ROUNDED
from rich.layout import Layout
from rich import print as rprint
from rich.text import Text

# Reuse ChallengeUI class functionality with CLI adaptations
class ChallengeUICLI:
    """
    Client class for interacting with the LLM Challenge API via CLI.
    
    Handles fetching challenge data, submitting user prompts,
    and validating responses.
    """
    def __init__(self, api_url: str, api_key: Optional[str] = None) -> None:
        """
        Initialize the Challenge UI client.
        
        Args:
            api_url: URL of the LLM Challenge API server
            api_key: API key for authentication (optional)
        """
        self.api_url: str = api_url.rstrip('/')
        self.api_key: Optional[str] = api_key
        self.challenges: List[Dict[str, Any]] = []
        self.user_token: str = str(uuid.uuid4())  # Generate a unique user token
        self.fetch_challenges()
    
    def get_api_headers(self) -> Dict[str, str]:
        """
        Get API headers including user's API key if set.
            
        Returns:
            Headers dictionary for API requests
        """
        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
            
        # Include user token in headers
        if self.user_token:
            headers['X-User-Token'] = self.user_token
            
        return headers
        
    def fetch_challenges(self) -> None:
        """
        Fetch challenges from the API server.
        
        Updates the internal challenges list with data from the API.
        """
        try:
            response = requests.get(f"{self.api_url}/challenges", verify=False)
            if response.status_code == 200:
                self.challenges = response.json()
        except requests.RequestException as e:
            print(f"Error fetching challenges: {e}")
            self.challenges = []

    def get_challenge_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a challenge by its name.
        
        Args:
            name: Name of the challenge to find
            
        Returns:
            Challenge dictionary or None if not found
        """
        for challenge in self.challenges:
            if challenge['name'].lower().replace(' ', '_') == name.lower().replace(' ', '_'):
                return challenge
        return None
    
    def submit_prompt(self, challenge_name: str, prompt_text: str) -> Dict[str, Any]:
        """
        Submit a prompt to a challenge via the API.
        
        Args:
            challenge_name: Name of the challenge
            prompt_text: User's prompt text
            
        Returns:
            Dictionary containing the API response or error information
        """
        try:
            headers = self.get_api_headers()
            
            endpoint = f"{self.api_url}/challenge/{challenge_name.lower().replace(' ', '_')}"
            response = requests.post(
                endpoint,
                json={"input": prompt_text},
                headers=headers,
                verify=False
            )
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "reason": str(e)}
    
    def reset_challenge(self, challenge_name: str) -> Dict[str, Any]:
        """
        Reset a challenge conversation via the API.
        
        Args:
            challenge_name: Name of the challenge to reset
            
        Returns:
            Dictionary containing the reset operation status
        """
        try:
            headers = self.get_api_headers()
            
            endpoint = f"{self.api_url}/reset/{challenge_name.lower().replace(' ', '_')}"
            response = requests.post(endpoint, headers=headers, verify=False)
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "reason": str(e)}
    
    def validate_response(self, challenge_name: str, response: str) -> Dict[str, Any]:
        """
        Validate a response against the challenge criteria via the API.
        
        Args:
            challenge_name: Name of the challenge
            response: Text to validate
            
        Returns:
            Dictionary containing the validation results
        """
        try:
            headers = self.get_api_headers()
            
            endpoint = f"{self.api_url}/validate/{challenge_name.lower().replace(' ', '_')}"
            api_response = requests.post(
                endpoint,
                json={"output": response},
                headers=headers,
                verify=False
            )
            return api_response.json()
        except requests.RequestException as e:
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "validation_issue": True,
                "match_type": "error"
            }

def display_challenges(console: Console, ui: ChallengeUICLI, completed_challenges: List[str] = None) -> None:
    """Display all available challenges in a table format."""
    if completed_challenges is None:
        completed_challenges = []
        
    table = Table(title="Available Challenges", box=ROUNDED, highlight=True)
    table.add_column("#", style="dim", justify="right", no_wrap=True)
    table.add_column("Name", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Status", justify="center", no_wrap=True)
    
    for i, challenge in enumerate(ui.challenges, 1):
        challenge_name = challenge["name"]
        challenge_id = challenge_name.lower().replace(' ', '_')
        status = "[green]✓ Completed[/green]" if challenge_id in completed_challenges else "[yellow]Pending[/yellow]"
        
        table.add_row(
            str(i),
            challenge_name, 
            challenge.get("description", "No description available"),
            status
        )
    
    console.print(table)

def display_help_in_conversation():
    """Display available commands during a conversation."""
    help_text = """
[bold]Available Commands:[/bold]

[cyan]/help[/cyan] - Show this help message
[cyan]/exit[/cyan] - Exit the current challenge conversation
[cyan]/reset[/cyan] - Reset the conversation for this challenge
[cyan]/status[/cyan] - Show validation status of the current challenge
[cyan]/clear[/cyan] - Clear the screen

To submit a prompt to the LLM, just type your message and press Enter.
    """
    return Panel(Markdown(help_text), title="Command Help", border_style="blue")

def handle_challenge_conversation(console: Console, ui: ChallengeUICLI, challenge: Dict[str, Any], 
                                  history: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Handle conversation with a specific challenge.
    
    Args:
        console: Rich console instance
        ui: ChallengeUICLI instance
        challenge: Challenge data dictionary
        history: Existing conversation history (optional)
        
    Returns:
        Updated conversation history
    """
    if history is None:
        history = []
    
    console.clear()
    
    # Create header with challenge info
    header_text = f"[bold blue]{challenge['name']}[/bold blue] - {challenge.get('description', 'No description available')}"
    console.print(Panel(header_text, border_style="blue"))
    
    # Display help text at start
    console.print("[dim]Type [bold]/help[/bold] to see available commands[/dim]")
    
    # Display initial prompt if there's no history
    if not history:
        console.print(Panel(
            challenge.get("input", "No initial prompt provided"),
            title="Initial Challenge Prompt",
            border_style="green"
        ))
    
    # Display conversation history
    for entry in history:
        console.print(Panel(
            entry.get("input", ""),
            title="You",
            border_style="cyan"
        ))
        
        console.print(Panel(
            entry.get("output", ""),
            title="AI Response",
            border_style="magenta"
        ))
        
        # Display validation results if available
        if "validation" in entry:
            validation = entry["validation"]
            if validation.get("valid", False):
                console.print(Panel(
                    "[bold green]✓ Challenge passed![/bold green]",
                    border_style="green", 
                    title="Validation"
                ))
            else:
                # Get details about the validation failure
                if "match_percent" in validation:
                    match_percent = validation.get("match_percent", 0)
                    threshold = validation.get("fuzzy_threshold", 0)
                    console.print(Panel(
                        f"[yellow]Challenge attempt failed.[/yellow]\nMatch: {match_percent}%, Threshold: {threshold}%",
                        border_style="yellow",
                        title="Validation"
                    ))
                else:
                    console.print(Panel(
                        "[yellow]Challenge attempt failed. Try a different approach.[/yellow]",
                        border_style="yellow",
                        title="Validation"
                    ))
    
    # Command processing loop
    while True:
        # Get user input with prefix
        user_input = Prompt.ask("\n[bold cyan]Prompt[/bold cyan]")
        
        # Process commands (all starting with /)
        if user_input.startswith('/'):
            cmd = user_input.lower().strip()
            
            if cmd == '/exit':
                return history
            
            elif cmd == '/reset':
                if Confirm.ask("Are you sure you want to reset this conversation?"):
                    ui.reset_challenge(challenge["name"])
                    console.print("[bold yellow]Conversation reset.[/bold yellow]")
                    return []
            
            elif cmd == '/help':
                console.print(display_help_in_conversation())
                continue
            
            elif cmd == '/clear':
                console.clear()
                console.print(Panel(header_text, border_style="blue"))
                console.print("[dim]Type [bold]/help[/bold] to see available commands[/dim]")
                continue
                
            elif cmd == '/status':
                completed = False
                for entry in history:
                    if "validation" in entry and entry["validation"].get("valid", False):
                        completed = True
                
                if completed:
                    console.print(Panel("[bold green]✓ This challenge has been completed![/bold green]", 
                                       border_style="green", title="Status"))
                else:
                    console.print(Panel("[yellow]This challenge is not yet completed.[/yellow]", 
                                       border_style="yellow", title="Status"))
                continue
                
            else:
                console.print(f"[bold red]Unknown command:[/bold red] {cmd}")
                console.print("[dim]Type [bold]/help[/bold] to see available commands[/dim]")
                continue
        
        # Process regular prompt input
        # Show progress spinner while waiting for response
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Sending prompt and waiting for response...[/bold blue]"),
            transient=True,
        ) as progress:
            task = progress.add_task("", total=None)
            
            # Submit the prompt
            result = ui.submit_prompt(challenge["name"], user_input)
        
        if result.get("status") == "success":
            # Display the response
            console.print(Panel(
                result.get("output", ""),
                title="AI Response",
                border_style="magenta"
            ))
            
            # Validate the response
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Validating response...[/bold blue]"),
                transient=True,
            ) as progress:
                task = progress.add_task("", total=None)
                validation = ui.validate_response(challenge["name"], result.get("output", ""))
                result["validation"] = validation
            
            # Display validation results
            if validation.get("valid"):
                console.print(Panel(
                    "[bold green]✓ Challenge passed![/bold green]",
                    border_style="green",
                    title="Validation"
                ))
            else:
                # Get details about the validation failure
                if "match_percent" in validation:
                    match_percent = validation.get("match_percent", 0)
                    threshold = validation.get("fuzzy_threshold", 0)
                    console.print(Panel(
                        f"[yellow]Challenge attempt failed.[/yellow]\nMatch: {match_percent}%, Threshold: {threshold}%",
                        border_style="yellow",
                        title="Validation"
                    ))
                else:
                    console.print(Panel(
                        "[yellow]Challenge attempt failed. Try a different approach.[/yellow]",
                        border_style="yellow",
                        title="Validation"
                    ))
            
            # Add to history
            history.append(result)
            
            # If challenge was completed, ask if user wants to continue
            if validation.get("valid"):
                if Confirm.ask("\nChallenge completed! Continue with this conversation?"):
                    continue
                else:
                    return history
        else:
            console.print(Panel(
                f"[bold red]Error:[/bold red] {result.get('reason', 'Unknown error')}",
                border_style="red"
            ))
    
    return history

def display_main_menu(console: Console):
    """Display the main menu options."""
    menu_text = """
[bold]Main Menu Commands:[/bold]

- Enter a [cyan]number[/cyan] to select a challenge
- Type [cyan]r[/cyan] to refresh the challenges list
- Type [cyan]c[/cyan] to clear your completed challenges
- Type [cyan]e[/cyan] or [cyan]q[/cyan] to exit the application
- Type [cyan]h[/cyan] or [cyan]?[/cyan] for this help message
"""
    console.print(Panel(Markdown(menu_text), title="Help", border_style="blue"))

def save_state(completed_challenges: List[str], conversation_history: Dict[str, List[Dict[str, Any]]]) -> None:
    """Save the current state to a file."""
    state_dir = os.path.expanduser("~/.folly")
    os.makedirs(state_dir, exist_ok=True)
    
    state = {
        "completed_challenges": completed_challenges,
        "conversation_history": conversation_history
    }
    
    with open(os.path.join(state_dir, "cli_state.json"), "w") as f:
        json.dump(state, f)

def load_state() -> Dict[str, Any]:
    """Load the current state from a file."""
    state_path = os.path.expanduser("~/.folly/cli_state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {"completed_challenges": [], "conversation_history": {}}

def export_conversation(console: Console, challenge_name: str, history: List[Dict[str, Any]]):
    """Export a conversation to a file."""
    if not history:
        console.print("[yellow]No conversation to export.[/yellow]")
        return
    
    # Format the conversation for export
    export_data = {
        "challenge": challenge_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "conversation": history
    }
    
    # Create export directory if it doesn't exist
    export_dir = os.path.expanduser("~/folly_exports")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate a filename based on challenge name and timestamp
    filename = f"{challenge_name.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(export_dir, filename)
    
    # Write the file
    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)
    
    console.print(f"[green]Conversation exported to:[/green] {filepath}")

def main() -> int:
    """
    Main entry point for the LLM Challenge CLI.
    
    Parses command line arguments and starts the CLI interface.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='LLM Challenge CLI')
    parser.add_argument('api_url', help='URL of the LLM Challenge API (e.g., http://localhost:5000)')
    parser.add_argument('--api-key', '-k', help='API key for authentication (optional)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--challenge', '-c', help='Start with a specific challenge')
    
    args = parser.parse_args()
    
    # Initialize console
    console = Console(no_color=args.no_color)
    
    try:
        # Display welcome banner
        console.print(Panel.fit(
            "[bold blue]Folly LLM Challenge CLI[/bold blue]\n"
            "[dim]A tool for testing prompt injection and jailbreaking attacks against LLMs[/dim]",
            border_style="blue",
            padding=(1, 2)
        ))
        
        console.print(f"[green]Connecting to API:[/green] {args.api_url}")
        
        # Create UI client
        ui = ChallengeUICLI(args.api_url, args.api_key)
        
        # Verify connection by checking if challenges were loaded
        if not ui.challenges:
            console.print(f"[bold red]Error:[/bold red] Could not load challenges from API. Please check the API URL and try again.")
            return 1
        
        console.print(f"[green]Successfully connected! Loaded {len(ui.challenges)} challenges.[/green]")
        
        # Load saved state
        state = load_state()
        completed_challenges = state.get("completed_challenges", [])
        conversation_history = state.get("conversation_history", {})
        
        # If a specific challenge was requested, go directly to it
        if args.challenge:
            challenge_name = args.challenge.lower().replace(' ', '_')
            challenge = ui.get_challenge_by_name(challenge_name)
            if challenge:
                history = conversation_history.get(challenge_name, [])
                updated_history = handle_challenge_conversation(console, ui, challenge, history)
                conversation_history[challenge_name] = updated_history
                
                # Check if challenge was completed
                for entry in updated_history:
                    if "validation" in entry and entry["validation"].get("valid", False):
                        if challenge_name not in completed_challenges:
                            completed_challenges.append(challenge_name)
                
                save_state(completed_challenges, conversation_history)
                return 0
            else:
                console.print(f"[bold red]Error:[/bold red] Challenge '{args.challenge}' not found.")
                return 1
        
        # Main menu loop
        while True:
            console.clear()
            console.print(Panel("[bold blue]Folly LLM Challenge CLI[/bold blue]", border_style="blue"))
            
            # Display challenges
            display_challenges(console, ui, completed_challenges)
            
            console.print("\n[bold cyan]Commands:[/bold cyan] [dim](enter number to select challenge, r=refresh, c=clear completed, h=help, q=quit)[/dim]")
            
            choice = Prompt.ask("\n[bold cyan]Enter your choice[/bold cyan]")
            
            if choice.lower() in ('q', 'e', 'exit', 'quit'):
                break
                
            elif choice.lower() in ('r', 'refresh'):
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]Refreshing challenges...[/bold blue]"),
                    transient=True,
                ) as progress:
                    task = progress.add_task("", total=None)
                    ui.fetch_challenges()
                console.print("[green]Challenges refreshed.[/green]")
                time.sleep(1)
                
            elif choice.lower() in ('c', 'clear'):
                if Confirm.ask("Are you sure you want to clear your completed challenges?"):
                    completed_challenges = []
                    console.print("[yellow]Completed challenges cleared.[/yellow]")
                    save_state(completed_challenges, conversation_history)
                    time.sleep(1)
                    
            elif choice.lower() in ('h', '?', 'help'):
                display_main_menu(console)
                Prompt.ask("[cyan]Press Enter to continue[/cyan]")
                    
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(ui.challenges):
                    challenge = ui.challenges[idx]
                    challenge_name = challenge["name"]
                    challenge_id = challenge_name.lower().replace(' ', '_')
                    
                    # Get or create history for this challenge
                    history = conversation_history.get(challenge_id, [])
                    
                    # Handle conversation until user exits
                    updated_history = handle_challenge_conversation(console, ui, challenge, history)
                    
                    # Update history in state
                    conversation_history[challenge_id] = updated_history
                    
                    # Check if this challenge is now complete
                    for entry in updated_history:
                        if "validation" in entry and entry["validation"].get("valid", False):
                            if challenge_id not in completed_challenges:
                                completed_challenges.append(challenge_id)
                    
                    # Save current state
                    save_state(completed_challenges, conversation_history)
                    
                    # Offer to export conversation if it's not empty
                    if updated_history:
                        if Confirm.ask("\nDo you want to export this conversation?"):
                            export_conversation(console, challenge_name, updated_history)
                            Prompt.ask("[cyan]Press Enter to continue[/cyan]")
                else:
                    console.print("[bold red]Invalid challenge number.[/bold red]")
                    time.sleep(1)
            else:
                console.print("[bold red]Invalid command.[/bold red]")
                time.sleep(1)
        
        # Save state on exit
        save_state(completed_challenges, conversation_history)
        console.print("[green]Session saved. Goodbye![/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted. Saving state...[/yellow]")
        save_state(completed_challenges, conversation_history)
        console.print("[green]Session saved. Goodbye![/green]")
        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
