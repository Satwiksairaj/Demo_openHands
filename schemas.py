from pydantic import BaseModel

class BookmarkBase(BaseModel):
    url: str
    title: str
    is_favorite: bool = False
    tags: str = ""

class BookmarkCreate(BookmarkBase):
    pass

class Bookmark(BookmarkBase):
    id: int

    class Config:
        orm_mode = True