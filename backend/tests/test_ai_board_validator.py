"""
Unit tests for AI Tutor Board Move Validator (python-chess).
Tests SAN move validation: legal moves, illegal moves, checkmate, castling, promotion, en passant.
"""
import pytest
from app.services.ai_tutor.board_validator import (
    extract_and_validate_board,
    validate_board_moves,
)


def test_valid_moves_italian_game():
    """Verify standard valid moves sequence generates correct FEN positions."""
    payload = {
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"],
        "caption": "Khai cuộc Ý",
    }
    result = validate_board_moves(payload)
    assert result is not None
    assert result["total_moves"] == 6
    assert result["caption"] == "Khai cuộc Ý"
    assert len(result["positions"]) == 7  # initial FEN + 6 moves
    assert result["is_checkmate"] is False


def test_invalid_illegal_move():
    """Verify illegal move returns None safely without raising exceptions."""
    payload = {
        "moves": ["e4", "e5", "Ke2", "Nf6", "Ke5"],  # Ke5 is completely illegal
        "caption": "Nước đi sai luật",
    }
    result = validate_board_moves(payload)
    assert result is None


def test_invalid_san_syntax():
    """Verify malformed move string returns None."""
    payload = {
        "moves": ["e4", "zz99", "Nf3"],
        "caption": "Lỗi cú pháp",
    }
    result = validate_board_moves(payload)
    assert result is None


def test_checkmate_scholars_mate():
    """Verify Scholar's Mate is validated and flagged as checkmate."""
    payload = {
        "moves": ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"],
        "caption": "Đòn Scholar's Mate",
    }
    result = validate_board_moves(payload)
    assert result is not None
    assert result["total_moves"] == 7
    assert result["is_checkmate"] is True


def test_castling_kingside_and_queenside():
    """Verify Kingside (O-O) and Queenside (O-O-O) castling."""
    # Play moves leading to white O-O and black O-O-O
    payload = {
        "moves": [
            "e4", "d5",
            "Nf3", "Nc6",
            "Bc4", "Bf5",
            "O-O", "Qd7",  # White castles kingside
            "Nc3", "O-O-O",  # Black castles queenside
        ],
        "caption": "Minh họa nhập thành gần và xa",
    }
    result = validate_board_moves(payload)
    assert result is not None
    assert result["total_moves"] == 10
    assert "O-O" in result["moves"]
    assert "O-O-O" in result["moves"]


def test_pawn_promotion():
    """Verify pawn promotion (e.g. g8=Q) from custom position."""
    # Custom FEN where white pawn on g7 is about to promote:
    # 8/6P1/8/8/8/8/k7/4K3 w - - 0 1
    custom_fen = "8/6P1/8/8/8/8/k7/4K3 w - - 0 1"
    payload = {
        "initial_fen": custom_fen,
        "moves": ["g8=Q+"],
        "caption": "Phong cấp tốt thành Hậu",
    }
    result = validate_board_moves(payload)
    assert result is not None
    assert result["total_moves"] == 1
    assert result["moves"] == ["g8=Q+"]
    assert "Q" in result["positions"][-1]


def test_en_passant():
    """Verify En Passant capture (exd6)."""
    # 1. e4 Nf6 2. e5 d5 3. exd6 (en passant)
    payload = {
        "moves": ["e4", "Nf6", "e5", "d5", "exd6"],
        "caption": "Bắt tốt qua đường (En Passant)",
    }
    result = validate_board_moves(payload)
    assert result is not None
    assert result["total_moves"] == 5
    assert result["moves"][-1] == "exd6"


def test_extract_and_validate_board_valid():
    """Verify extract_and_validate_board parses <board> tag and cleans text."""
    raw_text = (
        "Chào con! Đây là 4 nước đầu của khai cuộc Ý:\n"
        '<board>{"moves":["e4","e5","Nf3","Nc6"],"caption":"Khai cuộc Ý 4 nước đầu"}</board>\n'
        "Hãy luyện tập thêm nhé!"
    )
    clean, board = extract_and_validate_board(raw_text)
    assert "<board>" not in clean
    assert "</board>" not in clean
    assert "Chào con!" in clean
    assert "Hãy luyện tập thêm nhé!" in clean
    assert board is not None
    assert board["total_moves"] == 4


def test_extract_and_validate_board_no_tag():
    """Verify raw text without board tag returns unchanged text and None board."""
    raw = "Magnus Carlsen là Đại kiện tướng cờ vua số 1 thế giới người Na Uy."
    clean, board = extract_and_validate_board(raw)
    assert clean == raw
    assert board is None


def test_extract_and_validate_board_corrupted_json():
    """Verify corrupted JSON inside <board> is safely dropped without crashing."""
    raw = "Thế cờ: <board>{invalid json: true}</board> Chúc con vui vẻ!"
    clean, board = extract_and_validate_board(raw)
    assert "<board>" not in clean
    assert board is None
