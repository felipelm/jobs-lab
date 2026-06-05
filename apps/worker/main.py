from packages.common.jobs import create_job, run_job
from packages.common.models import JobCreateRequest, JobResult


def process_once() -> JobResult:
    request = JobCreateRequest(
        type="example",
        payload={"message": "hello from worker"},
    )
    job = create_job(request)
    return run_job(job)


def main() -> None:
    result = process_once()
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
