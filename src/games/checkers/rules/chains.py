"""The capture chain search.

A draughts capture is not a step onto an occupied square, it is a leap over one onto the
square beyond, and a player who has taken one piece may well be able to take another from
where the first leap landed. That whole sequence is one move, so it has to be found as one
move, and this module finds it.

Three rules of the game are what make the search what it is, and each of them is a property
of the piece's declared data rather than a kind the engine knows:

- **The direction is the piece's own.** A jump goes along a diagonal the piece declares in
  `getDirections()`. A man's declared diagonals point forwards, so a man cannot jump
  backwards; a king's point all four ways, so a king's can.
- **The reach is the piece's own.** A declared step length of one means the piece jumps
  exactly one square over what it takes, landing on the square immediately beyond. No
  declared step means it may travel any distance: it walks over empty squares until it meets
  the first piece on the diagonal, takes that piece, and may land on any empty square beyond
  it.
- **One piece per jump, always.** Even a king stops at the first piece it meets, takes it,
  and may not carry on along the same diagonal to take a second one in the same jump.

A chain cannot be abandoned part-way: while another jump is available from where the piece
stands, the search continues, so what comes out of here is always a chain that has taken
everything it could have taken. A man that reaches the far row mid-chain stops there and is
crowned, which is the game's own rule and the reason a chain can end in the middle of a
board rather than only where the search ran out of jumps.
"""

from typing import Any, List, Optional, Tuple

from .geometric import crowning_row, jump_reach, origin_of

#: One found chain: the landing square of each jump, and the square each victim stood on.
Chain = Tuple[Tuple[Tuple[int, int], ...], Tuple[Tuple[int, int], ...]]


def jump_options(
    position: Any, piece: Any, origin: Tuple[int, int]
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Return every landing square this piece may jump to from where it stands right now.

    The position is read as it stands, which during a chain means the pieces taken earlier
    in it have already been lifted — that is what makes a piece untakeable twice, and what
    lets a king jump back across the square it has just emptied.

    Args:
        position: The board as it stands, mid-chain.
        piece: The piece making the chain.
        origin: The (row, col) square it currently stands on.

    Returns:
        List[Tuple[Tuple[int, int], Tuple[int, int]]]: One (landing square, captured square)
        pair per jump available, in a stable order.
    """
    reach = jump_reach(piece)
    options: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []

    for dr, dc in piece.getDirections() or []:
        if reach == 1:
            options.extend(_man_jumps(position, piece, origin, dr, dc))
        else:
            options.extend(_king_jumps(position, piece, origin, dr, dc))
    return options


def _man_jumps(
    position: Any, piece: Any, origin: Tuple[int, int], dr: int, dc: int
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Return the one jump a man may make along a single diagonal step.

    A man leaps over the piece immediately beside it and lands on the square immediately
    beyond, so both squares are fixed by the diagonal it is travelling along. The square
    beyond is not optional: a man cannot slide further to line the jump up with something
    else.

    Args:
        position: The board as it stands.
        piece: The man making the chain.
        origin: The (row, col) square it stands on.
        dr: Row offset per step along this diagonal.
        dc: Column offset per step along this diagonal.

    Returns:
        List[Tuple[Tuple[int, int], Tuple[int, int]]]: The single (landing, captured) pair
        this diagonal offers, or nothing.
    """
    over = (origin[0] + dr, origin[1] + dc)
    landing = (origin[0] + 2 * dr, origin[1] + 2 * dc)
    if not position.is_within_bounds(*landing):
        return []
    victim = position.get_piece_at(over)
    if victim is None or victim.getColor() == piece.getColor():
        return []
    if position.get_piece_at(landing) is not None:
        return []
    return [(landing, over)]


def _king_jumps(
    position: Any, piece: Any, origin: Tuple[int, int], dr: int, dc: int
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Return every jump a king may make along a single diagonal step.

    The king walks over empty squares until it meets the first piece on the diagonal. That
    piece is either its own, which ends the diagonal for this jump, or its opponent's, which
    it takes — and then any empty square immediately beyond that piece is somewhere it may
    land. Only the first piece is ever taken: the walk stops there rather than carrying on
    past a second one.

    Args:
        position: The board as it stands.
        piece: The king making the chain.
        origin: The (row, col) square it stands on.
        dr: Row offset per step along this diagonal.
        dc: Column offset per step along this diagonal.

    Returns:
        List[Tuple[Tuple[int, int], Tuple[int, int]]]: One (landing, captured) pair per
        square the king may land on beyond the piece it takes.
    """
    colour = piece.getColor()
    options: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    step = 1
    while True:
        square = (origin[0] + dr * step, origin[1] + dc * step)
        if not position.is_within_bounds(*square):
            break

        occupant = position.get_piece_at(square)
        if occupant is None:
            step += 1
            continue
        if occupant.getColor() == colour:
            break

        beyond = 1
        while True:
            landing = (square[0] + dr * beyond, square[1] + dc * beyond)
            if not position.is_within_bounds(*landing):
                break
            if position.get_piece_at(landing) is not None:
                break
            options.append((landing, square))
            beyond += 1
        break
    return options


def chains_for(position: Any, piece: Any, crowning_kinds: Any) -> List[Chain]:
    """Return every capture chain this piece can play, each one taken as far as it goes.

    The board is put back exactly as it was found, including every piece the search lifted
    and every square it moved this piece across, so a question asked of a position does not
    change that position.

    Args:
        position: The board to read.
        piece: The piece whose chains are wanted.
        crowning_kinds: The piece kinds that are crowned on reaching the far row, which is
            where a man's chain stops.

    Returns:
        List[Chain]: One (hops, captures) pair per chain, where `hops` is the landing square
        of each jump in order and `captures` is the square each victim stood on in the same
        order. Empty when the piece cannot take anything.
    """
    origin = origin_of(position, piece)
    if origin is None:
        return []

    found: List[Chain] = []
    _walk(position, piece, origin, (), (), found, crowning_kinds)
    return found


def longest_chain(position: Any, piece: Any, crowning_kinds: Any) -> int:
    """Return how many pieces the best chain this piece can play takes.

    Args:
        position: The board to read.
        piece: The piece whose chains are wanted.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        int: The largest number of jumps any of this piece's chains makes, which is zero
        when it cannot take anything at all.
    """
    return max((len(hops) for hops, _ in chains_for(position, piece, crowning_kinds)), default=0)


def _walk(
    position: Any,
    piece: Any,
    here: Tuple[int, int],
    hops: Tuple[Tuple[int, int], ...],
    captures: Tuple[Tuple[int, int], ...],
    found: List[Chain],
    crowning_kinds: Any,
) -> None:
    """Extend a chain by every jump available, and record it where it cannot go further.

    A chain is recorded only when no further jump is available from where the piece stands,
    which is the rule that a chain may not be abandoned part-way. Where a jump *is* available
    the piece is moved onto its landing square so the next round of the walk reads the
    position as it will really be, with that piece gone from the square it left and every
    victim already lifted.

    Args:
        position: The board as it stands, mid-chain.
        piece: The piece making the chain.
        here: The (row, col) square the piece stands on now.
        hops: The landing square of each jump so far, in order.
        captures: The square each victim stood on, in order.
        found: The chains found so far, appended to.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        None
    """
    options = jump_options(position, piece, here)

    if not options or _is_crowned(position, piece, here, crowning_kinds):
        # An empty chain is not a capture: it is the piece standing still, and recording one
        # would offer a move that takes nothing and lands nowhere.
        if hops:
            found.append((hops, captures))
        return

    for landing, over in options:
        victim = position.get_piece_at(over)
        position.set_piece_at(over, None)
        position.set_piece_at(here, None)
        position.set_piece_at(landing, piece)
        _walk(
            position,
            piece,
            landing,
            (*hops, landing),
            (*captures, over),
            found,
            crowning_kinds,
        )
        position.set_piece_at(landing, None)
        position.set_piece_at(here, piece)
        position.set_piece_at(over, victim)


def _is_crowned(position: Any, piece: Any, square: Tuple[int, int], crowning_kinds: Any) -> bool:
    """Report whether this piece has just reached the row on which it becomes a king.

    A man that reaches the far row by a jump is crowned there and then, and its move is over:
    it does not carry on jumping as a king it has only just become. A king reaches the far
    row all the time and carries on, so this asks about the kind as well as the row.

    Args:
        position: The board to read.
        piece: The piece making the chain.
        square: The (row, col) square it stands on now.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        bool: True when the piece is of a crowning kind and is standing on its crowning row.
    """
    row = crowning_row(position, piece, crowning_kinds)
    return row is not None and square[0] == row


def side_chains(position: Any, color: int, crowning_kinds: Any) -> dict:
    """Return every capture chain available to a colour, by the square each starts on.

    Args:
        position: The board to read.
        color: The colour whose chains are wanted, 1 for White and -1 for Black.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        dict: Starting square to the list of chains from it. A square with no chain is
        absent, so an empty result means the colour cannot take anything anywhere.
    """
    found: dict = {}
    for row in range(position.rows):
        for col in range(position.cols):
            square = (row, col)
            piece = position.get_piece_at(square)
            if piece is None or piece.getColor() != color:
                continue
            chains = chains_for(position, piece, crowning_kinds)
            if chains:
                found[square] = chains
    return found


def side_chains_best(position: Any, color: int, crowning_kinds: Any) -> Optional[Chain]:
    """Return the longest capture chain available to a colour, if it has one.

    Args:
        position: The board to read.
        color: The colour whose chains are wanted, 1 for White and -1 for Black.
        crowning_kinds: The piece kinds that are crowned on reaching the far row.

    Returns:
        Optional[Chain]: A chain taking the most pieces this colour can take in one move, or
        None when it cannot take anything.
    """
    everything: List[Chain] = []
    for chains in side_chains(position, color, crowning_kinds).values():
        everything.extend(chains)
    if not everything:
        return None
    return max(everything, key=lambda chain: len(chain[0]))
