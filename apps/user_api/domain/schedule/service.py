from sqlalchemy.orm import Session
from apps.user_api.domain.schedule.dto.request import (
    CreateScheduleRequest,
    UpdateScheduleRequest,
)
from apps.user_api.domain.schedule.entity import Schedule
from apps.user_api.domain.schedule.exception import (
    ScheduleNotFound,
    ScheduleAccessDenied,
)
from datetime import datetime
from croniter import croniter
from lib.database import get_db
from typing import Optional


def create_schedule(
    db: Session, user_id: int, request: CreateScheduleRequest
) -> Schedule:
    """새로운 스케줄을 DB에 생성합니다."""
    new_schedule = Schedule.create(
        cron=request.cron, content=request.content, user_id=user_id
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    print(f"✅ 새로운 스케줄이 DB에 등록되었습니다: {new_schedule}")
    return new_schedule


def get_schedule_detail(db: Session, user_id: int, schedule_id: int) -> Schedule:
    """단일 스케줄을 조회합니다."""
    schedule = db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()

    if schedule is None:
        raise ScheduleNotFound()

    # 스케줄의 소유자인지 확인
    if schedule.user_id != user_id:
        raise ScheduleAccessDenied()

    return schedule


def get_schedules(db: Session, user_id: int) -> list[Schedule]:
    """모든 스케줄을 조회합니다."""
    schedules = db.query(Schedule).filter(Schedule.user_id == user_id).all()
    return schedules


def update_schedule(
    db: Session, schedule_id: int, user_id: int, request: UpdateScheduleRequest
) -> Optional[Schedule]:
    """스케줄을 업데이트합니다."""
    schedule = db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()
    if not schedule:
        raise ScheduleNotFound()

    # 스케줄의 소유자인지 확인
    if schedule.user_id != user_id:
        raise ScheduleAccessDenied()

    if request.cron is not None:
        schedule.cron = request.cron
    if request.content is not None:
        schedule.content = request.content

    db.commit()
    db.refresh(schedule)
    print(f"✅ 스케줄 ID {schedule_id}가 수정되었습니다: {schedule}")
    return schedule


def delete_schedule(db: Session, schedule_id: int, user_id: int) -> None:
    """스케줄을 삭제합니다."""
    schedule = db.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()

    if not schedule:
        raise ScheduleNotFound()

    # 스케줄의 소유자인지 확인
    if schedule.user_id != user_id:
        raise ScheduleAccessDenied()

    db.delete(schedule)
    db.commit()
    print(f"✅ 스케줄 ID {schedule_id}가 삭제되었습니다.")
    return True


def check_and_run_due_schedules():
    """
    모든 스케줄을 확인하고, 실행 시간이 된 스케줄을 처리합니다.
    이 함수는 main.py의 apscheduler와 연동되어 주기적으로 호출됩니다.
    """
    print(f"[{datetime.now()}] 스케줄 실행 여부 확인 중...")
    db: Session = next(get_db())  # HTTP 요청이 아니기에 수동으로 세션 가져오기

    all_schedules = db.query(Schedule).all()

    for schedule in all_schedules:
        now = datetime.now()
        # db에 저장된 스케줄러의 cron 표현식과 현재시간(now)를 비교하기 위해 객체 생성
        iter = croniter(schedule.cron, now)

        # get_prev()는 iter기준으로 cron 표현식에 맞는 가장 가까운 이전 시간을 반환
        # now.replace(second=0, microsecond=0)는 초와 마이크로초를 0으로 맞춰서 비교 (crontier가 초를 0으로 비교해서)
        # 현재 시간이 cron 표현식에 맞는 시간과 같다면 스케줄 실행
        if iter.get_prev(datetime) == now.replace(second=0, microsecond=0):

            print(
                f"실행 시간 도달. 스케줄 ID: {schedule.schedule_id}, 내용: {schedule.content}"
            )

            # content 값에 따라 적절한 에이전트 실행 함수를 호출 - Todo: agent 서비스가 구현되면 추가
            if schedule.content == "TASK_GRADE_CHECK":
                print("-> 성적 확인 에이전트 실행 - TODO")
                # run_grade_check_for_user(user_id=schedule.user_id, schedule_id=schedule.schedule_id)
            # elif schedule.content == "TASK_???":
            #   run_???(user_id=schedule.user_id, schedule_id=schedule.schedule_id)
            else:
                print(f"-> '{schedule.content}'에 해당하는 작업이 없어 건너뜁니다.")
    db.close()
