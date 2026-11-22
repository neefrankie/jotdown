from dataclasses import dataclass

from jotdown.common import (
    Range,
)

from .reader import Reader

@dataclass(frozen=True, slots=True)
class HeadingParts:
    indent: int
    level: int
    post_hash_space: int

    def __len__(self):
        return self.indent + self.level + self.post_hash_space

def parse_heading(reader: Reader, span: Range):
    pos = span.start
    leading_space = reader.skip_space(pos, span.end)

    pos += leading_space
    if reader.char_at(pos) != '#':
        return None

    level = reader.count_seq('#', pos, span.end)
    if level == 0:
        return None

    pos += level
    post_hash_ws = reader.skip_space(pos, span.end)

    if post_hash_ws == 0:
        return None

    return HeadingParts(
        indent=leading_space,
        level=level,
        post_hash_space=post_hash_ws
    )