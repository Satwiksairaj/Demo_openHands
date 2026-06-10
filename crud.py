from sqlalchemy.orm import Session
import models
import schemas

def get_bookmarks(db: Session, tag: str = None):
    if tag:
        return db.query(models.Bookmark).filter(models.Bookmark.tags.contains(tag)).all()
    return db.query(models.Bookmark).all()

def create_bookmark(db: Session, bookmark: schemas.BookmarkCreate):
    db_bookmark = models.Bookmark(**bookmark.dict())
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark

def get_bookmark(db: Session, bookmark_id: int):
    return db.query(models.Bookmark).filter(models.Bookmark.id == bookmark_id).first()

def delete_bookmark(db: Session, bookmark_id: int):
    db_bookmark = get_bookmark(db, bookmark_id)
    db.delete(db_bookmark)
    db.commit()
    return db_bookmark

def get_favorite_bookmarks(db: Session):
    return db.query(models.Bookmark).filter(models.Bookmark.is_favorite == True).all()

def get_unique_tags(db: Session):
    bookmarks = db.query(models.Bookmark).all()
    tags = set()
    for bookmark in bookmarks:
        tags.update(bookmark.tags.split(','))
    return list(tags)