# We assume that X is the first *starting* player and O is the second player

E = -1  # Empty
O = 0
X = 1


def init_board():
    board = [
        E, E, E,
        E, E, E,
        E, E, E
    ]
    return board


def set_symbol(board, index, symbol):
    assert is_board_valid(board)
    if index < 0 or index > len(board):
        raise IndexError(f'Index {index} out of range')
    if board[index] != E:
        raise ValueError(f'Index {index} is already occupied by symbol {board[index]}')
    if which_turn(board) != symbol:
        raise ValueError(f'Invalid symbol {symbol} for turn {which_turn(board)}')
    board[index] = symbol


def get_symbol(board, index):
    assert is_board_valid(board)
    if index < 0 or index > len(board):
        raise IndexError(f'Index {index} out of range')
    return board[index]


# Returns O, X or E
def get_winner(board):
    assert is_board_valid(board)
    # Check rows
    for i in range(3):
        if board[3 * i + 0] == board[3 * i + 1] == board[3 * i + 2] and board[3 * i + 0] != E:
            return board[3 * i + 0]
    # Check columns
    for i in range(3):
        if board[3 * 0 + i] == board[3 * 1 + i] == board[3 * 2 + i] and board[3 * 0 + i] != E:
            return board[3 * 0 + i]
    # Check diagonals
    if board[0] == board[4] == board[8] and board[0] != E:
        return board[0]
    if board[2] == board[4] == board[6] and board[2] != E:
        return board[2]
    # No winner
    return None


def get_symbol_occurrences_num(board, symbol):
    return len([x for x in board if x == symbol])


def is_board_valid(board):
    o_occurrences_num = get_symbol_occurrences_num(board, O)
    x_occurrences_num = get_symbol_occurrences_num(board, X)
    occurrences_diff = x_occurrences_num - o_occurrences_num
    return occurrences_diff == 0 or occurrences_diff == 1


def which_turn(board):
    o_occurrences_num = get_symbol_occurrences_num(board, O)
    x_occurrences_num = get_symbol_occurrences_num(board, X)
    occurrences_diff = x_occurrences_num - o_occurrences_num
    if occurrences_diff == 0:
        return X
    elif occurrences_diff == 1:
        return O
    else:
        raise ValueError(f'Invalid board: {board}')


def get_symbol_char(symbol):
    if symbol == O:
        return 'O'
    elif symbol == X:
        return 'X'
    elif symbol == E:
        return ' '
    else:
        raise ValueError(f'Invalid element: {symbol}')


# Note that empty symbols are not allowed here
def parse_symbol(char):
    if char == 'O':
        return O
    elif char == 'X':
        return X
    else:
        raise ValueError(f'Symbol parsing failed for symbol: {char}')


# Note that this function also prints an empty line before and after the board
def print_board_indexes():
    print("""
    1 | 2 | 3
    ---------
    4 | 5 | 6
    ---------
    7 | 8 | 9
    """)


# Note that this function also prints an empty line before and after the board
def print_board(board):
    print(f"""
    {get_symbol_char(board[0])} | {get_symbol_char(board[1])} | {get_symbol_char(board[2])}
    ---------
    {get_symbol_char(board[3])} | {get_symbol_char(board[4])} | {get_symbol_char(board[5])}
    ---------
    {get_symbol_char(board[6])} | {get_symbol_char(board[7])} | {get_symbol_char(board[8])}
    """)


if __name__ == '__main__':
    print_board_indexes()

    board = init_board()
    assert is_board_valid(board)
    assert which_turn(board) == X
    print_board(board)
    set_symbol(board, 0, X)
    assert is_board_valid(board)
    assert which_turn(board) == O
    set_symbol(board, 1, O)
    assert is_board_valid(board)
    assert which_turn(board) == X
    set_symbol(board, 3, X)
    assert is_board_valid(board)
    assert which_turn(board) == O
    set_symbol(board, 2, O)
    assert is_board_valid(board)
    assert which_turn(board) == X
    set_symbol(board, 6, X)
    assert is_board_valid(board)
    assert which_turn(board) == O
    print_board(board)

    winner = get_winner(board)
    print(f'Winner: {winner}')
