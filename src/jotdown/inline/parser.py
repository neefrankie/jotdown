import copy
from enum import Enum, auto
from typing import List, Optional, Tuple

from jotdown.utils import (
    is_ascii_whitespace
)
from jotdown.lex.lex import (
    Token,
    OpenToken,
    SymToken,
    SequenceToken,
)
from jotdown.attr import Attributes, Validator
from .event import (
    EventKind,
    Range,
    Event,
    EnterEvent,
    ExitEvent,
    PlaceholderEvent,
    StrEvent,
    AtomEvent,
)
from .element import (
    Container,
    Verbatim,
    RawFormat,
    InlineMath,
    DisplayMath,
    ensure_verbatim,
    AutoLink,
    Symbol,
    FootnoteReference,
)

from .input import Input
from .opener import (
    Opener,
)
from .state import (
    VerbatimState,
    AttributesState,
    AttrsElementContainer,
    AttrsElementType,
)

class ControlFlow(Enum):
    # At least one event has been emitted, continue parsing the line
    CONTINUE = auto()
    # Next line is needed to emit an event
    NEXT = auto()
    # More lines are needed to emit an event.
    # Unlike for the `NEXT` variant, the internal ahead
    # buffer has already been examined, and more lines
    # need to be retrieved from the block parser.
    MORE = auto()
    # Parsing of the line is completed.
    DONE = auto()

class InlineParser:
    def __init__(self, src: str):
        self._input = Input(src)

        # Stack of opener and index for containers.
        self._openers: List[Tuple[Opener, int]]

        # Buffer queue for next events. Events are buffered until no
        # modifications due to future characters are needed.
        self._events: List[Event] = []

        # State if inside a verbatim container.
        self._verbatim: Optional[VerbatimState] = None

        # State if currently parsing potential attributes.
        self._attributes: Optional[AttributesState] = None

        self.store_str: List[str] = []
        self.store_attributes: List[Attributes] = []

    def feed_line(self, line: Range, last: bool):
        self._input.feed_line(line, last)

    def reset(self):
        assert len(self._events) == 0
        self._input.reset()
        self._openers.clear()
        assert self._attributes is None
        assert self._verbatim is None
        self.store_str.clear()
        self.store_attributes.clear()

    def _push_span(self, kind: EventKind, span: Range):
        """
        Append a new Event.
        """
        self._events.append(Event(kind, span))

    def _push(self, kind: EventKind) -> ControlFlow:
        """
        Add current span as a new Event.
        """
        self._push_span(kind, copy.copy(self._input.span))
        return ControlFlow.CONTINUE

    # def _parse_event(self) -> ControlFlow:
    #     self._input.reset_span()
    #     tok = self._input.eat()
    
    

    def _close_verbatim(self, state: VerbatimState) -> ControlFlow:
        # Raw inline has format following closing token.
        # Example: `<img>`{=html}
        raw_format = self._input.ahead_raw_format()
        if raw_format is not None:
            self._set_raw_format(state, raw_format)
        
        # Ensure the opening event is not Placeholder.
        opener_event = self._events[state.event_opener].kind
        if not isinstance(opener_event, EnterEvent):
            raise Exception('Expected enter event')
        
        ty_opener = opener_event.container
        assert ensure_verbatim(ty_opener)
        
        if state.non_whitespace_last is not None:
            (tok, event_skip) = state.non_whitespace_last
            if isinstance(tok, SequenceToken) and tok.is_backtick:
               del self._events[:event_skip]
        
        self._push(ExitEvent(ty_opener))
        self._input.lexer.verbatim = False
        self._verbatim = None
        
        # If verbatim is not followed by format,
        # check if it is followed by attributes.
        if raw_format is None and self._peek_is_open_brace():
            ctrl_flow = self._ahead_attributes(
                elem_typ=AttrsElementContainer(
                    event_placdeholder_idx=state.event_opener-1
                ),
                opener_eatean=False
            )
            if ctrl_flow:
                return ctrl_flow

        return ControlFlow.CONTINUE

    def _set_raw_format(self, state: VerbatimState, raw_format: Range):
        # Find the opening event and update its kind from placeholder to concrete type.
        self._events[state.event_opener].kind = EnterEvent(
            container=RawFormat(
                format=self._input.src[raw_format.to_slice()]
            )
        )
        self._input.span.end = raw_format.end + 1

    def _peek_is_open_brace(self) -> bool:
        next_tok = self._input.peek()
        
        if next_tok is None:
            return False
        
        if not isinstance(next_tok, OpenToken):
            return False
        
        return next_tok.is_brace
        
    def _is_closing_backtick(self, first: Token, state: VerbatimState) -> bool:
        if state.len_opener != first.length:
            return False

        if not isinstance(first, SequenceToken):
            return False

        return first.is_backtick

    def _continue_verbatim(self, first: Token, state: VerbatimState) -> ControlFlow:
        """将内容添加到 verbatim 中"""
        # 检查是否是纯空白
        is_whitespace = all(
            is_ascii_whitespace(c) for c in self._input.src[self._input.span.to_slice()]
        )
        if is_whitespace:
            if not state.non_whitespace_encountered and self._peek_is_different_backtick(state.len_opener):
                # Ignore by not adding Event.
                return ControlFlow.CONTINUE
        else:
            state.non_whitespace_encountered = True
            state.non_whitespace_last = (first, len(self._events) + 1)
        
        self._push(StrEvent())

        return ControlFlow.CONTINUE

    def _peek_is_different_backtick(self, len_opener: int) -> bool:
        next_tok = self._input.peek()

        if next_tok is None:
            return False

        if not isinstance(next_tok, SequenceToken):
            return False

        return next_tok.length != len_opener
    

    def _parse_verbatim(self, first: Token) -> Optional[ControlFlow]:
        if self._verbatim is not None:
            # In verbatim mode, it should either continue or close the verbatim.
            if self._is_closing_backtick(first, self._verbatim):
                # Close token.
                return self._close_verbatim(self._verbatim)
            else:
                # continue verbatim
                return self._continue_verbatim(first, self._verbatim)
        elif isinstance(first, SequenceToken) and first.is_backtick: 
            # start verbatim
            return self._start_verbatim(first)
        else:
            return None


    def _start_verbatim(self, first: SequenceToken) -> ControlFlow:
        # A new verbatim span.
        len_opener = first.length
        # Find out if the backtck is followed by dollar.
        # Dollar should be the the end of previous token if the token is plain text.
        container = self._backtrace_math_span()
        
        self._push_span(
            kind=PlaceholderEvent(),
            span=Range(
                start=self._input.span.start,
                end=self._input.span.start
            )
        )
        self._input.lexer.verbatim = True
        self._verbatim = VerbatimState(
            event_opener=len(self._events),
            len_opener=len_opener,
            non_whitespace_encountered=False,
            non_whitespace_last=None,
        )
        self._attributes = None
        return self._push(EnterEvent(container))

    def _backtrace_math_span(self) -> Container:
        """
        Check if there's dollar sign before verbatim.

        Einstein dervied $`e=mc^2` will be tokenized into:

        1. Einstein dervied $
        2. `
        3. e=mc^2
        4. `

        If we find a verbatim span, then we have to backtrace to previous
        span to find out if there are any non-escaped consecutive $
        from the the end of last span.
        """
        if not self._events:
            return Verbatim()

        last_event = self._events[-1]
        if not last_event.is_str:
            return Verbatim()

        sp = copy.copy(last_event.span)
        # Last event must sit exactly before current one.
        if sp.end != self._input.span.start:
            return Verbatim()

        num_dollar = self._find_math_symbol(sp)
        if num_dollar == 0:
            return Verbatim()

        border = sp.end - num_dollar

        last_event.span = Range(
            start=sp.start,
            end=border,
        )
        self._input.span = Range(
            start=border,
            end=self._input.span.end
        )

        if num_dollar == 1:
            return InlineMath()
        elif num_dollar == 2:
            return DisplayMath()

        return Verbatim()


    def _find_math_symbol(self, sp: Range) -> int:
        """
        Find consecutive $ from back.

        Returns the number of dollars found.
        0: not math
        1: inline math
        2: display math
        """
        border = sp.end
        for _ in range(2):
            if border <= sp.start:
                break
            if border <= 0:
                break
            if self._input.src[border - 1] != '$': # any char before border is not not $, including backslash.
                break
            border -= 1

        if sp.start < border < sp.end:
            # if char before $ is escape.
            if self._input.src[border - 1] == '\\': 
                border += 1
            # otherwise border is either pointing to end or start,
            # indicating the span is either not math symbol,
            # or only math symbol.

        return sp.end - border

    def _ahead_attributes(
        self, 
        elem_typ: AttrsElementType,
        opener_eatean: bool,
    ) -> Optional[ControlFlow]:
        state = AttributesState(
            elem_ty=elem_typ,
            end_attr=self._input.span.end - int(opener_eatean),
            valid_lines=0,
            validator=Validator()
        )
        return self._resume_atributes(
            state=state,
            opener_eaten=opener_eatean,
            first=True
        )

    def _resume_atributes(
        self,
        state: AttributesState,
        opener_eaten: bool,
        first: bool
    ) -> Optional[ControlFlow]:
        start_attr = self._input.span.end - int(opener_eaten)

        assert self._input.src[start_attr:].startswith('{')

        if first:
            line_next = 0
            line_start = start_attr
            line_end = self._input.line_span.end
        else:
            line_next = len(self._input.ahead)
            last_line = self._input.ahead[-1]
            line_start = last_line.start
            line_end = last_line.end

    def _parse_autolink(self, first: Token) -> Optional[ControlFlow]:
        """
        A URL or email address enclosed in <...>
        The content is treated literally. No escape. No newline.
        """
        if not isinstance(first, SymToken):
            return None

        if not first.is_less_than:
            return None

        length = self._input.ahead_autolink_len()
        if length is None:
            return None

        self._input.lexer.skip_ahead(length + 1)
        span_url = Range(
            start=self._input.span.end,
            end=self._input.span.end + length,
        )
        url = self._input.src[span_url.to_slice()]
        
        self._push(EnterEvent(AutoLink(url)))
        self._input.span = span_url
        self._push(StrEvent())
        self._input.span = Range(
            start=self._input.span.end, # The closing >
            end=self._input.span.end + 1
        )
        return self._push(ExitEvent(AutoLink(url)))

    def _parse_symbol(self, first: Token) -> Optional[ControlFlow]:
        """
        A word surrounded by : creates a symbol.

        Example:
            :smiley:
        """
        if not isinstance(first, SymToken):
            return None

        if not first.is_colon:
            return None

        length = self._input.ahead_symbol_len()
        if length is None:
            return None
        
        self._input.lexer.skip_ahead(length + 1)
        span_symbol = Range(
            start=self._input.span.end,
            end=self._input.span.end + length,
        )
        self._input.span.end = span_symbol.end + 1

        symbol = self._input.src[span_symbol.to_slice()]

        return self._push(AtomEvent(Symbol(symbol)))

    def _parse_footnote_reference(self, first: Token) -> Optional[ControlFlow]:
        """
        ^ + the reference label in square bracket.

        Exmaple:
            [^foo]
        """
        if not isinstance(first, OpenToken):
            return None

        if not first.is_bracket: # the [
            return None

        next_tok = self._input.peek() # ^
        if not isinstance(next_tok, SymToken):
            return None

        if not next_tok.is_caret:
            return None

        self._input.eat() # consume the token ^

        assert next_tok.length == 1

        length = self._input.ahead_footnote_reference()
        if not length:
            return None
        
        self._input.lexer.skip_ahead(length + 1)
        span_label = Range(
            start=self._input.span.end,
            end=self._input.span.end + length,
        )
        label = self._input.src[span_label.to_slice()]
        self._input.span.end = span_label.end + 1
        return self._push(AtomEvent(FootnoteReference(label)))
