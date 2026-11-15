from typing import Optional

from jotdown.utils import (
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

    _SPACE_TAB = ' \t'
    _SPECIAL_CHARS = '\\[](){}*^=+~_\'"-!<|:`.\n'

    def __init__(self, src: str):
        self.src: str = src # a line of text
        self._length = len(src)

        self._pos: int = 0
        self._buffered_token: Token | None = None

        self._escape: bool = False
        self.verbatim: bool = False

    @property
    def length(self) -> int:
        return self._length


    def step(self, n: int = 1) -> bool:
        if n < 0 :
            raise Exception('Cannot go back')

        if n == 0:
            return True
        
        if self._pos < self.length:
            self._pos += n
            return True

        self._pos += n
        return False


    def char_at(self, pos: int) -> Optional[str]:
        if pos < self.length:
            return self.src[pos]
        else:
            return None

    def find_special(self, pos: int) -> Optional[int]:
        if pos >= self.length:
            return None
        
        if self.src[pos] in self._SPECIAL_CHARS:
            return pos
        
        while pos < self.length:
            c = self.src[pos]
            if c in self._SPECIAL_CHARS:
                return pos
            pos += 1

        return pos
    
    def read_hyphen(self, start: int) -> int:
        i = start
        while self.char_at(i) == '-' and self.char_at(i + 1) != '}':
            i += 1

        return i - start

    def read_seq(self, pos: int, ch: str) -> int:
        """Count consecutive chars"""        
        if self.char_at(pos) != ch:
            return 0
        
        i = pos
        
        while i < self.length and self.src[i] == ch:
            i += 1
        
        return i - pos

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

    def is_space_newline(self, start: int, end: int) -> bool:
        chars = self.src[start:end].lstrip(self._SPACE_TAB)
        return len(chars) == 1 and chars[0] == '\n'

    def is_finished(self) -> bool:
        return self._pos >= self.length

    def next_token(self) -> Optional[Token]:
        current = self.read_token(self._pos)
        if current is None:
            return None

        self.step(current.length)

        if isinstance(current, TextToken):
            while True:
                # Peek token will buffer a token
                next_token = self.peek_token()
                if next_token is None or not isinstance(next_token, TextToken):
                    break
                current.length += next_token.length
                # buffered token is consumed, so invalidate buffer immediately.
                self._buffered_token = None
                self.step(next_token.length)

        return current

    def peek_token(self) -> Optional[Token]:
        if self._buffered_token is None:
            self._buffered_token = self.read_token(self._pos)

        return self._buffered_token

    def read_token(self, start: int) -> Optional[Token]:
        if start >= self.length:
            return None

        if self._escape:
            return self.read_escaped_token(start)

        # Depending on the special char position,
        # we may have to generate one or two tokens.
        special_pos = self.find_special(start)
        if special_pos is None:
            return None
        
        if special_pos > start:
            return TextToken(
                length=special_pos - start,
            )

        return self.read_special_token(special_pos)

    def read_escaped_token(self, pos: int) -> Optional[Token]:
        self._escape = False
        ch = self.char_at(pos) # char after \
        if ch is None:
            return None
        
        match ch:
            case '\n': # \\n
                return HardbreakToken(1)
            case '\t' | ' ':
                # \'\t' | ' '
                if self.is_space_newline(pos, self.length):
                    return HardbreakToken(self.length - pos)
                else:
                    return NbspToken(1)
            case _:
                # \*bar will generate two Text token and concatenated.
                return TextToken(1)

    def read_special_token(self, start: int) -> Optional[Token]:
        ch = self.char_at(start)

        match ch:
            case '\n':
                return NewlineToken(1)
            case '\\':
                # \a -> TokenText(1), TokenText(1)
                # \* -> TokenEscape(1), TokenText(1)
                next_ch = self.char_at(start + 1)
                if next_ch is not None and (is_ascii_whitespace(next_ch) or is_ascii_punctuation(next_ch)):
                    self._escape = not self.verbatim
                    return EscapeToken(1)
                else:
                    return TextToken(1)

            case '[':
                return OpenToken(1, Delimiter.BRACKET)

            case ']':
                return CloseToken(1, Delimiter.BRACKET)
            
            case '(':
                return OpenToken(1, Delimiter.PAREN)
            
            case ')':
                return CloseToken(1, Delimiter.PAREN)

            case '{':
                next_ch = self.char_at(start + 1)
                if next_ch and next_ch in braced_delimiters:
                    kind = braced_delimiters[next_ch]
                    return OpenToken(2, delimiter=kind)

                return OpenToken(1, delimiter=Delimiter.BRACE)

            case '}':
                return CloseToken(1, Delimiter.BRACE)

            case '*':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_ASTERISK)
                else:
                    return SymToken(1, SymbolKind.ASTERISK)

            case '^':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_CARET)
                else:
                    return SymToken(1, SymbolKind.CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_EQUAL)
                else:
                    return TextToken(1)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_PLUS)
                else:
                    return TextToken(1)

            case '~':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_TILDE)
                else:
                    return SymToken(1, SymbolKind.TILDE)

            case '_':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_UNDERSCORE)
                else:
                    return SymToken(1, SymbolKind.UNDERSCORE)

            case '\'':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_QUOTE1)
                else:
                    return SymToken(1, SymbolKind.QUOTE1)

            case '"':
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_QUOTE2)
                else:
                    return SymToken(1, SymbolKind.QUOTE2)

            case '-':
                # -}
                if self.char_at(start+1) == '}':
                    return CloseToken(2, Delimiter.BRACE_HYPHEN)
                else:
                    # --} stop immediately
                    # --h stop at h
                    hyphen_len = self.read_hyphen(start)
                    return SequenceToken(hyphen_len, SeqKind.HYPHEN)

            case '!':
                # ![
                if self.char_at(start + 1) == '[':
                    return SymToken(2, SymbolKind.EXCLAIM_BRACKET)
                else:
                    return TextToken(1)

            case '<':
                return SymToken(1, SymbolKind.LT)

            case '|':
                return SymToken(1, SymbolKind.PIPE)

            case ':':
                return SymToken(1, SymbolKind.COLON)

            case '`':
                n = self.read_seq(start, SeqKind.BACKTICK.value)
                return SequenceToken(n, SeqKind.BACKTICK)

            case '.':
                n = self.read_seq(start, SeqKind.PERIOD.value)
                return SequenceToken(n, SeqKind.PERIOD)

            case _:
                return TextToken(1)

    def __iter__(self):
        return self

    def __next__(self) -> Token:
        if self._buffered_token is not None:
            token = self._buffered_token
            self._buffered_token = None
            self.step(token.length)
            return token
        
        token = self.next_token()
        if token is None:
            raise StopIteration

        return token