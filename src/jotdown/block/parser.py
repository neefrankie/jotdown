import copy
from dataclasses import dataclass
import itertools
from typing import Iterator, List

from jotdown.common import (
    Range,
)

from .event import (
    Event,
    ListType,
    Alignment,
    Node,
    ContainerNode,
    Document,
    EnterEvent,
    ExitEvent,
    InlineEvent,
    AtomEvent,
    StaleEvent,
)

from .block import (
    meter_block,
    TableToken,
    FencedToken,
)
from .reader import Reader

@dataclass(slots=True)
class OpenList:
    ty_start: ListType
    ty_prev: ListType
    depth: int
    event: int


class TreeParser:
    def __init__(self, src: str):
        self.reader = Reader(src)
        self.prev_blankline: bool = False
        self.prev_loose: bool = False
        self.attr_start: int | None = None
        self.open_lists: List[OpenList]
        self.open_sections: List[int] = []
        self.alignment: List[Alignment] = []
        self.open : List[int] = []
        self.events: List[Event] = []

    def parse(self) -> List[Event]:
        self.enter(ContainerNode(Document()), Range(0, 0))

        lines = list(self.reader.iter_lines())

        line_pos = 0

        while line_pos < len(lines):
            line_count = self.parse_block(lines[line_pos:], True)
            if line_count == 0:
                break

            line_pos += line_count

        return self.events

    def inline(self, span: Range):
        self.events.append(
            Event(
                kind=InlineEvent(),
                span=span,
            )
        )


    def enter(self, node: Node, span: Range) -> int:
        i = len(self.events)
        self.open.append(i)
        self.events.append(
            Event(
                kind=EnterEvent(node),
                span=span,
            )
        )
        return i

    def exit(self, span: Range) -> int:
        i = len(self.events)
        entered_event = self.events[self.open.pop()]
        if not isinstance(entered_event.kind, EnterEvent):
            raise RuntimeError("Unexpected exit")

        self.events.append(
            Event(
                kind=ExitEvent(entered_event.kind.node),
                span=span,
            )
        )
        return i

    def parse_block(self, lines: List[Range], top_level: bool) -> int:
        block = meter_block(self.reader, lines=lines)
        if block is None:
            return 0

        line_count = block.line_count
        lines = lines[:line_count]
        span_start = copy.copy(block.span)
        
        match block.token:
            case TableToken(caption=False, blankline=True):
                lines = self.reader.drop_trailing_empty_lines(lines)

        end_line = lines[-1]

        match block.token:
            case FencedToken(has_closing_fence=True):
                span_end = end_line
            case _:
                span_end = Range(end_line.end, end_line.end)

        
