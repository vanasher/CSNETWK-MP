from utils.network_utils import send_message
import config
import time
import random

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
            return "WIN", [a, b, c]

    if " " not in board:
        return "DRAW", None
    return None, None  # Game continues

def get_winning_line(board, symbol):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    for line in win_conditions:
        if all(board[i] == symbol for i in line):
            return line
    return None

def send_result_message(peer_manager, token, game_id, result, opponent_id, winner_id=None, winning_symbol=None, winning_line=None):
    
    import time
    now = int(time.time())
    message_id = f"{random.getrandbits(64):016x}"

    from_id = winner_id if winner_id else peer_manager.get_own_profile().get("USER_ID")

    msg = {
        "TYPE": "TICTACTOE_RESULT",
        "FROM": from_id,
        "TO": opponent_id,
        "GAMEID": game_id,
        "MESSAGE_ID": message_id,
        "RESULT": result,
        "SYMBOL": winning_symbol if result == "WIN" else None,
        "WINNING_LINE": ",".join(str(i) for i in winning_line) if result == "WIN" and winning_line else None,
        "TIMESTAMP": now
    }

    # Remove keys with value None to keep message clean
    msg = {k: v for k, v in msg.items() if v is not None}

    # Extract IP and send
    opponent_ip = opponent_id.split('@')[1]
    if opponent_ip:
        send_message(msg, (opponent_ip, config.PORT))
        peer_manager.logger.log_send("TICTACTOE_RESULT", opponent_id, msg)