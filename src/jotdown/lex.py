from typing import Callable, Optional

from .utils import (
    is_ascii_whitespace,
    is_ascii_punctuation,
)
from .token import (
    Delimiter,
    braced_delimiters,
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

class Lexer:

    _SPECIAL_CHARS = set('\\[](){}*^=+~_\'"-!<|:`.\n')

    def __init__(self, src: str):
        self._src: str = src
        self._pos: int = 0
        self._escape: bool = False
        # _next plays two role:
        # 1. cache next token when peeking
        # 2. cache token when concatenating consecutive 
        # text tokens.
        # This avoids repeated parsing of the same token.
        self._next: Optional[Token] = None
        self.verbatim: bool = False

    def peek(self) -> Optional[Token]:
        """
        Peeking the next token.
        
        This method is not really peeking. Strictly speaking,
        peek behavior should not move curent cursor.
        This method, however, does move the cursor.

        What's more, the action of peeking next token
        is usually the job of parser rathan than lexer.
        A lexer usually only peeks the next char.

        Hence the ahead method: you lost the starting postion
        of the token being 'peeked' since the cursor has
        already been moved forward by peeking.
        The ahead method backtracing the starting position
        of the token being 'peeked'. 
        """
        if self._next is None:
            self._next = self._token()
        return self._next

    def ahead(self) -> str:
        """
        Backtracing the starting position of a peeked token
        after peeking moved forward current cursor.
        """
        l = self._next.length if self._next else 0
        start = self._pos - l
        return self._src[start:]

    def skip_ahead(self, n: int):
        self._pos += n
        self._next = None

    def _next_token(self) -> Optional[Token]:
        current = self._token()
        if current is None:
            return None

        # Concatenate continuous string.
        # When such cases occur?
        # \a will produce KindText for \, and KindText for a
        # \*a will produce KindEscape for \, KindText for * and KindText for a.
        if isinstance(current, TextToken):
            while True:
                self._next = self._token()
                if self._next is None or not isinstance(self._next, TextToken):
                    break
                current.length += self._next.length

        return current

    def _token(self) -> Optional[Token]:
            start = self._pos
    
            # 当 Lexer 遇到一个反斜杠 \ 时，它会设置 self.escape = true，表示下一个字符需要被特殊对待。
            if self._escape:
                return self._escaped_token(start)
    
            self._eat_while(lambda c: c not in self._SPECIAL_CHARS)
            # If eat_while actually moved pos...
            if start < self._pos:
                return TextToken(
                    length=self._pos-start,
                )
    
            return self._special_token(start)

    def _escaped_token(self, start: int) -> Optional[Token]:
        self._escape = False
        ch = self._eat_char() # char after \
        if ch is None:
            return None
        
        match ch:
            case '\n': # \\n
                return HardbreakToken(self._pos - start)
            case '\t' | ' ':
                # \'\t' | ' '
                if self._is_next_non_space_newline():
                    while self._eat_char() != '\n':
                        pass
                    return HardbreakToken(self._pos - start)
                else:
                    return NbspToken(self._pos - start)
            case _:
                return TextToken(self._pos - start)

    def _special_token(self, start: int) -> Optional[Token]:

        ch = self._eat_char()
        if ch is None:
            return None

        match ch:
            case '\n':
                return NewlineToken(self._pos - start)

            case '\\':
                # \a -> TokenText(1), TokenText(1)
                # \* -> TokenEscape(1), TokenText(1)
                next_ch = self._peek_char()
                if next_ch is not None and (is_ascii_whitespace(next_ch) or is_ascii_punctuation(next_ch)):
                    self._escape = not self.verbatim
                    return EscapeToken(self._pos - start)
                else:
                    return TextToken(self._pos - start)

            case '[':
                return OpenToken(self._pos - start, Delimiter.BRACKET)

            case ']':
                return CloseToken(self._pos - start, Delimiter.BRACKET)
            
            case '(':
                return OpenToken(self._pos - start, Delimiter.PAREN)
            
            case ')':
                return CloseToken(self._pos - start, Delimiter.PAREN)

            case '{':
                next_ch = self._peek_char()
                if next_ch and next_ch in braced_delimiters:
                    kind = braced_delimiters[next_ch]
                    self._eat_char() # move pos after next_ch
                    return OpenToken(self._pos - start, delimiter=kind)
                
                return OpenToken(self._pos - start, delimiter=Delimiter.BRACE)
    
            case '}':
                return CloseToken(self._pos - start, Delimiter.BRACE)
    
            case '*':
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_ASTERISK)
                else:
                    return SymToken(self._pos - start, SymbolKind.ASTERISK)
    
            case '^':
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_CARET)
                else:
                    return SymToken(self._pos - start, SymbolKind.CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_EQUAL)
                else:
                    return TextToken(self._pos - start)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_PLUS)
                else:
                    return TextToken(self._pos - start, )

            case '~':
                if self._eat_close_brace():
                    return CloseToken(
                        self._pos - start,
                        Delimiter.BRACE_TILDE
                    )
                else:
                    return SymToken(
                        self._pos - start,
                        SymbolKind.TILDE
                    )

            case '_':
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_UNDERSCORE)
                else:
                    return SymToken(self._pos - start, SymbolKind.UNDERSCORE)

            case '\'':
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_QUOTE1)
                else:
                    return SymToken(self._pos - start, SymbolKind.QUOTE1)

            case '"':
                if self._eat_close_brace():
                    return CloseToken(self._pos - start, Delimiter.BRACE_QUOTE2)
                else:
                    return SymToken(self._pos - start, SymbolKind.QUOTE2)

            case '-':
                # -}
                if self._peek_char() == '}':
                    self._eat_char()
                    return CloseToken(self._pos - start, Delimiter.BRACE_HYPHEN)
                else:
                    # --}
                    while self._peek_char() == '-' and self._peek_char(1) != '}': # stop at -} or not -
                        self._eat_char()

                    return SequenceToken(self._pos - start, SeqKind.HYPHEN)

            case '!':
                # ![
                if self._peek_char() == '[':
                    self._eat_char()
                    return SymToken(self._pos - start, SymbolKind.EXCLAIM_BRACKET)
                else:
                    return TextToken(self._pos - start, )

            case '<':
                return SymToken(self._pos - start, SymbolKind.LT)

            case '|':
                return SymToken(self._pos - start, SymbolKind.PIPE)

            case ':':
                return SymToken(self._pos - start, SymbolKind.COLON)

            case '`':
                self._eat_seq(SeqKind.BACKTICK)
                return SequenceToken(self._pos - start, SeqKind.BACKTICK)

            case '.':
                self._eat_seq(SeqKind.PERIOD)
                return SequenceToken(self._pos - start, SeqKind.PERIOD)

            case _:
                return TextToken(self._pos - start, )

    def _is_next_non_space_newline(self) -> bool:
        """检查从当前位置到下一个非空格/制表符的字符是否是换行符"""
        for i in range(self._pos, len(self._src)):
            ch = self._src[i]
            if ch not in (' ', '\t'):
                return ch == '\n'
        return False  # All space after _pos

    def _peek_char(self, n: int = 0) -> Optional[str]:
        idx = self._pos + n
        if idx < len(self._src):
            return self._src[idx]

        return None
    
    def _eat_char(self) -> Optional[str]:
        if self._pos < len(self._src):
            c = self._src[self._pos]
            self._pos += 1
            return c
        return None

    def _eat_while(self, predicate: Callable[[str], bool]):
        c = self._peek_char()
        while c is not None:
            if predicate(c):
                self._eat_char()
                c = self._peek_char()
            else:
                break

    def _eat_seq(self, s: SeqKind):
        self._eat_while(lambda c: c == s.value) # stops after ```

    def _eat_close_brace(self):
        if self._peek_char() == '}':
            self._eat_char()
            return True

        return False

    def __iter__(self):
        return self

    def __next__(self) -> Token:
        if self._next:
            token = self._next
            self._next = None
            return token

        token = self._next_token()
        if token is None:
            raise StopIteration

        return token

