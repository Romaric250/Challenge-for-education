import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from tutor_api.core.settings import get_settings
from tutor_api.db.engine import create_database_engine
from tutor_api.ingestion.pipeline import ingest_pdf


def main() -> None:
    asyncio.run(_ingest())


async def _ingest() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python -m tutor_api.cli.ingest FILE [--title TITLE] [--subject CODE]"
        )
    path = Path(sys.argv[1])
    title = _flag("--title") or path.stem
    subject = _flag("--subject") or "mathematics"
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        document = await ingest_pdf(
            session,
            settings,
            path=path,
            title=title,
            subject_code=subject,
            subject_name=subject.replace("-", " ").title(),
            school_id=None,
            uploaded_by=None,
        )
        print(f"{document.status} {document.id} pages={document.page_count}")
    await engine.dispose()


def _flag(name: str) -> str | None:
    if name not in sys.argv:
        return None
    index = sys.argv.index(name)
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


if __name__ == "__main__":
    main()
