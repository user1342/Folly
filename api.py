#!/usr/bin/env python3
"""
LLM Testing Tool - API Server Component

This module provides a Flask REST API for testing LLM prompt injection challenges.
It handles LLM communication, response validation, and conversation management.
"""
import argparse
import json
import os
import datetime
import uuid
from typing import Dict, List, Optional, Any, Union

from openai import OpenAI
from flask import Flask, request, jsonify, session
from flask_session import Session
from fuzzywuzzy import fuzz

class LLMTester:
    """
    Main class for testing LLMs with various challenge scenarios.
    
    Handles communication with LLM APIs, validation of responses,
    and manages conversation history.
    """
    def __init__(self, api_url: str, api_key: Optional[str] = None, 
                 config_path: Optional[str] = None, model: Optional[str] = None,
                 log_path: Optional[str] = None) -> None:
        """
        Initialize the LLM Tester with API details and configuration.
        
        Args:
            api_url: Base URL for the LLM API
            api_key: API key for authentication (optional)
            config_path: Path to configuration JSON file
            model: Default model name to use for API calls
            log_path: Path to log file for storing interaction data (optional)
        """
        self.api_url: str = api_url
        self.client: Optional[OpenAI] = None
        self.config: List[Dict[str, Any]] = []
        # Remove conversations dictionary as we'll use Flask sessions instead
        self.model: Optional[str] = model  # Store the model name passed from command line
        self.log_path: Optional[str] = log_path  # Store the log file path
        
        # Initialize OpenAI client with the provided API URL
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key or 'dummy'  # Use provided key or dummy if none given
        )
        
        # Load configuration file
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """
        Load challenge configurations from a JSON file.
        
        Args:
            config_path: Path to the configuration JSON file
            
        Raises:
            ValueError: If the config file is invalid, missing, or has missing required fields
        """
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            
            # Validate config structure
            for challenge in self.config:
                required_fields = ['name', 'system_prompt', 'input', 'deny_inputs', 'deny_outputs']
                for field in required_fields:
                    if field not in challenge:
                        raise ValueError(f"Missing required field '{field}' in challenge: {challenge.get('name', 'unknown')}")
                
                # Process challenge config
                self._process_challenge_config(challenge)
        
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {config_path}")
        except FileNotFoundError:
            raise ValueError(f"Config file not found: {config_path}")
    
    def _process_challenge_config(self, challenge: Dict[str, Any]) -> None:
        """
        Process and normalize challenge configuration.
        
        Args:
            challenge: Challenge configuration dictionary
        """
        # Ensure answers field exists
        if "answers" not in challenge or not challenge["answers"]:
            # Add default answer validation criteria based on the challenge name and content
            keywords = [word for word in challenge["name"].split() if len(word) > 3]
            keywords.extend([word for word in challenge["system_prompt"].split()[:10] if len(word) > 4])
            challenge["answers"] = keywords[:5] if keywords else ["challenge criteria"]
        
        # Convert 'match' to 'fuzzy_match_score' if present
        if "match" in challenge:
            challenge["fuzzy_match_score"] = challenge["match"]
        
        # Ensure fuzzy_match_score is set properly
        if "fuzzy_match_score" not in challenge:
            challenge["fuzzy_match_score"] = None
        elif challenge["fuzzy_match_score"] is not None:
            # Validate that fuzzy_match_score is a number
            try:
                challenge["fuzzy_match_score"] = int(float(challenge["fuzzy_match_score"]))
            except (ValueError, TypeError):
                print(f"Warning: Challenge '{challenge['name']}' has invalid fuzzy match threshold. Setting to None.")
                challenge["fuzzy_match_score"] = None
                
        # Set match type for template rendering
        challenge["match_type"] = "fuzzy" if challenge.get("fuzzy_match_score") is not None else "direct"
    
    def check_denied_content(self, text: str, denied_list: List[str]) -> Optional[str]:
        """
        Check if any denied content appears in the given text.
        
        Args:
            text: The text to check
            denied_list: List of denied content strings
            
        Returns:
            The first matched denied content or None if no matches
        """
        for denied in denied_list:
            if denied.lower() in text.lower():
                return denied
        return None
    
    def log_interaction(self, challenge_name: str, user_input: str, 
                        response: Dict[str, Any], conversation: List[Dict[str, str]]) -> None:
        """
        Log an interaction to the specified log file.
        
        Args:
            challenge_name: Name of the challenge
            user_input: User input that triggered the interaction
            response: Response from the LLM API
            conversation: Current conversation history
        """
        if not self.log_path:
            return
            
        try:
            # Create log entry
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "challenge": challenge_name,
                "user_input": user_input,
                "response": response,
                "conversation_history": conversation.copy()
            }
            
            # Ensure directory exists
            log_dir = os.path.dirname(self.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Append to log file
            with open(self.log_path, 'a+') as f:
                # If file is empty, start with an array
                f.seek(0)
                content = f.read().strip()
                if not content:
                    f.write('[\n')
                else:
                    # Check if content ends with ']' and remove it to continue the array
                    if content.endswith(']'):
                        f.seek(0, os.SEEK_END)
                        f.truncate(f.tell() - 1)
                    f.write(',\n')
                
                # Write the entry
                json.dump(log_entry, f, indent=2)
                f.write('\n]')
                
        except Exception as e:
            print(f"Error logging interaction: {e}")
    
    def call_llm(self, challenge_name: str, user_input: str, conversation: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Call the LLM API with the given input for a specific challenge.
        
        Args:
            challenge_name: Name of the challenge to use
            user_input: User input to send to the LLM
            conversation: Current conversation history (from session)
            
        Returns:
            Dictionary containing the API response or error information
        """
        # Find the challenge configuration
        challenge = next((c for c in self.config if c['name'] == challenge_name), None)
        if not challenge:
            return {"status": "error", "reason": f"Challenge '{challenge_name}' not found"}
        
        # Check for denied inputs
        denied_input = self.check_denied_content(user_input, challenge['deny_inputs'])
        if denied_input:
            result = {
                "status": "failed",
                "reason": f"Input contains denied content: '{denied_input}'",
                "input": user_input
            }
            # No logging for denied inputs
            return result
        
        # Use provided conversation or empty list
        conversation = conversation or []
        
        # Prepare messages for the LLM
        messages = [{"role": "system", "content": challenge["system_prompt"]}]
        
        # Add conversation history
        for msg in conversation:
            messages.append(msg)
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Use the model specified in command line if available, otherwise use default
            model_to_use = self.model or "gpt-3.5-turbo"
            
            # Call the API with the specified model
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages
            )
            
            # Extract response content
            assistant_response = response.choices[0].message.content
            
            # Check for denied outputs
            denied_output = self.check_denied_content(assistant_response, challenge['deny_outputs'])
            if denied_output:
                result = {
                    "status": "failed",
                    "reason": f"Output contains denied content: '{denied_output}'",
                    "input": user_input,
                    "output": assistant_response
                }
                # No logging for denied outputs
                return result
            
            # Don't update server-side conversation storage; instead return the new messages
            # to be stored in user session
            updated_conversation = conversation.copy()
            updated_conversation.append({"role": "user", "content": user_input})
            updated_conversation.append({"role": "assistant", "content": assistant_response})
            
            result = {
                "status": "success",
                "input": user_input,
                "output": assistant_response,
                "conversation": updated_conversation
            }
            
            # Only log successful interactions
            if self.log_path:
                self.log_interaction(challenge_name, user_input, result, updated_conversation)
                
            return result
            
        except Exception as e:
            result = {
                "status": "error",
                "reason": str(e),
                "input": user_input
            }
            # No logging for error conditions
            return result
    
    def validate_response(self, challenge_name: str, response_text: str) -> Dict[str, Any]:
        """
        Validate a response against the challenge criteria.
        
        Args:
            challenge_name: Name of the challenge to validate against
            response_text: The text to validate
            
        Returns:
            Dictionary containing validation results
        """
        # Find the challenge configuration
        challenge = next((c for c in self.config if c['name'].lower().replace(' ', '_') == challenge_name.lower().replace(' ', '_')), None)
        if not challenge:
            return {
                "valid": False,
                "reason": f"Challenge '{challenge_name}' not found",
                "match_type": "error",
                "validation_issue": True
            }
        
        # Ensure valid answers exist
        if "answers" not in challenge or not challenge["answers"]:
            return {
                "valid": False,
                "reason": "This challenge requires a response containing specific keywords or patterns.",
                "missing_keywords": ["proper validation criteria"],
                "match_type": "unknown",
                "validation_issue": True
            }
                
        answers = challenge["answers"]
        
        # Get fuzzy threshold from either fuzzy_match_score or match field
        has_fuzzy = False
        fuzzy_threshold = None
        
        if "fuzzy_match_score" in challenge and challenge["fuzzy_match_score"] is not None:
            has_fuzzy = True
            fuzzy_threshold = challenge["fuzzy_match_score"]
        elif "match" in challenge and challenge["match"] is not None:
            has_fuzzy = True
            fuzzy_threshold = challenge["match"]
        
        # Based on presence of fuzzy threshold, use appropriate validation
        if has_fuzzy and fuzzy_threshold is not None:
            try:
                # Convert to int if needed
                fuzzy_threshold = int(fuzzy_threshold)
                
                # Use fuzzy matching
                best_match = 0
                best_answer = ""
                matches = []
                
                for answer in answers:
                    # For short answers, check for direct inclusion
                    if len(answer) < 20:
                        if answer.lower() in response_text.lower():
                            # Direct match found - give it a high score
                            current_match = 100
                        else:
                            # Use token set ratio for partial matching
                            current_match = fuzz.token_set_ratio(response_text.lower(), answer.lower())
                    else:
                        # Use token set ratio for longer text
                        current_match = fuzz.token_set_ratio(response_text.lower(), answer.lower())
                    
                    matches.append({"answer": answer, "score": current_match})
                    
                    if current_match > best_match:
                        best_match = current_match
                        best_answer = answer
                
                # Sort matches by score descending
                matches.sort(key=lambda x: x["score"], reverse=True)
                
                # Check if the match exceeds threshold
                if best_match >= fuzzy_threshold:
                    return {
                        "valid": True,
                        "match_percent": best_match,
                        "matched_answer": best_answer,
                        "all_matches": matches,
                        "match_type": "fuzzy",
                        "fuzzy_threshold": fuzzy_threshold,
                        "reason": f"Response matches {best_match}% with expected answer."
                    }
                else:
                    return {
                        "valid": False,
                        "match_percent": best_match,
                        "matched_answer": best_answer,
                        "all_matches": matches,
                        "match_type": "fuzzy",
                        "fuzzy_threshold": fuzzy_threshold,
                        "reason": f"Best match was {best_match}%, below threshold of {fuzzy_threshold}%."
                    }
            except (ValueError, TypeError) as e:
                return {
                    "valid": False,
                    "reason": f"Invalid fuzzy match threshold: {fuzzy_threshold}. Contact administrator.",
                    "match_type": "error",
                    "validation_issue": True
                }
        else:
            # Use direct keyword matching as fallback
            found_keywords = []
            missing_keywords = []
            
            for keyword in answers:
                if keyword.lower() in response_text.lower():
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            if len(found_keywords) > 0:
                return {
                    "valid": True, 
                    "found_keywords": found_keywords,
                    "missing_keywords": missing_keywords if missing_keywords else None,
                    "match_type": "direct",
                    "reason": f"Found {len(found_keywords)} out of {len(answers)} required keywords in the response."
                }
            else:
                return {
                    "valid": False,
                    "found_keywords": None,
                    "missing_keywords": missing_keywords,
                    "match_type": "direct",
                    "reason": "Your response didn't contain any of the required keywords."
                }
    
    def reset_conversation(self, challenge_name: str) -> Dict[str, Any]:
        """
        Prepare a reset response for a challenge conversation.
        
        Args:
            challenge_name: Name of the challenge to reset
            
        Returns:
            Dictionary containing status of the reset operation
        """
        challenge = next((c for c in self.config if c['name'].lower().replace(' ', '_') == challenge_name.lower().replace(' ', '_')), None)
        if not challenge:
            return {"status": "error", "reason": f"Challenge '{challenge_name}' not found"}
            
        # No need to reset conversations dictionary as each user maintains their own state
        return {"status": "success", "message": f"Conversation for '{challenge['name']}' has been reset"}


def create_app(tester: LLMTester) -> Flask:
    """Create and configure a Flask application for the API server."""
    app = Flask(__name__)
    
    # Configure server-side session
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    Session(app)
    
    # Create a dictionary to store conversations by user token
    user_conversations = {}
    
    # Create dynamic routes for each challenge
    for challenge in tester.config:
        challenge_name = challenge['name']
        
        # Define route handler with proper closure variable binding
        def create_route_handler(challenge_name=challenge_name):
            """Create a route handler for a specific challenge."""
            def route_handler():
                data = request.json
                user_input = data.get('input', '')
                
                # Get user token from header or generate a new one
                user_token = request.headers.get('X-User-Token')
                
                if not user_token:
                    # For users coming through the Flask session
                    user_token = session.get('user_token')
                    if not user_token:
                        user_token = str(uuid.uuid4())
                        session['user_token'] = user_token
                
                # Create a unique key for this user and challenge
                conversation_key = f"{user_token}:{challenge_name.lower().replace(' ', '_')}"
                
                # Get or create conversation history for this user and challenge
                if conversation_key not in user_conversations:
                    user_conversations[conversation_key] = []
                
                # Call LLM with the user-specific and challenge-specific conversation
                result = tester.call_llm(challenge_name, user_input, user_conversations[conversation_key])
                
                # Update conversation state if successful
                if result.get('status') == 'success' and 'conversation' in result:
                    user_conversations[conversation_key] = result['conversation']
                    # Remove conversation from result to avoid duplicate data
                    del result['conversation']
                
                return jsonify(result)
            return route_handler
        
        # Register the route
        endpoint_name = f"challenge_{challenge_name.lower().replace(' ', '_')}"
        app.add_url_rule(
            f"/challenge/{challenge_name.lower().replace(' ', '_')}",
            endpoint=endpoint_name,
            view_func=create_route_handler(),
            methods=['POST']
        )
    
    # Add a route to list all challenges with more details
    @app.route("/challenges", methods=["GET"])
    def list_challenges():
        """Return a list of all available challenges with their details"""
        return jsonify([{
            "name": challenge["name"],
            "endpoint": f"/challenge/{challenge['name'].lower().replace(' ', '_')}",
            "description": challenge.get("description", ""),
            "input": challenge.get("input", ""),
            "answers": challenge.get("answers", []),
            "fuzzy_match_score": challenge.get("fuzzy_match_score", None),
            "match": challenge.get("match", None),
            "match_type": challenge.get("match_type", "direct"),
            "help": challenge.get("help", None)  # Include help field in response
        } for challenge in tester.config])
    
    # Add a route to reset a specific conversation
    @app.route("/reset/<challenge_name>", methods=["POST"])
    def reset_conversation(challenge_name: str):
        """Reset the conversation for a specific challenge"""
        result = tester.reset_conversation(challenge_name)
        if "error" in result:
            return jsonify(result), 404
        
        # Get user token from header or session
        user_token = request.headers.get('X-User-Token')
        if not user_token and 'user_token' in session:
            user_token = session['user_token']
        
        # If we have a user token, reset their conversation
        if user_token:
            conversation_key = f"{user_token}:{challenge_name.lower().replace(' ', '_')}"
            if conversation_key in user_conversations:
                user_conversations[conversation_key] = []
        
        return jsonify(result)
    
    # Add a new endpoint for validating responses
    @app.route("/validate/<challenge_name>", methods=["POST"])
    def validate_response(challenge_name: str):
        """Validate if a response passes the challenge criteria"""
        data = request.json
        if not data or 'output' not in data:
            return jsonify({
                "valid": False,
                "reason": "No output provided for validation",
                "validation_issue": True,
                "match_type": "error"
            })
        
        result = tester.validate_response(challenge_name, data['output'])
        return jsonify(result)
    
    return app

def main() -> int:
    """
    Main entry point for the LLM Testing Tool.
    
    Parses command line arguments and starts the API server.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='LLM Testing Tool with Flask API')
    parser.add_argument('api', help='API URL (e.g., https://api.openai.com/v1 or http://localhost:11434/v1)')
    parser.add_argument('--api-key', '-k', help='API key (optional if not required by the API)')
    parser.add_argument('--model', '-m', help='Model name to use (e.g., gpt-3.5-turbo, llama3.2)')
    parser.add_argument('config', help='Path to configuration JSON file')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the API server (default: 5000)')
    parser.add_argument('--log', help='Path to save interaction logs in JSON format')
    
    args = parser.parse_args()
    
    try:
        # Create LLM tester instance with model and log path parameters
        tester = LLMTester(args.api, args.api_key, args.config, args.model, args.log)
        
        # Create and run Flask app
        app = create_app(tester)
        app.run(debug=True, host='0.0.0.0', port=args.port)
        
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
