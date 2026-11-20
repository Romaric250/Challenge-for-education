"""Create a sample school, accounts, and an original mathematics booklet."""

# mypy: disable-error-code="no-untyped-call"

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pymupdf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tutor_api.core.passwords import hash_password
from tutor_api.core.settings import get_settings
from tutor_api.db.engine import create_database_engine
from tutor_api.ingestion.pipeline import ingest_pdf
from tutor_api.models.identity import ClassEnrollment, ClassGroup, School, User
from tutor_api.tutor.prompts import repo_file

_TEACHER_PASSWORD = "orchard-maple-19"  # noqa: S105
_STUDENT_PASSWORD = "orchard-cedar-19"  # noqa: S105

_CHAPTERS = (
    (
        "Chapter 1 Whole numbers",
        "A whole number is 0, 1, 2, 3, and so on. It has no fractional part. "
        "The place value of a digit depends on its position. In 3,482 the digit 4 is hundreds.",
    ),
    (
        "Chapter 2 Factors and multiples",
        "A factor of a number divides it with no remainder. 1, 2, 3, and 6 are factors of 6. "
        "A multiple of 4 is 4, 8, 12, or 16. The lowest common multiple of 4 and 6 is 12.",
    ),
    (
        "Chapter 3 Fractions",
        "A fraction names equal parts of a whole. 3/4 means 3 of 4 equal parts. "
        "To add fractions with the same denominator, add the numerators. 1/5 + 2/5 = 3/5.",
    ),
    (
        "Chapter 4 Decimals",
        "A decimal uses a point to show parts of one. 0.5 is five tenths, which equals 1/2. "
        "To multiply by 10, move each digit one place to the left.",
    ),
    (
        "Chapter 5 Percentages",
        "A percentage is a fraction with denominator 100. 25% means 25/100, which is 1/4. "
        "To find 10% of 80, divide 80 by 10. The result is 8.",
    ),
    (
        "Chapter 6 Integers",
        "Integers are whole numbers and their opposites: ..., -2, -1, 0, 1, 2, ... "
        "Adding a negative number moves left on the number line. 3 + (-5) = -2.",
    ),
    (
        "Chapter 7 Algebraic expressions",
        "An expression can contain a number, a letter, and an operation. 2x + 3 means "
        "two groups of x, then add 3. Like terms have the same letter part. 2x + 5x = 7x.",
    ),
    (
        "Chapter 8 Linear equations",
        "Solve 2x + 3 = 11. Subtract 3 from both sides: 2x = 8. Divide both sides by 2: x = 4. "
        "Check by substitution: 2(4) + 3 = 11. The unknown is 4.",
    ),
    (
        "Chapter 9 Ratio and proportion",
        "A ratio compares quantities. 2:3 means 2 parts to 3 parts. "
        "If 2 books cost 600 francs, 1 book costs 300 francs, so 5 books cost 1,500 francs.",
    ),
    (
        "Chapter 10 Statistics tables",
        "A table organises data. Scores | Count. 1 | 2. 2 | 5. 3 | 3. "
        "The mode is the score that appears most often. Here the mode is 2 because its count is 5.",
    ),
)


def _write_booklet(path: Path) -> None:
    document = pymupdf.open()
    for title, body in _CHAPTERS:
        page = document.new_page()
        page.insert_text((72, 72), f"{title}\n\n{body}", fontsize=12)
    document.save(path)
    document.close()


async def _seed() -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    booklet = repo_file("data", "corpus", "sample-mathematics.pdf")
    booklet.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_write_booklet, booklet)
    async with factory() as session:
        school = await session.scalar(select(School).where(School.code == "demo"))
        if school is None:
            school = School(name="Demo Secondary School", code="demo")
            session.add(school)
            await session.flush()
        teacher = await _user(
            session,
            school_id=school.id,
            role="teacher",
            username="teacher",
            display_name="Demo Teacher",
            password=_TEACHER_PASSWORD,
        )
        student = await _user(
            session,
            school_id=school.id,
            role="student",
            username="student",
            display_name="Demo Student",
            password=_STUDENT_PASSWORD,
        )
        group = await session.scalar(
            select(ClassGroup).where(
                ClassGroup.school_id == school.id,
                ClassGroup.name == "S2 Mathematics",
            )
        )
        if group is None:
            group = ClassGroup(
                school_id=school.id,
                teacher_id=teacher.id,
                name="S2 Mathematics",
                subject_code="mathematics",
            )
            session.add(group)
            await session.flush()
        enrolled = await session.scalar(
            select(ClassEnrollment.id).where(
                ClassEnrollment.class_id == group.id,
                ClassEnrollment.student_id == student.id,
            )
        )
        if enrolled is None:
            session.add(ClassEnrollment(class_id=group.id, student_id=student.id))
        await session.commit()
        document = await ingest_pdf(
            session,
            settings,
            path=booklet,
            title="Sample mathematics booklet",
            subject_code="mathematics",
            subject_name="Mathematics",
            school_id=school.id,
            uploaded_by=None,
        )
        print(
            "School demo. Teacher teacher / orchard-maple-19. "
            f"Student student / orchard-cedar-19. Document {document.id}."
        )
    await engine.dispose()


async def _user(
    session: AsyncSession,
    *,
    school_id: UUID,
    role: str,
    username: str,
    display_name: str,
    password: str,
) -> User:
    existing = await session.scalar(
        select(User).where(User.school_id == school_id, User.username == username)
    )
    if existing is not None:
        return existing
    user = User(
        school_id=school_id,
        role=role,
        username=username,
        display_name=display_name,
        password_hash=await asyncio.to_thread(hash_password, password),
        consent_recorded_at=datetime.now(UTC),
        preferred_language="en",
    )
    session.add(user)
    await session.flush()
    return user


def main() -> None:
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
