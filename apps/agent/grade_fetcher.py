from typing import Optional
from apps.agent.session import Session
from apps.agent.usaint import (
    _get_frame, 
    _select_navigation_menu
)

async def fetch_grade_summary(session: Session, session_id_str: str) -> Optional[str]:
    """
    usaint 세션에서 학기별 성적 조회를 탐색하고 데이터를 추출합니다.
    """
    try:
        await _select_navigation_menu(session_id_str, "학사관리")
        await _select_navigation_menu(session_id_str, "성적/졸업")
        await _select_navigation_menu(session_id_str, "학기별 성적 조회")
        
        # 학기별 성적 조회 iframe으로 진입
        frame = await _get_frame(session)
        if not frame:
            raise Exception("iframe(_get_frame)을 찾는 데 실패했습니다.")
        
        target_id_selector = "#WD0147" 
        await frame.wait_for_selector(target_id_selector, timeout=10000)

        gpa_input_locator = frame.locator(target_id_selector)

        # 총 평점 데이터 추출 
        key_data = await gpa_input_locator.get_attribute("value")

        if key_data is None:
            print(f"[GradeFetcher] ID 셀렉터 '{target_id_selector}'를 찾지 못했습니다.")
            return None

        print(f"[GradeFetcher] 스케줄러 작업: 핵심 데이터 '총 평점' 추출 완료 ({key_data})")
        return key_data
    
    except Exception as e:
        print(f"[GradeFetcher] 성적 조회 작업 중 오류: {e}")
        return None