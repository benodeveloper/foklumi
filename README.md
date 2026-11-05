# Foklumi

A Pomodoro-style focus timer that turns every break into a short German vocabulary lesson.

[![Tests](https://github.com/benodeveloper/foklumi/actions/workflows/test.yml/badge.svg)](https://github.com/benodeveloper/foklumi/actions/workflows/test.yml)

**Version:** 0.1.0-beta (first beta) — **tested only on Arch Linux** (maintainer’s current system: Arch Linux rolling, X11/XFCE).

- **Focus:** 45-minute countdown (configurable).
- **Break:** a 2-minute break starts automatically (configurable). There is no long break.
- **Locked screen:** during the break a fullscreen overlay covers every monitor. On X11 it also grabs the keyboard and mouse.
- **One word per break:** the German word, its English translation, a plain-English explanation, an example sentence in German and its English translation.
- **Pause a break:** freeze the countdown while you finish reading, then resume it.
- **Listen buttons:** hear the word and the sentence spoken aloud with [Piper](https://github.com/rhasspy/piper) (natural voice), with fallbacks to espeak-ng, macOS `say` and Windows SAPI.
- **Floating round timer:** a draggable, always-on-top circular timer with a clock-style progress ring.
- **Settings:** timing, colors, timer size, speech speed, vocabulary file and more, saved to a JSON file.
- **Run at login:** optional autostart (Linux/Windows/macOS).
- **Fetch random words:** download random German candidates (noun/verb/adj/adv) from free/open sources (Wiktionary API + local Kaikki/Tatoeba) via **Settings → Vocabulary**.

The bundled vocabulary is a curated A1 list (19 words for now) with noun and verb grammar generated from [Kaikki](https://kaikki.org/). You can point the app at your own list.

## Platform support

| Platform | Window cover | Keyboard/mouse lock |
|---|---|---|
| Linux, X11 (XFCE, etc.) | yes | yes |
| Linux, Wayland | yes | no (Wayland does not allow it) |
| Windows / macOS | yes | no |

Developed and **tested only on Arch Linux** (maintainer’s current system: Arch Linux rolling, kernel 7.2.x, XFCE 4 on X11). Other platforms/desktops are untested in this beta.

## Requirements

- Python 3.11 or newer
- PySide6 (installed from `requirements.txt`)
- For speech (optional but recommended), on Linux: `piper-tts` and `aplay` (from `alsa-utils`), plus a German Piper voice such as `de_DE-thorsten-medium` (the `.onnx` file and its `.onnx.json` must sit side by side). Without Piper the app uses `espeak-ng` if installed.
- On Arch, the packaged build also needs `xcb-util-cursor` for the Qt X11 plugin.

## Run from source

```bash
git clone https://github.com/benodeveloper/foklumi.git
cd foklumi
python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
python main.py
```

Useful flags for testing:

| Flag | Effect |
|---|---|
| `--fast` | 10 s focus and 15 s break, ignoring saved timing |
| `--no-grab` | cover the screen but never grab keyboard and mouse |

Run the tests with `python -m unittest discover -s tests -t . -v`.

## Using the app

- **Drag** the round timer to move it.
- **Buttons:** ▶ start, ■ stop, » skip to the next phase.
- **Right-click** the timer for **Settings…** and **Quit**.
- **Pause break / Resume break:** pauses or resumes the countdown without hiding the word.
- **Emergency exit:** `Esc` ends a break and stops the timer. You can choose a different key in **Settings → Break screen → Emergency exit**. All other keys are blocked during a locked break.
- If you ever get stuck, switch to a text console with `Ctrl+Alt+F2`, log in and run `pkill -f main.py` (or `pkill -x foklumi` for the packaged build). Killing the process releases the grab.

## Settings

Open them from the right-click menu. They are stored in `~/.config/foklumi/settings.json` (on Windows `%APPDATA%\foklumi\settings.json`), outside the project folder.

| Group | Options |
|---|---|
| Timing | focus minutes, break seconds, auto-start the next focus session |
| Break screen | auto-speak, speech speed, lock keyboard and mouse, emergency exit key, Piper model path |
| Appearance | focus/break/idle colors, timer size, always on top, run at login |
| Vocabulary | path to a custom vocabulary JSON file, fetch random candidates (Wiktionary/Kaikki/Tatoeba) |

Timing changes apply from the next phase. Everything else applies immediately.

## Speech setup

Set the German Piper model in **Settings → Break screen → Piper model**, or export it as an environment variable:

```bash
export PIPER_MODEL_DE=~/voices/de_DE-thorsten-medium.onnx
```

Check it works outside the app:

```bash
echo "Ich lerne jeden Tag Deutsch" | piper-tts -m ~/voices/de_DE-thorsten-medium.onnx --output-raw | aplay -q -t raw -f S16_LE -r 22050 -c 1
```

The terminal prints which engine is active when the app starts (`[speech] using piper`).

## Custom vocabulary

Point **Settings → Vocabulary** at a JSON file. The file must use schema 2:

```json
{
  "schema": 2,
  "words": [
    {
      "id": "apfel-noun",
      "lemma": "Apfel",
      "pos": "noun",
      "level": "A1",
      "english": "apple",
      "explanation": "A round fruit that grows on trees.",
      "examples": [
        {
          "de": "Ich esse einen Apfel zum Frühstück.",
          "en": "I eat an apple for breakfast.",
          "source": "curated"
        }
      ],
      "noun": {
        "article": "der",
        "plural": "Äpfel",
        "genitive": "Apfels"
      }
    }
  ]
}
```

`pos` is `noun`, `verb`, `adj`, or `adv`. The `noun` and `verb` blocks are optional; without them the word still appears, but its grammar section is omitted. A `verb` block contains `auxiliary`, `separable`, `reflexive`, `participle`, `pronouns`, `tenses`, and `imperative` — see `data/vocab.json` for a complete example.

Words are shuffled and never repeat until the whole list has been shown. If the file is missing or broken, the app falls back to the built-in list and prints a warning.

## Rebuilding the bundled vocabulary

The learner-facing text lives in `data/curated_words.json`. Noun and verb grammar is generated from [Kaikki](https://kaikki.org/), and Tatoeba is used only as an example fallback for words without a curated sentence.

```bash
# One-time download: Kaikki (~1 GB) and Tatoeba into tools/
python tools/download_data.py

# Regenerate data/vocab.json and validate it
python tools/build_pipeline.py
```

The build refuses to write `data/vocab.json` if a noun lacks a definite article, a verb lacks its present tense, participle or auxiliary, or an entry has no translation. Less critical gaps are printed as warnings.

## Data attribution

The bundled vocabulary is built from Wiktionary data via [Kaikki](https://kaikki.org/) and, when needed, example sentences from [Tatoeba](https://tatoeba.org/). See `data/ATTRIBUTION.md` for the licenses and attribution details.

## Releases

Prebuilt Linux (x86_64) archives are attached to [GitHub Releases](https://github.com/benodeveloper/foklumi/releases) (tagged `v*`). The first beta tag is `v0.1.0-beta`.

## Testing / CI

Non-GUI unit tests run in GitHub Actions (`.github/workflows/test.yml`) on Python 3.11/3.12:

```bash
python -m unittest tests.test_timer tests.test_vocab tests.test_fetch_random tests.test_pipeline -v
```

Settings tests require `PySide6` (skipped automatically when it is not installed). Pushing a `v*` tag runs tests, builds the Linux archive, and publishes it to the GitHub Release (`.github/workflows/release.yml`).

## Build a standalone app

The build uses PyInstaller and produces a folder you can run without Python installed.

```bash
./build.sh
```

Output goes to `dist/foklumi/` plus a `.tar.gz` archive next to it. Run it with:

```bash
./dist/foklumi/foklumi
```

To install it for your user on Linux:

```bash
mkdir -p ~/.local/opt ~/.local/bin ~/.local/share/applications
cp -r dist/foklumi ~/.local/opt/foklumi
ln -sf ~/.local/opt/foklumi/foklumi ~/.local/bin/foklumi
cp foklumi.desktop ~/.local/share/applications/
```

`~/.local/bin` must be in your `PATH`. In fish: `fish_add_path ~/.local/bin`.

The build script is for Linux and macOS. On Windows, run PyInstaller directly and use `;` instead of `:` in the `--add-data` paths.

## Project layout

```
foklumi/
├── main.py                 # wires timer, vocabulary, speech and UI together
├── core/
│   ├── timer.py            # phase state machine (focus / break)
│   ├── vocab.py            # vocabulary loading and shuffling
│   └── settings.py         # settings load / save
├── ui/
│   ├── main_window.py      # floating round timer
│   ├── ring.py             # the clock-style progress ring
│   ├── break_overlay.py    # fullscreen break screen and input lock
│   ├── settings_dialog.py  # settings window
│   ├── speech.py           # Piper / espeak / say / SAPI wrapper
│   └── util.py
├── data/
│   ├── curated_words.json  # hand-written translations, explanations, examples
│   ├── vocab.json          # built-in A1 vocabulary (generated)
│   └── ATTRIBUTION.md      # data sources and licenses
├── tools/
│   ├── download_data.py    # fetch Kaikki and Tatoeba
│   └── build_pipeline.py   # generate and validate vocab.json
├── tests/
├── requirements.txt
├── build.sh
└── foklumi.desktop
```

## Known limitations (beta)

- No pre-break notification yet.
- Only 19 built-in words.
- The input lock only works on X11.
- Piper loads its model on every phrase, so speech starts about a second after you press Listen.
- **Tested only on Arch Linux** (Arch rolling, X11/XFCE) — the maintainer’s current system. Windows/macOS/Wayland and other distros are untested.

## Roadmap

- System tray icon
- Notification 30 seconds before a break
- Larger A1 word list, then A2 and B1
- Keep a Piper process warm for instant speech
- Packaging for Arch (PKGBUILD), Windows and macOS

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). Bundled vocabulary data sources are documented in [data/ATTRIBUTION.md](data/ATTRIBUTION.md).
