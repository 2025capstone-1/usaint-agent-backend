from typing import Optional
from apps.agent.session import Session
from apps.agent.usaint import (
    _get_frame, 
    _select_navigation_menu
)
import asyncio

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
    
async def fetch_full_grades(session: Session, session_id_str: str) -> Optional[str]:
    """
    [사용자 요청용] '학기별 성적 조회'의 테이블 전체를 파싱합니다.
    (현재 2024-1학기 조회를 위해 "이전학기" 2회 클릭 로직 고정)
    """
    try:
        # 1. 성적 페이지로 이동
        await _select_navigation_menu(session_id_str, "학사관리")
        await _select_navigation_menu(session_id_str, "성적/졸업")
        await _select_navigation_menu(session_id_str, "학기별 성적 조회")
        
        frame = await _get_frame(session)
        if not frame:
            raise Exception("iframe(_get_frame)을 찾는 데 실패했습니다.")
        
        target_tbody_selector = "#WD01F4-contentTBody"
        prev_semester_button_selector = "#WD01E3" # "이전학기" 버튼 ID
        
        frame = await _get_frame(session)
        if not frame:
            raise Exception("iframe(1)을 찾는 데 실패했습니다.")
        
        # 2. "이전학기" 2번 클릭 (2024-1학기로 이동)
        await frame.click(prev_semester_button_selector, timeout=5000)
        await frame.wait_for_load_state("networkidle", timeout=10000)

        frame = await _get_frame(session)
        if not frame:
            raise Exception("iframe(1)을 찾는 데 실패했습니다.")

        await frame.click(prev_semester_button_selector, timeout=5000)
        await frame.wait_for_load_state("networkidle", timeout=10000)

        frame = await _get_frame(session)
        if not frame:
            raise Exception("iframe(3)을 찾는 데 실패했습니다.")

        # 3. 테이블 파싱
        known_1st_semester_subject_id = "#WD023F"
        await frame.wait_for_selector(known_1st_semester_subject_id, state="visible", timeout=5000)
        rows = await frame.locator(f"{target_tbody_selector} tr").all()
        
        results = []
        
        for row in rows[1:]: # 헤더 스킵
            cols = await row.locator("td").all_inner_texts()
            
            if len(cols) >= 4:
                subject = cols[3].strip() # 과목명
                grade = cols[2].strip()   # 등급
                
                if subject and grade:
                    results.append(f"{subject}: {grade}")
        
        print(results)
        if not results:
            return "조회된 성적 데이터가 없습니다."

        return "\n".join(results)
    
    except Exception as e:
        print(f"[GradeFetcher-Full] '전체 성적' 조회 중 오류: {e}")
        return f"성적 조회 중 오류가 발생했습니다: {e}"