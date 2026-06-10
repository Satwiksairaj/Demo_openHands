from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import crud
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/bookmarks", response_model=list[schemas.Bookmark])
def list_bookmarks(tag: str = None, db: Session = Depends(get_db)):
    return crud.get_bookmarks(db, tag=tag)

@app.post("/bookmarks", response_model=schemas.Bookmark)
def create_bookmark(bookmark: schemas.BookmarkCreate, db: Session = Depends(get_db)):
    return crud.create_bookmark(db, bookmark)

@app.delete("/bookmarks/{bookmark_id}", response_model=schemas.Bookmark)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    db_bookmark = crud.get_bookmark(db, bookmark_id)
    if db_bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return crud.delete_bookmark(db, bookmark_id)

@app.get("/bookmarks/favorites", response_model=list[schemas.Bookmark])
def list_favorite_bookmarks(db: Session = Depends(get_db)):
    return crud.get_favorite_bookmarks(db)

@app.get("/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)):
    return crud.get_unique_tags(db)