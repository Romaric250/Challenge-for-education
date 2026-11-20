from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from tutor_api.api.deps import require_ready_user
from tutor_api.core.errors import DomainError
from tutor_api.db.session import get_db_session
from tutor_api.models.identity import User
from tutor_api.models.schema_meta import SchemaMeta
from tutor_api.repositories.schools import write_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class ProviderUpdate(BaseModel):
    provider: str = Field(pattern=r"^(none|anthropic|openai_compatible)$")
    model: str = Field(min_length=1, max_length=64)


@router.put("/provider", status_code=204)
async def update_provider(
    body: ProviderUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_ready_user),
) -> None:
    if user.role != "admin" and not user.is_super_admin:
        raise DomainError(
            status_code=403,
            code="forbidden",
            title="Forbidden",
            detail="Only an admin can change the model provider.",
        )
    for key, value in (("llm_provider", body.provider), ("llm_model", body.model)):
        statement = insert(SchemaMeta).values(key=key, value=value)
        statement = statement.on_conflict_do_update(
            index_elements=[SchemaMeta.key],
            set_={"value": value},
        )
        await session.execute(statement)
    await write_audit(
        session,
        actor_id=user.id,
        school_id=user.school_id,
        action="provider.updated",
        target_type="schema_meta",
        target_id="llm_provider",
        detail={"provider": body.provider, "model": body.model},
    )
    await session.commit()
