import asyncio
import os
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tutor_api.core.passwords import hash_password, validate_password
from tutor_api.core.settings import get_settings
from tutor_api.db.engine import create_database_engine
from tutor_api.models.identity import School, User


async def _seed() -> None:
    school_code = os.environ.get("SEED_ADMIN_SCHOOL_CODE", "").strip().lower()
    username = os.environ.get("SEED_ADMIN_USERNAME", "").strip().lower()
    password = os.environ.get("SEED_ADMIN_PASSWORD", "")
    display_name = os.environ.get("SEED_ADMIN_DISPLAY_NAME", "School admin").strip()
    school_name = os.environ.get("SEED_ADMIN_SCHOOL_NAME", school_code).strip()
    if not school_code or not username or not password:
        raise SystemExit(
            "Set SEED_ADMIN_SCHOOL_CODE, SEED_ADMIN_USERNAME, and SEED_ADMIN_PASSWORD."
        )
    problem = validate_password(password, username=username)
    if problem is not None:
        raise SystemExit(problem)
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        school = await session.scalar(select(School).where(School.code == school_code))
        if school is None:
            school = School(name=school_name or school_code, code=school_code)
            session.add(school)
            await session.flush()
        existing = await session.scalar(
            select(User).where(User.school_id == school.id, User.username == username)
        )
        if existing is not None:
            print(f"Admin {username} already exists for school {school_code}.")
            await engine.dispose()
            return
        session.add(
            User(
                school_id=school.id,
                role="admin",
                username=username,
                display_name=display_name or username,
                password_hash=hash_password(password),
                is_super_admin=True,
                consent_recorded_at=datetime.now(UTC),
                preferred_language="en",
            )
        )
        await session.commit()
    await engine.dispose()
    print(f"Created super admin {username} for school {school_code}.")


def main() -> None:
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
