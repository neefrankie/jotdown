from dataclasses import dataclass
from enum import Enum, auto
import string
from typing import Final, NamedTuple, Tuple

from jotdown.common import (
    Range,
)
from .list import (
    OrderedListStyle,
    OrderedListNumbering,
    BulletStyle,
)
from .event import (
    AtomKind,
    ListType,
    TaskList,
    UnorderedList,
    DescriptionList,
    OrderedList,
    BulletStyle,
)

from .reader import (
    Reader,
    is_valid_name,
    is_vaild_lang,
)

@dataclass(frozen=True, slots=True)
class Atom:
    kind: AtomKind

@dataclass(frozen=True, slots=True)
class Paragraph:
    pass

@dataclass(frozen=True, slots=True)
class Heading:
    level: int

class FenceKind(Enum):
    DIV = auto()
    CODE_BLOCK = auto()

@dataclass(frozen=True, slots=True)
class Fenced:
    indent: int
    fence_length: int
    kind: FenceKind
    border_char: str
    spec: str
    has_closing_fence: bool = False
    nested_raw: Tuple[int, int] | None = None

@dataclass(frozen=True, slots=True)
class Definition:
    indent: int
    footnote: bool
    label: str
    last_blankline: bool

@dataclass(frozen=True, slots=True)
class Blockquote:
    pass

@dataclass(frozen=True, slots=True)
class ListItem:
    indent: int
    typ: ListType
    last_blankline: bool

@dataclass(frozen=True, slots=True)
class Table:
    caption: bool
    blankline: bool

Kind = (
    Atom |
    Paragraph |
    Heading |
    Fenced |
    Definition |
    Blockquote |
    ListItem |
    Table
)


@dataclass(frozen=True, slots=True)
class MeteredBlock:
    kind: Kind
    span: Range
    line_count: int

class IdentifiedBlock(NamedTuple):
    kind: Kind
    span: Range


ASCII_SPACE = ' \t\r\n\x0c'

def identify_block(reader: Reader, span: Range) -> IdentifiedBlock:
    left_indent = reader.left_indent(span)

    indented_span = Range(
        span.start+left_indent,
        span.end
    )

    if len(indented_span) == 0:
        # TODO: figure out why here is indent length
        # rather than span.end or span.start+lindent
        return IdentifiedBlock(
            Atom(AtomKind.BLANKLINE),
            Range(
                span.start + left_indent,
                span.start + left_indent
            )
        )

    # First non-space char position from backward.
    end_char_pos = reader.rstrip(indented_span)

    first_char = reader.char_at(indented_span.start)

    match first_char:
        case '\n':
            return IdentifiedBlock(
                Atom(AtomKind.BLANKLINE),
                Range(span.start+left_indent, span.start+left_indent+1)
            )
        case '#':
            level = reader.read_heading_level(indented_span)
            if level is not None:
                return IdentifiedBlock(
                    Heading(level),
                    Range(
                        indented_span.start,
                        indented_span.start+level
                    )
                )

        case '>':
            if reader.is_none_or_whitespace(indented_span.start+1):
                return IdentifiedBlock(
                    Blockquote(),
                    Range(
                        indented_span.start,
                        indented_span.start+1
                    )
                )

        case '{':
            attr_end = reader.find_attr_end(indented_span)
            if attr_end == end_char_pos:
                return IdentifiedBlock(
                    Atom(AtomKind.ATTRIBUTES),
                    Range(
                        indented_span.start,
                        indented_span.start+1
                    )
                )

        case '|':
            if reader.is_table_row(Range(indented_span.start, end_char_pos+1)):
                return IdentifiedBlock(
                    Table(False, False),
                    Range(
                        indented_span.start,
                        indented_span.start
                    )
                )

        case '[':
            label = reader.find_definition_label(indented_span) # inlcudes opitonal ^
            if label is not None:
                is_footnote = label.startswith('^')
                return IdentifiedBlock(
                    Definition(
                        indent=left_indent,
                        footnote=is_footnote,
                        label=label[1:] if is_footnote else label,
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + 3 + len(label) # 3 for []: chars
                    )
                )
        case '-' | '*':
            if reader.is_thematic_break(indented_span):
                return IdentifiedBlock(
                    Atom(AtomKind.THEMATIC_BREAK),
                    Range(
                        indented_span.start,
                        end_char_pos+1,
                    )
                )

        case '-' | '*' | '+':
            if reader.is_task(indented_span):
                return IdentifiedBlock(
                    ListItem(
                        indent=left_indent,
                        typ=TaskList(BulletStyle(first_char)),
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + 5,
                    )
                )
            else:
                return IdentifiedBlock(
                    ListItem(
                        indent=left_indent,
                        typ=UnorderedList(BulletStyle(first_char)),
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + 1,
                    )
                )
        case ':':
            if reader.is_none_or_whitespace(indented_span.start+1):
                return IdentifiedBlock(
                    ListItem(
                        indent=left_indent,
                        typ=DescriptionList(),
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + 1,
                    )
                )

        case '`' | ':' | '~':
            fence_length = reader.read_seq(indented_span, first_char)
            spec_str = reader.text(indented_span.start+fence_length, end_char_pos+1)
            spec = spec_str.strip()
            valid_spec = is_valid_name(spec) if first_char == ':' else is_vaild_lang(spec)
            kind = FenceKind.DIV if first_char == ':' else FenceKind.CODE_BLOCK
            if valid_spec and fence_length >= 3:
                return IdentifiedBlock(
                    Fenced(
                        indent=left_indent,
                        fence_length=fence_length,
                        kind=kind,
                        border_char=first_char,
                        spec=spec,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.end,
                    )
                )

        case _:
            result = maybe_ordered_list_item(reader, indented_span)
            if result is not None:
                ordered_list, length = result
                return IdentifiedBlock(
                    ListItem(
                        indent=left_indent,
                        typ=ordered_list,
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + length,
                    )
                )

    return IdentifiedBlock(
        Paragraph(),
        Range(
            indented_span.start,
            indented_span.start,
        )
    )


ROMAN_LOWER: Final = frozenset('ivxlcdm')
ROMAN_UPPER: Final = frozenset('IVXLCDM')   

def maybe_ordered_list_item(reader: Reader, span: Range) -> Tuple[OrderedList, int] | None:

    pos = span.start
    first = reader.char_at(pos)

    start_paren = first == '('
    if start_paren:
        pos += 1
        first = reader.char_at(pos)

    if first is None:
        return None

    num_style = get_ordered_list_numbering(first)

    if num_style is None:
        return None

    len_num = count_ordered_list_digits(reader, num_style, pos, span.end)

    num_start = pos
    pos += len_num
    post_num = reader.char_at(pos)
    if post_num is None:
        return None
    
    style: OrderedListStyle | None = None
    if start_paren:
        if post_num == ')':
            style = OrderedListStyle.DOUBLE_PAREN
    elif post_num == ')':
        style = OrderedListStyle.PAREN
    elif post_num == '.':
        style = OrderedListStyle.PERIOD

    if style is None:
        return None

    len_style = 2 if start_paren else 1

    num_end = pos
    pos += 1
    if reader.is_none_or_whitespace(pos):
        l = len_num + len_style
        num_str = reader.src[num_start:num_end]
        return OrderedList(
            numbering=num_style,
            value=parse_ordered_number(num_style, num_str),
            style=style,
        ), l

    return None

def count_ordered_list_digits(reader: Reader, num_style: OrderedListNumbering, start: int, end: int) -> int:
    match num_style:
        case OrderedListNumbering.DECIMAL:
            return count_decimal(reader, start, end)
        case OrderedListNumbering.ALPHA_LOWER:
            return count_alpha_lower(reader, start, end)
        case OrderedListNumbering.ALPHA_UPPER:
            return count_alpha_upper(reader, start, end)
        case OrderedListNumbering.ROMAN_LOWER:
            return count_roman_lower(reader, start, end)
        case OrderedListNumbering.ROMAN_UPPER:
            return count_roman_upper(reader, start, end)

def count_decimal(reader: Reader, start: int, end: int) -> int:
    i = start
    while i < end:
        ch = reader.char_at(i)
        if ch is None:
            break
        if ch not in string.digits:
            break
        i += 1

    return i - start

def count_alpha_lower(reader: Reader, start: int, end: int) -> int:
    i = start
    while i < end:
        ch = reader.char_at(i)
        if ch is None:
            break
        if ch not in string.ascii_lowercase:
            break
        i += 1

    return i - start

def count_alpha_upper(reader: Reader, start: int, end: int) -> int:
    i = start
    while i < end:
        ch = reader.char_at(i)
        if ch is None:
            break
        if ch not in string.ascii_uppercase:
            break
        i += 1

    return i - start

def count_roman_lower(reader: Reader, start: int, end: int) -> int:
    i = start
    while i < end:
        ch = reader.char_at(i)
        if ch is None:
            break
        if ch not in ROMAN_LOWER:
            break
        i += 1

    return i - start

def count_roman_upper(reader: Reader, start: int, end: int) -> int:
    i = start
    while i < end:
        ch = reader.char_at(i)
        if ch is None:
            break
        if ch not in ROMAN_UPPER:
            break
        i += 1

    return i - start

        
def get_ordered_list_numbering(ch: str) -> OrderedListNumbering | None:
    if ch in string.digits:
        return OrderedListNumbering.DECIMAL
    
    if ch in ROMAN_LOWER:
        return OrderedListNumbering.ROMAN_LOWER
    
    if ch in ROMAN_UPPER:
        return OrderedListNumbering.ROMAN_UPPER
    
    if ch in string.ascii_lowercase:
        return OrderedListNumbering.ALPHA_LOWER
    
    if ch in string.ascii_uppercase:
        return OrderedListNumbering.ALPHA_UPPER

    return None

def alpha_to_number(s: str) -> int:
    d0 = ord('a') if s.islower() else ord('A')
    result = 0
    for i, ch in enumerate(reversed(s)):
        digit = ord(ch) - d0 + 1   # A=1, B=2, ..., Z=26
        result += digit * (26 ** i)
    return result

def roman_char_value(d: str) -> int:
    match d:
        case 'i' | 'I':
            return 1
        case 'v' | 'V':
            return 5
        case 'x' | 'X':
            return 10
        case 'l' | 'L':
            return 50
        case 'c' | 'C':
            return 100
        case 'd' | 'D':
            return 500
        case 'm' | 'M':
            return 1000
        case _:
            raise ValueError(f'Invalid Roman numeral character: {d}')

def roman_to_number(s: str) -> int:
    prev = 0
    sum = 0
    for d in reversed(s):
        v = roman_char_value(d)
        if v < prev:
            sum -= v
        else:
            sum += v
        prev = v

    return sum

def parse_ordered_number(numbering: OrderedListNumbering, n: str) -> int:
    match numbering:
        case OrderedListNumbering.DECIMAL:
            return int(n)
        case OrderedListNumbering.ALPHA_LOWER | OrderedListNumbering.ALPHA_UPPER:
            return alpha_to_number(n)
        case OrderedListNumbering.ROMAN_LOWER | OrderedListNumbering.ROMAN_UPPER:
            return roman_to_number(n)

