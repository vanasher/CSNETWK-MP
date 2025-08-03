from utils.network_utils import send_message
import config

# func for displaying tic tac toe board
def print_board(board):
    print("\n {} | {} | {} \n-----------\n {} | {} | {} \n-----------\n {} | {} | {} ".format(*board))
    
def check_game_result(board):
    # Define winning combinations
    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]

    for a, b, c in wins:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return "WIN"

    if " " not in board:
        return "DRAW"

    return None  # Game continues

def send_result_message(game_id, result, opponent_id, winner_id=None):
    msg = {
        "TYPE": "TICTACTOE_RESULT",
        "GAMEID": game_id,
        "RESULT": result
    }

    if result == "WIN" and winner_id:
        msg["WINNER"] = winner_id

    opponent_ip = opponent_id.split('@')[1]
    if opponent_ip:
        send_message(msg, (opponent_ip, config.PORT))