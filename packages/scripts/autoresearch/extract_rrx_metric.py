from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    payload = json.loads(Path(".ralph/outputs/research_clean.json").read_text())
    print(payload["dev"]["exact_3of3_rate"])


if __name__ == "__main__":
    main()
