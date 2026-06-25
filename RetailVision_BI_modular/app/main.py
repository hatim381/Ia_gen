"""Point d'entree : `streamlit run app/main.py`. Delegue a la couche UI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import main

if __name__ == "__main__":
    main()
