from enum import Enum, auto


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