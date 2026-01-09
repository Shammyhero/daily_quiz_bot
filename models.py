from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: int
    telegram_id: int
    track: Optional[str]
    preferred_time: str
    last_sent_date: Optional[str]
    is_active: bool
    created_at: str

@dataclass
class Question:
    id: int
    track: str
    difficulty: str
    question_text: str
    canonical_answer: str
    explanation: str

@dataclass
class UserQuestion:
    id: int
    user_id: int
    question_id: int
    answered_correctly: bool
    llm_confidence: float
    user_answer: str
    answered_at: str
