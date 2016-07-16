#!/usr/bin/env python

import collections
import datetime
import hashlib
import json
import random
import sys
import time

DEBUG = False

# describes a piece that can be moved
MovablePiece = collections.namedtuple(
    "MovablePiece",
    [
        "row_ix",  # row index
        "col_ix",  # column index
        "piece",  # the piece value
        "depth",  # depth of stack piece is on (1 means only this piece left)
    ],
)

MovablePiece.TOP = "T"
MovablePiece.LEFT = "L"
MovablePiece.RIGHT = "R"

PIECES = [
    str(_) for _ in range(10)
] + [
    chr(x + ord('A')) for x in range(26)
]
if DEBUG:
    print PIECES
    print len(PIECES)

class Board(object):
    DEPTHS = [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [      1, 2, 2, 2, 2, 2, 2, 1      ],
        [   1, 1, 2, 3, 3, 3, 3, 2, 1, 1   ],
        [1, 1, 1, 2, 3, 4, 4, 3, 2, 1, 1, 1],
        [1, 1, 1, 2, 3, 4, 4, 3, 2, 1, 1, 1],
        [   1, 1, 2, 3, 3, 3, 3, 2, 1, 1   ],
        [      1, 2, 2, 2, 2, 2, 2, 1      ],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]

    def __init__(self):
        self.rows = [
            [[] for cell in row]
            for row in self.DEPTHS
        ]
        self.top = []
        self.left_blocks = []
        self.right_blocks = []

    def clone(self):
        """clones the board"""
        clone_board = Board()
        clone_board.top = self.top[:]
        clone_board.left_blocks = self.left_blocks[:]
        clone_board.right_blocks = self.right_blocks[:]
        clone_board.rows = [
            [cell[:] for cell in row]
            for row in self.rows
        ]
        return clone_board

    def get_state(self):
        """gets a canonical state string"""
        md5 = hashlib.md5()
        md5.update(
            "|".join([
                str(len(stack))
                for row in self.rows
                for stack in row
            ]),
        )
        md5.update("|")
        md5.update("|".join([
            str(len(self.top)),
            str(len(self.left_blocks)),
            str(len(self.right_blocks)),
        ]))
        return md5.digest()

    def fill(self):
        """Fills the board randomly."""
        pieces = [piece for piece in PIECES for _ in range(4)]

        # shuffle pieces
        for i in range(len(pieces)):
            ix = i + int(random.random() * (len(pieces) - i))
            pieces[i], pieces[ix] = pieces[ix], pieces[i]

        # fill spaces up to depth
        for rix in range(len(self.rows)):
            for cix in range(len(self.rows[rix])):
                depth = self.DEPTHS[rix][cix]
                stack = self.rows[rix][cix]
                while depth:
                    stack.append(pieces.pop())
                    depth -= 1

        # fill remaining center and left and right spaces
        self.top.append(pieces.pop())
        self.left_blocks.append(pieces.pop())
        self.right_blocks.extend(pieces)

    @property
    def is_empty(self):
        """whether the board is empty"""
        if self.top:
            return False

        if self.left_blocks:
            return False

        if self.right_blocks:
            return False

        for row in self.rows:
            for stack in row:
                if stack:
                    return False

        return True

    def row_to_str(self, row):
        """Converts a row to a string."""
        return " ".join([
            "%s%s%s" % (
                stack[-1],
                "." * (len(stack) - 1),
                " " * (4 - len(stack)),
            ) if stack else "_   "
            for stack in row
        ])

    def is_movable(self, row_ix, col_ix, is_left_to_right=True):
        """Returns true if the piece at that position can be moved.

        :param int row_ix:
        :param int col_ix:
        :param bool is_left_to_right: whether we are looking to remove this
            from left going right.
        :return bool:
        """
        row = self.rows[row_ix]
        stack = row[col_ix]
        if not stack:
            return False

        depth = len(stack)
        if depth == 4:
            # center piece has to be gone first
            return not bool(self.top)
        elif depth == 1:
            if 3 <= row_ix <= 4:
                # ground level on the middle rows need side blocks cleared
                if is_left_to_right:
                    return not bool(self.left_blocks)
                else:
                    return not bool(self.right_blocks)

        return True

    def find_movable_pieces(self):
        """finds all movable pieces

        :return list(MovablePiece):
        """
        movable_pieces = set()

        for row_ix in range(len(self.rows)):
            row = self.rows[row_ix]

            # go left to right
            col_ix = 0
            last_depth = 0
            while col_ix < len(row):
                stack = row[col_ix]
                depth = len(stack)
                if (self.is_movable(row_ix, col_ix, is_left_to_right=True) and
                        depth > last_depth):
                    movable_pieces.add(
                        MovablePiece(
                            row_ix=row_ix,
                            col_ix=col_ix,
                            piece=stack[-1],
                            depth=depth,
                        ),
                    )
                    last_depth = depth
                elif depth < last_depth:
                    break

                col_ix += 1

            # go right to left
            col_ix = len(row) - 1
            last_depth = 0
            while col_ix >= 0:
                stack = row[col_ix]
                depth = len(stack)
                if (self.is_movable(row_ix, col_ix, is_left_to_right=False) and
                        depth > last_depth):
                    movable_pieces.add(
                        MovablePiece(
                            row_ix=row_ix,
                            col_ix=col_ix,
                            piece=stack[-1],
                            depth=depth,
                        ),
                    )
                    last_depth = depth
                elif depth < last_depth:
                    break

                col_ix -= 1

        if self.top:
            movable_pieces.add(
                MovablePiece(
                    row_ix=MovablePiece.TOP,
                    col_ix=None,
                    piece=self.top[-1],
                    depth=1,
                ),
            )

        if self.left_blocks:
            movable_pieces.add(
                MovablePiece(
                    row_ix=MovablePiece.LEFT,
                    col_ix=None,
                    piece=self.left_blocks[-1],
                    depth=1,
                ),
            )

        if self.right_blocks:
            movable_pieces.add(
                MovablePiece(
                    row_ix=MovablePiece.RIGHT,
                    col_ix=None,
                    piece=self.right_blocks[-1],
                    depth=1,
                ),
            )

        return list(
            sorted(
                movable_pieces,
                key=lambda x: (x.row_ix, x.col_ix),
            )
        )

    def find_moves(self, movable_pieces):
        """finds all valid moves

        :return list((MovablePiece, MovablePiece)):
        """
        # group movables by piece
        movables_by_piece = {}
        for movable_piece in movable_pieces:
            movables_by_piece.setdefault(movable_piece.piece, []).append(
                movable_piece,
            )

        # come up with all pairs of movables of same piece
        moves = set()
        for pieces in movables_by_piece.itervalues():
            for i in range(len(pieces) - 1):
                for j in range(i + 1, len(pieces)):
                    moves.add((pieces[i], pieces[j]))

        return list(
            sorted(
                moves,
                key=lambda x: (
                    x[0].row_ix,
                    x[0].col_ix,
                    x[1].row_ix,
                    x[1].col_ix,
                )
            )
        )

    def remove_piece(self, movable_piece):
        """removes the pieces at the coords"""
        if movable_piece.row_ix == MovablePiece.TOP:
            self.top.pop()
        elif movable_piece.row_ix == MovablePiece.LEFT:
            self.left_blocks.pop()
        elif movable_piece.row_ix == MovablePiece.RIGHT:
            self.right_blocks.pop()
        else:
            row = self.rows[movable_piece.row_ix]
            stack = row[movable_piece.col_ix]
            stack.pop()

    def replace_piece(self, movable_piece):
        """replaecs the pieces at the coords"""
        if movable_piece.row_ix == MovablePiece.TOP:
            self.top.append(movable_piece.piece)
        elif movable_piece.row_ix == MovablePiece.LEFT:
            self.left_blocks.append(movable_piece.piece)
        elif movable_piece.row_ix == MovablePiece.RIGHT:
            self.right_blocks.append(movable_piece.piece)
        else:
            row = self.rows[movable_piece.row_ix]
            stack = row[movable_piece.col_ix]
            stack.append(movable_piece.piece)

    def do_move(self, move):
        """does a move

        :param (MovablePiece, MovablePiece) move:
        """
        if DEBUG:
            print "\nRemoving:", move

        self.remove_piece(move[0])
        self.remove_piece(move[1])

    def undo_move(self, move):
        """undoes a move

        :param (MovablePiece, MovablePiece) move:
        """
        if DEBUG:
            print "\nReplacing:", move

        self.replace_piece(move[0])
        self.replace_piece(move[1])

    def __str__(self):
        indent = 2
        row_strs = [self.row_to_str(row) for row in self.rows]
        return "\n".join([
            "        0    1    2    3    4    5    6    7    8    9    a    b",
            " +--------------------------------------------------------------",
            "0|  " + " " * (indent + 2) + row_strs[0],
            "1|  " + " " * (indent + 12) + row_strs[1],
            "2|  " + " " * (indent + 7) + row_strs[2],
            "3|  " + " " * (indent + 2) + row_strs[3],
            (
                "M|  " + " ".join(self.left_blocks) + " " * 30 +
                " ".join(self.top) + " " * 31 +
                " ".join(self.right_blocks)
            ),
            "4|  " + " " * (indent + 2) + row_strs[4],
            "5|  " + " " * (indent + 7) + row_strs[5],
            "6|  " + " " * (indent + 12) + row_strs[6],
            "7|  " + " " * (indent + 2) + row_strs[7],
        ])


class BoardSearcher(object):
    def __init__(self, board):
        self.board = board

        # current list of 'moves's we've gone through
        self.moves = []
        self.trail = []

        # sets of tuples of 'Move's
        self.dead_ends = set()
        self.solutions = set()

        self.stats_calls = 0

        # set of states we have seen to not duplicate
        self.seen_states = set()

        self.num_moves = 0
        self.last_time = time.time()

    def print_stats(self):
        self.stats_calls += 1
        if self.stats_calls % 100 != 0:
            print self.board
            sys.stdout.flush()

        now = time.time()
        elapsed_time = float(now - self.last_time)
        if elapsed_time:
            moves_per_second = float(self.num_moves) / elapsed_time
            self.num_moves = 0
            self.last_time = now
            print "*** Moves per second: %d" % int(moves_per_second)

        progress = 0
        fraction = 1.0
        for num, den in self.trail:
            progress += num / den * fraction
            fraction /= den

        print "\nFound solutions: %d; dead ends: %d; progress: %.04f%%; trail: %s" % (
            len(self.solutions),
            len(self.dead_ends),
            100.0 * progress,
            " ".join([
                "%d/%d" % (int(trail[0]), int(trail[1])) for trail in self.trail
            ]),
        )


class BacktrackingSearcher(BoardSearcher):

    def backtracking_search(self):
        """conduct search over `board`"""
        if self.board.is_empty:
            solution = tuple(self.moves[:])
            self.solutions.add(solution)
            print "Found solution of length:", len(solution)
            self.print_stats()
            return

        state = self.board.get_state()
        if state in self.seen_states:
            return

        self.seen_states.add(state)

        movable_pieces = self.board.find_movable_pieces()
        moves = self.board.find_moves(movable_pieces)
        if not moves:
            # dead_end = tuple(self.moves[:])
            # self.dead_ends.add(dead_end)
            # print "Found dead end of length:", len(dead_end)
            self.print_stats()
        else:
            for ix, move in enumerate(moves):
                # self.trail.append("%d/%d" % (ix + 1, len(moves)))
                self.num_moves += 1
                self.trail.append((float(ix), float(len(moves))))
                self.moves.append(move)
                self.board.do_move(move)
                self.backtracking_search()
                self.board.undo_move(move)
                self.moves.pop()
                self.trail.pop()


class MonteCarloSearcher(BoardSearcher):

    def __init__(self, board):
        super(MonteCarloSearcher, self).__init__(board)
        self.max_depth = 0

    def monte_carlo_search(self):
        """takes random moves until done or stuck"""
        while True:
            if self.board.is_empty:
                return

            movable_pieces = self.board.find_movable_pieces()
            moves = self.board.find_moves(movable_pieces)
            if not moves:
                return

            move = moves[int(len(moves) * random.random())]
            self.max_depth += 1
            self.board.do_move(move)


board = Board()
print board

print '\nFilled:'
board.fill()
print board

if False:
    # simulate a single greedy run
    print "\nMovable pieces:"
    movable_pieces = board.find_movable_pieces()
    last_row = 0
    for movable_piece in sorted(movable_pieces, key=lambda x: (x.row_ix, x.col_ix)):
        if movable_piece.row_ix != last_row:
            print "---"
            last_row = movable_piece.row_ix

        print movable_piece

    print "\nMoves:"
    moves = board.find_moves(movable_pieces)
    for move in moves:
        print move

    # sys.exit(0)
    if not moves:
        print "\n" + "*" * 40 + " NO MORE MOVES! " + "*" * 40
        sys.exit(0)

    board.do_move(moves[0])
    print "\nExecuted move:"
    print board
elif False:
    # test replace
    print "\nMovable pieces:"
    movable_pieces = board.find_movable_pieces()
    last_row = 0
    for movable_piece in sorted(movable_pieces, key=lambda x: (x.row_ix, x.col_ix)):
        if movable_piece.row_ix != last_row:
            print "---"
            last_row = movable_piece.row_ix

        print movable_piece

    print "\nMoves:"
    moves = board.find_moves(movable_pieces)
    for move in moves:
        print move

    # sys.exit(0)
    if not moves:
        print "\n" + "*" * 40 + " NO MORE MOVES! " + "*" * 40
        sys.exit(0)

    board.do_move(moves[0])
    print "\nDid move:"
    print board

    board.undo_move(moves[0])
    print "\nUn-did move:"
    print board
elif False:
    # search whole board for stats
    searcher = BoardSearcher(board)
    searcher.backtracking_search()
else:
    move_histogram = {}
    num_boards = 1000
    num_moves_per_board = 10000
    num_solvable_boards = 0
    start_datetime = datetime.datetime.now()
    for i in range(num_boards):
        print "i:", i
        board = Board()
        board.fill()
        is_board_solvable = False
        for j in range(num_moves_per_board):
            if j % 100 == 0:
                print "  j:", j, (datetime.datetime.now() - start_datetime)

            searcher = MonteCarloSearcher(board.clone())
            searcher.monte_carlo_search()
            if searcher.max_depth not in move_histogram:
                move_histogram[searcher.max_depth] = 1
            else:
                move_histogram[searcher.max_depth] += 1

            if not is_board_solvable and searcher.max_depth == 72:
                is_board_solvable = True

        # print json.dumps(
        #     sorted(move_histogram.iteritems()),
        #     indent=2,
        # )

        if is_board_solvable:
            num_solvable_boards += 1

        print '# solvable/# boards:', num_solvable_boards, '/', i + 1
        with open('10M_run/histogram%d.json' % (i + 1), 'w') as out_file:
            out_file.write(
                '\n'.join(
                    '%d\t%d' % (k, move_histogram.get(k, 0))
                    for k in range(1, 73)
                )
            )
