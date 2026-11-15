from dataclasses import dataclass


@dataclass(slots=True)
class Range:
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start

    def is_empty(self) -> bool:
        return self.start >= self.end

    def contains(self, pos: int) -> bool:
        return self.start <= pos < self.end

    def to_slice(self) -> slice:
        return slice(self.start, self.end)