from dataclasses import dataclass
from enum import Enum, auto
from typing import Union

from jotdown.common import (
    Range,
)

from .list import ListType, ListItemKind

class Alignment(Enum):
    UNSPECFIED = auto()
    LEFT = auto()
    RIGHT = auto()
    CENTER = auto()

class Action(Enum):
    ENTER = auto()
    EXIT = auto()


class AtomKind(Enum):
    BLANKLINE = auto()
    ATTRIBUTES = auto()
    THEMATIC_BREAK = auto()


class LeafKind(Enum):
    PARAGRAPH = auto()
    HEADING = auto()
    DESCRIPTION_TERM = auto()
    TABEL_CELL = auto()
    CAPTION = auto()
    LINK_DEFINITION = auto()
    CODE_BLOCK = auto()

class ContainerKind(Enum):
    DOCUMENT = auto()
    BLOCKQUOTE = auto()
    DIV = auto()
    LIST = auto()
    LIST_ITEM = auto()
    FOOTNOTE = auto()
    TABLE = auto()
    TABLE_ROW = auto()
    SECTION = auto()

class Inline(Enum):
    pass

class Stale(Enum):
    pass

@dataclass(frozen=True, slots=True)
class HeadingPayload:
    level: int
    has_section: bool
    pos: int

@dataclass(slots=True)
class TableCellPayload:
    alignment: Alignment

@dataclass(frozen=True, slots=True)
class LinkDefinitionPayload:
    label: str

@dataclass(frozen=True, slots=True)
class CodeBlockPayload:
    langauge: str

@dataclass(frozen=True, slots=True)
class DivPayload:
    class_name: str

@dataclass(slots=True)
class ListPayload:
    tight: bool
    typ: ListType


@dataclass(frozen=True, slots=True)
class ListItemPayload:
    kind: ListItemKind
    checked: bool

@dataclass(frozen=True, slots=True)
class FootnotePayload:
    label: str

@dataclass(frozen=True, slots=True)
class TableRowPayload:
    head: bool

@dataclass(frozen=True, slots=True)
class SectionPayload:
    pos: int

Payload = Union[
    HeadingPayload,
    TableCellPayload,
    LinkDefinitionPayload,
    CodeBlockPayload,
    DivPayload,
    ListPayload,
    ListItemPayload,
    FootnotePayload,
    TableRowPayload,
    SectionPayload,
]

EventKind = Union[
    AtomKind,
    LeafKind,
    ContainerKind,
    Inline,
    Stale,
]


@dataclass(slots=True)
class Event:
    span: Range
    kind: EventKind
    action: Action | None
    payload: Payload | None = None

    def is_enter_container(self) -> bool:
        return self.action == Action.ENTER and self.kind == ContainerKind

    @classmethod
    def enter(
        cls,
        span: Range,
        kind: LeafKind | ContainerKind,
        payload: Payload | None = None
    ) -> 'Event':
        return cls(span, kind, Action.ENTER, payload)

    @classmethod
    def exit(
        cls,
        span: Range,
        kind: LeafKind | ContainerKind,
        payload: Payload | None = None
    ) -> 'Event':
        return cls(span, kind, Action.EXIT, payload)

    @classmethod
    def atom(cls, span: Range, kind: AtomKind) -> 'Event':
        return cls(span, kind, None)