"""
Database Schemas for SaaS Landing

Each Pydantic model represents a MongoDB collection.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    is_active: bool = Field(True, description="Whether the user is active")


class Blogpost(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: str
    tags: List[str] = []
    published_at: Optional[datetime] = None
    status: str = Field("published", description="draft|published")


class Contactmessage(BaseModel):
    name: str
    email: EmailStr
    message: str
    subject: Optional[str] = None
    handled: bool = False
