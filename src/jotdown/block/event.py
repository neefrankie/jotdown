from dataclasses import dataclass
from enum import Enum, auto

from jotdown.common import (
    Range,
)

from .list import (
    OrderedListNumbering,
    OrderedListStyle,
    BulletStyle,
)

class Alignment(Enum):
    UNSPECFIED = auto()
    LEFT = auto()
    RIGHT = auto()
    CENTER = auto()

class AtomKind(Enum):
    BLANKLINE = auto()
    ATTRIBUTES = auto()
    THEMATIC_BREAK = auto()

@dataclass(frozen=True, slots=True)
class Paragraph:
    pass

@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    has_section: bool
    pos: int

@dataclass(frozen=True, slots=True)
class DescriptionTerm:
    pass

@dataclass(frozen=True, slots=True)
class TableCell:
    alignment: Alignment

@dataclass(frozen=True, slots=True)
class Caption:
    pass

@dataclass(frozen=True, slots=True)
class LinkDefinition:
    label: str

@dataclass(frozen=True, slots=True)
class CodeBlock:
    langauge: str

Leaf = (
    Paragraph |
    Heading |
    DescriptionTerm |
    TableCell |
    Caption |
    LinkDefinition |
    CodeBlock
)

@dataclass(frozen=True, slots=True)
class Document:
    pass

@dataclass(frozen=True, slots=True)
class Blockquote:
    pass

@dataclass(frozen=True, slots=True)
class Div:
    class_name: str

@dataclass(frozen=True, slots=True)
class UnorderedList:
    style: BulletStyle

@dataclass(frozen=True, slots=True)
class OrderedList:
    numbering: OrderedListNumbering
    value: int
    style: OrderedListStyle

@dataclass(frozen=True, slots=True)
class TaskList:
    style: BulletStyle

@dataclass(frozen=True, slots=True)
class DescriptionList:
    pass

ListType = (
    UnorderedList |
    OrderedList |
    TaskList |
    DescriptionList
)

@dataclass(frozen=True, slots=True)
class ListContainer:
    tight: bool
    typ: ListType


class ListItemKind(Enum):
    TASK = auto()
    DESCRIPTION = auto()
    LIST = auto()

@dataclass(frozen=True, slots=True)
class ListItem:
    kind: ListItemKind
    checked: bool

@dataclass(frozen=True, slots=True)
class Footnote:
    label: str

@dataclass(frozen=True, slots=True)
class Table:
    pass

@dataclass(frozen=True, slots=True)
class TableRow:
    head: bool

@dataclass(frozen=True, slots=True)
class Section:
    pos: int


Container = (
    Document |
    Blockquote |
    Div |
    ListContainer |
    ListItem |
    Footnote |
    Table |
    TableRow |
    Section
)

@dataclass(frozen=True, slots=True)
class AtomBlock:
    kind: AtomKind

@dataclass(frozen=True, slots=True)
class LeafBlock:
    leaf: Leaf

@dataclass(frozen=True, slots=True)
class ContainerBlock:
    container: Container

Block = (
    AtomBlock |
    LeafBlock |
    ContainerBlock
)

@dataclass(frozen=True, slots=True)
class ContainerNode:
    container: Container

@dataclass(frozen=True, slots=True)
class LeafNode:
    leaf: Leaf

Node = (
    ContainerNode |
    LeafNode
)

@dataclass(frozen=True, slots=True)
class EnterEvent:
    node: Node

@dataclass(frozen=True, slots=True)
class InlineEvent:
    pass

@dataclass(frozen=True, slots=True)
class ExitEvent:
    node: Node

@dataclass(frozen=True, slots=True)
class AtomEvent:
    kind: AtomKind

@dataclass(frozen=True, slots=True)
class StaleEvent:
    pass

EventKind = (
    EnterEvent |
    InlineEvent |
    ExitEvent |
    AtomEvent |
    StaleEvent
)

@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    span: Range

