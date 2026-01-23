"""Atom model and related data structures."""

from pydantic import BaseModel, Field

from .enums import AtomStatus, AtomType, Confidence, LinkRel, SourceKind


class Source(BaseModel):
    """Reference source for a knowledge atom."""

    kind: SourceKind
    ref: str


class Link(BaseModel):
    """Link to another knowledge atom."""

    rel: LinkRel
    id: str


class UpdateNote(BaseModel):
    """Note about an update to the atom."""

    date: str
    note: str


class AtomContent(BaseModel):
    """Content of a knowledge atom."""

    summary: str
    details: str = ""
    pitfalls: list[str] = Field(default_factory=list)
    update_notes: list[UpdateNote] = Field(default_factory=list)


class Atom(BaseModel):
    """Knowledge atom - the fundamental unit of knowledge storage."""

    id: str
    title: str
    type: AtomType
    status: AtomStatus
    confidence: Confidence
    content: AtomContent
    language: str | None = None
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None

    model_config = {"use_enum_values": True}
