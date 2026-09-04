# MyBrowser

A Chromium-based desktop browser built with Python + PySide6/QtWebEngine.

**Current status: Phase 1 (browser core) is implemented.** Tabs, navigation,
address bar, keyboard shortcuts, and a persistent Chromium profile all work.
AI-assisted quiz detection (Phases 2–4) is scaffolded but not yet implemented.

> A note on scope: the planned quiz-detection/AI-verification feature is
> designed to read on-page question/answer content and check it against a
> local LLM. It is **not** intended, and should not be configured, to
> auto-answer real graded quizzes, tests, or exams — see the roadmap section
> below for the intended use case discussion before Phase 2/3 land.

---

## 1. Installation

Requires Python 3.12+.

```bash
python -m venv .venv
```

Activate the virtual environment:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 2. Running the browser

```bash
python main.py
```

A window titled "MyBrowser" opens at 1400x900 with one tab open on the
new-tab page. Type a URL or a search query into the address bar and press
Enter.

## 3. Running tests

```bash
pytest
```

Phase 1 tests cover URL normalization / search-query handling
(`tests/test_navigation.py`) and require no running services, no display
server beyond what pytest needs, and no network access.

`tests/test_quiz_detector.py` and `tests/test_ollama.py` are currently
skipped placeholders — they'll be filled in during Phase 2 and Phase 3
respectively, and are designed to run fully mocked (no live Ollama instance
required).

## 4. Project structure

```text
MyBrowser/
├── main.py                # Application entry point
├── requirements.txt
├── README.md
│
├── browser/                # UI layer (Phase 1 — implemented)
│   ├── window.py           # MainWindow: wires nav bar + tabs together
│   ├── tabs.py              # Tab lifecycle: new/close/switch/reorder
│   ├── navigation.py        # Nav bar widget + URL/search resolution logic
│   ├── webview.py           # QWebEngineView wrapper + new-tab page HTML
│   ├── profile.py           # Persistent QWebEngineProfile (cookies/cache)
│   ├── menu.py              # "⋮" menu: Ollama status/model picker, AI-review + debug toggles
│   ├── debug_log.py         # In-memory event log powering Debug Mode (real traffic only)
│   ├── debug_panel.py       # Debug Mode's read-only traffic-log panel
│   └── shortcuts.py         # Keyboard shortcut wiring
│
├── ai/                      # Phase 3 — not yet implemented
│   ├── ollama.py            # Will talk to a local Ollama instance
│   ├── verifier.py          # Will validate/structure model output
│   └── prompts.py           # Will hold prompt templates
│
├── quiz/                    # Phase 2 — not yet implemented
│   ├── detector.py          # Will inspect page DOM for quiz structures
│   ├── parser.py            # Will turn raw DOM matches into QuizQuestion
│   └── models.py            # QuizQuestion data model
│
├── server/                  # Phase 4 — not yet implemented
│   ├── client.py            # Will POST verified results to a backend
│   └── models.py            # Request/response schemas
│
├── config/
│   └── settings.py          # JSON-persisted app settings (Phase 1: used)
│
├── utils/
│   └── logger.py            # Shared logging setup
│
└── tests/
    ├── test_navigation.py    # Implemented (Phase 1)
    ├── test_quiz_detector.py # Skipped placeholder (Phase 2)
    └── test_ollama.py        # Skipped placeholder (Phase 3)
```

## 5. The "⋮" settings menu

The toolbar's rightmost button opens a menu with:

- **Ollama status** — a live "Online (N models)" / "Not running" indicator.
  The check runs on a background thread against `GET {ollama_url}/api/tags`
  each time you open the menu, so the UI never freezes waiting on it.
- **Ollama Model** — a submenu listing installed models (populated from the
  status check above); picking one saves it to settings immediately.
- **Send quiz data to AI for review** — a toggle, on by default. Turning it
  off means quiz data is never sent to Ollama. (Once the backend
  integration in Phase 4 exists, this same flag will control whether
  detected data instead goes directly to the server.)
- **Debug Mode** — a toggle that splits the window: the webpage stays on
  the left, and a live, read-only log of real AI (and, later, server)
  request/response traffic appears on the right. It only ever shows real
  traffic that actually happened — right now that's the Ollama status
  check requests you see in this same menu; it'll show real quiz-AI and
  server traffic once Phases 2–4 exist. Off by default; never blocks
  normal browsing.

This menu only manages connectivity/settings right now — no quiz data is
detected or sent anywhere yet, since Phase 2/3 haven't landed.

## 6. Keyboard shortcuts (Phase 1)

| Shortcut       | Action                  |
|----------------|--------------------------|
| Ctrl+L         | Focus address bar        |
| Ctrl+T         | New tab                  |
| Ctrl+W         | Close current tab        |
| Ctrl+Shift+T   | Reopen last closed tab   |
| Ctrl+R / F5    | Reload                   |
| Alt+Left       | Back                     |
| Alt+Right      | Forward                  |

## 7. Configuration

Settings are stored as JSON at (Windows) `%APPDATA%\MyBrowser\settings.json`
or (Linux/macOS) `~/.config/MyBrowser/settings.json`, and are created
automatically on first run with sensible defaults. Relevant now:

```json
{
  "home_page": "https://www.google.com",
  "search_engine_url": "https://www.google.com/search?q={query}",
  "window_width": 1400,
  "window_height": 900
}
```

The `ollama_url`, `ollama_model`, `backend_url`, `ai_confidence_threshold`,
and `quiz_detection_enabled` fields already exist in the schema for later
phases but have no effect yet.

## 8. Ollama (for later phases — not required for Phase 1)

Phase 1 does not use Ollama at all — you can build, run, and test the
browser without installing it. When Phase 3 lands, you'll separately
install and run Ollama (https://ollama.com), pull a model, e.g.:

```bash
ollama pull qwen2.5
```

and the browser will talk to it over HTTP at `http://localhost:11434` by
default. The model name will be configurable in settings rather than
hard-coded.

## 9. Building a Windows .exe

Not yet finalized (this arrives with Phase 5, once QtWebEngine's runtime
files need to be verified in a packaged build), but the base command will
be:

```bash
pyinstaller --noconfirm --windowed --name MyBrowser main.py
```

QtWebEngine ships its own Chromium resources (`.pak` files, `icudtl.dat`,
locales, and the QtWebEngineProcess executable) that a bare PyInstaller
command frequently misses. A `MyBrowser.spec` file that explicitly bundles
`PySide6/Qt/resources` and `PySide6/Qt/translations/qtwebengine_locales`
will be added and tested before Phase 5 is considered complete — do not
rely on the bare command above yet.

## 10. Roadmap

- **Phase 1 (done):** Browser window, tabs, navigation, Chromium rendering.
- **Phase 2:** DOM-based quiz detection + a non-blocking side panel showing
  detected question/options.
- **Phase 3:** Local Ollama integration with structured, validated JSON
  output and confidence display.
- **Phase 4:** Optional backend submission of verified results, off by
  default, with the browser fully functional if the backend is unreachable.
- **Phase 5:** PyInstaller packaging into `MyBrowser.exe`.
