@echo off
set OAUTHLIB_INSECURE_TRANSPORT=1
pip install -r requirements.txt
python app.py
pause
