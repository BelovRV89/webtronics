from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Описываем модели таблиц базы данных
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))


class Dislike(Base):
    __tablename__ = "dislikes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))


engine = create_engine('sqlite:///./test.db')
Base.metadata.create_all(engine)
