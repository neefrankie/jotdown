import string
from typing import Final, Iterator, List, NamedTuple

from jotdown.common import (
    Range,
)

from jotdown.attr import State

NAME_CHARS: Final = frozenset(string.ascii_letters + string.digits + ':_-')
ASCII_WHITESPACE = ' \t\r\n\x0c'


def is_valid_name(s: str) -> bool:
    for ch in s:
        if ch not in NAME_CHARS:
            return False

    return True

def is_vaild_lang(s: str) -> bool:
    for ch in s:
        if ch == '`':
            return False
        if ch in ASCII_WHITESPACE:
            return False

    return True

class Reader:
    
    def __init__(self, src: str) -> None:
        src = src.replace('\r\n', '\n')
        if src and src[-1] != '\n':
            src += '\n'

        self.src = src
        
        self.length = len(src)

    def iter_lines(self) -> Iterator[Range]:
        if self.length == 0:
            return

        start = 0
        end = self.src.find('\n', start)
        while end > -1:
            yield Range(
                start=start,
                end=end + 1,
            )
            start = end+1
            end = self.src.find('\n', start)

        # In case the last line is not ended with newline
        if start < self.length:
            yield Range(
                start=start,
                end=self.length,
            )

    def calc_indent(self, span: Range) -> int:
        newpos = span.start

        while newpos < span.end:
            ch = self.src[newpos]
            if ch == '\n' or ch not in ASCII_WHITESPACE:
                break
            newpos += 1

        return newpos - span.start

    def trim_end_whitespace(self, span: Range) -> int:
        start = span.end - 1
        end = start
    
        while end >= span.start:
            ch = self.src[end]
            if ch not in ASCII_WHITESPACE:
                break
            end -= 1

        return start - end

    def left_strip(self, span: Range) -> int:
        text = self.src[span.start:span.end]
        return len(text) - len(text.lstrip())

    def is_empty(self, span: Range) -> bool:
        text = self.src[span.start:span.end]
        return len(text.strip()) == 0

    def drop_trailing_empty_lines(self, lines: List[Range]) -> List[Range]:

        end = len(lines)
        while end > 0:
            if self.is_empty(lines[end-1]):
                end -= 1
            else:
                break

        return lines[:end]
        

    def char_at(self, pos: int) -> str | None:
        if pos < self.length:
            return self.src[pos]
        else:
            return None

    def text(self, start: int, end: int) -> str:
        return self.src[start:end]

    def read_seq(self, span: Range, ch: str) -> int:
        """Count consecutive chars"""        
        if self.char_at(span.start) != ch:
            return 0
        
        i = span.start
        
        while i <= span.end:
            if self.char_at(i) != ch:
                break
            i += 1
        
        return i - span.start

    def read_heading_level(self, span: Range) -> int | None:
        level = self.read_seq(span, '#')
        end_char = self.char_at(span.start + level)
        if end_char is None or end_char in ASCII_WHITESPACE:
            return level

        return None

    def is_none_or_whitespace(self, pos: int) -> bool:
        ch = self.char_at(pos)
        if ch is None:
            return True
        return ch in ASCII_WHITESPACE

    def find_attr_end(self, span: Range) -> int:
        state = State.START
        
        i = span.start
        ch = self.char_at(i)

        while ch is not None and i < span.end:
            i += 1
            state = state.step(ch)
            match state:
                case State.DONE | State.INVALID:
                    break

        if state == State.DONE:
            return i
        else:
            return -1

    def is_table_row(self, span: Range) -> bool:
        if len(span) < 2:
            return False

        if self.char_at(span.end - 1) != '|':
            return False

        if self.char_at(span.end-1) == '\\' and self.char_at(span.end-1) == '|':
            return False

        return True

    def find_definition_label(self, span: Range) -> str | None:
        right_bracket = self.src.find(']', span.start)
        if right_bracket == -1:
            return None

        if self.char_at(right_bracket+1) != ':':
            return None
        
        return self.src[span.start+1:right_bracket]

    def is_thematic_break(self, span: Range) -> bool:
        i = span.start

        n = 1
        while i < span.end:
            ch = self.src[i]
            if ch in '-*':
                n += 1
            elif not ch in ASCII_WHITESPACE:
                return False
            i += 1

        return n >= 3

    def is_task(self, span: Range) -> bool:
        pos = span.start + 1 # after -, *, +
        if not self.is_none_or_whitespace(pos):
            return False

        pos += 1
        if self.char_at(pos) != '[':
            return False

        pos += 1
        ch = self.char_at(pos)
        if ch is None:
            return False
        if ch not in ' xX':
            return False

        pos += 1
        if self.char_at(pos) != ']':
            return False

        pos += 1
        if not self.is_none_or_whitespace(pos):
            return False

        return True

