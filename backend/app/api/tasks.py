from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import authenticate_developer
from app.database import get_db
from app.models import Developer, Task
from app.schemas import TaskOut

router = APIRouter(prefix="/api/v1/tasks", tags=["任务"])


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(
        Task.task_id == task_id,
        Task.developer_id == developer.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task
