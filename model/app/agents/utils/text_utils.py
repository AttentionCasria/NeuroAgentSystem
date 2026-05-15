def truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    half = max_chars // 2

    return (
        text[:half]
        + f"\n\n... [已截断 {len(text) - max_chars} 字符] ...\n\n"
        + text[-half:]
    )