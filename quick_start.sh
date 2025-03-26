#!/bin/bash

# Ensure the API key is set
if [ -z "$CHATGPT_API_KEY" ]; then
    echo "Error: CHATGPT_API_KEY environment variable is not set."
    exit 1
fi

# Install required dependencies
pip install git+https://github.com/user1342/folly

# Clone the repository
git clone https://github.com/user1342/folly.git

# Start the folly API using OpenAI's ChatGPT API
nohup folly-api "https://api.openai.com/v1" --model "gpt-4" --api-key "$CHATGPT_API_KEY" folly/example_challenges/prompt_injection_masterclass.json > output.log 2>&1 & disown

echo "Folly API now running with ChatGPT."

# Start the folly UI
folly-ui "https://required-juieta-user1342-1a8f84b0.koyeb.app" --port 8000

