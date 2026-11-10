
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class OCRRecord:
    id: int

    text: str

    x1: int
    y1: int
    x2: int
    y2: int

    confidence: float | None = None

    kind: str = "literary"

    braille: str = ""

    approved: bool = True

    source_word: str = ""

    group_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
