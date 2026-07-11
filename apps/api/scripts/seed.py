"""
Seed script — generates a handful of synthetic customers, samples, tests, and
events so the agent has something to talk about in dev/staging.

NEVER run this against a production database with real customer data.

Usage:
    cd apps/api && uv run python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.logging import get_logger, setup_logging
from app.db.base import dispose_engine, session_scope
from app.models import (
    AuditLog,
    Conversation,
    Customer,
    Message,
    Sample,
    SampleEvent,
    SampleTest,
)

log = get_logger("seed")


CUSTOMERS = [
    {"id": "CUST-0001", "name": "Acme Environmental", "email": "ops@acme-env.com",
     "phone": "+15555550101", "tier": "contract"},
    {"id": "CUST-0002", "name": "Greenfield University", "email": "lab@greenfield.edu",
     "phone": "+15555550102", "tier": "academic"},
    {"id": "CUST-0003", "name": "BioGenix Pharma", "email": "qa@biogenix.com",
     "phone": "+15555550103", "tier": "contract"},
]

MATRICES = ["groundwater", "soil", "drinking water", "surface water", "wastewater"]
TEST_CODES = [
    ("PFAS-537", "PFAS by EPA 537.1", 38500),
    ("METALS-ICPMS-6020B", "Metals by EPA 6020B (ICP-MS)", 22000),
    ("VOC-8260D", "Volatiles by EPA 8260D", 28500),
    ("SVOC-8270E", "Semi-volatiles by EPA 8270E", 35000),
    ("MERCURY-7470A", "Mercury by EPA 7470A", 15000),
    ("MICRO-HPC", "Heterotrophic plate count", 8500),
]
STATUS_FLOW = ["received", "logged", "in_process", "on_instrument", "review", "reported"]


async def seed() -> None:
    setup_logging()
    log.info("seeding.start")

    # Wipe in dependency order so reseeding is idempotent
    async with session_scope() as s:
        await s.execute(delete(AuditLog))
        await s.execute(delete(Message))
        await s.execute(delete(Conversation))
        await s.execute(delete(SampleEvent))
        await s.execute(delete(SampleTest))
        await s.execute(delete(Sample))
        await s.execute(delete(Customer))

    now = datetime.now(timezone.utc)
    rng = random.Random(42)

    async with session_scope() as s:
        # Customers
        for c in CUSTOMERS:
            s.add(Customer(**c, metadata_={"seeded": True}))
        await s.flush()

        # 50 samples spread across customers + days
        sample_idx = 0
        for day_offset in range(30):
            samples_today = rng.randint(0, 4)
            for _ in range(samples_today):
                sample_idx += 1
                cust = rng.choice(CUSTOMERS)
                year = now.year
                sample_id = f"GL-{year}-{sample_idx:04d}"
                collected = now - timedelta(days=day_offset, hours=rng.randint(0, 23))
                received = collected + timedelta(hours=rng.randint(4, 48))
                status_idx = min(rng.randint(0, 5), day_offset // 2)
                status = STATUS_FLOW[status_idx]
                matrix = rng.choice(MATRICES)
                sample = Sample(
                    id=sample_id,
                    customer_id=cust["id"],
                    matrix=matrix,
                    collected_at=collected,
                    received_at=received,
                    status=status,
                    container=rng.choice(["HDPE 1L", "Glass amber 40mL", "HDPE 250mL"]),
                    preservation=rng.choice(["≤6°C", "≤4°C", "pH<2 + ≤4°C"]),
                    notes="Seeded synthetic data — not real.",
                )
                s.add(sample)
                await s.flush()

                # 1-3 tests per sample
                for code, _name, price in rng.sample(TEST_CODES, k=rng.randint(1, 2)):
                    test = SampleTest(
                        sample_id=sample_id,
                        test_code=code,
                        tat_requested=rng.choice(["standard", "rush", "stat"]),
                        price_cents=price,
                        analyst_id=f"analyst-{rng.randint(1, 5):02d}",
                        started_at=received + timedelta(hours=rng.randint(4, 48))
                        if status_idx >= 2 else None,
                        completed_at=received + timedelta(days=rng.randint(2, 12))
                        if status_idx >= 5 else None,
                    )
                    s.add(test)

                # Event log mirrors the status journey so far
                for j in range(status_idx + 1):
                    s.add(SampleEvent(
                        sample_id=sample_id,
                        ts=received + timedelta(hours=j * 6),
                        event_type=STATUS_FLOW[j],
                        actor="system",
                        data={"note": f"Seeded transition {j}"},
                    ))

    log.info("seeding.done", customers=len(CUSTOMERS), samples=sample_idx)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(seed())