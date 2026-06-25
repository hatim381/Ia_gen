"""Configuration centrale — source unique de verite (constantes, modeles, seuils)."""
import os

# --- Domaine metier ---
REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]
PAGES = ["Vue Globale", "Performance", "Régions"]   # le chatbot est flottant sur toutes les pages

DATE_MIN = "2024-01-01"
DATE_MAX = "2025-12-31"

# --- LLM (surchargeable par variables d'environnement) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))

# --- STT Whisper ---
# Presets pratiques (mettre WHISPER_MODEL a l'une de ces valeurs) :
#   "base"   -> multilingue force au FR, rapide (~1s CPU), defaut.
#   "small"  -> meilleure qualite, ~3s CPU.
#   "bofenghuang/whisper-large-v3-french-distil-dec2"  -> specialise FR (decodeur distille),
#   "deepdml/faster-whisper-large-v3-turbo-ct2"        -> turbo, ou un repo CT2 FR pret a l'emploi.
# Les modeles "french-distil" sont bases sur large-v3 (~1.5 Go) : meilleure precision FR mais
# plus lourds sur CPU sans GPU. A choisir selon la puissance du poste.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
WHISPER_LANG = os.getenv("WHISPER_LANG", "fr")

WHISPER_PROMPT = (
    "Accueil, Vue globale, Performance, Régions, Reset, Réinitialiser, "
    "Résumé, Synthèse, Aide, Assistant, Nord, Sud, Est, Ouest, Île-de-France, "
    "Électronique, Vêtements, Alimentation, Maison, Sport, "
    "Affiche, Ventes, Catégorie, Région, Filtre, "
    "Janvier, Février, Mars, Avril, Mai, Juin, "
    "Juillet, Août, Septembre, Octobre, Novembre, Décembre"
)

# --- Wake-word (openWakeWord) ---
# WAKE_ENABLED active l'ecoute mains-libres par mot-cle (en plus du bouton).
# WAKE_MODEL : un mot-cle pre-entraine openWakeWord ("hey_jarvis", "alexa", "hey_mycroft"...)
# OU le chemin vers un modele .onnx/.tflite custom (ex. "ok dashboard" entraine soi-meme).
WAKE_ENABLED = os.getenv("WAKE_ENABLED", "1") == "1"
WAKE_MODEL = os.getenv("WAKE_MODEL", "hey_jarvis")   # ou "alexa", "hey_mycroft"
WAKE_PHRASE_LABEL = os.getenv("WAKE_PHRASE_LABEL", "ok dashboard")  # libelle affiche a l'utilisateur
WAKE_THRESHOLD = float(os.getenv("WAKE_THRESHOLD", "0.5"))

DATA_PATH = os.getenv("DATA_PATH", "")
