"""Database setup and seeding script for Coligo.

Initializes extensions (vector, pg_trgm), creates all ORM tables,
populates structured TNEA cutoff records, and ingests knowledge-base documents.
"""

import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text  # noqa: E402

from api.core.database import Base, async_session_factory, engine  # noqa: E402
from api.core.logging import get_logger  # noqa: E402
from api.models import *  # noqa: F401, F403, E402
from api.models.document import Document  # noqa: E402
from api.services.cutoff_service import seed_cutoffs_from_file  # noqa: E402
from api.services.document_service import process_document  # noqa: E402

logger = get_logger(__name__)


async def seed():
    print("=" * 60)
    print("Starting Database Schema Initialization & Seeding...")
    print(f"Target DB: {engine.url.render_as_string(hide_password=True)}")
    print("=" * 60)

    # 1. Initialize extensions and create all tables
    print("\n[1/4] Creating extensions and ORM tables...")
    async with engine.begin() as conn:
        print(" -> Creating EXTENSION vector...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        print(" -> Creating EXTENSION pg_trgm...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        print(" -> Running Base.metadata.create_all...")
        await conn.run_sync(Base.metadata.create_all)
        print(" -> Creating GIN trigram index on document_chunks...")
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_document_chunks_text_trgm "
                "ON document_chunks USING gin (text_content gin_trgm_ops);"
            )
        )
    print(" ✓ Extensions and tables successfully initialized.")

    # 2. Seed Structured TNEA Cutoffs
    print("\n[2/4] Seeding structured TNEA cutoffs table...")
    async with async_session_factory() as db:
        cutoff_file = "data/tnea_top_colleges_cutoffs.txt"
        if os.path.exists(cutoff_file):
            seeded_cutoffs = await seed_cutoffs_from_file(db, cutoff_file)
            await db.commit()
            print(f" ✓ TNEA Cutoffs seeded/verified: {seeded_cutoffs} records.")
        else:
            print(f" ! Cutoff seed file not found: {cutoff_file}")

    # 3. Seed Knowledge Base Documents (PDF & Scraped Text)
    print("\n[3/4] Ingesting knowledge-base documents into pgvector...")
    seed_docs = [
        "data/skcet_tnea_knowledge_base.pdf",
        "data/scraped_colleges/psg_tech_scraped.txt",
        "data/tnea_top_colleges_cutoffs.txt",
    ]

    async with async_session_factory() as db:
        for doc_path in seed_docs:
            if not os.path.exists(doc_path):
                print(f" ! Skipping non-existent doc: {doc_path}")
                continue

            # Check if document already exists
            res = await db.execute(
                select(Document).where(Document.document_ref == doc_path)
            )
            existing = res.scalar_one_or_none()
            if existing:
                print(f" ✓ Already ingested: {doc_path}")
            else:
                print(f" -> Ingesting & embedding: {doc_path}...")
                try:
                    _, total, inserted, reused = await process_document(db, doc_path)
                    await db.commit()
                    print(
                        f"   ✓ Ingested: {doc_path} "
                        f"(total: {total}, new: {inserted}, reused: {reused})"
                    )
                except Exception as e:
                    await db.rollback()
                    print(f"   ✗ Ingestion failed for {doc_path}: {e}")

    # 4. Verification & Table Stats
    print("\n[4/4] Verifying Table Statistics...")
    async with async_session_factory() as db:
        tables = [
            ("colleges", "SELECT count(*) FROM colleges;"),
            ("courses", "SELECT count(*) FROM courses;"),
            ("facilities", "SELECT count(*) FROM facilities;"),
            ("brochures", "SELECT count(*) FROM brochures;"),
            ("documents", "SELECT count(*) FROM documents;"),
            ("document_chunks", "SELECT count(*) FROM document_chunks;"),
            ("tnea_cutoffs", "SELECT count(*) FROM tnea_cutoffs;"),
            ("conversations", "SELECT count(*) FROM conversations;"),
            ("conversation_messages", "SELECT count(*) FROM conversation_messages;"),
            ("escalations", "SELECT count(*) FROM escalations;"),
        ]
        print("-" * 40)
        print(f"{'Table':<25} | {'Count':<10}")
        print("-" * 40)
        for tbl, query in tables:
            try:
                cnt = (await db.execute(text(query))).scalar() or 0
                print(f"{tbl:<25} | {cnt:<10}")
            except Exception as e:
                print(f"{tbl:<25} | Error: {e}")
        print("-" * 40)

    await engine.dispose()
    print("\n✓ Database seeding successfully finished!")


if __name__ == "__main__":
    asyncio.run(seed())
