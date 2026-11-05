# Contributing to Foklumi

Thanks for your interest in improving Foklumi.

## Reporting issues

- Search existing issues first: https://github.com/benodeveloper/foklumi/issues
- Include your OS/desktop/session (e.g. Arch Linux, XFCE, X11/Wayland), Python and PySide6 versions, and steps to reproduce.
- For UI/input-lock problems, note whether `--no-grab` changes the behavior.

## Development setup

```bash
git clone https://github.com/benodeveloper/foklumi.git
cd foklumi
python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt -r tools/requirements.txt
python main.py
```

## Tests

Run the non-GUI unit tests before opening a PR:

```bash
python -m unittest tests.test_timer tests.test_vocab tests.test_fetch_random tests.test_pipeline -v
```

Settings tests require PySide6. On a machine with PySide6 you can run the full suite:

```bash
python -m unittest discover -s tests -t . -v
```

CI runs the non-GUI tests on Python 3.11/3.12.

## Pull requests

- Keep changes focused and describe what/why.
- Add or update tests for behavior changes when practical.
- Do not commit secrets, personal paths, or large generated data files (Kaikki/Tatoeba downloads live under `tools/` and are gitignored as appropriate).
- Vocabulary data changes: see `data/ATTRIBUTION.md` and the rebuild steps in `README.md`.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see `LICENSE`).
