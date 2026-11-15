from dataclasses import dataclass
from typing import Iterator, List

from jotdown.common import (
    Range,
)

from .event import (
    Event,
    ListType,
    Alignment,
    Node,
    EnterEvent,
    ContainerNode,
    Document,
)

@dataclass(slots=True)
class OpenList:
    ty_start: ListType
    ty_prev: ListType
    depth: int
    event: int


class TreeParser:
    def __init__(self, src: str):
        self.src = src
        self.prev_blankline: bool = False
        self.prev_loose: bool = False
        self.attr_start: int | None = None
        self.open_lists: List[OpenList]
        self.open_sections: List[int] = []
        self.alignment: List[Alignment] = []
        self.open : List[int] = []
        self.events: List[Event] = []

    def iter_lines(self) -> Iterator[Range]:
        if not self.src:
            return
        
        length = len(self.src)

        start = 0
        end = self.src.find('\n', start)
        while end > -1:
            yield Range(
                start=start,
                end=end,
            )
            start = end+1
            end = self.src.find('\n', start)

        # In case the last line is not ended with newline
        if start < length:
            yield Range(
                start=start,
                end=length-1,
            )

    def parse(self) -> List[Event]:
        self.enter(ContainerNode(Document()), Range(0, 0))

        lines = list(self.iter_lines())

        line_pos = 0

        while line_pos < len(lines):
            line_count = 0
            if line_count == 0:
                break

            line_pos += line_count

        return self.events


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
