from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional
from .utils import (
    is_ascii_whitespace,
    is_name_char
)

class AttributeElement(ABC):

    @abstractmethod
    def key(self) -> Optional[str]:
        pass

    @abstractmethod
    def value(self) -> str:
        pass

    @abstractmethod
    def raw_text(self) -> str:
        pass

@dataclass
class ClassAttribute(AttributeElement):
    name: str

    def key(self) -> str | None:
        return 'class'

    def value(self) -> str:
        return self.name

    def raw_text(self) -> str:
        return f'.{self.name}'

    def __repr__(self):
        return f"ClassAttr({self.name!r})"

@dataclass
class IdAttribute(AttributeElement):
    name: str

    def key(self) -> str | None:
        return 'id'

    def value(self) -> str:
        return self.name

    def raw_text(self) -> str:
        return f'#{self.name}'

    def __repr__(self):
        return f"IdAttr({self.name!r})"

@dataclass
class PairAttribute(AttributeElement):
    key_: str
    value_: str

    def key(self) -> str | None:
        return self.key_

    def value(self) -> str:
        return self.value_

    def raw_text(self) -> str:
        if self._needs_quotes():
            return f'{self.key_}="{self.value_}"'
        return f'{self.key_}={self.value_}'

    def _needs_quotes(self) -> bool:
        for ch in self.value_:
            if not is_name_char(ch):
                return True
        return False

    def __repr__(self):
        return f"PairAttr({self.key_!r}, {self.value_!r})"

@dataclass
class CommentAttribute(AttributeElement):
    """Comment: %...%"""
    text: str

    def key(self) -> str | None:
        return None

    def value(self) -> str:
        return self.text

    def raw_text(self) -> str:
        return f'%{self.text}%'

    def __repr__(self):
        return f"CommentAttr({self.text!r})"

class Attributes:
    def __init__(self, elements: Optional[List[AttributeElement]] = None):
        self._elems: List[AttributeElement] = elements or []
        self._idx: Dict[str, List[int]] = defaultdict(list)
        self._build_index()

    def _build_index(self):
        self._idx.clear()
        for i, elem in enumerate(self._elems):
            key = elem.key()
            if key is not None:
                self._idx[key].append(i)

    def push(self, elem: AttributeElement):
        self._elems.append(elem)
        key = elem.key()
        if key is not None:
            self._idx[key].append(len(self._elems) - 1)

    def contains_key(self, key: str) -> bool:
        return key in self._idx

    def get_value(self, key: str) -> Optional[str]:
        if key not in self._idx:
            return None
        if key == 'class':
            idx = self._idx[key]
            values: List[str] = []
            for i in idx:
                v = self._elems[i].value()
                if v:
                    values.append(v)
            return ' '.join(values) if values else None

        idx = self._idx.get(key, [])
        if not idx:
            return None
        last = idx[-1]
        return self._elems[last].value()

    def get_values(self, key: str) -> List[str]:
        """返回所有值（用于 class）"""
        if key not in self._idx:
            return []
        return [self._elems[i].value() for i in self._idx[key]]

    

    def unique_pairs(self) -> Dict[str, str]:
        data: Dict[str, str] = {}
        for e in self._elems:
            key = e.key()
            if key is None:
                continue
            if key == 'class':
                v = e.value()
                if v:
                    if key in data and data[key]:
                        data[key] += ' ' + v
                    else:
                        data[key] = v
            else:
                data[key] = e.value()

        return data

    def raw_text(self) -> str:
        parts = []
        for elem in self._elems:
            parts.append(elem.raw_text())

        return '{' + ' '.join(parts) + '}'

    def __len__(self):
        return len(self._elems)

    def __iter__(self):
        return iter(self._elems)

    def __repr__(self) -> str:
        return f'Attributes({self._elems})'

class ParseError(Exception):
    pass

class AttributeParser:
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.pos = 0

    def parse(self) -> Iterator[AttributeElement]:

        while self.pos < self.length:
            self._skip_whitespace()

            if self.text[self.pos] == '{':
                yield from self._parse_one_block()
            else:
                self.pos += 1

    def finish(self) -> Attributes:
        attrs = Attributes()
        for element in self.parse():
            attrs.push(element)

        return attrs


    def _parse_one_block(self) -> Iterator[AttributeElement]:
        self._expect('{')

        while self.pos < self.length:

            self._skip_whitespace()
            if self.pos >= self.length:
                break
            
            if self.text[self.pos] == '}':
                self.pos += 1
                break

            elem = self._parse_element()
            if elem is not None:
                yield elem
            else:
                raise ParseError(f'Unknown character at {self.pos}: {self.text[self.pos]}')

    def _parse_element(self) -> Optional[AttributeElement]:
        ch = self.text[self.pos]

        if ch == '.':
            return self._parse_class()
        elif ch == '#':
            return self._parse_id()
        elif ch == '%':
            return self._parse_comment()
        elif is_name_char(ch):
            return self._parse_pair()
        else:
            return None

    def _parse_class(self) -> ClassAttribute:
        """
        parse .foo
        """
        self.pos += 1 # ignore the '.'
        value = self._read_identifier()
        if not value:
            raise ParseError(f"Expected class name at {self.pos}")
        return ClassAttribute(value)

    def _parse_id(self) -> IdAttribute:
        """
        Parse #id
        """
        self.pos += 1 # ignore the '#'
        value = self._read_identifier()
        if not value:
            raise ParseError(f"Expected id name at {self.pos}")
        return IdAttribute(value)

    def _parse_comment(self) -> CommentAttribute:
        """
        Parse %...% or %...}.
        """
        content = self._read_comment()
        return CommentAttribute(content)

    def _parse_pair(self) -> PairAttribute:
        key = self._read_identifier()
        if not key:
            raise ParseError(f"Expected key at {self.pos}")
        
        self._skip_whitespace()
        self._expect('=')
        self._skip_whitespace()

        if self.pos < self.length and self.text[self.pos] == '"':
            value = self._read_quoted_string()
        else:
            value = self._read_identifier()
            # Empty string is not not allowed for ascii value.
            if not value:
                raise ParseError(f"Expected value for key {key} at {self.pos}")

        return PairAttribute(key, value)

    # === Lexer methods ===

    def _read_identifier(self) -> Optional[str]:
        """
        Short form of id, class, and unquoted value could be parsed as identifier.
        """
        start = self.pos
        while self.pos < self.length and is_name_char(self.text[self.pos]):
            self.pos += 1
        if self.pos == start:
            # WARNING: caller should handle this case.
            # If cursor is not moved, it will result in infinite loop
            return None
        return self.text[start:self.pos]

    def _read_quoted_string(self) -> str:
        self.pos += 1 # skip opening `"`
        start = self.pos

        escaped = False
        while self.pos < self.length:
            ch = self.text[self.pos]
            # "foo\\\\"
            # "foo\" bar
            if not escaped:
                if ch == '\\':
                    escaped = True
                    self.pos += 1
                    continue
                elif ch == '"':
                    end = self.pos
                    self.pos += 1
                    return self.text[start:end]
            escaped = False
            self.pos += 1

        raise ParseError("Unclosed quoted string")

    def _read_comment(self) -> str:
        self.pos += 1 # ignore the '%'
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '%':
                # comment ends
                end = self.pos
                self.pos += 1
                return self.text[start:end]
            elif ch == '}': # Leave the closing brace to caller.
                end = self.pos
                return self.text[start:end]
            self.pos += 1

        # Reaching EOF, comment not closed.
        return self.text[start:self.pos]

    def _skip_whitespace(self):
        while self.pos < self.length:
            ch = self.text[self.pos]
            if is_ascii_whitespace(ch):
                self.pos += 1
            else:
                break # stops at first non-whitespace

    def _expect(self, expected: str):
        if self.pos < self.length and self.text[self.pos] == expected:
            self.pos += 1
        else:
            raise ParseError(f"Expected {expected} at position {self.pos}")
