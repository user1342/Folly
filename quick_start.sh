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
folly-api "https://api.openai.com/v1" --model "gpt-4" --api-key "$CHATGPT_API_KEY" folly/example_challenges/test.json &

echo "Folly API now running with ChatGPT."

# Start the folly UI
folly-ui "http://localhost:5000" --port 8000

