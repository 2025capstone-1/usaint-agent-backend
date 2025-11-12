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

import asyncio
from apps.agent.agent_service import agent_service
from apps.agent.agent_service import get_agent_data_function


def create_schedule(
    db: Session, user_id: int, request: CreateScheduleRequest
) -> Schedule:
    """새로운 스케줄을 DB에 생성합니다."""
    new_schedule = Schedule.create(
        cron=request.cron, content=request.content, user_id=user_id, task_type=request.task_type, chat_room_id=request.chat_room_id
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


async def check_and_run_due_schedules():
    """
    모든 스케줄을 확인하고, 실행 시간이 된 스케줄을 처리합니다.
    이 함수는 main.py의 apscheduler와 연동되어 주기적으로 호출됩니다. (agent 호출로 인한 비동기)
    """
    print(f"[{datetime.now()}] 스케줄 실행 여부 확인 중...")

    db: Session = next(get_db())  # HTTP 요청이 아니기에 수동으로 세션 가져오기

    try:
        all_schedules = db.query(Schedule).filter(Schedule.task_type != None).all()

        tasks_to_run = [] # 실행할 작업들을 모아둘 리스트

        for schedule in all_schedules:

            if schedule.cron is None:
                continue  # cron이 설정되지 않은 스케줄은 건너뜀

            now = datetime.now()
            # db에 저장된 스케줄러의 cron 표현식과 현재시간(now)를 비교하기 위해 객체 생성
            iter = croniter(schedule.cron, now)

            # get_prev()는 iter기준으로 cron 표현식에 맞는 가장 가까운 이전 시간을 반환
            # now.replace(second=0, microsecond=0)는 초와 마이크로초를 0으로 맞춰서 비교 (crontier가 초를 0으로 비교해서)
            # 현재 시간이 cron 표현식에 맞는 시간과 같다면 스케줄 실행
            if iter.get_prev(datetime) == now.replace(second=0, microsecond=0):
                print(f"[스케줄러] 스케줄 ID {schedule.schedule_id} 실행 시간 도달. 작업 유형: {schedule.task_type}")

                # 리스트에 추가 
                tasks_to_run.append(
                    run_schedule_agent_task(db, schedule)
                )

        # 실행 시간이 된 작업들을 비동기로 실행
        if tasks_to_run:
            print(f"총 {len(tasks_to_run)}개의 스케줄을 병렬로 실행합니다.")
            await asyncio.gather(*tasks_to_run)
    
    except Exception as e:
        print(f"[스케줄러] 스케줄 실행 중 오류 발생: {e}")

    finally:
        db.close()


async def run_schedule_agent_task(db: Session, schedule: Schedule):
    """
    schedule.task_type에 따라 적절한 작업 헬퍼를 호출하고,
    변경 감지시 알림을 생성합니다.
    """

    agent_data_function = get_agent_data_function(schedule.task_type)
    
    if agent_data_function is None:
        print(f"알 수 없는 task_type: {schedule.task_type}. 건너뜁니다.")
        return

    try:
        new_result = None # AI가 반환한 핵심 데이터

        if schedule.task_type == "NOTICE_CHECK":
            new_result = await agent_data_function(
                chat_room_id=schedule.chat_room_id,
                user_id=schedule.user_id,
                task_content=schedule.content
                )
        else:
            new_result = await agent_data_function(
                chat_room_id=schedule.chat_room_id,
                user_id=schedule.user_id
        )

        if new_result is not None and new_result != schedule.last_known_result:
            
            print(f"[스케줄러] '핵심 데이터' 변화 감지! (ID: {schedule.schedule_id})")

            schedule.last_known_result = new_result

            # 최초 한번 알림 후 스케줄러 삭제
            #if schedule.task_type == "GRADE_CHECK":
                #db.delete(schedule)

            notification_content = f"'{schedule.content}' 작업에 변동사항이 감지되었습니다. (결과: {new_result})"
            print(f"[스케줄러] 알림 생성: {notification_content}")

            db.commit()

        else:
            # 변화가 없거나, AI가 None을 반환함
            print(f"[스케줄러] 핵심 데이터 변화 없음. (ID: {schedule.schedule_id}) 알림 스킵.")

    except Exception as e:
        print(f"[스케줄러] 작업 실행 중 오류: {e}")
        db.rollback()

