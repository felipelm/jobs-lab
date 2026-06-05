from apps.worker.main import process_once
from packages.common.models import JobStatus


def test_process_once_completes_example_job() -> None:
    result = process_once()

    assert result.job.type == "example"
    assert result.job.status == JobStatus.SUCCEEDED
    assert result.output == {"echo": {"message": "hello from worker"}}
