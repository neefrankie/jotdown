from abc import ABC
from dataclasses import dataclass
from enum import Enum, StrEnum, auto


class Delimiter(Enum):
    BRACE = auto() # {
    BRACE_ASTERISK = auto() # {*, strong
    BRACE_CARET = auto() # {^, superscript
    BRACE_EQUAL = auto() # {=, highlighted
    BRACE_HYPHEN = auto() # {-, delete
    BRACE_PLUS = auto() # {+, insert
    BRACE_TILDE = auto() # {~, subscript
    BRACE_UNDERSCORE = auto() # {_, epmhasis
    BRACKET = auto() # [
    BRACE_QUOTE1 = auto() # {'
    BRACE_QUOTE2 = auto() # {"
    PAREN = auto() # (

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

class SymbolKind(Enum):
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

class SeqKind(StrEnum):
    BACKTICK = '`'
    HYPHEN = '-'
    PERIOD = '.'


@dataclass
class Token(ABC):
    length: int

@dataclass
class TextToken(Token):
    pass

@dataclass
class NewlineToken(Token):
    pass

@dataclass
class NbspToken(Token):
    pass

@dataclass
class HardbreakToken(Token):
    pass

@dataclass
class EscapeToken(Token):
    pass

@dataclass
class DelimiterToken(Token, ABC):
    delimiter: Delimiter

    @property
    def is_brace(self):
        return self.delimiter == Delimiter.BRACE

@dataclass
class OpenToken(DelimiterToken):
    pass

@dataclass
class CloseToken(DelimiterToken):
    pass

@dataclass
class SymToken(Token):
    symbol: SymbolKind

@dataclass
class SequenceToken(Token):
    sequence: SeqKind

    @property
    def is_backtick(self) -> bool:
        return self.sequence == SeqKind.BACKTICK