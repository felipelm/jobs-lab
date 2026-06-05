from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_session
from apps.api.repository import JobRepository, SqlAlchemyJobRepository


def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobRepository:
    return SqlAlchemyJobRepository(session)

