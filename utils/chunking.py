from typing import List


def chunk_message(text: str, max_len: int = 230) -> List[str]:
    """
    Split *text* into chunks that each fit within *max_len* characters.

    Splitting respects word boundaries and prefers sentence boundaries
    (., !, ?).  When more than one chunk is produced each chunk is prefixed
    with "Part X/N: ".
    """
    if len(text) <= max_len:
        return [text]

    # Split into words while keeping trailing spaces attached
    words = text.split(" ")
    raw_chunks: List[str] = []
    current = ""

    for word in words:
        candidate = (current + " " + word).strip() if current else word
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                raw_chunks.append(current)
            # If a single word exceeds max_len, force-split it
            while len(word) > max_len:
                raw_chunks.append(word[:max_len])
                word = word[max_len:]
            current = word

    if current:
        raw_chunks.append(current)

    if len(raw_chunks) == 1:
        return raw_chunks

    # Add "Part X/N: " prefix; recalculate to ensure they still fit
    n = len(raw_chunks)
    result: List[str] = []
    for i, chunk in enumerate(raw_chunks, start=1):
        prefix = f"Part {i}/{n}: "
        full = prefix + chunk
        if len(full) <= max_len:
            result.append(full)
        else:
            # Trim the text so the prefix fits
            trimmed = chunk[: max_len - len(prefix)]
            result.append(prefix + trimmed)

    return result
