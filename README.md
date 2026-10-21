# YAVIS – kostenloser, lokaler Sprachassistent für Windows 11

**Status (ehrlich):** Code geschrieben, 10 automatische Tests für Logik/Sicherheit bestanden (Linux-Testumgebung).
**Nicht getestet:** Oberfläche, Mikrofon, Sprachausgabe, PyInstaller-Build und `YAVIS-Setup.exe` – das geht nur auf Windows.
Es gibt noch keine fertige EXE. Erst nach `build.bat` bzw. GitHub-Build und deinem Test ist sie fertig.

## Kosten: 0 €
Ollama (MIT), Qwen2.5 (Apache-2.0 für 3B/7B – bitte Lizenz des gewählten Modells prüfen), faster-whisper (MIT), PySide6 (LGPL),
edge-tts (kostenlos, **braucht Internet**, inoffizielle Schnittstelle – kann sich ändern), DuckDuckGo-Suche (kostenlos, inoffiziell, kann limitiert sein),
Inno Setup (kostenlos), GitHub Actions (kostenlos für öffentliche Repos).

## EXE bekommen – Weg A (ohne Programmierwerkzeuge, kostenlos)
1. Kostenloses Konto auf github.com, neues **öffentliches** Repository, alle Dateien dieses Ordners hochladen.
2. Tab **Actions** → „Build YAVIS-Setup“ → **Run workflow**. Nach ~10–20 Min unter *Artifacts* `YAVIS-Setup` herunterladen.
3. Entpacken, `YAVIS-Setup.exe` doppelklicken. Fertig (Desktop-Verknüpfung + optional Autostart im Installer).

## Weg B (lokal)
Python 3.12 und Inno Setup installieren, dann im Ordner `build.bat` doppelklicken → `dist\YAVIS-Setup.exe`.

## Erster Start
- Fehlt Ollama, öffnet der Installer die Download-Seite (kostenlos). Danach lädt YAVIS beim ersten Start das Modell selbst (~2 GB) und das Hörmodell (~500 MB). Einmalig, dauert.
- Sag „**YAVIS**, öffne YouTube“. Nach einer Antwort kannst du 10 s ohne Aktivierungswort weitersprechen.
- Zahnrad: Aktivierungswörter, Stimme (Frau/Mann), Neutral-Modus, Modell, Autostart, Gedächtnis ansehen/löschen.
- Beenden: Fenster schließen. Stopp-Knopf bricht Denken/Sprechen sofort ab.

## Was YAVIS kann
Siehe **FUNKTIONEN.md** (61 echte Werkzeuge + weitere App-Funktionen). Neue Oberfläche nach deinem Entwurf: Home, Chat, Projekte, Dateien,
Wissen, Tools, Musik, Automatisierungen, Einstellungen. Klick aufs Logo = großer Orb, der beim Sprechen größer/kleiner wird.

## Update einspielen (GitHub, nur im Browser)
Neue Dateien in dein Repository hochladen (Add file → Upload files → Inhalt des Ordners hineinziehen → Commit). Gleiche Dateinamen werden ersetzt.
Der Build startet danach automatisch (Tab Actions).

## Bewusste Grenzen
- Nicht auf Windows getestet: Oberfläche, Mikrofon, Sprache, Musik, Installer. Nur die Logik (25 Tests) läuft automatisch.
- „Zugriff auf alles“ = alles, was im Startmenü steht (Programme, Steam-Spiele) oder eine Website ist, plus freigegebene Ordner. Keine freie Shell.
- Tastatur-Steuerung und Zwischenablage sind standardmäßig AUS (Seite „Tools“ einschalten).
- Beenden/Herunterfahren/Neustart brauchen immer deine Bestätigung. Kaufen/Bezahlen/Senden/Veröffentlichen gibt es nicht als Funktion.
- Stimmen: 13 Varianten aus 11 Neural-Stimmen (Frau/Mann, DE/AT/CH) – die besten kostenlosen, aber keine Menschen. Gefühle über Tempo/Tonhöhe. Benötigt Internet; offline Windows-Stimme (roboterhafter).
- Zuhören: Läuft laute Musik über Lautsprecher, kann die Erkennung stören – mit Kopfhörern oder leiser Musik am besten. Beim Sprechen pausiert das Mikrofon absichtlich (kein Selbsthören).
- Lernen = harmlose Vorlieben als sichtbare Einträge (Seite Wissen), keine Selbstveränderung des Programms.
- Tempo: Häufige Befehle (öffnen, Musik, Zeit, Timer …) laufen ohne KI sofort. Freie Fragen hängen von deinem PC ab (kleines Modell = schneller).
- Websuche nutzt eine inoffizielle kostenlose Schnittstelle; sie kann gelegentlich ausfallen.
