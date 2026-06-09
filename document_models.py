from dataclasses import dataclass, field


@dataclass
class Section:
    heading: str | None
    level: int | None
    content: list[str]


@dataclass
class Chunk:
    chunk_index: int
    chunk_id: str
    section_heading: str | None
    content: str


@dataclass
class ParsedDocument:
    page_id: str
    title: str
    source_url: str
    labels: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
