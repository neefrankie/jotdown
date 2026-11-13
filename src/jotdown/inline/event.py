from abc import ABC
from dataclasses import dataclass

from .element import Atom, Container

@dataclass(slots=True)
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

    
@dataclass(slots=True)
class EventKind(ABC):
    pass

@dataclass(slots=True)
class EnterEvent(EventKind):
    container: Container

@dataclass(slots=True)
class ExitEvent(EventKind):
    container: Container

@dataclass(slots=True)
class AtomEvent(EventKind):
    atom: Atom

@dataclass(slots=True)
class StrEvent(EventKind):
    pass

@dataclass(slots=True)
class EmptyEvent(EventKind):
    pass

@dataclass
class AttrbutesEvent(EventKind):
    container: bool
    attrs_index: int

@dataclass(slots=True)
class PlaceholderEvent(EventKind):
    pass

@dataclass(slots=True)
class Event:
    kind: EventKind
    span: Range

    @property
    def is_str(self) -> bool:
        return isinstance(self.kind, StrEvent)