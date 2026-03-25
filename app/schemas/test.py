from pydantic import BaseModel
from typing import Optional


# --- Test Schemas ---
class TestQuestionCreate(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # a, b, c, d
    order: int = 0


class TestQuestionResponse(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    order: int

    class Config:
        from_attributes = True


class TestQuestionWithAnswer(TestQuestionResponse):
    correct_option: str


class TestCreate(BaseModel):
    lesson_id: int
    title: str
    time_limit: int = 420
    passing_score: int = 7
    questions: list[TestQuestionCreate] = []


class TestResponse(BaseModel):
    id: int
    lesson_id: int
    title: str
    time_limit: int
    passing_score: int
    questions: list[TestQuestionResponse] = []

    class Config:
        from_attributes = True


class TestSubmitRequest(BaseModel):
    answers: dict[str, str]  # {"question_id": "a/b/c/d"}


class TestResultResponse(BaseModel):
    id: int
    test_id: int
    score: int
    total: int
    grade: int = 0  # 1, 2, or 3 based on score
    passed: bool
    started_at: str | None = None
    completed_at: str | None = None

    class Config:
        from_attributes = True


# --- Homework Schemas ---
class HomeworkCreate(BaseModel):
    lesson_id: int
    title: str
    description: str | None = None
    deadline_hours: int = 24


class HomeworkResponse(BaseModel):
    id: int
    lesson_id: int
    title: str
    description: str | None = None
    deadline_hours: int

    class Config:
        from_attributes = True


class HomeworkSubmitRequest(BaseModel):
    answer_text: str | None = None
    file_url: str | None = None


class HomeworkSubmissionResponse(BaseModel):
    id: int
    homework_id: int
    answer_text: str | None = None
    file_url: str | None = None
    score: int | None = None
    admin_comment: str | None = None
    is_graded: bool
    submitted_at: str | None = None

    class Config:
        from_attributes = True


class HomeworkGradeRequest(BaseModel):
    score: int  # 0, 1, or 2
    admin_comment: str | None = None


# --- Game Schemas ---
class GameCreate(BaseModel):
    lesson_id: int
    title: str
    description: str | None = None
    task_data: str | None = None
    time_limit: int = 10800


class GameResponse(BaseModel):
    id: int
    lesson_id: int
    title: str
    description: str | None = None
    task_data: str | None = None
    time_limit: int

    class Config:
        from_attributes = True


class GameSubmitRequest(BaseModel):
    answer_data: str | None = None


class GameSubmissionResponse(BaseModel):
    id: int
    game_id: int
    is_completed: bool
    started_at: str | None = None
    completed_at: str | None = None

    class Config:
        from_attributes = True


# --- Exam Schemas ---
class ExamQuestionCreate(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    order: int = 0


class ExamQuestionResponse(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    order: int

    class Config:
        from_attributes = True


class ExamCreate(BaseModel):
    course_id: int
    title: str
    after_lesson_order: int
    time_limit: int = 1800
    passing_score: int = 60
    questions: list[ExamQuestionCreate] = []


class ExamResponse(BaseModel):
    id: int
    course_id: int
    title: str
    after_lesson_order: int
    time_limit: int
    passing_score: int
    questions: list[ExamQuestionResponse] = []

    class Config:
        from_attributes = True


class ExamSubmitRequest(BaseModel):
    answers: dict[str, str]


class ExamResultResponse(BaseModel):
    id: int
    exam_id: int
    score: int
    total: int
    percentage: int
    passed: bool
    started_at: str | None = None
    completed_at: str | None = None

    class Config:
        from_attributes = True


# --- Rating ---
class TeacherRatingCreate(BaseModel):
    rating: int  # 1-5


class RatingResponse(BaseModel):
    user_id: int
    full_name: str
    total_score: int
    rank: int
