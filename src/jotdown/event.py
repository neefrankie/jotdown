from abc import ABC
from dataclasses import dataclass

from .element import Atom, Container

@dataclass
class Range:
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start

    def is_empty(self) -> bool:
        return self.start >= self.end

    def contains(self, pos: int) -> bool:
        return self.start <= pos < self.end

    def to_slice(self) -> slice:
        return slice(self.start, self.end)

    
@dataclass
class EventKind(ABC):
    pass

@dataclass
class EventKindEnter(EventKind):
    container: Container

@dataclass
class EventKindExit(EventKind):
    container: Container

@dataclass
class EventKindAtom(EventKind):
    atom: Atom

@dataclass
class EventKindStr(EventKind):
    pass

@dataclass
class EventKindEmpty(EventKind):
    pass

@dataclass
class EventKindAttrs(EventKind):
    container: bool
    attrs_index: int

@dataclass
class EventKindPlaceholder(EventKind):
    pass

@dataclass
class Event:
    kind: EventKind
    span: Range

    @property
    def is_str(self) -> bool:
        return isinstance(self.kind, EventKindStr)