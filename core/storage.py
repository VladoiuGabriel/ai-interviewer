import json
import re
from pathlib import Path

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent / "transcripts"


def _slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "interview"


def path_for(data: dict) -> Path:
    stamp = data["started_at"][:16].replace(":", "")
    return TRANSCRIPTS_DIR / f"{stamp}_{_slug(data['topic'])}_{data['id']}.json"


def save(data: dict) -> Path:
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    path = path_for(data)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_all() -> list[Path]:
   #all saved, newest first
    if not TRANSCRIPTS_DIR.exists():
        return []
    return sorted(TRANSCRIPTS_DIR.glob("*.json"), reverse=True)