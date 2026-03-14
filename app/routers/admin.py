from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, UserCourse
from app.models.course import Module, Course, Lesson
from app.models.payment import Payment
from app.models.test import Test, TestQuestion, TestSubmission
from app.models.homework import Homework, HomeworkSubmission
from app.models.game import GameExample, GameSubmission
from app.models.exam import Exam, ExamQuestion, ExamSubmission
from app.models.progress import LessonProgress
from app.utils.auth import get_current_admin
from app.schemas.course import ModuleCreate, ModuleUpdate, CourseCreate, CourseUpdate, LessonCreate, LessonUpdate
from app.schemas.test import TestCreate, HomeworkCreate, GameCreate, ExamCreate, HomeworkGradeRequest
from app.schemas.payment import PaymentReview

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== DASHBOARD ====================
@router.get("/dashboard")
async def admin_dashboard(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    students = await db.execute(select(func.count()).select_from(User).where(User.role == "student"))
    modules = await db.execute(select(func.count()).select_from(Module))
    courses = await db.execute(select(func.count()).select_from(Course))
    lessons = await db.execute(select(func.count()).select_from(Lesson))
    pending_payments = await db.execute(
        select(func.count()).select_from(Payment).where(Payment.status == "pending")
    )
    approved_payments = await db.execute(
        select(func.count()).select_from(Payment).where(Payment.status == "approved")
    )
    return {
        "total_students": students.scalar() or 0,
        "total_modules": modules.scalar() or 0,
        "total_courses": courses.scalar() or 0,
        "total_lessons": lessons.scalar() or 0,
        "pending_payments": pending_payments.scalar() or 0,
        "approved_payments": approved_payments.scalar() or 0,
    }


# ==================== STUDENTS ====================
@router.get("/students")
async def list_students(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).where(User.role == "student").order_by(User.created_at.desc()))
    users = result.scalars().all()
    response = []
    for u in users:
        # Count payments
        payment_result = await db.execute(
            select(func.count()).select_from(Payment).where(
                Payment.user_id == u.id, Payment.status == "approved"
            )
        )
        paid_modules = payment_result.scalar() or 0
        # Count completed lessons
        progress_result = await db.execute(
            select(func.count()).where(
                LessonProgress.user_id == u.id, LessonProgress.is_completed == True
            )
        )
        completed = progress_result.scalar() or 0

        response.append({
            "id": u.id,
            "full_name": u.full_name,
            "phone": u.phone,
            "is_active": u.is_active,
            "created_at": str(u.created_at),
            "paid_modules": paid_modules,
            "completed_lessons": completed,
        })
    return response


@router.get("/students/{user_id}")
async def get_student_detail(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")

    # Payments
    payments_result = await db.execute(
        select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
    )
    payments = payments_result.scalars().all()

    # Test submissions
    tests_result = await db.execute(
        select(TestSubmission).where(TestSubmission.user_id == user_id)
    )
    test_subs = tests_result.scalars().all()

    # Homework submissions
    hw_result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.user_id == user_id)
    )
    hw_subs = hw_result.scalars().all()

    # Progress
    prog_result = await db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user_id)
    )
    progress = prog_result.scalars().all()

    return {
        "id": user.id,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "avatar": user.avatar,
        "bio": user.bio,
        "created_at": str(user.created_at),
        "payments": [{"id": p.id, "module_id": p.module_id, "amount": p.amount, "status": p.status, "created_at": str(p.created_at)} for p in payments],
        "test_submissions": [{"id": s.id, "test_id": s.test_id, "score": s.score, "total": s.total, "passed": s.passed} for s in test_subs],
        "homework_submissions": [{"id": s.id, "homework_id": s.homework_id, "score": s.score, "is_graded": s.is_graded} for s in hw_subs],
        "lesson_progress": [{"lesson_id": p.lesson_id, "video_watched": p.video_watched, "test_passed": p.test_passed, "game_completed": p.game_completed, "homework_submitted": p.homework_submitted, "is_completed": p.is_completed} for p in progress],
    }


class StudentUpdateAdmin(BaseModel):
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


@router.patch("/students/{user_id}")
async def update_student(user_id: int, data: StudentUpdateAdmin, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    await db.commit()
    return {"success": True}


@router.delete("/students/{user_id}")
async def delete_student(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    await db.delete(user)
    await db.commit()
    return {"success": True}


# ==================== MODULES ====================
@router.post("/modules")
async def create_module(data: ModuleCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    m = Module(**data.model_dump())
    db.add(m)
    await db.commit()
    return {"id": m.id}


@router.put("/modules/{module_id}")
async def update_module(module_id: int, data: ModuleUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Module).where(Module.id == module_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Modul topilmadi")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    await db.commit()
    return {"success": True}


@router.delete("/modules/{module_id}")
async def delete_module(module_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Module).where(Module.id == module_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Modul topilmadi")
    await db.delete(m)
    await db.commit()
    return {"success": True}


# ==================== COURSES ====================
@router.post("/courses")
async def create_course(data: CourseCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    course = Course(**data.model_dump())
    db.add(course)
    await db.commit()
    return {"id": course.id}


@router.put("/courses/{course_id}")
async def update_course(course_id: int, data: CourseUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    await db.commit()
    return {"success": True}


@router.delete("/courses/{course_id}")
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")
    await db.delete(course)
    await db.commit()
    return {"success": True}


# ==================== LESSONS ====================
@router.get("/lessons")
async def list_lessons(course_id: int = None, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    q = select(Lesson)
    if course_id:
        q = q.where(Lesson.course_id == course_id)
    q = q.order_by(Lesson.order)
    result = await db.execute(q)
    lessons = result.scalars().all()
    return [{"id": l.id, "course_id": l.course_id, "title": l.title, "slug": l.slug, "order": l.order, "is_free": l.is_free, "video_url": l.video_url} for l in lessons]


@router.post("/lessons")
async def create_lesson(data: LessonCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    lesson = Lesson(**data.model_dump())
    db.add(lesson)
    await db.commit()
    return {"id": lesson.id}


@router.put("/lessons/{lesson_id}")
async def update_lesson(lesson_id: int, data: LessonUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(lesson, k, v)
    await db.commit()
    return {"success": True}


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
    await db.delete(lesson)
    await db.commit()
    return {"success": True}


# ==================== TESTS ====================
@router.post("/tests")
async def create_test(data: TestCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    test = Test(lesson_id=data.lesson_id, title=data.title, time_limit=data.time_limit, passing_score=data.passing_score)
    db.add(test)
    await db.flush()
    for q_data in data.questions:
        q = TestQuestion(test_id=test.id, **q_data.model_dump())
        db.add(q)
    await db.commit()
    return {"id": test.id}


@router.get("/tests/{test_id}")
async def get_test_admin(test_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return {
        "id": test.id, "lesson_id": test.lesson_id, "title": test.title,
        "time_limit": test.time_limit, "passing_score": test.passing_score,
        "questions": [{"id": q.id, "question": q.question, "option_a": q.option_a, "option_b": q.option_b,
                       "option_c": q.option_c, "option_d": q.option_d, "correct_option": q.correct_option, "order": q.order}
                      for q in sorted(test.questions, key=lambda x: x.order)]
    }


@router.delete("/tests/{test_id}")
async def delete_test(test_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    await db.delete(test)
    await db.commit()
    return {"success": True}


# ==================== HOMEWORK ====================
@router.post("/homework")
async def create_homework(data: HomeworkCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    hw = Homework(**data.model_dump())
    db.add(hw)
    await db.commit()
    return {"id": hw.id}


@router.delete("/homework/{hw_id}")
async def delete_homework(hw_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Homework).where(Homework.id == hw_id))
    hw = result.scalar_one_or_none()
    if not hw:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi")
    await db.delete(hw)
    await db.commit()
    return {"success": True}


@router.get("/homework/submissions")
async def get_all_homework_submissions(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(HomeworkSubmission).order_by(HomeworkSubmission.submitted_at.desc()))
    subs = result.scalars().all()
    response = []
    for s in subs:
        user_result = await db.execute(select(User).where(User.id == s.user_id))
        user = user_result.scalar_one_or_none()
        hw_result = await db.execute(select(Homework).where(Homework.id == s.homework_id))
        hw = hw_result.scalar_one_or_none()
        response.append({
            "id": s.id, "user_id": s.user_id, "user_name": user.full_name if user else "",
            "homework_id": s.homework_id, "homework_title": hw.title if hw else "",
            "answer_text": s.answer_text, "file_url": s.file_url,
            "score": s.score, "is_graded": s.is_graded, "admin_comment": s.admin_comment,
            "submitted_at": str(s.submitted_at),
        })
    return response


@router.patch("/homework/submissions/{sub_id}/grade")
async def grade_homework(sub_id: int, data: HomeworkGradeRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(HomeworkSubmission).where(HomeworkSubmission.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Topshiriq topilmadi")
    if data.score < 0 or data.score > 10:
        raise HTTPException(status_code=400, detail="Baho 0 dan 10 gacha bo'lishi kerak")
    sub.score = data.score
    sub.admin_comment = data.admin_comment
    sub.is_graded = True
    sub.graded_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# ==================== GAMES ====================
@router.post("/games")
async def create_game(data: GameCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    game = GameExample(**data.model_dump())
    db.add(game)
    await db.commit()
    return {"id": game.id}


@router.delete("/games/{game_id}")
async def delete_game(game_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(GameExample).where(GameExample.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="O'yin topilmadi")
    await db.delete(game)
    await db.commit()
    return {"success": True}


# ==================== EXAMS ====================
@router.post("/exams")
async def create_exam(data: ExamCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    exam = Exam(course_id=data.course_id, title=data.title, after_lesson_order=data.after_lesson_order,
                time_limit=data.time_limit, passing_score=data.passing_score)
    db.add(exam)
    await db.flush()
    for q_data in data.questions:
        q = ExamQuestion(exam_id=exam.id, **q_data.model_dump())
        db.add(q)
    await db.commit()
    return {"id": exam.id}


@router.delete("/exams/{exam_id}")
async def delete_exam(exam_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Imtihon topilmadi")
    await db.delete(exam)
    await db.commit()
    return {"success": True}


# ==================== PAYMENTS ====================
@router.get("/payments")
async def list_payments(status: str = None, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    q = select(Payment).order_by(Payment.created_at.desc())
    if status:
        q = q.where(Payment.status == status)
    result = await db.execute(q)
    payments = result.scalars().all()
    response = []
    for p in payments:
        user_result = await db.execute(select(User).where(User.id == p.user_id))
        user = user_result.scalar_one_or_none()
        module_result = await db.execute(select(Module).where(Module.id == p.module_id))
        module = module_result.scalar_one_or_none()
        # Telegram link yaratish
        tg_link = None
        if user:
            if user.telegram_username:
                tg_link = f"https://t.me/{user.telegram_username}"
            elif user.telegram_id:
                tg_link = f"tg://user?id={user.telegram_id}"

        response.append({
            "id": p.id, "user_id": p.user_id, "user_name": user.full_name if user else "",
            "user_phone": user.phone if user else "",
            "telegram_link": tg_link,
            "module_id": p.module_id, "module_name": module.name if module else "",
            "amount": p.amount, "status": p.status,
            "check_image_url": p.check_image_url,
            "admin_comment": p.admin_comment,
            "ai_verified": p.ai_verified,
            "ai_comment": p.ai_comment,
            "created_at": str(p.created_at),
            "reviewed_at": str(p.reviewed_at) if p.reviewed_at else None,
        })
    return response


@router.patch("/payments/{payment_id}/review")
async def review_payment(
    payment_id: int,
    data: PaymentReview,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Approve or reject a payment check"""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")
    if payment.status not in ["pending", "auto_approved"]:
        raise HTTPException(status_code=400, detail="Bu to'lov allaqachon ko'rib chiqilgan")

    payment.status = data.status
    payment.admin_comment = data.admin_comment
    payment.reviewed_by = admin.id
    payment.reviewed_at = datetime.utcnow()
    await db.commit()

    # If approved, grant access to all courses in the module
    if data.status == "approved":
        courses_result = await db.execute(
            select(Course).where(Course.module_id == payment.module_id)
        )
        courses = courses_result.scalars().all()
        for course in courses:
            uc_result = await db.execute(
                select(UserCourse).where(
                    UserCourse.user_id == payment.user_id,
                    UserCourse.course_id == course.id
                )
            )
            uc = uc_result.scalar_one_or_none()
            if uc:
                uc.is_paid = True
                uc.purchased_at = datetime.utcnow()
            else:
                uc = UserCourse(
                    user_id=payment.user_id,
                    course_id=course.id,
                    is_paid=True,
                    purchased_at=datetime.utcnow()
                )
                db.add(uc)
        await db.commit()

    return {"success": True, "status": data.status}


# ==================== GRANT COURSE ====================
@router.post("/grant-course")
async def grant_course(user_id: int, course_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(UserCourse).where(UserCourse.user_id == user_id, UserCourse.course_id == course_id))
    uc = result.scalar_one_or_none()
    if uc:
        uc.is_paid = True
        uc.purchased_at = datetime.utcnow()
    else:
        uc = UserCourse(user_id=user_id, course_id=course_id, is_paid=True, purchased_at=datetime.utcnow())
        db.add(uc)
    await db.commit()
    return {"success": True}


# ==================== CERTIFICATES ====================
@router.get("/certificates")
async def list_certificates(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    from app.models.certificate import Certificate
    result = await db.execute(
        select(Certificate).order_by(Certificate.created_at.desc())
    )
    certs = result.scalars().all()
    response = []
    for c in certs:
        u = await db.execute(select(User).where(User.id == c.user_id))
        user = u.scalar_one_or_none()
        response.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_name": user.full_name if user else "?",
            "title": c.title,
            "description": c.description,
            "file_url": c.file_url,
            "issued_at": str(c.issued_at),
        })
    return response


@router.post("/certificates")
async def send_certificate(
    user_id: int, title: str, file_url: str,
    description: str = "",
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    from app.models.certificate import Certificate
    cert = Certificate(
        user_id=user_id,
        title=title,
        description=description,
        file_url=file_url,
    )
    db.add(cert)
    await db.commit()
    return {"id": cert.id, "message": "Sertifikat yuborildi"}


@router.delete("/certificates/{cert_id}")
async def delete_certificate(cert_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    from app.models.certificate import Certificate
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Sertifikat topilmadi")
    await db.delete(cert)
    await db.commit()
    return {"success": True}


# ==================== SELECT DROPDOWN DATA ====================
@router.get("/select/modules")
async def get_modules_for_select(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin formasi uchun modullar ro'yxati (select dropdown)"""
    result = await db.execute(select(Module).where(Module.is_active == True).order_by(Module.order))
    modules = result.scalars().all()
    return [{"id": m.id, "name": m.name, "price": m.price} for m in modules]


@router.get("/select/courses")
async def get_courses_for_select(
    module_id: int = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin formasi uchun kurslar ro'yxati (select dropdown)
    
    module_id berilsa, faqat shu moduldagi kurslar qaytariladi.
    """
    q = select(Course).where(Course.is_active == True).order_by(Course.order)
    if module_id:
        q = q.where(Course.module_id == module_id)
    result = await db.execute(q)
    courses = result.scalars().all()
    
    response = []
    for c in courses:
        module_result = await db.execute(select(Module).where(Module.id == c.module_id))
        module = module_result.scalar_one_or_none()
        response.append({
            "id": c.id,
            "name": c.name,
            "module_id": c.module_id,
            "module_name": module.name if module else "",
        })
    return response


@router.get("/select/lessons")
async def get_lessons_for_select(
    course_id: int = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin formasi uchun darslar ro'yxati (select dropdown)
    
    course_id berilsa, faqat shu kursdagi darslar qaytariladi.
    Test/Vazifa/O'yin yaratishda lesson_id tanlash uchun ishlatiladi.
    """
    q = select(Lesson).order_by(Lesson.order)
    if course_id:
        q = q.where(Lesson.course_id == course_id)
    result = await db.execute(q)
    lessons = result.scalars().all()
    
    response = []
    for l in lessons:
        course_result = await db.execute(select(Course).where(Course.id == l.course_id))
        course = course_result.scalar_one_or_none()
        response.append({
            "id": l.id,
            "title": l.title,
            "order": l.order,
            "course_id": l.course_id,
            "course_name": course.name if course else "",
            "has_test": l.test is not None,
            "has_homework": l.homework is not None,
            "has_game": l.game is not None,
        })
    return response


@router.get("/select/students")
async def get_students_for_select(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin formasi uchun o'quvchilar ro'yxati (select dropdown)
    
    Sertifikat berish, kurs berish uchun student tanlash.
    """
    result = await db.execute(
        select(User).where(User.role == "student", User.is_active == True).order_by(User.full_name)
    )
    users = result.scalars().all()
    return [{"id": u.id, "name": u.full_name, "phone": u.phone} for u in users]
