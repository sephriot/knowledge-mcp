"""Enumerations for knowledge atom types, statuses, and related values."""

from enum import Enum


class AtomType(str, Enum):
    """Type of knowledge atom."""

    FACT = "fact"
    DECISION = "decision"
    PROCEDURE = "procedure"
    PATTERN = "pattern"
    GOTCHA = "gotcha"
    GLOSSARY = "glossary"
    SNIPPET = "snippet"


class AtomStatus(str, Enum):
    """Status of a knowledge atom."""

    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Confidence(str, Enum):
    """Confidence level of a knowledge atom."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceKind(str, Enum):
    """Kind of source reference."""

    REPO_PATH = "repo_path"
    TICKET = "ticket"
    URL = "url"
    CONVERSATION = "conversation"


class LinkRel(str, Enum):
    """Relationship type of a link between atoms."""

    DEPENDS_ON = "depends_on"
    SEE_ALSO = "see_also"
    CONTRADICTS = "contradicts"
