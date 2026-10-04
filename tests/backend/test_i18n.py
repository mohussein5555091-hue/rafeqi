"""The English and Arabic screen texts (frontend/src/i18n/*.json) have the same keys, and every {placeholder} a
text uses in English is one the Arabic text may use (no Arabic text asks for a value that isn't passed)."""

import json
import re
from pathlib import Path

I18N = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n"


def flat(d: dict, prefix: str = "") -> dict[str, str]:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        out.update(flat(v, key + ".") if isinstance(v, dict) else {key: v})
    return out


def test_english_and_arabic_have_the_same_keys():
    en, ar = (flat(json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))) for lang in ("en", "ar"))
    assert sorted(set(en) - set(ar)) == [], "missing in ar.json"
    assert sorted(set(ar) - set(en)) == [], "missing in en.json"
    for k in en:
        if isinstance(en[k], str) and isinstance(ar[k], str):
            assert set(re.findall(r"\{(\w+)\}", ar[k])) <= set(re.findall(r"\{(\w+)\}", en[k])), k
