def strip_whitespace(v: str | None) -> str | None:
    if v is None:
        return v
    stripped = str(v).strip()
    return stripped if stripped else None
