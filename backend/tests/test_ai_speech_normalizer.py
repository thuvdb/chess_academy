"""
Unit tests for AI Tutor Speech Normalizer.
Tests markdown stripping and chess notation (SAN) pronunciation mapping.
"""
from app.services.ai_tutor.speech_normalizer import (
    clean_markdown_for_speech,
    convert_chess_notation_to_speech,
    prepare_text_for_speech,
)


def test_clean_markdown_strips_board_tag():
    """Verify <board>...</board> tags and their JSON payload are stripped."""
    text = 'Giải thích khai cuộc:<board>{"moves":["e4","e5"]}</board>Chúc con học tốt!'
    cleaned = clean_markdown_for_speech(text)
    assert "<board>" not in cleaned
    assert "</board>" not in cleaned
    assert '{"moves"' not in cleaned
    assert "Giải thích khai cuộc:" in cleaned
    assert "Chúc con học tốt!" in cleaned


def test_clean_markdown_strips_multiline_board_tag():
    """Verify multiline <board> tags with newlines before </board> are stripped."""
    text = (
        "Quan sát thế trận:\n"
        '<board>{"moves":["e4","e5","Nf3","Nc6","Bc4"]}\n</board>\n'
        "Con thấy thế nào?"
    )
    cleaned = clean_markdown_for_speech(text)
    assert "<board" not in cleaned.lower()
    assert "</board" not in cleaned.lower()
    assert '{"moves"' not in cleaned
    assert "Quan sát thế trận:" in cleaned
    assert "Con thấy thế nào?" in cleaned

    # Also verify prepare_text_for_speech
    spoken = prepare_text_for_speech(text)
    assert "<board" not in spoken.lower()
    assert "Quan sát thế trận:" in spoken
    assert "Con thấy thế nào?" in spoken


def test_clean_markdown_formatting():
    """Verify headers, code blocks, bold/italics, and links are stripped cleanly."""
    text = (
        "# Khai Cuộc Cờ Vua\n"
        "Chào con! Hãy đọc kỹ **nguyên tắc vàng** và *nước đi* sau:\n"
        "```python\nprint('hello')\n```\n"
        "Xem thêm tại [Học viện CAMS](https://cams.academy).\n"
        "- Nguyên tắc 1: Kiểm soát trung tâm\n"
        "- Nguyên tắc 2: Phát triển quân nhẹ\n"
        "| Quân | Điểm |\n| Mã | 3 |"
    )
    cleaned = clean_markdown_for_speech(text)
    assert "#" not in cleaned
    assert "**" not in cleaned
    assert "*" not in cleaned
    assert "print('hello')" not in cleaned
    assert "https://cams.academy" not in cleaned
    assert "Học viện CAMS" in cleaned
    assert "nguyên tắc vàng" in cleaned
    assert "Kiểm soát trung tâm" in cleaned
    assert "|" not in cleaned


def test_convert_castling_pronunciation():
    """Verify castling symbols are converted into spoken words."""
    assert "nhập thành gần" in convert_chess_notation_to_speech("Trắng đi O-O để bảo vệ vua.")
    assert "nhập thành xa" in convert_chess_notation_to_speech("Đen chuẩn bị 0-0-0.")


def test_convert_piece_moves_pronunciation():
    """Verify pieces and moves with checks and checkmates are converted properly."""
    # Nf3 -> Mã f3
    assert "Mã f3" in convert_chess_notation_to_speech("Trắng chơi Nf3.")
    # Bc4 -> Tượng c4
    assert "Tượng c4" in convert_chess_notation_to_speech("Phát triển Bc4.")
    # Bxf7+ -> Tượng ăn f7 chiếu
    assert "Tượng ăn f7 chiếu" in convert_chess_notation_to_speech("Đòn chiến thuật Bxf7+ rất nguy hiểm.")
    # Qh5# -> Hậu h5 chiếu hết
    assert "Hậu h5 chiếu hết" in convert_chess_notation_to_speech("Trắng kết thúc ván bằng Qh5#.")
    # Disambiguation: Nbd7 -> Mã b d7
    assert "Mã b d7" in convert_chess_notation_to_speech("Đen nhảy Nbd7.")
    # Ke2 -> Vua e2
    assert "Vua e2" in convert_chess_notation_to_speech("Nước đi Ke2 bất thường.")


def test_convert_pawn_moves_pronunciation():
    """Verify pawn captures and promotions are spoken naturally."""
    # exd5 -> e ăn d5
    assert "e ăn d5" in convert_chess_notation_to_speech("Tốt trắng exd5.")
    # cxd4 -> c ăn d4
    assert "c ăn d4" in convert_chess_notation_to_speech("Tốt đen cxd4.")
    # e8=Q# -> e8 phong cấp Hậu chiếu hết
    assert "e8 phong cấp Hậu chiếu hết" in convert_chess_notation_to_speech("Tốt tiến lên e8=Q#.")
    # g8=N -> g8 phong cấp Mã
    assert "g8 phong cấp Mã" in convert_chess_notation_to_speech("Phong cấp bất ngờ g8=N.")


def test_prepare_text_for_speech_pipeline():
    """Verify end-to-end speech preparation pipeline."""
    sample = (
        "### Khai cuộc Ý\n"
        "Chào con! Các nước đi gồm: 1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5. "
        "Trắng có thể chơi O-O hoặc Bxf7+ nếu đen sơ hở!\n"
        '<board>{"moves":["e4","e5"]}</board>'
    )
    result = prepare_text_for_speech(sample)
    assert "<board>" not in result
    assert "###" not in result
    assert "nước 1: e4 e5" in result
    assert "nước 2: Mã f3 Mã c6" in result
    assert "nước 3: Tượng c4 Tượng c5" in result
    assert "nhập thành gần" in result
    assert "Tượng ăn f7 chiếu" in result


def test_prepare_text_for_speech_truncation():
    """Verify text exceeding max_chars is gracefully truncated at sentence boundary."""
    long_text = "Đây là một câu cờ vua rất hay. " * 100
    res = prepare_text_for_speech(long_text, max_chars=100)
    assert len(res) <= 100
    assert res.endswith(".")
