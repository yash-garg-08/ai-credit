"""Temporal worker entrypoint. Run with: python -m app.workflows.worker"""
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import settings
from app.workflows.activities import (
    calculate_cost,
    check_balance_and_limits,
    fetch_pricing,
    record_usage_and_deduct,
)
from app.workflows.process_usage import ProcessUsageWorkflow


async def main() -> None:
    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ProcessUsageWorkflow],
        activities=[
            fetch_pricing,
            calculate_cost,
            check_balance_and_limits,
            record_usage_and_deduct,
        ],
    )

    print(f"Worker started on task queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
