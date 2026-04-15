mac的安装：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export LITELLM_TOKEN="你的duke gpt api"
python app.py
```

windows的安装:
(假设你用的是powershell)
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LITELLM_TOKEN="你的duke gpt api"
python app.py
```
