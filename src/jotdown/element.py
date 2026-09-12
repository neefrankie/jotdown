from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto


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

# === Verbatim has 4 variants
@dataclass
class Verbatim(Container):
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

def ensure_verbatim(container: Container) -> bool:
    return (isinstance(container, Verbatim) or 
            isinstance(container, RawFormat) or 
            isinstance(container, InlineMath) or 
            isinstance(container, DisplayMath))

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