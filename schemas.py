from typing import Optional
from pydantic import BaseModel


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserSchema(UserBase):
    id: int

    class Config:
        orm_mode = True


class PostBase(BaseModel):
    content: str


class PostCreate(PostBase):
    pass


class PostSchema(BaseModel):
    id: Optional[int]
    content: str
    owner_id: int
    is_liked: Optional[bool]

    class Config:
        orm_mode = True


class LikeBase(BaseModel):
    post_id: int


class LikeCreate(LikeBase):
    pass


class LikeSchema(LikeBase):
    id: int

    class Config:
        orm_mode = True


class DislikeBase(BaseModel):
    post_id: int


class DislikeCreate(DislikeBase):
    pass


class DislikeSchema(DislikeBase):
    id: int

    class Config:
        orm_mode = True
