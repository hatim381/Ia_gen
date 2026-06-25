@echo off
REM Setup RetailVision BI — Windows (cmd)
echo == Creation du venv (.venv) ==
py -3 -m venv .venv || python -m venv .venv
call .venv\Scripts\activate.bat
echo == Mise a jour de pip ==
python -m pip install --upgrade pip
echo == Installation des dependances ==
pip install -r requirements.txt
if errorlevel 1 (
  echo webrtcvad a echoue, bascule sur webrtcvad-wheels
  pip install webrtcvad-wheels
  pip install -r requirements.txt
)
echo.
echo OK. Ensuite : installer Ollama (https://ollama.com), puis "ollama pull gemma3:4b"
echo Lancer : run.bat   ou   streamlit run app/main.py
