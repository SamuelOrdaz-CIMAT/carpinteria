def money(value) -> str:
    if value in (None, ""):
        return "-"
    return f"${float(value):,.2f}"


def fit_text(text, max_chars: int) -> str:
    clean = " ".join(str(text if text is not None else "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "..."
