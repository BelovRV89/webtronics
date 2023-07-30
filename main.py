from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
from init_db import User, Post, Like, Dislike
from schemas import (
    PostSchema,
    LikeSchema, PostBase, UserOut, UserCreate,
    PostCreate, LikeCreate, DislikeCreate, DislikeSchema
)

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Создаём базовый класс для SQLAlchemy моделей
Base = declarative_base(bind=engine)

# Создаём фабрику сессий SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаём контекст криптографического алгоритма
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Функция для создания хэша пароля
def get_password_hash(password):
    return pwd_context.hash(password)


# Функция для проверки пароля
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# Функция для создания JWT-токена
def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Создаём таблицы в базе данных
Base.metadata.create_all(bind=engine)

SECRET_KEY = "SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Создаём объект для работы с OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Описываем модель JWT-токена
class Token(BaseModel):
    access_token: str
    token_type: str


# Описываем данные JWT-токена
class TokenData(BaseModel):
    username: Optional[str] = None


# Функция для создания сессии SQLAlchemy
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Функция для получения текущего пользователя
def get_current_user(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(
        User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


app = FastAPI()

# Метод для получения токена
@app.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == form_data.username).first()
    if not user or not verify_password(
            form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Метод для создания пользователя
@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")
    return db_user

# Метод для получения всех постов
@app.get("/posts/", response_model=List[PostSchema])
async def read_posts(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    posts = db.query(Post).all()
    posts_with_is_liked = []
    for post in posts:
        is_liked = db.query(Like).filter(
            Like.post_id == post.id, Like.owner_id == current_user.id).first()
        post_dict = post.__dict__
        post_dict["is_liked"] = is_liked is not None
        posts_with_is_liked.append(post_dict)
    return posts_with_is_liked

# Метод для создания поста
@app.post("/posts/", response_model=PostSchema)
async def create_post(
        post: PostCreate, current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    db_post = Post(**post.dict(), owner_id=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

# Метод для получения поста по ID
@app.get("/posts/{post_id}", response_model=PostSchema)
async def read_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

# Метод для обновления поста
@app.put("/posts/{post_id}", response_model=PostSchema)
async def update_post(
        post_id: int, post: PostBase, db: Session = Depends(get_db)
):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in post.dict().items():
        setattr(db_post, key, value)
    db.commit()
    db.refresh(db_post)
    return db_post


# Метод для удаления поста
@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}

# Метод для создания лайка
@app.post("/likes/", response_model=LikeSchema)
async def create_like(
        like: LikeCreate, current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == like.post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.owner_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="You cannot like your own post")
    db_like = Like(**like.dict(), owner_id=current_user.id)
    db.add(db_like)
    db.commit()
    db.refresh(db_like)
    return db_like

# Метод для получения лайка по ID
@app.get("/likes/{like_id}", response_model=LikeSchema)
async def read_like(like_id: int, db: Session = Depends(get_db)):
    like = db.query(Like).filter(Like.id == like_id).first()
    if like is None:
        raise HTTPException(status_code=404, detail="Like not found")
    return like

# Метод для удаления лайка
@app.delete("/likes/{like_id}")
async def delete_like(like_id: int, db: Session = Depends(get_db)):
    db_like = db.query(Like).filter(Like.id == like_id).first()
    if db_like is None:
        raise HTTPException(status_code=404, detail="Like not found")
    db.delete(db_like)
    db.commit()
    return {"detail": "Like deleted"}

# Метод для создания дизлайка
@app.post("/dislikes/", response_model=DislikeSchema)
async def create_dislike(
        dislike: DislikeCreate, current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == dislike.post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.owner_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="You cannot dislike your own post")
    db_dislike = Dislike(**dislike.dict(), owner_id=current_user.id)
    db.add(db_dislike)
    db.commit()
    db.refresh(db_dislike)
    return db_dislike

# Метод для получения дизлайка по ID
@app.get("/dislikes/{dislike_id}", response_model=DislikeSchema)
async def read_dislike(dislike_id: int, db: Session = Depends(get_db)):
    dislike = db.query(Dislike).filter(Dislike.id == dislike_id).first()
    if dislike is None:
        raise HTTPException(status_code=404, detail="Dislike not found")
    return dislike

# Метод для удаления дизлайка
@app.delete("/dislikes/{dislike_id}")
async def delete_dislike(dislike_id: int, db: Session = Depends(get_db)):
    db_dislike = db.query(Dislike).filter(Dislike.id == dislike_id).first()
    if db_dislike is None:
        raise HTTPException(status_code=404, detail="Dislike not found")
    db.delete(db_dislike)
    db.commit()
    return {"detail": "Dislike deleted"}
