#!/usr/bin/env python3
"""
LLM Challenge Web UI

This module provides a Flask web interface for interacting with the LLM Challenge API.
It handles user interface, form submission, and result display.
"""
import argparse
import os
import requests
from typing import Dict, List, Optional, Any, Union
import uuid

from flask import Flask, render_template, redirect, url_for, flash, session as flask_session, request
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

class PromptForm(FlaskForm):
    """Form for submitting prompts to the LLM Challenge API."""
    prompt = TextAreaField('Your Prompt', validators=[DataRequired()])
    submit = SubmitField('Submit')

class ChallengeUI:
    """
    Client class for interacting with the LLM Challenge API.
    
    Handles fetching challenge data, submitting user prompts,
    and validating responses.
    """
    def __init__(self, api_url: str) -> None:
        """
        Initialize the Challenge UI client.
        
        Args:
            api_url: URL of the LLM Challenge API server
        """
        self.api_url: str = api_url.rstrip('/')
        self.challenges: List[Dict[str, Any]] = []
        self.fetch_challenges()
    
    def get_effective_url(self, session: Any) -> str:
        """
        Get the effective API URL, considering user settings.
        
        Args:
            session: Flask session object
            
        Returns:
            Effective API URL to use for requests
        """
        user_api_url = session.get('user_api_url')
        return user_api_url or self.api_url
    
    def get_api_headers(self, session: Any) -> Dict[str, str]:
        """
        Get API headers including user's API key if set.
        
        Args:
            session: Flask session object
            
        Returns:
            Headers dictionary for API requests
        """
        headers = {}
        user_api_key = session.get('user_api_key')
        if user_api_key:
            headers['Authorization'] = f"Bearer {user_api_key}"
            
        # Include user token in headers if available
        user_token = session.get('user_token')
        if user_token:
            headers['X-User-Token'] = user_token
            
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
    
    def submit_prompt(self, challenge_name: str, prompt_text: str, session: Any = None) -> Dict[str, Any]:
        """
        Submit a prompt to a challenge via the API.
        
        Args:
            challenge_name: Name of the challenge
            prompt_text: User's prompt text
            session: Flask session for user API settings
            
        Returns:
            Dictionary containing the API response or error information
        """
        try:
            api_url = self.get_effective_url(session) if session else self.api_url
            headers = self.get_api_headers(session) if session else {}
            
            endpoint = f"{api_url}/challenge/{challenge_name.lower().replace(' ', '_')}"
            response = requests.post(
                endpoint,
                json={"input": prompt_text},
                headers=headers,
                verify=False
            )
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "reason": str(e)}
    
    def reset_challenge(self, challenge_name: str, session: Any = None) -> Dict[str, Any]:
        """
        Reset a challenge conversation via the API.
        
        Args:
            challenge_name: Name of the challenge to reset
            session: Flask session for user API settings
            
        Returns:
            Dictionary containing the reset operation status
        """
        try:
            api_url = self.get_effective_url(session) if session else self.api_url
            headers = self.get_api_headers(session) if session else {}
            
            endpoint = f"{api_url}/reset/{challenge_name.lower().replace(' ', '_')}"
            response = requests.post(endpoint, headers=headers, verify=False)
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "reason": str(e)}
    
    def validate_response(self, challenge_name: str, response: str, session: Any = None) -> Dict[str, Any]:
        """
        Validate a response against the challenge criteria via the API.
        
        Args:
            challenge_name: Name of the challenge
            response: Text to validate
            session: Flask session for user API settings
            
        Returns:
            Dictionary containing the validation results
        """
        try:
            api_url = self.get_effective_url(session) if session else self.api_url
            headers = self.get_api_headers(session) if session else {}
            
            endpoint = f"{api_url}/validate/{challenge_name.lower().replace(' ', '_')}"
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

def create_app(ui: ChallengeUI) -> Flask:
    """
    Create and configure a Flask application for the web UI.
    
    Args:
        ui: An initialized ChallengeUI instance
        
    Returns:
        A configured Flask application
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', str(uuid.uuid4()))
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable cache during development
    
    # Initialize Session extension
    Session(app)
    
    # Create a context processor to inject challenges into all templates
    @app.context_processor
    def inject_challenges() -> Dict[str, Any]:
        """Make challenges available to all templates."""
        challenges = ui.challenges
        # Add completed_challenges to context so it's available in all templates
        completed_challenges = flask_session.get('completed_challenges', [])
        return dict(
            challenges=challenges,
            completed_challenges=completed_challenges
        )
    
    # Add route to refresh static files during development
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files with cache control for development."""
        response = app.send_static_file(filename)
        response.headers['Cache-Control'] = 'no-store'
        return response
    
    @app.route('/')
    def index():
        """Render the home page with challenge list."""
        ui.fetch_challenges()  # Refresh challenges list
        
        # Ensure user has a persistent token
        if 'user_token' not in flask_session:
            flask_session['user_token'] = str(uuid.uuid4())
            flask_session.modified = True
        
        # Get completed challenges from the session
        if 'completed_challenges' not in flask_session:
            flask_session['completed_challenges'] = []
            
        completed_challenges = flask_session['completed_challenges']
        
        # Get user settings for the template
        user_api_url = flask_session.get('user_api_url', '')
        user_api_key = flask_session.get('user_api_key', '')
        
        return render_template('index.html', 
                              completed_challenges=completed_challenges,
                              user_api_url=user_api_url,
                              user_api_key=user_api_key)
    
    @app.route('/settings', methods=['POST'])
    def update_settings():
        """Update user-specific API settings."""
        user_api_url = request.form.get('user_api_url', '').strip()
        user_api_key = request.form.get('user_api_key', '').strip()
        
        # If we have a new API URL, store it
        if user_api_url:
            flask_session['user_api_url'] = user_api_url
        elif 'user_api_url' in flask_session:
            # If empty was submitted, remove it
            del flask_session['user_api_url']
        
        # If we have a new API key, store it
        if user_api_key:
            flask_session['user_api_key'] = user_api_key
        elif 'user_api_key' in flask_session:
            # If empty was submitted, remove it
            del flask_session['user_api_key'] 
        
        flask_session.modified = True
        
        # Get referer for redirect, or default to index
        referer = request.headers.get('Referer')
        if referer:
            return redirect(referer)
        return redirect(url_for('index'))
    
    # Add a route to list all challenges with more details
    @app.route("/challenges", methods=["GET"])
    def list_challenges():
        """Return a list of all available challenges with their details"""
        ui.fetch_challenges()  # Refresh challenges list
        
        # Get completed challenges from the session
        if 'completed_challenges' not in flask_session:
            flask_session['completed_challenges'] = []
            
        completed_challenges = flask_session['completed_challenges']
        
        # Get user settings for the template
        user_api_url = flask_session.get('user_api_url', '')
        user_api_key = flask_session.get('user_api_key', '')
        
        return render_template('index.html', 
                              completed_challenges=completed_challenges,
                              user_api_url=user_api_url,
                              user_api_key=user_api_key)
    
    @app.route('/challenge/<challenge_name>', methods=['GET', 'POST'])
    def show_challenge(challenge_name: str):
        """
        Show a specific challenge and handle user interactions.
        
        Args:
            challenge_name: Name of the challenge to show
            
        Returns:
            Rendered challenge template or redirect
        """
        # Force fetch the latest challenge data to ensure we have the correct configuration
        ui.fetch_challenges()
        challenge = ui.get_challenge_by_name(challenge_name)
        
        # Ensure user has a persistent token
        if 'user_token' not in flask_session:
            flask_session['user_token'] = str(uuid.uuid4())
            flask_session.modified = True
        
        # Check if we really do have the challenge data
        if not challenge:
            flash('Challenge not found', 'danger')
            return redirect(url_for('index'))
        
        form = PromptForm()
        
        # Get history from session - using challenge-specific key
        # This ensures each challenge has its own isolated conversation history
        history_key = f"history_{challenge_name}"
        if history_key not in flask_session:
            flask_session[history_key] = []
        
        if form.validate_on_submit():
            prompt_text = form.prompt.data
            
            # Submit the prompt - pass session to use user's API settings
            result = ui.submit_prompt(challenge_name, prompt_text, flask_session)
            
            # Add to history
            if result.get('status') == 'success':
                # Validate the answer by calling the API endpoint - not locally
                validation = ui.validate_response(challenge_name, result.get('output', ''), flask_session)
                result['validation'] = validation
                
                flask_session[history_key].append(result)
                flask_session.modified = True
                
                if validation.get('valid'):
                    flash('Challenge passed! 🎉', 'success')
                    
                    # Mark this challenge as completed
                    if 'completed_challenges' not in flask_session:
                        flask_session['completed_challenges'] = []
                    
                    # Store challenge_name in lowercase with underscores for consistent matching
                    challenge_name_normalized = challenge_name.lower().replace(' ', '_')
                    
                    # Add to completed challenges if not already there
                    if challenge_name_normalized not in flask_session['completed_challenges']:
                        flask_session['completed_challenges'].append(challenge_name_normalized)
                        flask_session.modified = True
                else:
                    # More descriptive failure message
                    if 'match_percent' in validation:
                        match_threshold = validation.get('fuzzy_threshold', 0)
                        flash(f"Challenge attempt failed. Match: {validation['match_percent']}%, Threshold: {match_threshold}%", 'warning')
                    else:
                        flash('Challenge attempt failed. Try a different approach.', 'warning')
            else:
                flask_session[history_key].append(result)
                flask_session.modified = True
                flash(f"Error: {result.get('reason', 'Unknown error')}", 'danger')
                
            return redirect(url_for('show_challenge', challenge_name=challenge_name))
        
        # Add JavaScript for handling loading state
        loading_js = """
        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const form = document.querySelector('form');
            const sendButton = document.querySelector('.send-button');
            
            if (form && sendButton) {
              // Add spinner element to the button
              const buttonContent = `
                <span class="send-button-icon">
                  <i class="bi bi-send-fill"></i>
                </span>
                <span class="spinner"></span>
              `;
              sendButton.innerHTML = buttonContent;
              
              form.addEventListener('submit', function() {
                // Show loading state
                sendButton.classList.add('loading');
                sendButton.disabled = true;
                
                // Disable textarea
                const textarea = form.querySelector('textarea');
                if (textarea) {
                  textarea.readOnly = true;
                }
              });
            }
          });
        </script>
        """
        
        return render_template(
            'challenge.html', 
            challenge=challenge, 
            form=form, 
            history=flask_session.get(history_key, []),
            ui=ui,  # Pass the UI object to access base API URL
            custom_js=loading_js  # Pass the custom JavaScript
        )
    
    @app.route('/challenge/<challenge_name>/reset', methods=['POST'])
    def reset_challenge(challenge_name: str):
        """
        Reset a challenge conversation.
        
        Args:
            challenge_name: Name of the challenge to reset
            
        Returns:
            Redirect to the challenge page
        """
        challenge = ui.get_challenge_by_name(challenge_name)
        if not challenge:
            flash('Challenge not found', 'danger')
            return redirect(url_for('index'))
        
        # Reset on API - pass session to use user's API settings
        # This resets only the specific challenge conversation on the API side
        ui.reset_challenge(challenge_name, flask_session)
        
        # Reset local history for only this specific challenge
        # Other challenge histories remain untouched
        history_key = f"history_{challenge_name}"
        flask_session[history_key] = []
        
        # Remove from completed challenges if present
        if 'completed_challenges' in flask_session and challenge_name in flask_session['completed_challenges']:
            flask_session['completed_challenges'].remove(challenge_name)
            
        flask_session.modified = True
        
        flash('Challenge conversation reset', 'info')
        return redirect(url_for('show_challenge', challenge_name=challenge_name))
    
    # Add a new route to reset all progress
    @app.route('/reset-all', methods=['POST'])
    def reset_all_progress():
        """Reset all challenge progress and conversation history."""
        
        # Reset all challenge conversations one by one
        # This ensures each challenge's conversation is handled separately
        for challenge in ui.challenges:
            challenge_name = challenge['name']
            history_key = f"history_{challenge_name}"
            if history_key in flask_session:
                flask_session[history_key] = []
            
            # Also reset on API - pass session to use user's API settings
            ui.reset_challenge(challenge_name.lower().replace(' ', '_'), flask_session)
        
        # Clear completed challenges
        flask_session['completed_challenges'] = []
        flask_session.modified = True
        
        flash('All progress has been reset', 'info')
        return redirect(url_for('index'))
    
    # Add a new route to clear user settings
    @app.route('/clear-settings', methods=['POST'])
    def clear_settings():
        """Clear user-specific API settings."""
        if 'user_api_url' in flask_session:
            del flask_session['user_api_url']
        if 'user_api_key' in flask_session:
            del flask_session['user_api_key']
            
        flask_session.modified = True
        
        flash('Your custom API settings have been cleared.', 'info')
        
        # Get referer for redirect, or default to index
        referer = request.headers.get('Referer')
        if referer:
            return redirect(referer)
        return redirect(url_for('index'))
    
    return app

def main() -> int:
    """
    Main entry point for the LLM Challenge UI.
    
    Parses command line arguments and starts the web UI server.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='LLM Challenge UI')
    parser.add_argument('api_url', help='URL of the LLM Challenge API (e.g., http://localhost:5000)')
    parser.add_argument('--port', '-p', type=int, default=5001, help='Port to run the UI server (default: 5001)')
    
    args = parser.parse_args()
    
    try:
        ui = ChallengeUI(args.api_url)
        app = create_app(ui)
        app.run(debug=True, host='0.0.0.0', port=args.port)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())