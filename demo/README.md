# Demo

`run_demo.py` runs the full check loop and a fix dry-run with everything
stubbed: a fake simctl, a fake Ollama responder, and a fake app bundle.
It needs no Xcode, no simulator, no Ollama, and no network.

Run it from the repo root with the venv active:

python demo/run_demo.py

Reports land in demo/output/ as report.json and report.html.
