from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, NamedTuple

from jotdown.common import (
    Range,
)
from .list import (
    BulletStyle,
    ListType,
    TaskList,
    UnorderedList,
    DescriptionList,
    maybe_ordered_list_item,
)

from .reader import (
    Reader,
    is_valid_name,
    is_vaild_lang,
)
from .heading import (
    parse_heading,
)
from .event2 import (
    AtomKind,
)

class BlockCap(Enum):
    ATOM = auto()
    LEAF = auto()
    CONTAINER = auto()

@dataclass(slots=True)
class BaseRule(ABC):

    @property
    @abstractmethod
    def cap(self) -> BlockCap:
        pass

    @abstractmethod
    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        pass


@dataclass(slots=True)
class AtomRule(BaseRule):
    kind: AtomKind

    @property
    def cap(self) -> BlockCap:
        return BlockCap.ATOM

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        return False

def is_blankline(rule: BaseRule):
    return isinstance(rule, AtomRule) and rule.kind == AtomKind.BLANKLINE

@dataclass(slots=True)
class ParaRule(BaseRule):
    @property
    def cap(self) -> BlockCap:
        return BlockCap.LEAF

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        return not reader.is_empty(next_line)

@dataclass(slots=True)
class HeadingRule(BaseRule):
    level: int

    @property
    def cap(self) -> BlockCap:
        return BlockCap.LEAF

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        new_block = identify_block(reader, next_line)
        if new_block is None:
            return False

        match new_block.rule:
            case ParaRule():
                return True
            case HeadingRule(level=level):
                return level == self.level

        return False

class NestedRaw(NamedTuple):
    border_char: str
    fence_length: int

@dataclass(slots=True)
class Fenced:
    indent: int
    fence_length: int
    border_char: str
    spec: str # lang part
    has_closing_fence: bool = False

    def is_closing_raw(self, raw: NestedRaw) -> bool:
        return (
            self.border_char == raw.border_char
            and
            self.fence_length >= raw.fence_length
            and
            len(self.spec) == 0
        )

    def is_closing(self, opener: 'Fenced') -> bool:
        return (
            self.border_char == opener.border_char
            and
            self.fence_length >= opener.fence_length
            and
            len(self.spec) == 0
        )

    def has_same_border(self, other_border: str) -> bool:
        return self.border_char == other_border
    

    def verify_closing(self, other: 'Fenced'):
        self.has_closing_fence = (
            self.border_char == other.border_char
            and
            self.fence_length >= other.fence_length 
            and
            len(self.spec) == 0
        )


@dataclass(slots=True)
class CodeBlockRule(BaseRule, Fenced):

    @property
    def cap(self) -> BlockCap:
        return BlockCap.LEAF

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        new_frame = identify_block(reader, next_line)
        
        if isinstance(new_frame.rule, Fenced):
            self.has_closing_fence = new_frame.rule.is_closing(self)

        return True


@dataclass(slots=True)
class DivRule(BaseRule, Fenced):
    nested_raw: NestedRaw | None = None # indicates we are inside a code block. Any ::: should be taken literally.

    @property
    def cap(self) -> BlockCap:
        return BlockCap.CONTAINER

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        new_frame = identify_block(reader, next_line)
        
        if isinstance(new_frame.rule, Fenced):
            if self.nested_raw is not None: # enclosing a clode block
                if new_frame.rule.is_closing_raw(self.nested_raw):
                    self.nested_raw = None

            elif new_frame.rule.has_same_border(self.border_char):
                # only close when not inside a code block.
                self.has_closing_fence = new_frame.rule.is_closing(self)

            elif isinstance(new_frame.rule, CodeBlockRule): # start clode block inside div
                self.nested_raw = NestedRaw(
                    border_char=new_frame.rule.border_char,
                    fence_length=new_frame.rule.fence_length
                )

        return True

    

@dataclass(slots=True)
class DefinitionData:
    indent: int
    footnote: bool
    label: str
    last_blankline: bool

@dataclass(slots=True)
class LinkDefRule(BaseRule, DefinitionData):

    @property
    def cap(self) -> BlockCap:
        return BlockCap.LEAF

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        blankline = reader.is_empty(next_line)
        return (
            reader.char_at(next_line.start) == ' '
            and not blankline
        )

@dataclass(slots=True)
class FootnoteRule(BaseRule, DefinitionData):

    @property
    def cap(self) -> BlockCap:
        return BlockCap.CONTAINER

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        next_block = identify_block(reader, next_line)
        if next_block is None:
            return False

        whitespace = reader.left_strip(next_line)
        cont_para = (
            not self.last_blankline
            and isinstance(next_block.rule, ParaRule)
        )

        self.last_blankline = is_blankline(next_block.rule)

        return (
            whitespace > self.indent 
            or self.last_blankline 
            or cont_para
        )

@dataclass(slots=True)
class BlockquoteRule(BaseRule):
    @property
    def cap(self) -> BlockCap:
        return BlockCap.CONTAINER

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        new_block = identify_block(reader, next_line)
        if new_block is None:
            return False

        match new_block.rule:
            case BlockquoteRule() | ListItemRule():
                return True

        return False

@dataclass(slots=True)
class ListItemRule(BaseRule):
    indent: int
    detail: ListType
    last_blankline: bool
    
    @property
    def cap(self) -> BlockCap:
        return BlockCap.CONTAINER

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        whitespace = reader.left_strip(next_line)
        next_block = identify_block(reader, next_line)

        para = (not self.last_blankline) and isinstance(next_block.rule, ParaRule)

        self.last_blankline = is_blankline(next_block.rule)
        
        return (
            self.last_blankline
            or whitespace > self.indent
            or para
        )

@dataclass(slots=True)
class TableRule(BaseRule):
    caption: bool
    blankline: bool

    @property
    def cap(self) -> BlockCap:
        return BlockCap.CONTAINER

    def try_continue(self, reader: Reader, next_line: Range) -> bool:
        if self.caption:
            return reader.is_empty(next_line)
            
        text = reader.text(next_line.start, next_line.end)
        text = text.strip()
        if len(text) == 0:
            self.blankline = True
            return True
        elif text.startswith('^ '):
            self.caption = True
            return True
        else:
            return (
                not self.blankline
                and (
                    text.startswith('|')
                    and text.endswith('|')
                    and not text.endswith('\\|') # this cannot handle consecutive escapes.
                )
            )


class MeteredBlock(NamedTuple):
    rule: BaseRule
    span: Range
    line_count: int

    def locate_lines(self, reader: Reader, lines: List[Range]):
        lines = lines[:self.line_count] # lines for current block

        match self.rule:
            # Table without caption and ended with blanline
            case TableRule(
                caption=False,
                blankline=True
            ):
                lc = reader.drop_trailing_empty_lines(lines)
                lines = lines[:len(lines) - lc]

                return lines, lc

        return lines, self.line_count

    def find_end_span(self, lines: List[Range]) -> Range:
        last_line = lines[-1]
        
        match self.rule:
            case (
                CodeBlockRule(has_closing_fence=True) |
                DivRule(has_closing_fence=True)
            ):
                return copy.copy(last_line) # closing token of fence.
            case _:
                return Range(last_line.end, last_line.end)

    def adjust_line_start(self, reader: Reader, lines: List[Range]):
        lines[0].start += self.span.end

        match self.rule:
            case BlockquoteRule():
                if (
                    lines[0].start < lines[0].end
                    and
                    reader.is_space_or_tab(lines[0].start)
                ):
                    lines[0].start += 1
            case HeadingRule(level=level):
                for line in lines[1:]:
                    heading_parts = parse_heading(reader, line)
                    if heading_parts is not None:
                        assert heading_parts.level == level
                        line.start += len(heading_parts)

    def skip_fence_border(self, lines: List[Range]) -> List[Range]:
        match self.rule:
            case (
                DivRule(has_closing_fence=has_closing_fence) | CodeBlockRule(has_closing_fence=has_closing_fence)
            ):
                if has_closing_fence:
                    return lines[1:-1]
                else:
                    return lines[1:]

        return lines


class IdentifiedBlock(NamedTuple):
    rule: BaseRule
    span: Range


def meter_block(reader: Reader, lines: List[Range]) -> MeteredBlock | None:
    opened_block = identify_block(reader, lines[0])
    if opened_block is None:
        return None

    i = 1
    while i < len(lines):
        if opened_block.rule.try_continue(reader, lines[i]):
            i += 1
        else:
            break

    return MeteredBlock(
        rule=opened_block.rule,
        span=opened_block.span,
        line_count=i
    )


def identify_block(reader: Reader, span: Range) -> IdentifiedBlock:
    indent = reader.skip_space(span.start, span.end)

    span = Range(
        span.start+indent,
        span.end
    )

    if len(span) == 0:
        return IdentifiedBlock(
            AtomRule(AtomKind.BLANKLINE),
            Range(
                span.start,
                span.start
            )
        )

    
    end_whitespace = reader.trim_end_whitespace(span)
    # First non-space char position from backward.
    end_char_pos = span.end - end_whitespace - 1

    first_char = reader.char_at(span.start)

    match first_char:
        case '\n':
            return IdentifiedBlock(
                AtomRule(AtomKind.BLANKLINE),
                Range(
                    span.start,
                    span.start+1
                )
            )
        case '#':
            heading_parts = parse_heading(reader, span)
            if heading_parts is not None:
                return IdentifiedBlock(
                    HeadingRule(heading_parts.level),
                    Range(
                        span.start,
                        span.start+heading_parts.level
                    ),
                )

        case '>':
            if reader.is_none_or_whitespace(span.start+1):
                return IdentifiedBlock(
                    BlockquoteRule(),
                    Range(
                        span.start,
                        span.start+1
                    )
                )

        case '{':
            attr_end = reader.find_attr_end(span)
            if attr_end == end_char_pos:
                return IdentifiedBlock(
                    AtomRule(AtomKind.ATTRIBUTES),
                    Range(
                        span.start,
                        span.start+1
                    )
                )

        case '|':
            if reader.is_table_row(Range(span.start, end_char_pos+1)):
                return IdentifiedBlock(
                    TableRule(False, False),
                    Range(
                        span.start,
                        span.start
                    ),
                    
                )

        case '[':
            label = reader.find_definition_label(span) # inlcudes opitonal ^
            if label is not None:
                is_footnote = label.startswith('^')
                if is_footnote:
                    return IdentifiedBlock(
                        FootnoteRule(
                            indent=indent,
                            footnote=is_footnote,
                            label=label[1:],
                            last_blankline=False,
                        ),
                        Range(
                            span.start,
                            span.start + 3 + len(label) # 3 for []: chars
                        ),
                    )
                
                return IdentifiedBlock(
                    FootnoteRule(
                        indent=indent,
                        footnote=is_footnote,
                        label=label,
                        last_blankline=False,
                    ),
                    Range(
                        span.start,
                        span.start + 3 + len(label) # 3 for []: chars
                    ),
                )
        case '-' | '*':
            if reader.is_thematic_break(span):
                return IdentifiedBlock(
                    AtomRule(AtomKind.THEMATIC_BREAK),
                    Range(
                        span.start,
                        end_char_pos+1,
                    )
                )

        case '-' | '*' | '+':
            if reader.is_task(span):
                return IdentifiedBlock(
                    ListItemRule(
                        indent=indent,
                        detail=TaskList(BulletStyle(first_char)),
                        last_blankline=False,
                    ),
                    Range(
                        span.start,
                        span.start + 5,
                    ),
                )
            else:
                return IdentifiedBlock(
                    ListItemRule(
                        indent=indent,
                        detail=UnorderedList(BulletStyle(first_char)),
                        last_blankline=False,
                    ),
                    Range(
                        span.start,
                        span.start + 1,
                    ),
                    
                )
        case ':':
            if reader.is_none_or_whitespace(span.start+1):
                return IdentifiedBlock(
                    ListItemRule(
                        indent=indent,
                        detail=DescriptionList(),
                        last_blankline=False,
                    ),
                    Range(
                        span.start,
                        span.start + 1,
                    ),
                    
                )

        case '`' | ':' | '~':
            fence_length = reader.count_seq(first_char, span.start, span.end)
            spec_str = reader.text(span.start+fence_length, end_char_pos+1)
            spec = spec_str.strip()
            valid_spec = is_valid_name(spec) if first_char == ':' else is_vaild_lang(spec)
            
            if valid_spec and fence_length >= 3:
                is_div = True if first_char == ':' else False
                if is_div:
                    IdentifiedBlock(
                        DivRule(
                            indent=indent,
                            fence_length=fence_length,
                            border_char=first_char,
                            spec=spec,
                        ),
                        Range(
                            span.start,
                            span.end,
                        ),
                    )

                return IdentifiedBlock(
                    CodeBlockRule(
                        indent=indent,
                        fence_length=fence_length,
                        border_char=first_char,
                        spec=spec,
                    ),
                    Range(
                        span.start,
                        span.end,
                    ),
                )
                    

        case _:
            result = maybe_ordered_list_item(reader, span)
            if result is not None:
                ordered_list, length = result
                return IdentifiedBlock(
                    ListItemRule(
                        indent=indent,
                        detail=ordered_list,
                        last_blankline=False,
                    ),
                    Range(
                        span.start,
                        span.start + length,
                    ),
                )

    return IdentifiedBlock(
        ParaRule(),
        Range(
            span.start,
            span.start,
        )
    )


