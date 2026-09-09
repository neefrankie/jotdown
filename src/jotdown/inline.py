from abc import ABC
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from .lex import (
    Lexer,
    Token,
    TokenOpen,
    Delimiter,
)
from .utils import (
    is_ascii_whitespace
)

class QuoteType(Enum):
    SINGLE = auto()
    DOUBLE = auto()

class Atom(ABC):
    pass

@dataclass
class FootnoteReference(Atom):
    label: str

@dataclass
class Symbol(Atom):
    s: str

@dataclass
class Softbreak(Atom):
    pass

@dataclass
class Hardbreak(Atom):
    pass

@dataclass
class Escape(Atom):
    pass

@dataclass
class Nbsp(Atom):
    pass

@dataclass
class Ellipsis(Atom):
    pass

@dataclass
class EnDash(Atom):
    pass

@dataclass
class EmDash(Atom):
    pass

@dataclass
class Quote(Atom):
    ty: QuoteType
    left: bool

class Container(ABC):
    pass

@dataclass
class SpanBox(Container):
    pass

@dataclass
class Subscript(Container):
    pass

@dataclass
class Superscript(Container):
    pass

@dataclass
class Insert(Container):
    pass

@dataclass
class Delete(Container):
    pass

@dataclass
class Emphasis(Container):
    pass

@dataclass
class Strong(Container):
    pass

@dataclass
class Mark(Container):
    pass

@dataclass
class Verbbatim(Container):
    pass

@dataclass
class RawFormat(Container):
    format: str

@dataclass
class InlineMath(Container):
    pass

@dataclass
class DisplayMath(Container):
    pass

@dataclass
class ReferenceLink(Container):
    index: int

@dataclass
class ReferenceImage(Container):
    index: int

@dataclass
class InlineLink(Container):
    index: int

@dataclass
class inlineImage(Container):
    index: int

@dataclass
class AutoLink(Container):
    index: int

@dataclass
class Event:
    start: int
    end: int
    pass

@dataclass
class EventEnter(Event):
    container: Container

@dataclass
class EventExit(Event):
    container: Container

@dataclass
class EventAtom(Event):
    atom: Atom

@dataclass
class EventStr(Event):
    pass

@dataclass
class EventEmpty(Event):
    pass

@dataclass
class EventAttributes(Event):
    container: bool
    attrs_index: int

@dataclass
class Range:
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start

    def is_empty(self) -> bool:
        return self.start >= self.end

    def contains(self, pos: int) -> bool:
        return self.start <= pos < self.end

class Input:
    def __init__(self, src: str):
        self.src = src
        self.lexer = Lexer("")
        self.complete: bool = False
        self.span_line: Range = Range(0, 0)
        self.ahead: deque[Range] = deque()
        self.span: Range = Range(0, 0)

    def feed_line(self, line: Range, last: bool):
        assert not self.complete
        self.complete = last
        if not self.lexer.ahead():
            if self.ahead:
                nxt = self.ahead.popleft()
                self.set_current_line(nxt)
                self.ahead.append(line)
            else:
                self.set_current_line(line)
        else:
            self.ahead.append(line)

        
    def set_current_line(self, line: Range):
        self.lexer = Lexer(self.src[line.start:line.end])
        self.span = Range(line.start, line.start)
        self.span_line = line

    def reset(self):
        self.lexer = Lexer("")
        self.complete = False
        self.ahead.clear()

    def last(self) -> bool:
        return self.complete and len(self.ahead) == 0

    def eat(self) -> Optional[Token]:
        tok = next(self.lexer, None)
        if tok is not None:
            self.span.end += tok.length
        return tok

    def peek(self) -> Optional[Token]:
        self.lexer.peek()

    def reset_span(self):
        self.span.start = self.span.end

    def ahead_raw_format(self) -> Optional[Range]:
        """
        Example:

        `<?php ehco 'Hello world!' ?>`{=html}
        """
        tok = self.lexer.peek()
        if tok is None:
            return None
        if not isinstance(tok, TokenOpen):
            return None
        if tok.delimiter != Delimiter.BRACE_EQUAL: # {=
            return None

        # Now the cursor is move after {=.
        # However we need to process this token starting from {.
        
        ahead_str = self.lexer.ahead()
        if len(ahead_str) <= 2:
            return None

        is_end = False
        start = 2
        end = start
        while True:
            ch = ahead_str[end]
            if ch == '{':
                break

            if ch == '}' or is_ascii_whitespace(ch):
                break

            end += 1

        l = end - start
        if l > 0 and ahead_str[end] == '}':
            tok = self.eat() # consume this token
            assert isinstance(tok, TokenOpen)
            assert tok.delimiter == Delimiter.BRACE_EQUAL
            assert tok.length == 2

            # the cursor is pointing to the the position after `{=`.
            # end is point to `}`.
            # Now move position after `}`
            self.lexer.skip_ahead(l + 1)
            return Range(
                start=self.span.end,
                end=self.span.end + l
            )

        return None

@dataclass
class VertabimState:
    event_opener: int
    len_opener: int
    non_whitespace_encountered: bool
    non_whitespace_last: Optional[Tuple[Token, int]]

class AttributesElementType(Enum):
    CONTAINER = auto()
    WORD = auto()
@dataclass
class AttributesState:
    elem_ty: AttributesElementType
    end_attr: int
    valid_lines: int

class Directionality(Enum):
    UNI = auto()
    BI = auto()

class SpanType(Enum):
    IMAGE = auto()
    GENERAL = auto()

class Opener(ABC):
    pass

@dataclass
class SpanOpener(Opener):
    typ: SpanType

@dataclass
class DirectionalOpener(Opener, ABC):
    direction: Directionality

@dataclass
class StrongOpener(DirectionalOpener):
    pass

@dataclass
class EmphasisOpener(DirectionalOpener):
    pass

@dataclass
class SuperscriptOpener(Opener):
    pass

@dataclass
class MarkOpener(Opener):
    pass

@dataclass
class DeleteOpener(Opener):
    pass

@dataclass
class InsertOpener(Opener):
    pass

@dataclass
class SingleQuotedOpener(Opener):
    pass

@dataclass
class DoubleQuoted(Opener):
    pass

@dataclass
class LinkOpener(Opener):
    event_span: int
    image: bool
    inline: bool

class InlineParser:
    def __init__(self, src: str):
        self.input = Input(src)
        self.openers: List[Tuple[Opener, int]]
