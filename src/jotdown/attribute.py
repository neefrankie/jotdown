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

        escaped = False # handle % and }
        while self.pos < self.length:
            ch = self.text[self.pos]
            if not escaped:
                if ch == '\\':
                    escaped = True
                    self.pos += 1
                    continue
                elif ch == '%':
                    # comment ends
                    end = self.pos
                    self.pos += 1
                    return self.text[start:end]
                elif ch == '}': # Leave the closing brace to caller.
                    end = self.pos
                    return self.text[start:end]
            self.pos += 1
            escaped = False

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


def find_attribute_end(src: str, start_pos: int) -> int:
    """
    给定原始字符串 src 和起始 '{' 的位置 start_pos，
    返回匹配的 '}' 的索引位置。如果未匹配成功，返回 -1。
    """
    n = len(src)
    i = start_pos + 1  # 跳过开头的 '{'
    
    in_string = False
    in_comment = False
    
    while i < n:
        c = src[i]
        
        # 1. 处理转义字符：直接跳过下一个字符
        if c == '\\':
            i += 2
            continue
            
        # 2. 处理字符串内部状态
        if c == '"' and not in_comment:
            in_string = not in_string
            i += 1
            continue
            
        # 3. 处理注释内部状态
        if c == '%' and not in_string:
            in_comment = not in_comment
            i += 1
            continue
            
        # 4. 在非字符串、非注释状态下寻找闭合大括号
        if c == '}' and not in_string and not in_comment:
            return i
            
        # 5. 如果遇到换行符且不在注释/字符串中（根据 Djot 规范，块级属性可跨行，但内联属性不能跨空行）
        # 这里可以根据需要加入边界拦截
        
        i += 1
        
    return -1  # 没找到匹配的 '}'

# 多组属性之间允许空白吗？
# 允许，但仅限无换行的空白字符（Spaces 和 Tabs），不能跨空行。
# 1. 紧贴排列：{.c1}{.c2}（最常见的无缝连接）。
# 2. 同行空格/Tab：{.c1}   {.c2}（合法，视为连续属性）。
# 3. 普通换行：在块级属性中，只要中间没有空行（Blank Line），换行也是允许的（如连续两行的属性块）。
# 4. 遇空行中断：如果属性块之间出现了空行，或者遇到了非空白的普通文本，属性链条即宣告终止。

def is_inline_space(ch: str) -> bool:
    return ch in " \t"

def scan_attribute_chain(src: str, start_pos: int):
    i = start_pos
    n = len(src)

    while i < n and src[i] == '{':
        # 寻找当前这组 '{...}' 的闭合位置
        end_pos = find_attribute_end(src, i)
        if end_pos == -1:
            break

        # 游标移动到当前 '}' 的下一位
        i = end_pos + 1

        # 跳过属性块之间的空白字符（Spaces, Tabs, 甚至非空行的换行）
        lookahead = i
        while lookahead < n and is_ascii_whitespace(src[lookahead]):
            # 如果遇到连续两个换行（即空行），说明属性块链终止
            if src[lookahead] == '\n' and lookahead + 1 < n and src[lookahead + 1] == '\n':
                break
            lookahead += 1

        # 如果跳过空白后紧接着又是 '{'，则继续下一轮循环
        if lookahead < n and src[lookahead] == '{':
            i = lookahead
        else:
            # 后面不是属性块了，退出循环
            break

    return i