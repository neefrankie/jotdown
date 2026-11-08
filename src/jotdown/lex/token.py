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


@dataclass(slots=True)
class Token(ABC):
    length: int

@dataclass(slots=True)
class TextToken(Token):
    pass

@dataclass(slots=True)
class NewlineToken(Token):
    pass

@dataclass(slots=True)
class NbspToken(Token):
    pass

@dataclass(slots=True)
class HardbreakToken(Token):
    pass

@dataclass(slots=True)
class EscapeToken(Token):
    pass

@dataclass(slots=True)
class DelimiterToken(Token, ABC):
    delimiter: Delimiter

    @property
    def is_brace(self) -> bool:
        return self.delimiter == Delimiter.BRACE

    @property
    def is_brace_equal(self) -> bool:
        return self.delimiter == Delimiter.BRACE_EQUAL

    @property
    def is_bracket(self) -> bool:
        return self.delimiter == Delimiter.BRACKET

@dataclass(slots=True)
class OpenToken(DelimiterToken):
    pass

@dataclass(slots=True)
class CloseToken(DelimiterToken):
    pass

@dataclass(slots=True)
class SymToken(Token):
    symbol: SymbolKind

    @property
    def is_less_than(self):
        return self.symbol == SymbolKind.LT

    @property
    def is_colon(self):
        return self.symbol == SymbolKind.COLON

    @property
    def is_caret(self):
        return self.symbol == SymbolKind.CARET

@dataclass(slots=True)
class SequenceToken(Token):
    sequence: SeqKind

    @property
    def is_backtick(self) -> bool:
        return self.sequence == SeqKind.BACKTICK