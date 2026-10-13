from app.advisor import DemoAdvisor
from app.game import Game, legal_moves, move_board


def test_merge_once_and_score():
    board = [
        [2, 2, 2, 2],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    moved, gained = move_board(board, "left")
    assert moved[0] == [4, 4, 0, 0]
    assert gained == 8
    assert board[0] == [2, 2, 2, 2]


def test_right_and_vertical_moves():
    board = [[2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    right, _ = move_board(board, "right")
    up, gained = move_board(board, "up")
    assert right[0] == [0, 0, 0, 2]
    assert up[0][0] == 4
    assert gained == 4


def test_legal_moves_detect_full_board_loss():
    board = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert legal_moves(board) == []


def test_game_rejects_no_op_without_mutating_counters():
    game = Game(board=[[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    assert game.apply("left", "test") is False
    assert game.moves == 0
    assert game.score == 0


def test_demo_advisor_uses_search_to_choose_a_merge():
    board = [
        [2, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    suggestion = DemoAdvisor(depth=2).suggest(board, score=0)
    assert suggestion.direction == "left"
    assert suggestion.direction in legal_moves(board)
