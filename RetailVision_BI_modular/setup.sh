#!/usr/bin/env bash
# Setup RetailVision BI — macOS / Linux
set -e
echo "== Création du venv (.venv) =="
python3 -m venv .venv
source .venv/bin/activate
echo "== Mise à jour de pip =="
pip install --upgrade pip
echo "== Installation des dépendances =="
pip install -r requirements.txt
echo
echo "OK. Ensuite : installer Ollama (https://ollama.com), puis 'ollama pull gemma3:4b'"
echo "Lancer : ./run.sh   ou   streamlit run app/main.py"
