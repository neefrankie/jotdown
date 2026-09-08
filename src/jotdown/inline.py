from abc import ABC
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

from .lex import Lexer

class QuoteType(Enum):
    SINGLE = auto()
    DOUBLE = auto()

class Atom(ABC):
    pass

@dataclass
class FootnoteReference(Atom):
    label: str

@dataclass
class Symbol(Atom):
    s: str

@dataclass
class Softbreak(Atom):
    pass

@dataclass
class Hardbreak(Atom):
    pass

@dataclass
class Escape(Atom):
    pass

@dataclass
class Nbsp(Atom):
    pass

@dataclass
class Ellipsis(Atom):
    pass

@dataclass
class EnDash(Atom):
    pass

@dataclass
class EmDash(Atom):
    pass

@dataclass
class Quote(Atom):
    ty: QuoteType
    left: bool

class Container(ABC):
    pass

@dataclass
class SpanBox(Container):
    pass

@dataclass
class Subscript(Container):
    pass

@dataclass
class Superscript(Container):
    pass

@dataclass
class Insert(Container):
    pass

@dataclass
class Delete(Container):
    pass

@dataclass
class Emphasis(Container):
    pass

@dataclass
class Strong(Container):
    pass

@dataclass
class Mark(Container):
    pass

@dataclass
class Verbbatim(Container):
    pass

@dataclass
class RawFormat(Container):
    format: str

@dataclass
class InlineMath(Container):
    pass

@dataclass
class DisplayMath(Container):
    pass

@dataclass
class ReferenceLink(Container):
    index: int

@dataclass
class ReferenceImage(Container):
    index: int

@dataclass
class InlineLink(Container):
    index: int

@dataclass
class inlineImage(Container):
    index: int

@dataclass
class AutoLink(Container):
    index: int

@dataclass
class Event:
    start: int
    end: int
    pass

@dataclass
class EventEnter(Event):
    container: Container

@dataclass
class EventExit(Event):
    container: Container

@dataclass
class EventAtom(Event):
    atom: Atom

@dataclass
class EventStr(Event):
    pass

@dataclass
class EventEmpty(Event):
    pass

@dataclass
class EventAttributes(Event):
    container: bool
    attrs_index: int

@dataclass
class Range:
    start: int
    end: int

class Input:
    def __init__(self, src: str):
        self.src = src
        self.lexer = Lexer("")
        self.complete: bool = False
        self.span_line: Range = Range(0, 0)
        self.ahead: deque[Range] = deque()
        self.span: Range = Range(0, 0)
        
        