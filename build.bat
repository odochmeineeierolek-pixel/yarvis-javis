@echo off
REM Baut YAVIS-Setup.exe lokal (Python 3.12 + Inno Setup nötig). Einfacher: GitHub Actions (siehe README).
python -m venv .venv || goto :err
call .venv\Scripts\activate
pip install -r requirements-dev.txt || goto :err
python -m unittest discover -s tests || goto :err
pyinstaller --noconfirm --noconsole --name YAVIS --collect-all faster_whisper --collect-all ctranslate2 ^
  --collect-all edge_tts --collect-all pyttsx3 --collect-all sounddevice --collect-all duckduckgo_search run_yavis.pyw || goto :err
iscc installer\yavis.iss || goto :err
echo FERTIG: dist\YAVIS-Setup.exe
exit /b 0
:err
echo FEHLER beim Bauen.
exit /b 1
