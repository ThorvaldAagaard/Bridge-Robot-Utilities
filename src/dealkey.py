"""Compare deals independent of how they are written or which seat holds which hand.

A board that is just rotated has the same four hands, moved one, two or three
seats around the table. rotation_key() gives such deals the same key,
hands_from_north() tells an exact duplicate from a rotated one, and
same_board() checks that dealer and vulnerability were turned along too - only
then is it really the same board.
"""

SEATS = "NESW"

VULS = {'none': 'None', 'love': 'None', '-': 'None', 'ns': 'NS', 'ew': 'EW',
        'all': 'All', 'both': 'All'}

# endplay's Vul enum values: none, both, ns, ew
ENDPLAY_VULS = ['None', 'All', 'NS', 'EW']


def hands_from_north(deal):
    """The hands of a PBN deal in N, E, S, W order.

    Accepts the deal value ("E:AK.. .. .. ..") or the whole [Deal "..."] line,
    starting at any seat.
    """
    if deal.lstrip().startswith('[Deal'):
        deal = deal.split('"')[1]
    first, hands = deal.strip().split(':', 1)
    hands = hands.split()
    start = SEATS.index(first.strip().upper())
    return tuple(hands[(seat - start) % 4] for seat in range(4))


def rotation_key(hands):
    """The same key for hands (N, E, S, W) and their rotations by 1, 2 or 3 seats."""
    return min(hands[r:] + hands[:r] for r in range(4))


def rotation(hands, other):
    """How many seats clockwise the hands moved from *hands* to *other* (0-3), or None."""
    for r in range(4):
        if tuple(hands[(seat - r) % 4] for seat in range(4)) == tuple(other):
            return r
    return None


def _seat(dealer):
    # A PBN tag ("N") or an endplay Player (an int)
    if isinstance(dealer, int):
        return dealer % 4
    if dealer and dealer.strip().upper() in SEATS:
        return SEATS.index(dealer.strip().upper())
    return None


def _vul(vul):
    # A PBN tag ("NS", "Both", ...) or an endplay Vul (an int)
    if isinstance(vul, int):
        return ENDPLAY_VULS[vul]
    return VULS.get(str(vul).strip().lower()) if vul is not None else None


def same_board(hands, dealer, vul, other, other_dealer, other_vul):
    """True if *other* is this board turned around the table.

    The hands, the dealer and the vulnerability must all have moved the same
    number of seats; an unknown dealer or vulnerability never matches.
    """
    r = rotation(hands, other)
    d, od = _seat(dealer), _seat(other_dealer)
    v, ov = _vul(vul), _vul(other_vul)
    if r is None or None in (d, od, v, ov):
        return False
    if r % 2:
        v = {'NS': 'EW', 'EW': 'NS'}.get(v, v)
    return od == (d + r) % 4 and ov == v
