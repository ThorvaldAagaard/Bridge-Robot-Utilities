"""Local fixes to endplay, applied by importing this module.

The executables are built against the stock endplay release from PyPI, which
misses fixes a locally patched endplay has. They are re-applied here at runtime,
so a tool behaves the same from source and as an executable. Nothing is written
to disk differently than a patched endplay would write it.

  [Dealer] on a board without a contract (PBN parser)
      endplay (0.5.10 and 0.5.12) applies the tag only when the board has a
      contract, so a board with no [Contract] tag, or [Contract "?"], silently
      gets the dealer implied by its board number instead - and a tool that
      resets the dealer then computes the wrong vulnerability.

  Annotations ($1, $2, ...) in the auction (PBN parser)
      The PBN standard allows a Numeric Annotation Glyph after a call. endplay
      passes it to Bid(), which raises
      "ValueError: invalid literal for int() with base 10: '$'".

  mn|| at the start of a board (LIN encoder)
      BBO's own LIN files open with the "main name" command; endplay omits it.

  A trick with fewer than four cards (trick_winner)
      endplay always reads trick[1..3] and raises IndexError on a part trick;
      with fewer than four cards the player on lead is still winning.

endplay 0.5.12 handles [Contract "?"] itself, as None rather than the patched
endplay's Pass, so that one is not repeated here.

Drop a fix once the endplay we build with has it.
"""
import endplay.parsers.lin as lin
import endplay.parsers.pbn as pbn
import endplay.utils.play as play
from endplay.types import Player

_tags_to_board = pbn.PBNDecoder._tags_to_board
_serialise_board = lin.LINEncoder.serialise_board
_trick_winner = play.trick_winner


def _tags_to_board_with_fixes(self):
    for raw_key, fields in self.curtags.items():
        if raw_key.lower() == "auction" and fields.get("data"):
            fields["data"] = [[call for call in row if not call.startswith("$")]
                              for row in fields["data"]]
    board = _tags_to_board(self)
    if board is not None:
        for raw_key, fields in self.curtags.items():
            if raw_key.lower() == "dealer":
                if fields["value"] == "#":
                    fields = self.prevtags[raw_key]
                if fields["value"] not in ("", "?"):
                    board.dealer = Player.find(fields["value"])
    return board


def _serialise_board_with_mn(self, board):
    return "mn||" + _serialise_board(self, board)


def _already_emits_mn():
    """True when endplay itself writes the mn|| command (a patched build)."""
    from endplay.types import Board, Deal
    try:
        board = Board(deal=Deal(), dealer=Player.north)
        return _serialise_board(lin.LINEncoder(), board).startswith("mn|")
    except Exception:
        return False


def _trick_winner_part_trick(trick, first, trump):
    if len(trick) == 4:
        return _trick_winner(trick, first, trump)
    trick[0]  # an empty trick has no winner, as in endplay itself
    return first


pbn.PBNDecoder._tags_to_board = _tags_to_board_with_fixes
if not _already_emits_mn():
    lin.LINEncoder.serialise_board = _serialise_board_with_mn
play.trick_winner = _trick_winner_part_trick
