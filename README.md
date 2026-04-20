mac terminal：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Choose one:
# Option 1: Duke GPT API
export LITELLM_TOKEN="your duke gpt api"

# Option 2: OpenAI API
# export OPENAI_API_KEY="your openai api key"

python app.py
```

window powershell:
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Choose one:
# Option 1: Duke GPT API
$env:LITELLM_TOKEN="your duke gpt api"

# Option 2: OpenAI API
# $env:OPENAI_API_KEY="your openai api key"
python app.py
```
