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
Programme **und Spiele** aus dem Startmenü starten (inkl. Steam-Verknüpfungen), Websites/Browser öffnen, Websuche mit Quellen,
Dateien suchen (Desktop/Dokumente/Downloads…), Notizen, Uhrzeit, Gedächtnis (nur auf Wunsch), Verkaufstexte/Angebote entwerfen, Preise recherchieren.

## Bewusste Grenzen
- „Zugriff auf alles“ = alles, was als Startmenü-Programm/Spiel oder Website startbar ist. Keine freie Shell/Admin-Rechte (Sicherheit).
- Löschen, Kaufen, Bezahlen, Veröffentlichen, Nachrichten senden: nicht automatisch; Bestätigungsdialog vorgesehen, die Aktionen selbst sind noch nicht eingebaut.
- Die Stimmen sind die besten kostenlosen (Edge Neural), klingen aber nicht wie ein echter Mensch; Gefühle laufen über Tempo/Tonhöhe. Offline-Stimme (Windows) klingt deutlich robotischer.
- Orb-Bewegung beim Sprechen ist eine Simulation, beim Zuhören reagiert er auf dein Mikrofon.
- „Lernen“: bisher nur über das Gedächtnis (Fakten/Vorlieben), keine Selbstveränderung.
- Geschwindigkeit hängt von deinem PC ab. Ohne Grafikkarte: Modell `qwen2.5:3b` (Standard) + Hörmodell `base`/`small`.
