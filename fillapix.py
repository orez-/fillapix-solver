# -*- coding: utf8 -*-
from __future__ import print_function

import collections

af = '\x1b[38;5;{}m'
ab = '\x1b[48;5;{}m'
clear = '\x1b[0m'

BLACK = 0
GRAY = 8
WHITE = 15
YELLOW = 3
GREEN = 2
RED = 1
MAGENTA = 5
CYAN = 6
SALMON = 9
LIMEGREEN = 10

UNKNOWN = object()
YES = object()
NO = object()

class Board(object):
    def __init__(self, numbers):
        self.numbers = [
            [
                int(elem) if elem.strip() else None
                for elem in row
            ] for row in numbers
        ]
        self.filled = [[UNKNOWN for _ in row] for row in numbers]

        self.highlight = {}

    def __iter__(self):
        for row in zip(self.numbers, self.filled):
            yield zip(*row)

    @property
    def tty(self):
        """
        Get TTY color formatted string.
        """
        output = []
        for y, row in enumerate(self):
            for x, (number, filled) in enumerate(row):
                if filled is UNKNOWN:
                    output.append((af + ab).format(BLACK, WHITE))
                elif filled is YES:
                    output.append((af + ab).format(WHITE, BLACK))
                elif filled is NO:
                    output.append((af + ab).format(BLACK, GRAY))
                if (x, y) in self.highlight:
                    output.append(af.format(self.highlight[(x, y)]))
                output.append(str(number) if number is not None else '.')
                output.append(clear)
            output.append('\n')
        return ''.join(output)

    def fill_around(self, coord, value, exclude=frozenset()):
        """
        Fill all unknown squares around a coordinate with the specified value.

        Optionally, do not fill squares with coordinates in `exclude`.
        """
        count = 0
        for ox, oy in self.surrounding_tiles(coord):
            if self.filled[oy][ox] is UNKNOWN and (ox, oy) not in exclude:
                count += 1
                self.filled[oy][ox] = value
        return count

    def fill(self, coords, value):
        for x, y in coords:
            assert self.filled[y][x] is UNKNOWN, self.filled[y][x]
            self.filled[y][x] = value

    def surrounding_stats(self, coord):
        stats = collections.Counter(
            self.filled[oy][ox]
            for ox, oy in self.surrounding_tiles(coord)
        )
        # Consider out of bounds as NO.
        stats[NO] += 9 - sum(stats.itervalues())
        return stats

    def in_bounds(self, x, y):
        return 0 <= y < len(self.filled) and 0 <= x < len(self.filled[y])

    def surrounding_tiles(self, coord):
        """
        Iterator of coordinates of all squares surrounding the specified coordinate.
        """
        x, y = coord
        for ox in (x - 1, x, x + 1):
            for oy in (y - 1, y, y + 1):
                if self.in_bounds(ox, oy):
                    yield ox, oy

    def sharing_friends(self, coord):
        """
        Iterator of coordinates of all squares that share at least one
        neighboring square with the specified coordinate's neighbors and
        have a number.
        """
        x, y = coord
        for ox in xrange(x - 2, x + 3):
            for oy in xrange(y - 2, y + 3):
                if self.in_bounds(ox, oy) and self.numbers[oy][ox] is not None:
                    if (ox, oy) != (x, y):
                        yield ox, oy

    def num_shared(self, coord1, coord2):
        x1, y1 = coord1
        x2, y2 = coord2
        return (
            (3 - abs(x1 - x2)) *
            (3 - abs(y1 - y2))
        )

    def shared(self, coord1, coord2):
        """
        Iterator of squares neighboring both specified coordinates.

        nb: resulting squares may be out of bounds!
        """
        x1, y1 = coord1
        x2, y2 = coord2
        for x in xrange(max(x1, x2) - 1, min(x1, x2) + 2):
            for y in xrange(max(y1, y2) - 1, min(y1, y2) + 2):
                yield x, y


def solve(board):
    progress = True
    while progress:
        progress = False
        for y, row in enumerate(board):
            for x, (number, filled) in enumerate(row):
                if number is None:
                    continue
                stats = board.surrounding_stats((x, y))
                # Sufficient
                if number == stats[YES]:
                    if board.fill_around((x, y), NO):
                        progress = True
                    continue
                # Necessary
                if 9 - number == stats[NO]:
                    if board.fill_around((x, y), YES):
                        progress = True
                    continue
                # num shared + num difference = 9
                for ox, oy in board.sharing_friends((x, y)):
                    shared = list(board.shared((ox, oy), (x, y)))
                    o_number = board.numbers[oy][ox]
                    diff = abs(number - o_number)
                    if len(shared) + diff == 9:
                        if number < o_number:
                            small_x, small_y = x, y
                            large_x, large_y = ox, oy
                        else:
                            small_x, small_y = ox, oy
                            large_x, large_y = x, y
                        if board.fill_around((small_x, small_y), NO, exclude=shared):
                            progress = True
                        if board.fill_around((large_x, large_y), YES, exclude=shared):
                            progress = True

def solve2(board):
    # Preprocess 'numbers' into 'zones'.
    known_areas = {}
    for y, row in enumerate(board):
        for x, (number, _) in enumerate(row):
            if number is None:
                continue
            tiles = board.surrounding_tiles((x, y))
            known_areas[frozenset(tiles)] = number

    progress = True
    while progress:
        progress = False
        for tiles, number in known_areas.items():
            del known_areas[tiles]

            # Bookkeeping.
            new_number = number
            new_tiles = set()

            for x, y in tiles:
                filled = board.filled[y][x]
                if filled is YES:
                    new_number -= 1
                elif filled is UNKNOWN:
                    new_tiles.add((x, y))
                elif filled is not NO:
                    raise AssertionError(filled)
            del number
            del tiles

            if new_number == len(new_tiles):
                board.fill(new_tiles, YES)
                progress = True
                continue

            if new_number == 0:
                board.fill(new_tiles, NO)
                progress = True
                continue

            # CHECK THE OVERLAP
            for otiles, onumber in known_areas.items():
                overlap = frozenset(otiles & new_tiles)
                if not overlap:
                    continue
                new_tiles_overlap = frozenset(new_tiles - overlap)
                otiles_overlap = frozenset(otiles - overlap)
                # find the upper and lower bounds for each that can fit in the overlap.
                omax = min(len(overlap), onumber, new_number)
                omin = max(
                    onumber - len(otiles_overlap),
                    new_number - len(new_tiles_overlap),
                    0,
                )
                if omin == omax:
                    known_areas[overlap] = omax
                    known_areas[new_tiles_overlap] = new_number - omax
                    known_areas[otiles_overlap] = onumber - omax

            known_areas[frozenset(new_tiles)] = new_number

def highlight(tiles, color, wait=False):
    for t in tiles:
        board.highlight[t] = color
    if not wait:
        show_highlight()

def show_highlight():
    print(board.tty)
    board.highlight = {}
    raw_input()

if __name__ == '__main__':
    # raw_board = [
    #     " 01 44  0 ",
    #     "0        0",
    #     "  5   23  ",
    #     "  66   55 ",
    #     " 6 65434 4",
    #     "    5 6  5",
    #     "4    4 5 4",
    #     "  45 5 5  ",
    #     "4 6 65   3",
    #     "4 564323 3",
    #     "45 542    ",
    #     "  5432 5  ",
    #     " 465  5  1",
    #     "  777 7  0",
    #     " 56  64   ",
    # ]
    raw_board = [
        " 4543     2 2  334  ",
        "      3 3  3     5 4",
        "1  4 4 5 43 35  1  4",
        " 3  3 334  33 44    ",
        "2 2 343   343    1  ",
        "   5  2 443324     5",
        "  466    4  2 4 3 7 ",
        "0   7  0  43 3      ",
        "  67    24  5 3 57  ",
        "       3 5 6 333 8 6",
        " 6  76  3    3    7 ",
        "  8  6  146      6  ",
        "    6 200 66   3    ",
        " 6 7 53   6  4   5 5",
        "  7 54 3 44 2   6   ",
        "    5        35   6 ",
        "56  6 65 5 35  466 4",
        "46   45   6   63 5  ",
        "  6  2   4   3     4",
        "2 5   3 4   3  463  ",
        "  4 24  65 3 45     ",
        "  30   3 4 2 3  6  3",
        "4    4    1      4 3",
        "4 113 2 23  2 4464 3",
        "      22 2 2        ",
        "   2   122   23  44 ",
        "4 2 10  1  1 4   3 0",
        "   1  3  4  3 33    ",
        "6             3     ",
        " 6  4 4  3 3  0  0 0",
    ]
    board = Board(raw_board)
    solve2(board)
    print(board.tty)
