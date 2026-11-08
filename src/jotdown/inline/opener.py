from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from jotdown.lex.lex import (
    Token,
    Delimiter,
    OpenToken,
    CloseToken,
    SymToken,
    SymbolKind,
)

class Directionality(Enum):
    UNI = auto()
    BI = auto()

class SpanType(Enum):
    IMAGE = auto()
    GENERAL = auto()

class Opener(ABC):

    @abstractmethod
    def close_by(self, tok: Token) -> bool:
        pass

@dataclass
class SpanOpener(Opener):
    """
    [read the manual]{.big .red}
    """
    typ: SpanType

    def close_by(self, tok: Token) -> bool:
        match tok:
            case CloseToken(delimiter=Delimiter.BRACKET): # ]
                return True
            case _:
                return False

@dataclass
class DirectionalOpener(Opener, ABC):
    direction: Directionality

    def bidirectional(self) -> bool:
        return self.direction == Directionality.BI

@dataclass
class StrongOpener(DirectionalOpener):
    """
    * or {*
    """

    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.ASTERISK) if self.direction == Directionality.BI: # *
                return True
            case CloseToken(delimiter=Delimiter.BRACE_ASTERISK) if self.direction == Directionality.UNI: # *}
                return True

            case _:
                return False

@dataclass
class EmphasisOpener(DirectionalOpener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.UNDERSCORE) if self.direction == Directionality.BI: # _
                return True
            case CloseToken(delimiter=Delimiter.BRACE_UNDERSCORE) if self.direction == Directionality.UNI: # _}
                return True
    
            case _:
                return False

@dataclass
class SuperscriptOpener(DirectionalOpener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.CARET) if self.direction == Directionality.BI: # ^
                return True
            case CloseToken(delimiter=Delimiter.BRACE_CARET) if self.direction == Directionality.UNI: # ^}
                return True
    
            case _:
                return False

@dataclass
class SubscriptOpener(DirectionalOpener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.TILDE) if self.direction == Directionality.BI: # ~
                return True
            case CloseToken(delimiter=Delimiter.BRACE_TILDE) if self.direction == Directionality.UNI: # ~}
                return True
    
            case _:
                return False

@dataclass
class MarkOpener(Opener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case CloseToken(delimiter=Delimiter.BRACE_EQUAL): # =}
                return True
    
            case _:
                return False

@dataclass
class DeleteOpener(Opener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case CloseToken(delimiter=Delimiter.BRACE_HYPHEN): # -}
                return True
    
            case _:
                return False

@dataclass
class InsertOpener(Opener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case CloseToken(delimiter=Delimiter.BRACE_PLUS): # +}
                return True
    
            case _:
                return False

@dataclass
class SingleQuotedOpener(Opener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.QUOTE1) | CloseToken(delimiter=Delimiter.BRACE_QUOTE1): # ' or '}
                return True
    
            case _:
                return False

@dataclass
class DoubleQuotedOpener(Opener):
    def close_by(self, tok: Token) -> bool:
        match tok:
            case SymToken(symbol=SymbolKind.QUOTE2) | CloseToken(delimiter=Delimiter.BRACE_QUOTE2): # " or "}
                return True
    
            case _:
                return False

@dataclass
class LinkOpener(Opener):
    event_span: int
    image: bool
    inline: bool

    def close_by(self, tok: Token) -> bool:
        match tok:
            case CloseToken(delimiter=Delimiter.BRACKET) if not self.inline: 
                return True
            case CloseToken(delimiter=Delimiter.PAREN) if self.inline:
                return True
    
            case _:
                return False

def opener_from_token(tok: Token) -> Optional[Opener]:
    match tok:
        case SymToken(symbol=SymbolKind.ASTERISK): # *
            return StrongOpener(Directionality.BI)
        case SymToken(symbol=SymbolKind.UNDERSCORE): # _
            return EmphasisOpener(Directionality.BI)
        case SymToken(symbol=SymbolKind.CARET): # ^
            return SuperscriptOpener(Directionality.BI)
        case SymToken(symbol=SymbolKind.TILDE): # ~
            return SubscriptOpener(Directionality.BI)
        case SymToken(symbol=SymbolKind.QUOTE1): # '
            return SingleQuotedOpener()
        case SymToken(symbol=SymbolKind.QUOTE2): # "
            return DoubleQuotedOpener()
        case SymToken(symbol=SymbolKind.EXCLAIM_BRACKET): # ![
            return SpanOpener(SpanType.IMAGE)
        case OpenToken(delimiter=Delimiter.BRACKET): # [
            # [read the manaual]{.big .red}
            return SpanOpener(SpanType.GENERAL)
        case OpenToken(delimiter=Delimiter.BRACE_ASTERISK): # {*
            return StrongOpener(Directionality.UNI)
        case OpenToken(delimiter=Delimiter.BRACE_UNDERSCORE): # {-
            return EmphasisOpener(Directionality.UNI)
        case OpenToken(delimiter=Delimiter.BRACE_CARET): # {^
            return SuperscriptOpener(Directionality.UNI)
        case OpenToken(delimiter=Delimiter.BRACE_TILDE): # {~
            return SubscriptOpener(Directionality.UNI)
        case OpenToken(delimiter=Delimiter.BRACE_EQUAL): # {=
            return MarkOpener()
        case OpenToken(delimiter=Delimiter.BRACE_HYPHEN): # {-
            return DeleteOpener()
        case OpenToken(delimiter=Delimiter.BRACE_PLUS): # {+
            return InsertOpener()
        case OpenToken(delimiter=Delimiter.BRACE_QUOTE1): # {'
            return SingleQuotedOpener()
        case OpenToken(delimiter=Delimiter.BRACE_QUOTE2): # {"
            return DoubleQuotedOpener()