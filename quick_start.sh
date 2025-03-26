curl -fsSL https://ollama.com/install.sh | sh
ollama run llama3.1 &
pip install git+https://github.com/user1342/folly
git clone https://github.com/user1342/folly.git
nohup folly-api http://localhost:11434/v1 --model llama3.1 folly/example_challenges/prompt_injection_masterclass.json > output.log 2>&1 & disown
nohup folly-ui http://localhost:8000 > folly-ui.log 2>&1 & disown
