import copy
from dataclasses import dataclass
from typing import List

from jotdown.common import (
    Range,
)

from .event2 import (
    Alignment,
    Event,
    Action,
    ListPayload,
    LeafKind,
    ContainerKind,
    AtomKind,
)

from .rule import (
    meter_block,
    BaseRule,
    MeteredBlock,
    ListItemRule,
    AtomRule,
    ParaRule,
)
from .reader import Reader
from .list import (
    can_list_continues,
    ListType,
)

@dataclass(slots=True)
class OpenList:
    start_list: ListType
    prev_list: ListType
    depth: int
    event: int


class TreeParser:
    def __init__(self, src: str):
        self.reader = Reader(src)
        # The previous block element was a blank line.
        self.prev_blankline: bool = False
        self.prev_loose: bool = False
        self.attr_start: int | None = None
        # Stack of currently open lists.
        self.open_lists: List[OpenList]
        self.open_sections: List[int] = []
        # Alignments for each column in for the current table.
        self.alignment: List[Alignment] = []
        # Current container depth.
        self.open: List[int] = []
        # Buffer queue for next events. Events are buffered until no modifications due to future
        #  characters are needed.
        self.events: List[Event] = []

    def parse(self) -> List[Event]:
        self.enter(ContainerKind.DOCUMENT, Range(0, 0))

        lines = list(self.reader.iter_lines())

        line_pos = 0

        while line_pos < len(lines):
            line_count = self.parse_block(lines[line_pos:], True)
            if line_count == 0:
                break

            line_pos += line_count

        return self.events


    def enter(self, kind: ContainerKind | LeafKind, span: Range) -> int:
        i = len(self.events)
        self.open.append(i)
        self.events.append(
            Event.enter(
                span=span,
                kind=kind,
            )
        )
        return i

    def on_exit(self, span: Range):
        i = len(self.events)
        event = self.events[self.open.pop()]
        if event.kind != Action.ENTER:
            raise Exception("Invalid event")

        self.events.append(
            Event(
                span=span,
                kind=event.kind,
                action=Action.EXIT,
                payload=event.payload
            )
        )

        return i

    def parse_block(self, lines: List[Range], top_level: bool) -> int:
        """
        Args:
            lines (List[Range]): from first line of current block to EOF.
        """
        block = meter_block(self.reader, lines=lines)
        if block is None:
            return 0

        # lines for current block
        lines, line_count = block.locate_lines(self.reader, lines)
        
        start_span = copy.copy(block.span) # block start token
        end_line = block.find_end_span(lines)

        block.adjust_line_start(self.reader, lines)

        lines = block.skip_fence_border(lines)

        # close list if a non list item or a list item of new type appeared
        if self.open_lists:
            last_list = self.open_lists[-1]
            assert last_list.depth <= len(self.open)
            # If opened container is the same as list depth.
            if len(self.open) == last_list.depth:
                can_continue = self.continue_list(last_list, block.rule)
                if not can_continue:
                    last_list = self.open_lists.pop()
                    self.close_list(last_list, start_span.start)

        self.set_loose_list(block)

        match block.rule:
            case AtomRule(kind=kind):
                assert isinstance(block.rule, AtomRule)
                self.events.append(
                    Event.atom(
                        copy.copy(start_span),
                        kind,
                    )
                )
            case ParaRule():
                pass

        return line_count
                

    def set_loose_list(self, block: MeteredBlock):
        """
        set list to loose if blankline discovered

        - Item 1

        - Item 2
        """
        match block.rule:
            case AtomRule(kind=AtomKind.BLANKLINE):
                self.prev_blankline = True
                return

            case _:
                self.prev_loose = False

                if self.prev_blankline:
                    last_list = self.open_lists.pop() if self.open_lists else None
                    if last_list is not None:
                        if (
                            last_list.depth >= len(self.open) or 
                            not isinstance(block.rule, ListItemRule)
                        ):
                            event = self.events[last_list.event]
                            if (
                                event.is_enter_container()
                                and isinstance(event.payload, ListPayload)
                            ):
                                if event.payload.tight:
                                    self.prev_loose = True
                                    event.payload.tight = False

                self.prev_blankline = False
                        



    def continue_list(self, last_list: OpenList, rule: BaseRule) -> bool:
        match rule:
            case ListItemRule(detail=new_list):
                alternatives = can_list_continues(
                    last_list.prev_list,
                    new_list
                )
                if not alternatives:
                    return False

                prev_list_res, new_list_res = alternatives

                if last_list.start_list == last_list.prev_list:
                    last_list.start_list = prev_list_res

                last_list.prev_list = new_list_res

                return True
            
            case _:
                return False

    def close_list(self, open_list: OpenList, pos: int):
        event = self.events[open_list.event]
        match event.payload:
            case ListPayload():
                if self.prev_loose:
                    event.payload.tight = True

                event.payload.typ = open_list.start_list
            case _:
                raise Exception("Invalid payload")

        self.on_exit(Range(pos, pos))

                

        



        
