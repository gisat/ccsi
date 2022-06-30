# base classes
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, PrivateAttr


class BaseModelSetter(BaseModel):

    class Config:
        allow_mutation = True


class BaseModelPartialEQ(BaseModel):

    def __eq__(self, other: BaseModel):
        return all([sv == other.__dict__[sk] for sk, sv in self.__dict__.items() if sv is not None])


# schema
class Attrib(BaseModelSetter, BaseModelPartialEQ):
    href: Optional[str]
    rel: Optional[str]
    type: Optional[str]


class Tag(BaseModelSetter, BaseModelPartialEQ):
    tag: str
    text: Optional[str]
    attrib: Optional[Attrib]


class Entry(BaseModelSetter):
    entry: List[Tag] = Field(default_factory=list)


class Feed(BaseModelSetter):
    entries: List[Entry] = Field(default_factory=list)
    head: Optional[List[Tag]] = Field(default_factory=list)
    totalResults: int = Field(default=0)


# schema
class JsonCCSISchema(BaseModelSetter):
    feeds: Optional[List[Feed]]
    _level: Literal['feeds', 'entries', 'tags'] = PrivateAttr(default='entries')

    def __iter__(self):
        """iter trought certain level """
        for feed in self.feeds:
            if self._level == 'feeds':
                yield feed
            for entry in feed.entries:
                if self._level == 'entries':
                    yield entry
                for tag in entry.entry:
                    if self._level == 'tags':
                        yield tag

    def __next__(self):
        return self

    def __call__(self, level: Literal['feeds', 'entries', 'tags'] = 'tags'):
        self._level = level
        return self