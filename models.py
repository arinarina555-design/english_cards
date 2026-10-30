from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(40), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    words = relationship(
        "UserWord", back_populates="user", cascade="all, delete-orphan"
    )
    stats = relationship(
        "LearningStat", back_populates="user", cascade="all, delete-orphan"
    )


class CommonWord(Base):
    __tablename__ = "common_words"

    id = Column(Integer, primary_key=True)
    russian_word = Column(String(40), nullable=False, unique=True)
    english_word = Column(String(40), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_words = relationship("UserWord", back_populates="common_word")


class UserWord(Base):
    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # NULL означает персональное слово; иначе ссылка на CommonWord.
    word_id = Column(
        Integer, ForeignKey("common_words.id", ondelete="CASCADE"), nullable=True
    )
    russian_word = Column(String(40), nullable=False)
    english_word = Column(String(40), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="words")
    common_word = relationship("CommonWord", back_populates="user_words")
    stats = relationship(
        "LearningStat", back_populates="user_word", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "russian_word", "english_word", name="user_word_unique"
        ),
    )


class LearningStat(Base):
    __tablename__ = "learning_stats"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    word_id = Column(
        Integer, ForeignKey("user_words.id", ondelete="CASCADE"), nullable=False
    )
    word_type = Column(String(10), nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    total_attempts = Column(Integer, default=0, nullable=False)
    last_reviewed = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="stats")
    user_word = relationship("UserWord", back_populates="stats")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_learning_stat_user_word"),
        CheckConstraint(
            "word_type IN ('common', 'personal')", name="ck_learning_stat_word_type"
        ),
    )