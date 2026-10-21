# Startet YAVIS ohne Konsolenfenster
import os, sys
if sys.stdout is None:          # ohne Konsole gibt es keine Ausgabekanäle -> sonst Abstürze in Bibliotheken
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
from yavis.app import main
main()
