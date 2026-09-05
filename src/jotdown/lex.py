from dataclasses import dataclass
from enum import Enum, StrEnum, auto
import string
from typing import Callable, Optional


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

class TokenKind:
    """基类，所有 Token 类型继承自它"""
    pass

@dataclass
class KindText(TokenKind): pass

@dataclass
class KindNewline(TokenKind): pass

@dataclass
class KindNbsp(TokenKind): pass

@dataclass
class KindHardbreak(TokenKind): pass

@dataclass
class KindEscape(TokenKind): pass

# 带额外信息的类型
@dataclass
class KindOpen(TokenKind):
    delimiter: 'Delimiter'

@dataclass
class KindClose(TokenKind):
    delimiter: 'Delimiter'

@dataclass
class KindSym(TokenKind):
    symbol: 'Symbol'

@dataclass
class KindSeq(TokenKind):
    sequence: 'Sequence'

@dataclass
class Span:
    start: int
    end: int

@dataclass
class Token:
    kind: TokenKind
    text: str
    span: Span

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
        For python this might not be needed.
        """
        start = self._next.span.start if self._next else self._pos
        return self._src[start:]

    def skip_ahead(self, n: int):
        self._pos += n
        self._next = None

    def _next_token(self) -> Optional[Token]:
        current = self._token()
        if current is None:
            return None

        # Concatenate continuous string.
        if isinstance(current.kind, KindText):
            self._next = self._token()
            while self._next and isinstance(self._next.kind, KindText):
                current.span.end = self._next.span.end
                self._next = self._token()

        return current

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

    def _token(self) -> Optional[Token]:
        start = self._pos

        # 当 Lexer 遇到一个反斜杠 \ 时，它会设置 self.escape = true，表示下一个字符需要被特殊对待。
        if self._escape:
            self._escape = False
            ch = self._eat_char()
            if ch is None:
                return None
            kind = self._handle_escaped(ch)
            return Token(
                kind=kind,
                text=self._src[start:self._pos],
                span=Span(start, self._pos)
            )

        self._eat_while(lambda c: c not in self._SPECIAL_CHARS)
        # If eat_while actually moved pos...
        if start < self._pos:
            return Token(
                kind=KindText(),
                text=self._src[start:self._pos],
                span=Span(start, self._pos),
            )

        ch = self._eat_char()
        if ch is None:
            return None
        kind = self._handle_special(ch)
        return Token(
            kind=kind,
            text=self._src[start:self._pos],
            span=Span(start, self._pos)
        )

    def _handle_escaped(self, ch: str) -> TokenKind:
        match ch:
            case '\n': # \\n
                return KindHardbreak()
            case '\t' | ' ':
                # \'\t' | ' '
                if self._is_next_non_space_newline():
                    while self._eat_char() != '\n':
                        pass
                    return KindHardbreak()
                else:
                    return KindNbsp()
            case _:
                return KindText()

    def _is_next_non_space_newline(self) -> bool:
        """检查从当前位置到下一个非空格/制表符的字符是否是换行符"""
        for i in range(self._pos, len(self._src)):
            ch = self._src[i]
            if ch not in (' ', '\t'):
                return ch == '\n'
        return False  # All space after _pos

    def _handle_special(self, ch: str) -> TokenKind:
        match ch:
            case '\n':
                return KindNewline()

            case '\\':
                next_ch = self._peek_char()
                if next_ch is not None and (next_ch.isascii() and (next_ch.isspace() or next_ch in string.punctuation)):
                    self._escape = not self.verbatim
                    return KindEscape()
                else:
                    return KindText()

            case '[':
                return KindOpen(Delimiter.BRACKET)

            case ']':
                return KindClose(Delimiter.BRACKET)
            
            case '(':
                return KindOpen(Delimiter.PAREN)
            
            case ')':
                return KindClose(Delimiter.PAREN)

            case '{':
                brace_mapping = {
                    '*': KindOpen(Delimiter.BRACE_ASTERISK), # strong
                    '^': KindOpen(Delimiter.BRACE_CARET), # superscript
                    '=': KindOpen(Delimiter.BRACE_EQUAL), # highlighed
                    '-': KindOpen(Delimiter.BRACE_HYPHEN), # delete
                    '+': KindOpen(Delimiter.BRACE_PLUS), # insert
                    '~': KindOpen(Delimiter.BRACE_TILDE), # subscript
                    '_': KindOpen(Delimiter.BRACE_UNDERSCORE), # emphasis
                    '\'': KindOpen(Delimiter.BRACE_QUOTE1),
                    '"': KindOpen(Delimiter.BRACE_QUOTE2),
                }
                next_ch = self._peek_char()
                if next_ch and next_ch in brace_mapping:
                    kind = brace_mapping[next_ch]
                    self._eat_char() # move pos after next_ch
                    return kind
                
                return KindOpen(Delimiter.BRACE)
    
            case '}':
                return KindClose(Delimiter.BRACE)
    
            case '*':
                return self._maybe_eat_close_brace(KindSym(Symbol.ASTERISK), Delimiter.BRACE_ASTERISK)
    
            case '^':
                return self._maybe_eat_close_brace(KindSym(Symbol.CARET), Delimiter.BRACE_CARET)
    
            case '=':
                # If it is =}, it is highlighted; otherwise plain text.
                return self._maybe_eat_close_brace(KindText(), Delimiter.BRACE_EQUAL)
    
            case '+':
                # If it is +}, this is insert; otherwise plain text.
                return self._maybe_eat_close_brace(KindText(), Delimiter.BRACE_PLUS)

            case '~':
                return self._maybe_eat_close_brace(KindSym(Symbol.TILDE), Delimiter.BRACE_TILDE)

            case '_':
                return self._maybe_eat_close_brace(KindSym(Symbol.UNDERSCORE), Delimiter.BRACE_UNDERSCORE)

            case '\'':
                return self._maybe_eat_close_brace(KindSym(Symbol.QUOTE1), Delimiter.BRACE_QUOTE1)

            case '"':
                return self._maybe_eat_close_brace(KindSym(Symbol.QUOTE2), Delimiter.BRACE_QUOTE2)

            case '-':
                # -}
                if self._peek_char() == '}':
                    self._eat_char()
                    return KindClose(Delimiter.BRACE_HYPHEN)
                else:
                    # --}
                    while self._peek_char() == '-' and self._peek_char(1) != '}':
                        self._eat_char()

                    return KindSeq(Sequence.HYPHEN)

            case '!':
                # ![
                if self._peek_char() == '[':
                    self._eat_char()
                    return KindSym(Symbol.EXCLAIM_BRACKET)
                else:
                    return KindText()

            case '<':
                return KindSym(Symbol.LT)

            case '|':
                return KindSym(Symbol.PIPE)

            case ':':
                return KindSym(Symbol.COLON)

            case '`':
                return self._eat_seq(Sequence.BACKTICK)

            case '.':
                return self._eat_seq(Sequence.PERIOD)

            case _:
                return KindText()

    def _eat_seq(self, s: Sequence) -> TokenKind:
        self._eat_while(lambda c: c == s.value)
        return KindSeq(s)

    def _maybe_eat_close_brace(self, kind: TokenKind, d: Delimiter) -> TokenKind:
        if self._peek_char() == '}':
            self._eat_char()
            return KindClose(d)

        return kind

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

