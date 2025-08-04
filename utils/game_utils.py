from utils.network_utils import send_message
import config
import time

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

def send_result_message(peer_manager, game_id, result, opponent_id, winner_id=None, winning_symbol=None, winning_line=None):
    
    import time
    now = int(time.time())
    
    msg = {
        "TYPE": "TICTACTOE_RESULT",
        "GAMEID": game_id,
        "RESULT": result,  # e.g. "WIN" or "DRAW"
        "TIMESTAMP": now
    }

    # Include winner details only if it's a win
    if result == "WIN" and winner_id:
        msg["FROM"] = winner_id  # sender is the winner
        msg["TO"] = opponent_id
        msg["WINNER"] = winner_id
        msg["SYMBOL"] = winning_symbol  # "X" or "O"
        msg["WINNING_LINE"] = ",".join(str(i) for i in winning_line) if winning_line else ""
    else:
        # For draw: no winner, but still notify opponent
        msg["FROM"] = winner_id if winner_id else "system"
        msg["TO"] = opponent_id

    # Extract IP and send
    opponent_ip = opponent_id.split('@')[1]
    if opponent_ip:
        send_message(msg, (opponent_ip, config.PORT))
        peer_manager.logger.log_send("TICTACTOE_RESULT", opponent_id, )