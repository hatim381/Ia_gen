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

---

## Nouvelles fonctionnalités

### Modèle Whisper français (configurable)
Whisper est déjà forcé au français. Pour un modèle spécialisé FR, change une variable (sans toucher au code) :
```powershell
# rapide (défaut)        : base
# meilleur               : small
# spécialisé FR (lourd)  : un repo CTranslate2 FR
$env:WHISPER_MODEL = "bofenghuang/whisper-large-v3-french-distil-dec2"
.\run.ps1
```

### Résumés sur toutes les pages + lecture vocale (TTS)
Chaque page (Vue Globale, Performance, Régions) a un bouton **« 🤖 Générer la synthèse »** puis **« 🔊 Lire »**
qui lit le texte à voix haute via la voix française du navigateur (aucune installation).

### Chatbot flottant (toutes les pages)
Un bouton **💬 Assistant** en bas à droite ouvre un chat analytique en langage naturel,
branché sur le moteur Q&A sécurisé (text-to-query). Disponible sur toutes les pages.

### Écoute mains-libres par mot-clé (openWakeWord)
Deux modes dans la barre latérale : **🎤 Démarrer l'écoute** (immédiat) et
**🪄 Écoute mains-libres** (le micro attend un mot-clé pour s'activer).
```powershell
$env:WAKE_ENABLED = "1"          # activer/désactiver
$env:WAKE_MODEL   = "hey_jarvis" # mot-clé pré-entraîné openWakeWord
```
> Mot-clé personnalisé (ex. « ok dashboard ») : openWakeWord fournit des mots-clés pré-entraînés
> (`hey_jarvis`, `alexa`, `hey_mycroft`…). Pour une phrase 100 % custom, entraîne un modèle
> `.onnx`/`.tflite` (voir https://github.com/dscripka/openWakeWord) et mets son chemin dans `WAKE_MODEL`.
> Si openWakeWord n'est pas installé, le bouton classique reste disponible (dégradation gracieuse).
