@echo off
echo Iniciando ngrok...
start C:\ngrok\ngrok.exe http 5000
timeout /t 3
echo Iniciando sistema...
python app.py
pause