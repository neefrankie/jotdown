from dataclasses import dataclass
from enum import Enum, auto
import string
from typing import Final, List, NamedTuple, Tuple

from jotdown.common import (
    Range,
)
from .list import (
    OrderedListStyle,
    OrderedListNumbering,
    BulletStyle,
)
from .event import (
    ListType,
    TaskList,
    UnorderedList,
    DescriptionList,
    OrderedList,
)

from .reader import (
    Reader,
    is_valid_name,
    is_vaild_lang,
)


@dataclass(frozen=True, slots=True)
class BlankToken:
    pass

@dataclass(frozen=True, slots=True)
class AttrToken:
    pass

@dataclass(frozen=True, slots=True)
class ThematicToken:
    pass


@dataclass(frozen=True, slots=True)
class ParaToken:
    pass

@dataclass(frozen=True, slots=True)
class HeadingToken:
    level: int

class FenceKind(Enum):
    DIV = auto()
    CODE_BLOCK = auto()

class NestedRaw(NamedTuple):
    border_char: str
    fence_length: int

@dataclass(slots=True)
class FencedToken:
    indent: int
    fence_length: int
    kind: FenceKind
    border_char: str
    spec: str # lang part
    has_closing_fence: bool = False
    nested_raw: NestedRaw | None = None # a flag whehter code block is nested withint div.

@dataclass(slots=True)
class DefinitionToken:
    indent: int
    footnote: bool
    label: str
    last_blankline: bool

@dataclass(frozen=True, slots=True)
class BlockquoteToken:
    pass

@dataclass(slots=True)
class ListItemToken:
    indent: int
    typ: ListType
    last_blankline: bool

@dataclass(slots=True)
class TableToken:
    caption: bool
    blankline: bool

TriggerToken = (
    BlankToken |
    AttrToken |
    ThematicToken |
    ParaToken |
    HeadingToken |
    FencedToken |
    DefinitionToken |
    BlockquoteToken |
    ListItemToken |
    TableToken
)


class MeteredBlock(NamedTuple):
    token: TriggerToken
    span: Range
    line_count: int

class IdentifiedBlock(NamedTuple):
    token: TriggerToken
    span: Range

def meter_block(reader: Reader, lines: List[Range]) -> MeteredBlock | None:
    opend_block = identify_block(reader, lines[0])
    if opend_block is None:
        return None

    token, span = opend_block

    i = 1
    while i < len(lines):
        if can_continue(token, reader, lines[i]):
            i += 1
        else:
            break

    return MeteredBlock(
        token=token,
        span=span,
        line_count=i
    )

def can_continue(token: TriggerToken, reader: Reader, line: Range) -> bool:
    match token:
        case BlankToken() | AttrToken() | ThematicToken() | FencedToken(has_closing_fence=True):
            return False
        case BlockquoteToken():
            new_block = identify_block(reader, line)
            if new_block is None:
                return False
    
            if isinstance(new_block.token, (BlockquoteToken, ParaToken)):
                return True
    
            return False
        case HeadingToken(level=level):
            new_block = identify_block(reader, line)
            if new_block is None:
                return False
    
            if isinstance(new_block.token, ParaToken):
                return True
    
            if isinstance(new_block.token, HeadingToken) and new_block.token.level == level:
                return True
    
            return False

        case ParaToken() | TableToken(caption=True):
            return not reader.is_empty(line)

        case ListItemToken(indent=indent, last_blankline=last_blankline):
            whitespace = reader.left_strip(line)
            next_block = identify_block(reader, line)
            if next_block is None:
                return False

            para = (not last_blankline) and isinstance(next_block.token, ParaToken)
            token.last_blankline = isinstance(next_block.token, BlankToken)
            return token.last_blankline or whitespace > indent or para

        case DefinitionToken(indent=indent, footnote=True, last_blankline=last_blankline):
            next_block = identify_block(reader, line)
            if next_block is None:
                return False

            whitespace = reader.left_strip(line)
            cont_para = (not last_blankline) and isinstance(next_block.token, ParaToken)
            token.last_blankline = isinstance(next_block.token, BlankToken)

            return whitespace > indent or token.last_blankline or cont_para

        case DefinitionToken():
            blankline = reader.is_empty(line)

            return reader.char_at(line.start) == ' ' and not blankline

        case FencedToken(
            fence_length=fence_length,
            kind=kind,
            nested_raw=nested_raw,
        ):
            new_block = identify_block(reader, line)
            if new_block is None:
                return True

            new_token = new_block.token

            if not isinstance(new_token, FencedToken):
                return True

            # If a div has code block nested.
            if nested_raw is not None:
                if (
                    # and we find the nested code block's closing delimiter
                    new_token.kind == FenceKind.CODE_BLOCK 
                    and 
                    new_token.fence_length >= nested_raw.fence_length 
                    and 
                    len(new_token.spec) == 0
                    # and the closing delimiter should be longer than opening delimiter, 
                    # and does not have attributes followed
                ):
                    token.nested_raw = None
            elif new_token.kind == kind:
                # Might be closing delimiter
                token.has_closing_fence =  (
                    (new_token.fence_length >= fence_length) # closing delimiter should be longer
                    and
                    (len(new_token.spec) == 0) # closing delimiter should not have attributes followed
                )
            elif kind == FenceKind.DIV: # if outer container is div.
                if new_token.kind == FenceKind.CODE_BLOCK:
                    token.nested_raw = NestedRaw(
                        border_char=new_token.border_char,
                        fence_length=new_token.fence_length
                    )

            return True

        case TableToken(caption=caption, blankline=blankline):
            text = reader.text(line.start, line.end)
            text = text.strip()
            if len(text) == 0:
                token.blankline = True
                return True
            elif text.startswith('^ '):
                token.caption = True
                return True
            else:
                return (
                    not token.blankline
                    and (text.startswith('|')
                         and text.endswith('|')
                         and not text.endswith('\\|'))
                )



def identify_block(reader: Reader, span: Range) -> IdentifiedBlock:
    indent = reader.calc_indent(span)

    indented_span = Range(
        span.start+indent,
        span.end
    )

    if len(indented_span) == 0:
        # TODO: figure out why here is indent length
        # rather than span.end or span.start+lindent
        return IdentifiedBlock(
            BlankToken(),
            Range(
                span.start + indent,
                span.start + indent
            )
        )

    
    end_whitespace = reader.trim_end_whitespace(indented_span)
    # First non-space char position from backward.
    end_char_pos = indented_span.end - end_whitespace - 1

    first_char = reader.char_at(indented_span.start)

    match first_char:
        case '\n':
            return IdentifiedBlock(
                BlankToken(),
                Range(span.start+indent, span.start+indent+1)
            )
        case '#':
            level = reader.read_heading_level(indented_span)
            if level is not None:
                return IdentifiedBlock(
                    HeadingToken(level),
                    Range(
                        indented_span.start,
                        indented_span.start+level
                    )
                )

        case '>':
            if reader.is_none_or_whitespace(indented_span.start+1):
                return IdentifiedBlock(
                    BlockquoteToken(),
                    Range(
                        indented_span.start,
                        indented_span.start+1
                    )
                )

        case '{':
            attr_end = reader.find_attr_end(indented_span)
            if attr_end == end_char_pos:
                return IdentifiedBlock(
                    AttrToken(),
                    Range(
                        indented_span.start,
                        indented_span.start+1
                    )
                )

        case '|':
            if reader.is_table_row(Range(indented_span.start, end_char_pos+1)):
                return IdentifiedBlock(
                    TableToken(False, False),
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
                    DefinitionToken(
                        indent=indent,
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
                    ThematicToken(),
                    Range(
                        indented_span.start,
                        end_char_pos+1,
                    )
                )

        case '-' | '*' | '+':
            if reader.is_task(indented_span):
                return IdentifiedBlock(
                    ListItemToken(
                        indent=indent,
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
                    ListItemToken(
                        indent=indent,
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
                    ListItemToken(
                        indent=indent,
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
                    FencedToken(
                        indent=indent,
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
                    ListItemToken(
                        indent=indent,
                        typ=ordered_list,
                        last_blankline=False,
                    ),
                    Range(
                        indented_span.start,
                        indented_span.start + length,
                    )
                )

    return IdentifiedBlock(
        ParaToken(),
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

