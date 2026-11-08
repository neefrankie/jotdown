from collections import deque
from typing import Optional

from jotdown.utils import (
    is_ascii_whitespace
)
from jotdown.lex import (
    Lexer,
    Token,
    Delimiter,
    OpenToken,
)
from .event import (
    Range,
)


class Input:
    def __init__(self, src: str):
        self.src = src
        self.lexer = Lexer("")
        # The block is complete, the final line has been provided.
        self.complete: bool = False
        # Span of current line.
        self.span_line: Range = Range(0, 0)
        # Upcoming lines within the current block.
        self.ahead: deque[Range] = deque()
        # Span of current event
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
        """
        Consume the next token in lexer and extend current span.
        """
        tok = next(self.lexer, None)
        if tok is not None:
            self.span.end += tok.length
        return tok

    def peek(self) -> Optional[Token]:
        """
        Get the next token from lexer.
        """
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
        if not isinstance(tok, OpenToken):
            return None
        if not tok.is_brace_equal: # {=
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
            assert isinstance(tok, OpenToken)
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

    def ahead_symbol_len(self) -> Optional[int]:
        # :smiley:
        # The first : is processed now.
        ended = False
        valid = True

        # NOTE the index is only valid for lexer.
        # This is not the index in the full source document.
        start_idx = self.lexer.next_token_start()
        end_idx = start_idx

        while end_idx < self.lexer.length:
            ch = self.lexer.src[end_idx]
            if ch == ':':
                ended = True
                break
            if is_ascii_whitespace(ch):
                break

            if ch in '-+_':
                valid = False

            end_idx += 1

        if not ended or not valid:
            return None

        # Now end_idx point to closing :
        l = end_idx - start_idx

        return l

    def ahead_autolink_len(self) -> Optional[int]:
        ended = False
        is_url = False

        start_idx = self.lexer.next_token_start()
        end_idx = start_idx

        while end_idx < self.lexer.length:
            ch = self.lexer.src[end_idx]
            if ch == '>':
                ended = True
                break
            if ch == '<':
                break
            if is_ascii_whitespace(ch):
                break

            if ch in ':@':
                is_url = True

            end_idx += 1

        if not ended or not is_url:
            return None

        l = end_idx - start_idx

        return l

    def ahead_footnote_reference(self) -> Optional[int]:
        """
        Parse footnote content and returns its length.
        Position is pointing to the char after caret in [^ now.
        """

        ended = False
        start_idx = self.lexer.next_token_start()
        end_idx = start_idx
        while end_idx < self.lexer.length:
            ch = self.lexer.src[end_idx]
            if ch == ']':
                ended = True
                break
            if ch == '[':
                break
            if ch == '\n':
                break

        if not ended:
            return None

        return end_idx - start_idx






