"""Configuration centrale — source unique de verite (constantes, modeles, seuils)."""
import os

# --- Domaine metier ---
REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]
PAGES = ["Vue Globale", "Performance", "Régions", "Assistant Q&A"]

DATE_MIN = "2024-01-01"
DATE_MAX = "2025-12-31"

# --- Modeles (surchargeables par variables d'environnement) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")   # modele retenu au benchmark
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")

# Biais Whisper vers le vocabulaire du dashboard
WHISPER_PROMPT = (
    "Accueil, Vue globale, Performance, Régions, Reset, Réinitialiser, "
    "Résumé, Synthèse, Aide, Assistant, Nord, Sud, Est, Ouest, Île-de-France, "
    "Électronique, Vêtements, Alimentation, Maison, Sport, "
    "Affiche, Ventes, Catégorie, Région, Filtre, "
    "Janvier, Février, Mars, Avril, Mai, Juin, "
    "Juillet, Août, Septembre, Octobre, Novembre, Décembre"
)

DATA_PATH = os.getenv("DATA_PATH", "")  # resolu par data.repository si vide
