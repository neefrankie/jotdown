from abc import ABC
from dataclasses import dataclass
from typing import Optional, Tuple

from jotdown.lex.lex import (
    Token,
)
from jotdown.attr import Validator


@dataclass
class VerbatimState:
    event_opener: int # Index in events list.
    # length of opener Token, e.g. the number of backtick.
    # It is remembered because later we need to compare closing
    # token against it.
    len_opener: int
    non_whitespace_encountered: bool
    non_whitespace_last: Optional[Tuple[Token, int]]


class AttrsElementType(ABC):
    pass

@dataclass
class AttrsElementContainer(AttrsElementType):
    event_placdeholder_idx: int

@dataclass
class AttrsElementWord(AttrsElementType):
    pass

@dataclass
class AttributesState:
    elem_ty: AttrsElementType
    end_attr: int
    valid_lines: int
    validator: Validator



