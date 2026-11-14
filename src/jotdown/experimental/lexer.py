from collections import deque
import re
from typing import Optional

from jotdown.utils import (
    is_ascii_whitespace,
    is_ascii_punctuation,
)
from jotdown.lex.token import (
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
    """
    This version uses regex to search for special chars.
    This introduces another problem: each special char will execute regex engine twice.
    To avoid this problem, you have to generate one to two tokens when a special
    char is seen.
    To solve this problem, a deque is introduced.
    """

    # Has extra !, | thatn djot.js.
    # No `$`, `\r` in djot.js
    _RE_SPECIAL = re.compile(r'''[\n\[\\\](){}*^=+~_'"!<|:`.-]''')
    _SPACE_TAB = ' \t'

    def __init__(self, src: str):
        self.src: str = src # a line of text
        self._length = len(src)

        self._pos: int = 0
        self._queue: deque[Token] = deque()

        self._escape: bool = False
        self.verbatim: bool = False

    @property
    def length(self) -> int:
        return self._length

    def step(self, n: int = 1) -> bool:
        if n < 0 :
            raise Exception('Cannot go back')
        
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

    def is_close_brace_followed(self, pos: int) -> bool:
        return self.char_at(pos + 1) == '}'

    def read_hyphen(self, start: int) -> int:
        i = start
        while self.char_at(i) == '-' and self.char_at(i + 1) != '}':
            i += 1

        return i - start

    def read_seq(self, pos: int, ch: str) -> int:
        """Count consecutive chars"""        
        if self.src[pos] != ch:
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
        current = self.eat_token()
        if current is None:
            return None

        if isinstance(current, TextToken):
            while True:
                next_token = self.peek_token()
                if next_token is None or not isinstance(next_token, TextToken):
                    break
                self.eat_token()
                current.length += next_token.length

        return current

    def eat_token(self) -> Optional[Token]:
        if not self._queue:
            self.read_token(self._pos)
        
        if not self._queue:
            return None
        
        tok = self._queue.popleft()
        self.step(tok.length)
        return tok

    def peek_token(self) -> Optional[Token]:
        if not self._queue:
            self.read_token(self._pos)

        if self._queue:
            return self._queue[0]
        else:
            return None
        
    def read_token(self, start: int) -> None:
        if start >= self.length:
            return None

        if self._escape:
            text_tok = self.read_escaped_token(start)
            if text_tok is not None:
                self._queue.append(text_tok)
            return

        # Depending on the special char position,
        # we may have to generate one or two tokens.
        special_pos = self.find_special(start)
        # Plain text till the end of line.
        if special_pos is None:
            text_tok = TextToken(
                length=self.length - start,
            )
            self._queue.append(text_tok)
            return

        special_tok = self.read_special_token(special_pos)

        # There are text between start and special char.
        # Should generate two tokens.
        if special_pos > start:
            tok = TextToken(
                length=special_pos - start,
            )
            self._queue.append(tok)

        special_tok = self.read_special_token(special_pos)
        if special_tok is not None:
            self._queue.append(special_tok)

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
                if self.is_ahead_blank(pos):
                    return HardbreakToken(self.length - pos)
                else:
                    return NbspToken(1)
            case _:
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
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_ASTERISK)
                else:
                    return SymToken(1, SymbolKind.ASTERISK)

            case '^':
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_CARET)
                else:
                    return SymToken(1, SymbolKind.CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_EQUAL)
                else:
                    return TextToken(1)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_PLUS)
                else:
                    return TextToken(1)

            case '~':
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_TILDE)
                else:
                    return SymToken(1, SymbolKind.TILDE)

            case '_':
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_UNDERSCORE)
                else:
                    return SymToken(1, SymbolKind.UNDERSCORE)

            case '\'':
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_QUOTE1)
                else:
                    return SymToken(1, SymbolKind.QUOTE1)

            case '"':
                if self.is_close_brace_followed(start):
                    return CloseToken(2, Delimiter.BRACE_QUOTE2)
                else:
                    return SymToken(1, SymbolKind.QUOTE2)

            case '-':
                # -}
                if self.is_close_brace_followed(start):
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
        token = self.next_token()
        if token is None:
            raise StopIteration

        return token