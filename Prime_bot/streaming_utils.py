def iter_text_stream(text: str, chunk_chars: int = 24):
    if not text:
        return

    words = text.split()
    if not words:
        return

    buf = ""
    for word in words:
        candidate = word if not buf else f"{buf} {word}"
        if len(candidate) <= chunk_chars:
            buf = candidate
            continue
        if buf:
            yield buf + " "
        buf = word

    if buf:
        yield buf
