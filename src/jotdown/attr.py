from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
import string
from typing import Dict, List, Optional

_ASCII_WHITESPACE = set(' \t\n\r\x0c')

def is_ascii_punctuation(c: str) -> bool:
    return c in string.punctuation

def is_name(c: str) -> bool:
    return (c.isascii and c.isalnum()) or c in {':', '_', '-'}

def is_ascii_whitespace(c: str) -> bool:
    return c in _ASCII_WHITESPACE

def attribute_value_parts(s: str):
    start = 0 # start of current slice
    i = 0 # start of find index.

    while i < len(s):
        j = s.find('\\', i) # find next backslash
        if j == -1:
            # No more backslashes
            yield s[start:]
            break

        # char after backslash
        if j + 1 < len(s):
            if s[j + 1] == '\\':
                # Unescape backslash
                yield s[i:j + 1]
                start = j + 2
                i = j + 2
            elif is_ascii_punctuation(s[j + 1]):
                # Unscape punctuation
                yield s[start:j]
                start = j + 1
                i = j + 1
            else:
                i = j + 1
        else:
            yield s[start:]
            break


class AttrKind(ABC):
    @property
    def key(self) -> Optional[str]:
        return None

@dataclass
class ClassKind(AttrKind):
    @property
    def key(self) -> str:
        return 'class'

    def __repr__(self):
        return "ClassKind()"

@dataclass
class IdKind(AttrKind):
    @property
    def key(self) -> str:
        return 'id'

    def __repr__(self):
        return "IdKind()"

@dataclass
class PairKind(AttrKind):
    key_: str

    @property
    def key(self) -> str:
        return self.key

    def __repr__(self):
        return f"PairKind(key={self.key!r})"

@dataclass
class CommentKind(AttrKind):
    @property
    def key(self) -> Optional[str]:
        return None

    def __repr__(self):
        return "CommentKind()"

@dataclass
class AttributeElem:
    kind: AttrKind
    value: str

class Attributes:
    def __init__(self, elements: Optional[List[AttributeElem]] = None):
        self._elements: List[AttributeElem] = elements or []
        self._idx: Dict[str, List[int]] = {}

    def contains_key(self, key: str) -> bool:
        return key in self._idx

    def get_value(self, key: str) -> Optional[str]:
        if key not in self._idx:
            return None
        if key == 'class':
            idx = self._idx[key]
            values: List[str] = []
            for i in idx:
                v = self._elements[i].value
                if v:
                    values.append(v)
            return ' '.join(values) if values else None

        idx = self._idx.get(key, [])
        if not idx:
            return None
        last = idx[-1]
        return self._elements[last].value

    def push(self, kind: AttrKind, value: str):
        self._elements.append(AttributeElem(kind, value))
        key = kind.key
        if key is None:
            return
        if key not in self._idx:
            self._idx[key] = []

        self._idx[key].append(len(self._elements) - 1)

    def set_last_value(self, value: str):
        self._elements[-1].value = value

    def unique_pairs(self) -> Dict[str, str]:
        data: Dict[str, str] = {}
        for e in self._elements:
            key = e.kind.key
            if key is None:
                continue
            if key == 'class':
                if not e.value:
                    continue
                if key in data and data[key]:
                    data[key] += ' ' + e.value
                else:
                    data[key] = e.value
            else:
                data[key] = e.value

        return data

    def __repr__(self) -> str:
        return f'Attributes({self._elements})'

class State(Enum):
    START = auto()
    WHITESPACE = auto()
    COMMENT_FIRST = auto()
    COMMENT = auto()
    COMMENT_NEWLINE = auto()
    CLASS_FIRST = auto()
    CLASS = auto()
    IDENTIFIER_FIRST = auto()
    IDENTIFIER = auto()
    KEY = auto()
    VALUE_FIRST = auto()
    VALUE = auto()
    VALUE_QUOTED = auto()
    VALUE_ESCAPE = auto()
    VALUE_NEWLINE = auto()
    VALUE_CONTINUED = auto()
    DONE = auto()
    INVALID = auto()

    def step(self, ch: str) -> 'State':
        match self:
            case State.START:
                if ch == '{':
                    return State.WHITESPACE
                else:
                    return State.INVALID
            case State.WHITESPACE:
                if ch == '}':
                    return State.DONE
                elif ch == '.':
                    return State.CLASS_FIRST
                elif ch == '#':
                    return State.IDENTIFIER_FIRST
                elif ch == '%':
                    return State.COMMENT_FIRST
                elif is_name(ch):
                    return State.KEY
                elif is_ascii_whitespace(ch):
                    return State.WHITESPACE
                else:
                    return State.INVALID
            case State.COMMENT_FIRST | State.COMMENT | State.COMMENT_NEWLINE:
                if ch == '%':
                    return State.WHITESPACE
                elif ch == '}':
                    return State.DONE
                elif ch == '\n':
                    return State.COMMENT_NEWLINE
                else:
                    return State.COMMENT
            case State.CLASS_FIRST:
                if is_name(ch):
                    return State.CLASS
                else:
                    return State.INVALID
            case State.IDENTIFIER_FIRST:
                if is_name(ch):
                    return State.IDENTIFIER
                else:
                    return State.INVALID
            case State.CLASS | State.IDENTIFIER | State.VALUE:
                if is_name(ch):
                    return self
                elif is_ascii_whitespace(ch):
                    return State.WHITESPACE
                elif ch == '}':
                    return State.DONE
                else:
                    return State.INVALID
            case State.KEY:
                if is_name(ch):
                    return State.KEY
                elif ch == '=':
                    return State.VALUE_FIRST
                else:
                    return State.INVALID
            case State.VALUE_FIRST:
                if is_name(ch):
                    return State.VALUE
                elif ch == '"':
                    return State.VALUE_QUOTED
                else:
                    return State.INVALID
            case State.VALUE_QUOTED:
                if ch == '"':
                    return State.WHITESPACE
                elif ch == '\n':
                    return State.VALUE_NEWLINE
                elif ch == '\\':
                    return State.VALUE_ESCAPE
                else:
                    return State.VALUE_QUOTED
            case State.VALUE_NEWLINE | State.VALUE_CONTINUED:
                if ch == '"':
                    return State.WHITESPACE
                elif ch == '\n':
                    return State.VALUE_NEWLINE
                else:
                    return State.VALUE_CONTINUED
            case State.VALUE_ESCAPE:
                if ch == '\n':
                    return State.VALUE_NEWLINE
                else:
                    return State.VALUE_QUOTED
            case State.INVALID | State.DONE:
                raise Exception(f'Invalid state {self.name}')

class ParseError(Exception):
    pass

class InvalidStateError(ParseError):
    def __init__(self, pos: int):
        self.pos = pos


class Parser:
    def __init__(self, attrs: Attributes):
        self.attrs = attrs
        self.state = State.START

    def parse(self, src: str) -> int:
        pos_prev = 0 # update upon state changed

        for pos, c in enumerate(src):
            state_next = self.state.step(c)

            if state_next == State.INVALID:
                raise InvalidStateError(pos)

            prev_state = self.state
            self.state = state_next

            if prev_state != self.state and (prev_state != State.VALUE_ESCAPE or self.state != State.VALUE_ESCAPE):
                content = src[pos_prev:pos]
                pos_prev = pos
                match prev_state:
                    case State.CLASS:
                        self.attrs.push(ClassKind(), content)
                    case State.IDENTIFIER:
                        self.attrs.push(IdKind(), content)
                    case State.KEY:
                        self.attrs.push(PairKind(content), '')
                    case State.VALUE | State.VALUE_QUOTED | State.VALUE_CONTINUED:
                        idx = 0
                        if prev_state == State.VALUE_QUOTED:
                            idx = 1
                        self.attrs.set_last_value(content[idx:])
                    case State.COMMENT | State.COMMENT_NEWLINE:
                        if prev_state == State.COMMENT:
                            self.attrs.set_last_value(content)
                        else:
                            self.attrs.set_last_value('\n')
                    case State.COMMENT_FIRST:
                        self.attrs.push(CommentKind(), "")
                    case _:
                        pass

            assert self.state != State.INVALID

            if self.state == State.DONE:
                if src[pos+1:].startswith('{'):
                    self.state = State.START
                else:
                    return pos + 1

        return len(src)

    def finish(self) -> Attributes:
        return self.attrs

class AttrbuteParser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.attrs = Attributes()

    def parse(self, src: str):
        self._expect("{")
        while self.pos < self.length:
            self._skip_whitespace()

            if self.pos >= self.length or self.text[self.pos] == '}':
                break

            ch = self.text[self.pos]
            if ch == '.':
                self._parse_class()
            elif ch == '#':
                self._parse_id()
            elif ch == '%':
                self._parse_comment()
            else:
                self._parse_pair()

        self._expect('}')
        return self.attrs

    def _expect(self, expected: str):
        if self.pos < self.length and self.text[self.pos] == expected:
            self.pos += 1
        else:
            raise ParseError(f"Expected {expected} at position {self.pos}")

    def _parse_class(self):
        self.pos += 1 # ignore the '.'
        value = self._read_identifier()
        self.attrs.push(ClassKind(), value)

    def _parse_id(self):
        self.pos += 1 # ignore the '#'
        value = self._read_identifier()
        self.attrs.push(IdKind(), value)

    def _parse_comment(self):
        
        self.pos += 1 # ignore the '%'
        value = self._read_comment()
        self.attrs.push(CommentKind(), value)

    def _parse_pair(self):
        key = self._read_identifier()
        self._skip_whitespace()
        self._expect('=')
        self._skip_whitespace()

        if self.text[self.pos] == '"':
            value = self._read_quoted_string()
        else:
            value = self._read_identifier()

        self.attrs.push(PairKind(key), value)

    # === Lexer methods ===

    def _read_identifier(self) -> str:
        start = self.pos
        while self.pos < self.length and is_name(self.text[self.pos]):
            self.pos += 1
        return self.text[start:self.pos]

    def _read_quoted_string(self) -> str:
        self.pos += 1 # skip opening `"`
        start = self.pos
        escaped = False

        while self.pos < self.length:
            ch = self.text[self.pos]
            # "foo\\\\"
            # "foo\"bar"
            if not escaped and ch == '\\':
                escaped = True
                self.pos += 1
                continue
            if not escaped and ch == '"':
                end = self.pos
                self.pos += 1
                return self.text[start:end]
            escaped = False
            self.pos += 1

        raise ParseError("Unclosed quote")

    def _read_comment(self) -> str:
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]

            if ch == '}':
                end = self.pos
                self.pos += 1
                return self.text[start:end]
            if ch == '%':
                # TODO: the specification does not say if escaped % should be allowed inside comment.
                end = self.pos
                self.pos += 1
                return self.text[start:end]
            self.pos += 1

        raise ParseError("Unclosed comment")



    def _skip_whitespace(self):
        while self.pos < self.length and is_ascii_whitespace(self.text[self.pos]):
            self.pos += 1 # stops at first non-whitespace
