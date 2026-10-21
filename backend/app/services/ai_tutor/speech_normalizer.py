"""
CAMS AI Tutor — Speech Normalizer.
Cleans raw text (removes board markup, markdown formatting, tables, code)
and maps chess algebraic notation (SAN) into natural Vietnamese speech.
"""
import re

BOARD_TAG_REGEX = re.compile(r"<board>.*?</board>", re.DOTALL | re.IGNORECASE)

# Mapping piece abbreviations to Vietnamese words
CHESS_PIECE_NAMES = {
    "K": "Vua",
    "Q": "Hậu",
    "R": "Xe",
    "B": "Tượng",
    "N": "Mã",
}

CHESS_PROMOTION_NAMES = {
    "Q": "Hậu",
    "R": "Xe",
    "B": "Tượng",
    "N": "Mã",
}


def clean_markdown_for_speech(text: str) -> str:
    """Strip markup, board tags, code blocks, tables, and links for clean speech audio."""
    if not text:
        return ""

    # 1. Remove <board>...</board>
    cleaned = BOARD_TAG_REGEX.sub("", text)

    # 2. Remove code blocks ```...``` and inline code `...`
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # 3. Remove images ![alt](url) and links [text](url) -> text
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", " ", cleaned)
    cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned)

    # 4. Remove HTML tags if any
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # 5. Remove markdown headers (#, ##, ...)
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)

    # 6. Remove bold, italic, strikethrough: **text**, *text*, __text__, _text_, ~~text~~
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)

    # 7. Remove markdown table pipes and dashes
    cleaned = re.sub(r"\|", " ", cleaned)
    cleaned = re.sub(r"^[-*_]{3,}\s*$", " ", cleaned, flags=re.MULTILINE)

    # 8. Clean up list markers (*, -, +, 1.) at beginning of lines
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*>\s*", "", cleaned, flags=re.MULTILINE)

    return cleaned


def _replace_piece_move(match: re.Match) -> str:
    """Format piece move like 'Nf3', 'Bxf7+', 'Qh5#', 'Nbd7'."""
    piece_char = match.group(1)
    disambiguation = match.group(2) or ""
    is_capture = match.group(3)
    target_square = match.group(4)
    promotion = match.group(5)
    check_mate = match.group(6)

    parts = [CHESS_PIECE_NAMES.get(piece_char, piece_char)]
    if disambiguation:
        parts.append(disambiguation)
    if is_capture:
        parts.append("ăn")
    parts.append(target_square)

    if promotion:
        prom_char = promotion.replace("=", "").upper()
        parts.append(f"phong cấp {CHESS_PROMOTION_NAMES.get(prom_char, prom_char)}")

    if check_mate == "#":
        parts.append("chiếu hết")
    elif check_mate == "+":
        parts.append("chiếu")

    return " ".join(parts)


def _replace_pawn_capture(match: re.Match) -> str:
    """Format pawn capture like 'exd5', 'cxd4', 'exd6 e.p.'."""
    source_file = match.group(1)
    target_square = match.group(3)
    promotion = match.group(4)
    check_mate = match.group(5)

    parts = [source_file, "ăn", target_square]
    if promotion:
        prom_char = promotion.replace("=", "").upper()
        parts.append(f"phong cấp {CHESS_PROMOTION_NAMES.get(prom_char, prom_char)}")

    if check_mate == "#":
        parts.append("chiếu hết")
    elif check_mate == "+":
        parts.append("chiếu")

    return " ".join(parts)


def _replace_pawn_check(match: re.Match) -> str:
    """Format pawn check/mate like 'e4+', 'd8#'."""
    square = match.group(1)
    check_mate = match.group(2)
    label = "chiếu hết" if check_mate == "#" else "chiếu"
    return f"{square} {label}"


def convert_chess_notation_to_speech(text: str) -> str:
    """Convert chess SAN notations into spoken Vietnamese."""
    if not text:
        return ""

    # 1. Castling notation (O-O-O, O-O, 0-0-0, 0-0)
    result = re.sub(r"\b[O0]-[O0]-[O0]\b", "nhập thành xa", text)
    result = re.sub(r"\b[O0]-[O0]\b", "nhập thành gần", result)

    # 2. Numbered moves (e.g., '1. e4 e5' -> 'nước 1: e4 e5')
    result = re.sub(r"\b(\d+)\.\s*", r"nước \1: ", result)

    # 3. Piece moves: Nf3, Bxf7+, Qh5#, Nbd7, R1e2, e8=Q#
    piece_move_regex = re.compile(r"\b([KQRBN])([a-h1-8])?(x)?([a-h][1-8])(=[QRBN])?([+#])?(?!\w)")
    result = piece_move_regex.sub(_replace_piece_move, result)

    # 4. Pawn capture moves: exd5, cxd4, exd6#
    pawn_capture_regex = re.compile(r"\b([a-h])(x)([a-h][1-8])(=[QRBN])?([+#])?(?!\w)")
    result = pawn_capture_regex.sub(_replace_pawn_capture, result)

    # 5. Pawn check/mate: e4+, d5#
    pawn_check_regex = re.compile(r"\b([a-h][1-8])([+#])(?!\w)")
    result = pawn_check_regex.sub(_replace_pawn_check, result)

    return result


def prepare_text_for_speech(text: str, max_chars: int = 2000) -> str:
    """
    Complete text cleaning pipeline before speech synthesis:
    1. Clean markdown & board tags
    2. Convert chess notations to Vietnamese words
    3. Normalize whitespace and sentence flow
    4. Truncate to maximum character limit for speech synthesis
    """
    cleaned = clean_markdown_for_speech(text)
    spoken = convert_chess_notation_to_speech(cleaned)

    # Normalize whitespace & punctuation for smoother speech flow
    spoken = re.sub(r"\s+", " ", spoken)
    spoken = re.sub(r"\s+([,.:?!])", r"\1", spoken)
    spoken = spoken.strip()

    if len(spoken) > max_chars:
        # Truncate at last complete sentence within limit
        truncated = spoken[:max_chars]
        last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_punct > max_chars // 2:
            spoken = truncated[: last_punct + 1]
        else:
            spoken = truncated.rstrip() + "..."

    return spoken
