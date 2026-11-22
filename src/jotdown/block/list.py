from dataclasses import dataclass
from enum import Enum, auto
import string
from typing import Dict, Final, Optional, Tuple

ROMAN_LOWER: Final = frozenset('ivxlcdm')
ROMAN_UPPER: Final = frozenset('IVXLCDM')  

from .reader import Reader, Range

class OrderedListStyle(Enum):
    PERIOD = auto()
    PAREN = auto()
    DOUBLE_PAREN = auto()

class OrderedListNumbering(Enum):
    DECIMAL = auto()
    ALPHA_LOWER = auto()
    ALPHA_UPPER = auto()
    ROMAN_LOWER = auto()
    ROMAN_UPPER = auto()
        

class BulletStyle(Enum):
    PLUS = '+'
    DASH = '-'
    ASTERISK = '*'

@dataclass(frozen=True, slots=True)
class UnorderedList:
    style: BulletStyle

DIGIT_TO_ROMAN: Dict[int, str] = {
    1: 'i',
    5: 'v',
    10: 'x',
    50: 'l',
    100: 'c',
    500: 'd',
    1000: 'm',
}

@dataclass(frozen=True, slots=True)
class OrderedList:
    numbering: OrderedListNumbering
    value: int
    style: OrderedListStyle

    def ambiguity(self) -> Optional['OrderedList']:
        match self.numbering:
            case OrderedListNumbering.ROMAN_LOWER:
                single_digit = DIGIT_TO_ROMAN.get(self.value, None)
                if single_digit is None:
                    return None
                return OrderedList(
                    numbering=OrderedListNumbering.ALPHA_LOWER,
                    value=alpha_to_number(single_digit),
                    style=self.style
                )

            case OrderedListNumbering.ROMAN_UPPER:
                single_digit = DIGIT_TO_ROMAN.get(self.value, None)
                if single_digit is None:
                    return None
                return OrderedList(
                    numbering=OrderedListNumbering.ALPHA_UPPER,
                    value=alpha_to_number(single_digit),
                    style=self.style
                )

            case _:
                return None
        

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

class ListItemKind(Enum):
    TASK = auto()
    DESCRIPTION = auto()
    LIST = auto()

def can_list_continues(self: ListType, other: ListType) -> Tuple[ListType, ListType] | None:
    if self == other:
        return (self, other)

    match (self, other):
        case (
            OrderedList(numbering=n0, style=s0),
            OrderedList(numbering=n1, style=s1),
        ) if n0 == n1 and s0 == s1:
            return (self, other)

        # Different numering.
        # For example, previous is roman, current is alpha.
        case (
            OrderedList(numbering=n0, value=v0, style=s0),
            OrderedList(numbering=n1, value=v1, style=s1),
        ) if s0 == s1:
            candidate0 = self.ambiguity()
            if candidate0 is not None:
                if candidate0.numbering == n1 and candidate0.value + 1 == v1:
                    return (candidate0, other)
                else:
                    return None

            candidate1 = other.ambiguity()
            if candidate1 is not None:
                if n0 == candidate1.numbering and v0 + 1 == candidate1.value:
                    return (self, candidate1)
                else:
                    return None

            return None

        case _:
            return None
            
            
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

def roman_to_digit(d: str) -> int:
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
        v = roman_to_digit(d)
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
    