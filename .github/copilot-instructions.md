<!--
Guidance for AI coding agents working on LEAudio_PyQt
Keep this short (20-50 lines), actionable, and codebase-specific.
-->

# Copilot instructions — LEAudio_PyQt

Purpose: help an AI agent be immediately productive editing the Multilingual PyQt translator app.

- Project entry points

  - `MainProject/MultilanProject.py` — canonical desktop app used in distribution; contains core STT/translate/TTS workers, VAD, and playback logic.
  - `integrated_translator.py` — a more modular PyQt6 implementation (signals, workers, TTS/STT integration). Good reference for thread-safe signal usage.
  - `main.py`, `responsive_ui.py` — UI variants (PyQt5 and PyQt6 styles). Use them for widget/layout patterns and responsive behavior examples.

- Big-picture architecture (what to edit safely)

  - UI layer (PyQt5/PyQt6 files): `main.py`, `responsive_ui.py`, `MultilanProject.py` (UI sections). Keep GUI changes here.
  - Audio & workers: `MultilanProject.py` and `integrated_translator.py` contain STT (speech_recognition), translation (requests to Google/Mymemory), and TTS (gTTS). Changes here affect runtime/audio flow — run manual tests.
  - Shared patterns: both `MultilanProject.py` and `integrated_translator.py` use a small Signals class (Qt signals) for thread-safe UI updates — follow this pattern when adding background threads.

- Developer workflows & how to run

  - Preferred run for dev/testing: run `MainProject/MultilanProject.py` from that folder (see `MainProject/how_to_run.txt`). Typical commands:
    - Create venv; pip install PyQt5, speech_recognition, gtts, pygame, pyaudio, requests, numpy
    - cd into `MainProject/` and run `python MultilanProject.py`
  - Files to check when debugging audio/permissions: `MainProject/how_to_run.txt`, `MainProject/Replace_Your_Own_API_Guide.txt` (shows where STT/Translate/TTS calls live).

- Project-specific conventions

  - Multiple PyQt versions coexist: some files use PyQt5 (e.g., `main.py`, `MultilanProject.py`) while others use PyQt6 (`responsive_ui.py`, `integrated_translator.py`). Match the module (PyQt5 vs PyQt6) used by the file you edit.
  - Signals-first concurrency: long-running work runs in background threads and emits Qt signals (e.g., `transcription_ready`, `translation_ready`, `tts_ready`). Add/emit signals rather than directly mutating widgets from threads.
  - VAD/energy detection: VAD constants are in `MultilanProject.py` (VAD_SILENCE_TIMEOUT, VAD_ENERGY_THRESHOLD). If tuning recording behavior, update those constants.

- Integration points & external dependencies

  - STT: `speech_recognition` with `recognize_google` (calls to Google free endpoint) — see `do_record_with_vad()` in `MultilanProject.py` and `integrated_translator.py`.
  - Translation: quick Google endpoint `translate.googleapis.com` used as primary; fallback to MyMemory. See `do_translate()`.
  - TTS: `gTTS` used to save MP3 files; files are played with `pygame.mixer` and cleaned up after play. See `do_tts()` and `play_all_audio()`.
  - Audio input/output: `pyaudio` for recording (portaudio system dependency), `pygame` for playback — be careful with device init/termination.

- What to change cautiously / common pitfalls

  - Replacing APIs: `MainProject/Replace_Your_Own_API_Guide.txt` documents where to swap Google APIs for custom endpoints. Keep the signals contract (`translation_ready`, `tts_ready`) when replacing to avoid UI changes.
  - PyQt5 vs PyQt6 imports: do not mix imports in a single file. If migrating a file, update imports and test the GUI start.
  - Audio resource management: ensure `pyaudio.PyAudio().terminate()` and `pygame.mixer.init()/quit()` are handled; dangling resources can block subsequent runs.

- Examples (what to search for)

  - Background worker pattern: search for `signals.translation_ready.emit` and `threading.Thread(target=...)` to find producers/consumers.
  - VAD loop + temp file: search `do_record_with_vad` in `MainProject/MultilanProject.py`.

- Quick checklist for PRs
  - Run the app (`python MainProject/MultilanProject.py`) and exercise the mic flow (if you changed audio/STT/Translate/TTS code).
  - Verify no cross-imports between PyQt5 and PyQt6 in the same module.
  - If changing API calls, keep sample fallback logic and preserve signal emissions so the UI code stays stable.

If any behavior or environment detail is missing (preferred interpreter, CI commands, or a test script), say so and I will add it.
