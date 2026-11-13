import re
from typing import Callable, Optional

from ..utils import (
    is_ascii_whitespace,
    is_ascii_punctuation,
)
from .token import (
    Delimiter,
    SymbolKind,
    SeqKind,
    Token,
    TextToken,
    NewlineToken,
    NbspToken,
    HardbreakToken,
    EscapeToken,
    OpenToken,
    CloseToken,
    SymToken,
    SequenceToken,
)

braced_delimiters = {
    '*': Delimiter.BRACE_ASTERISK, # strong
    '^': Delimiter.BRACE_CARET, # superscript
    '=': Delimiter.BRACE_EQUAL, # highlighed
    '-': Delimiter.BRACE_HYPHEN, # delete
    '+': Delimiter.BRACE_PLUS, # insert
    '~': Delimiter.BRACE_TILDE, # subscript
    '_': Delimiter.BRACE_UNDERSCORE, # emphasis
    '\'': Delimiter.BRACE_QUOTE1,
    '"': Delimiter.BRACE_QUOTE2,
}

class Lexer:

    # Has extra !, | thatn djot.js.
    # No `$`, `\r` in djot.js
    _RE_SPECIAL = re.compile(r'''[\\\[\](){}*^=+~_'"-!<|:`.\n]''')
    _SPACE_TAB = ' \t'

    def __init__(self, src: str):
        self.src: str = src # a line of text
        self._length = len(src)

        # Double pointer.
        # Always move _next_pos only.
        # _current_pos should always follow _next_pos's previous state.
        self._current_pos: int = 0
        self._next_pos: int = 0
        self._buffered_token: Optional[Token] = None

        self._escape: bool = False
        self.verbatim: bool = False

    @property
    def length(self) -> int:
        return self._length

    @property
    def current_char(self) -> Optional[str]:
        if self._current_pos < self.length:
            return self.src[self._current_pos] 
        else:
            return None

    def char_at(self, pos: int) -> Optional[str]:
        if pos < self.length:
            return self.src[pos]
        else:
            return None

    def find_special(self, start: int) -> Optional[int]:
        """
        Find special char using regex.

        The end position has 3 cases:
        1. Equal to start means current position is a special char.
        2. Betwenn start and length means there's plain text from start to special_pos.
        3. None means it is plain text from start to end of line.
        """
        m = self._RE_SPECIAL.search(self.src, start)

        if m:
            return m.start() # this may include self._next_pos itself.

        # If not found, it means there's plain text from self._next_pos to the end of line.
        # This behaves similar to Rust version's 
        # self.eat_while(|c| !is_special(c));
        # which stops at length of src if no special char is found.
        return None


    def step(self, n: int = 1) -> bool:
        if n < 0 :
            raise Exception('Cannot go back')
        
        if self._next_pos < self.length:
            self._current_pos = self._next_pos
            self._next_pos += n
            return True

        self._next_pos += n
        return False

    def advance(self, new_pos: int) -> bool:
        if new_pos <= self._next_pos:
            raise Exception('Cannot go back')
        
        if self._next_pos < self.length:
            self._current_pos = self._next_pos
            self._next_pos = new_pos
            return True

        self._next_pos = new_pos
        return False

    def read_token(self) -> Optional[Token]:
        if self._buffered_token is not None:
            tok = self._buffered_token
            self._buffered_token = None
            return tok
        
        start = self._next_pos

        if start >= self.length:
            return None

        if self._escape:
            return self.read_escaped_token(start)

        # Depending on the special char position,
        # we may have to generate one or two tokens.
        special_pos = self.find_special(start)
        # Plain text till the end of line.
        if special_pos is None:
            tok = TextToken(
                length=self.length - start,
            )
            self.advance(self.length)
            return tok

        # There are text between start and special char.
        # Should generate two tokens.
        if special_pos > start:
            tok = TextToken(
                length=special_pos - start,
            )
            self.advance(special_pos)

            self._buffered_token = self.read_special_token(special_pos)

            return tok

        # start position is special char
        return self.read_special_token(special_pos)

    def read_escaped_token(self, pos: int) -> Optional[Token]:
        self._escape = False
        ch = self.char_at(pos) # char after \
        if ch is None:
            return None
        
        match ch:
            case '\n': # \\n
                self.advance(pos + 1)
                return HardbreakToken(1)
            case '\t' | ' ':
                # \'\t' | ' '
                if self.is_ahead_blank(pos):
                    self.advance(self.length)
                    return HardbreakToken(self.length - pos)
                else:
                    self.advance(pos + 1)
                    return NbspToken(1)
            case _:
                self.advance(pos + 1)
                return TextToken(1)

    def read_special_token(self, start: int) -> Optional[Token]:
        ch = self.char_at(start)

        match ch:
            case '\n':
                self.advance(start + 1)
                return NewlineToken(1)
            case '\\':
                # \a -> TokenText(1), TokenText(1)
                # \* -> TokenEscape(1), TokenText(1)
                next_ch = self.char_at(start + 1)
                if next_ch is not None and (is_ascii_whitespace(next_ch) or is_ascii_punctuation(next_ch)):
                    self._escape = not self.verbatim
                    self.advance(start + 1)
                    return EscapeToken(1)
                else:
                    self.advance(start + 1)
                    return TextToken(1)

            case '[':
                self.advance(start + 1)
                return OpenToken(1, Delimiter.BRACKET)

            case ']':
                self.advance(start + 1)
                return CloseToken(1, Delimiter.BRACKET)
            
            case '(':
                self.advance(start + 1)
                return OpenToken(1, Delimiter.PAREN)
            
            case ')':
                self.advance(start + 1)
                return CloseToken(1, Delimiter.PAREN)

            case '{':
                next_ch = self.char_at(start + 1)
                if next_ch and next_ch in braced_delimiters:
                    kind = braced_delimiters[next_ch]
                    self.advance(start + 2)
                    return OpenToken(2, delimiter=kind)

                self.advance(start + 1)
                return OpenToken(1, delimiter=Delimiter.BRACE)

            case '}':
                self.advance(start + 1)
                return CloseToken(1, Delimiter.BRACE)

            case '*':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_ASTERISK)
                else:
                    self.advance(start + 1)
                    return SymToken(1, SymbolKind.ASTERISK)

            case '^':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_CARET)
                else:
                    self.advance(start + 1)
                    return SymToken(1, SymbolKind.CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_EQUAL)
                else:
                    self.advance(start + 1)
                    return TextToken(1)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_PLUS)
                else:
                    self.advance(start + 1)
                    return TextToken(1)

            case '~':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_TILDE)
                else:
                    self.advance(start + 1)
                    return SymToken(1, SymbolKind.TILDE)

            case '_':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_UNDERSCORE)
                else:
                    self.advance(start + 1)
                    return SymToken(1, SymbolKind.UNDERSCORE)

            case '\'':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_QUOTE1)
                else:
                    return SymToken(1, SymbolKind.QUOTE1)

            case '"':
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_QUOTE2)
                else:
                    return SymToken(1, SymbolKind.QUOTE2)

            case '-':
                # -}
                if self.is_close_brace_followed(start):
                    self.advance(start + 2)
                    return CloseToken(2, Delimiter.BRACE_HYPHEN)
                else:
                    # --} stop immediately
                    # --h stop at h
                    hyphen_len = self.read_hyphen(start)
                    self.advance(hyphen_len)
                    return SequenceToken(hyphen_len, SeqKind.HYPHEN)

            case '!':
                # ![
                if self.char_at(start + 1) == '[':
                    self.advance(start + 2)
                    return SymToken(2, SymbolKind.EXCLAIM_BRACKET)
                else:
                    self.advance(start + 1)
                    return TextToken(1)

    def is_close_brace_followed(self, pos: int) -> bool:
        return self.src[pos + 1] == '}'

    def read_hyphen(self, start: int) -> int:
        i = start
        while self.char_at(i) == '-' and self.char_at(i + 1) != '}':
            i += 1

        return i - start

    def is_ahead_blank(self, start: int) -> bool:
        while start < self.length:
            c = self.src[start]
            if c in self._SPACE_TAB:
                start += 1
            elif c == '\n':
                return True
            else:
                return False # non-space

        return False # EOF without newline.