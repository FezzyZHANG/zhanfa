"""Scheduler router — status and manual trigger."""

from fastapi import APIRouter

from zhanfa.api.models import SchedulerJob, SchedulerStatus, SchedulerTriggerRequest
from zhanfa.automation.scheduler import scheduler
from zhanfa.automation.workflows import update_daily_data, weekly_index_rebalance

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/status", response_model=SchedulerStatus)
def get_status():
    jobs = [SchedulerJob(**j) for j in scheduler.list_jobs()]
    return SchedulerStatus(jobs=jobs, running=False)


@router.post("/trigger")
def trigger(body: SchedulerTriggerRequest):
    if body.action == "update_daily":
        result = update_daily_data(body.codes)
        return {"action": "update_daily", "result": result}
    elif body.action == "rebalance_index":
        codes = weekly_index_rebalance(body.index_code or "000300")
        return {"action": "rebalance_index", "codes": codes}
    return {"action": body.action, "result": "unknown action"}
