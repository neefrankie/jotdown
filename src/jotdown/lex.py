from abc import ABC
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import Callable, Optional

from .utils import (
    is_ascii_whitespace,
    is_ascii_punctuation,
)


class Delimiter(Enum):
    BRACE = auto() # {
    BRACE_ASTERISK = auto() # {*
    BRACE_CARET = auto() # {^
    BRACE_EQUAL = auto() # {=
    BRACE_HYPHEN = auto() # {-
    BRACE_PLUS = auto() # {+
    BRACE_TILDE = auto() # {~
    BRACE_UNDERSCORE = auto() # {_
    BRACKET = auto() # [
    BRACE_QUOTE1 = auto() # {'
    BRACE_QUOTE2 = auto() # {"
    PAREN = auto() # (

class Symbol(Enum):
    ASTERISK = auto() # *
    CARET = auto() # ^
    EXCLAIM_BRACKET = auto() # ![
    LT = auto() # <
    PIPE = auto() # |
    QUOTE1 = auto() # '
    QUOTE2 = auto() # "
    TILDE = auto() # ~
    UNDERSCORE = auto() # _
    COLON = auto() # :

class Sequence(StrEnum):
    BACKTICK = '`'
    HYPHEN = '-'
    PERIOD = '.'


@dataclass
class Token(ABC):
    length: int

@dataclass
class TokenText(Token):
    pass

@dataclass
class TokenNewline(Token):
    pass

@dataclass
class TokenNbsp(Token):
    pass

@dataclass
class TokenHardbreak(Token):
    pass

@dataclass
class TokenEscape(Token):
    pass

@dataclass
class TokenOpen(Token):
    delimiter: Delimiter

@dataclass
class TokenClose(Token):
    delimiter: Delimiter

@dataclass
class TokenSym(Token):
    symbol: Symbol

@dataclass
class TokenSeq(Token):
    sequence: Sequence

class Lexer:

    _SPECIAL_CHARS = set('\\[](){}*^=+~_\'"-!<|:`.\n')

    def __init__(self, src: str):
        self._src: str = src
        self._pos: int = 0
        self._escape: bool = False
        self._next: Optional[Token] = None
        self.verbatim: bool = False

    def peek(self) -> Optional[Token]:
        if self._next is None:
            self._next = self._token()
        return self._next

    def ahead(self) -> str:
        """
        The slice from the start of of token being parsed to the end of the string.
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
        if isinstance(current, TokenText):
            while True:
                self._next = self._token()
                if self._next is None or not isinstance(self._next, TokenText):
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
                return TokenText(
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
                return TokenHardbreak(self._pos - start)
            case '\t' | ' ':
                # \'\t' | ' '
                if self._is_next_non_space_newline():
                    while self._eat_char() != '\n':
                        pass
                    return TokenHardbreak(self._pos - start)
                else:
                    return TokenNbsp(self._pos - start)
            case _:
                return TokenText(self._pos - start)

    def _special_token(self, start: int) -> Optional[Token]:

        ch = self._eat_char()
        if ch is None:
            return None

        match ch:
            case '\n':
                return TokenNewline(self._pos - start)

            case '\\':
                # \a -> TokenText(1), TokenText(1)
                # \* -> TokenEscape(1), TokenText(1)
                next_ch = self._peek_char()
                if next_ch is not None and (is_ascii_whitespace(next_ch) or is_ascii_punctuation(next_ch)):
                    self._escape = not self.verbatim
                    return TokenEscape(self._pos - start)
                else:
                    return TokenText(self._pos - start)

            case '[':
                return TokenOpen(self._pos - start, Delimiter.BRACKET)

            case ']':
                return TokenClose(self._pos - start, Delimiter.BRACKET)
            
            case '(':
                return TokenOpen(self._pos - start, Delimiter.PAREN)
            
            case ')':
                return TokenClose(self._pos - start, Delimiter.PAREN)

            case '{':
                brace_mapping = {
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
                next_ch = self._peek_char()
                if next_ch and next_ch in brace_mapping:
                    kind = brace_mapping[next_ch]
                    self._eat_char() # move pos after next_ch
                    return TokenOpen(self._pos - start, delimiter=kind)
                
                return TokenOpen(self._pos - start, delimiter=Delimiter.BRACE)
    
            case '}':
                return TokenClose(self._pos - start, Delimiter.BRACE)
    
            case '*':
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_ASTERISK)
                else:
                    return TokenSym(self._pos - start, Symbol.ASTERISK)
    
            case '^':
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_CARET)
                else:
                    return TokenSym(self._pos - start, Symbol.CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_EQUAL)
                else:
                    return TokenText(self._pos - start)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_PLUS)
                else:
                    return TokenText(self._pos - start, )

            case '~':
                if self._eat_close_brace():
                    return TokenClose(
                        self._pos - start,
                        Delimiter.BRACE_TILDE
                    )
                else:
                    return TokenSym(
                        self._pos - start,
                        Symbol.TILDE
                    )

            case '_':
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_UNDERSCORE)
                else:
                    return TokenSym(self._pos - start, Symbol.UNDERSCORE)

            case '\'':
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_QUOTE1)
                else:
                    return TokenSym(self._pos - start, Symbol.QUOTE1)

            case '"':
                if self._eat_close_brace():
                    return TokenClose(self._pos - start, Delimiter.BRACE_QUOTE2)
                else:
                    return TokenSym(self._pos - start, Symbol.QUOTE2)

            case '-':
                # -}
                if self._peek_char() == '}':
                    self._eat_char()
                    return TokenClose(self._pos - start, Delimiter.BRACE_HYPHEN)
                else:
                    # --}
                    while self._peek_char() == '-' and self._peek_char(1) != '}': # stop at -} or not -
                        self._eat_char()

                    return TokenSeq(self._pos - start, Sequence.HYPHEN)

            case '!':
                # ![
                if self._peek_char() == '[':
                    self._eat_char()
                    return TokenSym(self._pos - start, Symbol.EXCLAIM_BRACKET)
                else:
                    return TokenText(self._pos - start, )

            case '<':
                return TokenSym(self._pos - start, Symbol.LT)

            case '|':
                return TokenSym(self._pos - start, Symbol.PIPE)

            case ':':
                return TokenSym(self._pos - start, Symbol.COLON)

            case '`':
                self._eat_seq(Sequence.BACKTICK)
                return TokenSeq(self._pos - start, Sequence.BACKTICK)

            case '.':
                self._eat_seq(Sequence.PERIOD)
                return TokenSeq(self._pos - start, Sequence.PERIOD)

            case _:
                return TokenText(self._pos - start, )

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

    def _eat_seq(self, s: Sequence):
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

