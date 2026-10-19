"""Schema tests (CPE-FR-01): migrations, cascade deletes and constraints.

Needs PostgreSQL with pgvector (``docker compose up -d db``). These tests rebuild the
schema, so never point DATABASE_URL at data you want to keep.

The tests are plain functions because Alembic runs its own event loop. Each database
check runs inside a transaction that is rolled back, so tests leave no rows behind.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import Connection, delete, func, insert, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import Settings
from app.db.models import (
    EMBEDDING_DIMENSIONS,
    Base,
    ChatSession,
    Document,
    ExtractedTrait,
    Message,
    VectorMemory,
)

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
TABLES = {"sessions", "messages", "extracted_traits", "documents", "vector_memories"}

T = TypeVar("T")
DbJob = Callable[[AsyncConnection], Awaitable[T]]


def alembic_config(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["database_url"] = url
    return config


def run_db(url: str, job: DbJob[T]) -> T:
    """Run one async database job inside a transaction that is always rolled back."""

    async def main() -> T:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    return await job(connection)
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    return asyncio.run(main())


@pytest.fixture(scope="module")
def url() -> Iterator[str]:
    try:
        database_url = Settings().database_url
    except ValidationError:
        pytest.skip("DATABASE_URL is not configured (see .env.example)")
    command.upgrade(alembic_config(database_url), "head")
    yield database_url


# --- helpers that insert one row and return its id ------------------------------------


async def add_session(connection: AsyncConnection) -> uuid.UUID:
    result = await connection.execute(insert(ChatSession).returning(ChatSession.id))
    return result.scalar_one()


async def add_message(
    connection: AsyncConnection, session_id: uuid.UUID, seq: int = 1, role: str = "user"
) -> uuid.UUID:
    result = await connection.execute(
        insert(Message)
        .values(session_id=session_id, seq=seq, role=role, content="I plan my day every morning")
        .returning(Message.id)
    )
    return result.scalar_one()


async def add_trait(
    connection: AsyncConnection, message_id: uuid.UUID, confidence: str = "0.8"
) -> uuid.UUID:
    result = await connection.execute(
        insert(ExtractedTrait)
        .values(
            source_message_id=message_id, trait="Highly Organized", confidence=Decimal(confidence)
        )
        .returning(ExtractedTrait.id)
    )
    return result.scalar_one()


async def add_document(connection: AsyncConnection, sha256: str = "a" * 64) -> uuid.UUID:
    result = await connection.execute(
        insert(Document).values(source="habits.pdf", sha256=sha256).returning(Document.id)
    )
    return result.scalar_one()


async def add_chunk(
    connection: AsyncConnection,
    document_id: uuid.UUID,
    content: str = "Habits form through repetition and reward.",
    page_start: int = 1,
    page_end: int = 1,
) -> uuid.UUID:
    result = await connection.execute(
        insert(VectorMemory)
        .values(
            document_id=document_id,
            chunk_index=0,
            page_start=page_start,
            page_end=page_end,
            content=content,
            token_count=8,
            embedding=[0.1] * EMBEDDING_DIMENSIONS,
            embedding_model="nomic-embed-text",
        )
        .returning(VectorMemory.id)
    )
    return result.scalar_one()


async def count(connection: AsyncConnection, model: type[Base], *conditions: Any) -> int:
    result = await connection.execute(select(func.count()).select_from(model).where(*conditions))
    return result.scalar_one()


# --- migrations -----------------------------------------------------------------------


def test_migration_goes_down_and_up_cleanly(url: str) -> None:
    async def table_names(connection: AsyncConnection) -> set[str]:
        names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
        return set(names)

    config = alembic_config(url)

    command.downgrade(config, "base")
    assert run_db(url, table_names) & TABLES == set()

    command.upgrade(config, "head")
    assert run_db(url, table_names) >= TABLES


def test_models_match_the_migration(url: str) -> None:
    def differences(sync_connection: Connection) -> list[Any]:
        return list(compare_metadata(MigrationContext.configure(sync_connection), Base.metadata))

    async def job(connection: AsyncConnection) -> list[Any]:
        return await connection.run_sync(differences)

    assert run_db(url, job) == []


# --- cascade deletes ------------------------------------------------------------------


def test_deleting_a_session_deletes_its_messages_and_traits(url: str) -> None:
    async def job(connection: AsyncConnection) -> tuple[int, int]:
        session_id = await add_session(connection)
        message_id = await add_message(connection, session_id)
        await add_trait(connection, message_id)

        await connection.execute(delete(ChatSession).where(ChatSession.id == session_id))

        messages = await count(connection, Message, Message.session_id == session_id)
        traits = await count(
            connection, ExtractedTrait, ExtractedTrait.source_message_id == message_id
        )
        return messages, traits

    assert run_db(url, job) == (0, 0)


def test_deleting_a_document_deletes_its_chunks(url: str) -> None:
    async def job(connection: AsyncConnection) -> int:
        document_id = await add_document(connection)
        await add_chunk(connection, document_id)

        await connection.execute(delete(Document).where(Document.id == document_id))

        return await count(connection, VectorMemory, VectorMemory.document_id == document_id)

    assert run_db(url, job) == 0


# --- constraints ----------------------------------------------------------------------


async def trait_with_confidence_above_one(connection: AsyncConnection) -> None:
    message_id = await add_message(connection, await add_session(connection))
    await add_trait(connection, message_id, confidence="1.5")


async def same_trait_twice_for_one_message(connection: AsyncConnection) -> None:
    message_id = await add_message(connection, await add_session(connection))
    await add_trait(connection, message_id)
    await add_trait(connection, message_id)


async def two_messages_with_same_seq(connection: AsyncConnection) -> None:
    session_id = await add_session(connection)
    await add_message(connection, session_id, seq=1)
    await add_message(connection, session_id, seq=1)


async def message_with_unknown_role(connection: AsyncConnection) -> None:
    await add_message(connection, await add_session(connection), role="system")


async def same_document_twice(connection: AsyncConnection) -> None:
    await add_document(connection, sha256="b" * 64)
    await add_document(connection, sha256="b" * 64)


async def chunk_ending_before_it_starts(connection: AsyncConnection) -> None:
    await add_chunk(connection, await add_document(connection), page_start=3, page_end=2)


@pytest.mark.parametrize(
    "bad_insert",
    [
        trait_with_confidence_above_one,
        same_trait_twice_for_one_message,
        two_messages_with_same_seq,
        message_with_unknown_role,
        same_document_twice,
        chunk_ending_before_it_starts,
    ],
)
def test_database_rejects_invalid_rows(url: str, bad_insert: DbJob[None]) -> None:
    with pytest.raises(IntegrityError):
        run_db(url, bad_insert)


# --- generated keyword-search column --------------------------------------------------


def test_keyword_search_column_is_filled_in_by_postgres(url: str) -> None:
    async def job(connection: AsyncConnection) -> int:
        await add_chunk(connection, await add_document(connection))
        query = func.websearch_to_tsquery("english", "habit repetition")
        return await count(connection, VectorMemory, VectorMemory.content_tsv.op("@@")(query))

    assert run_db(url, job) == 1
