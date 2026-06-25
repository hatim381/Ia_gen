# Démarrage — RetailVision BI

## Prérequis
- **Python 3.10+**
- **Ollama** (pour l'IA générative locale) : https://ollama.com

## Installation en une commande

### Windows (PowerShell)
```powershell
cd RetailVision_BI_modular
.\setup.ps1
```
> Si PowerShell bloque le script : `Set-ExecutionPolicy -Scope Process Bypass` puis relance.
> Alternative en invite de commandes : `setup.bat`

### macOS / Linux
```bash
cd RetailVision_BI_modular
chmod +x setup.sh && ./setup.sh
```

Le script crée le `.venv`, met pip à jour et installe **toutes** les dépendances de `requirements.txt`.

## Installation manuelle (équivalent)
```bash
python -m venv .venv
# Windows :  .venv\Scripts\activate
# mac/linux : source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Modèles IA locaux
```bash
ollama pull gemma3:4b      # LLM (intent + narration + Q&A)
# Whisper (STT) se télécharge tout seul au 1er lancement (~140 Mo)
```

## Lancer l'application
```bash
# Windows : .\run.ps1   |   mac/linux : ./run.sh   |   ou directement :
streamlit run app/main.py
```
→ http://localhost:8501

## Autres commandes
```bash
python app/tests/test_features.py            # tests (sans Ollama)
python app/eval/runner.py --brick all        # pipeline d'évaluation
python app/tools/benchmark.py                # benchmark des modèles sur ton PC
```

## Dépannage
- **webrtcvad** échoue à l'installation sous Windows (manque le compilateur C++) :
  `pip install webrtcvad-wheels` (même module, wheel précompilée). Les scripts le tentent automatiquement.
- **Micro non détecté** : la capture vocale lit le micro **de la machine** (sounddevice).
  Vérifie qu'un micro est branché et autorisé.
- **Ollama injoignable** : lance `ollama serve` (ou l'app Ollama) avant de démarrer l'app.
