import asyncio
import json

from langchain_core.tools import tool
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

from apps.agent.session import Session, session_manager
from lib.env import get_env


@tool
async def search_menu() -> str:
    """유세인트의 전체 메뉴 구조를 JSON 문자열로 반환합니다. 메뉴 이동이 필요할 때 이 도구로 메뉴 구조를 확인하세요."""
    import os
    from pathlib import Path

    # 현재 파일의 디렉토리 경로
    current_dir = Path(__file__).parent
    menu_file = current_dir / "menu.json"

    # menu.json 파일 읽기
    with open(menu_file, "r", encoding="utf-8") as f:
        menu_data = json.load(f)

    # JSON을 보기 좋은 문자열로 변환하여 반환
    return json.dumps(menu_data, ensure_ascii=False, indent=2)


class GotoArgs(BaseModel):
    session_id: str = Field(description="Session ID for the browser session")
    url: str = Field(description="URL to navigate to")


async def goto(session_id: str, url: str):
    """goto url page"""

    session = session_manager.get_session(session_id)
    await session.page.goto(url, wait_until="domcontentloaded")

    return True


class SelectNavigationMenuArgs(BaseModel):
    session_id: str = Field(description="Session ID for the browser session")
    menu_title: str = Field(description="이동할 메뉴명")


@tool(args_schema=SelectNavigationMenuArgs)
async def select_navigation_menu(session_id: str, menu_title: str):
    """유세인트 메뉴를 선택합니다."""
    return await _select_navigation_menu(session_id, menu_title)


async def _select_navigation_menu(session_id: str, menu_title: str):
    """유세인트 메뉴를 선택합니다."""
    session = session_manager.get_session(session_id)
    menu = session.page.get_by_role("link", name=menu_title)
    print(f"{menu_title}: {menu}")
    await menu.click()
    await session.page.wait_for_load_state("domcontentloaded", timeout=4 * 1000)
    await asyncio.sleep(2)

    return True


@tool()
async def get_iframe_text_content(session_id: str):
    """iframe에서 내부의 화면 내용을 텍스트로 가져옵니다."""
    return await _get_iframe_text_content(session_id)


async def _get_iframe_text_content(session_id: str):
    session = session_manager.get_session(session_id)
    work_area_frame = await _get_frame(session=session)
    body = await work_area_frame.query_selector("body")
    to_ignore = await work_area_frame.query_selector("#sapur-aria")

    body_text = await body.inner_text()
    to_ignore_text = await to_ignore.inner_text()

    return body_text.replace(to_ignore_text, "").replace("\n\n", "\n")


@tool()
async def get_iframe_interactive_element(session_id: str):
    """iframe에서 상호작용할 수 있는 HTML 요소들을 가져옵니다."""
    return await _get_iframe_interactive_element(session_id)


async def _get_iframe_interactive_element(session_id: str):
    session = session_manager.get_session(session_id)
    work_area_frame = await _get_frame(session=session)

    # 인터랙션 가능한 후보 요소 수집
    interaction_element_list = await work_area_frame.query_selector_all(
        "input, select, textarea, button, a, [role='button'], [role='input']"
    )

    filtered_elements_html = []

    for handle in interaction_element_list:
        element = handle.as_element()
        if element is None:
            continue

        # 기본 정보 가져오기
        tag_name = await element.evaluate("(el) => el.tagName.toLowerCase()")
        element_type = await element.evaluate("(el) => el.getAttribute('type') || ''")
        aria_hidden = await element.evaluate("(el) => el.getAttribute('aria-hidden')")
        is_hidden = await element.is_hidden()

        # 1) 숨겨진 input 제외
        if tag_name == "input" and element_type == "hidden":
            continue

        # 2) aria-hidden="true" 또는 display:none 등 숨겨진 요소 제외
        if aria_hidden == "true" or is_hidden:
            continue

        # 3) 시각적 텍스트/라벨이 없는 버튼류 제거
        has_text = await element.evaluate(
            """(el) => {
                const txt = el.innerText || el.getAttribute('aria-label') || el.title;
                return txt && txt.trim().length > 0;
            }"""
        )
        if tag_name in ["button", "div", "span", "a"] and not has_text:
            continue

        # outerHTML 추출
        outer_html = await element.evaluate("(el) => el.outerHTML")
        filtered_elements_html.append(outer_html)

    return "\n".join(filtered_elements_html)


async def _get_frame(session: Session):
    # iframe 요소 선택
    content_area_frame = await session.page.query_selector("iframe#contentAreaFrame")
    print(f"frame element: {content_area_frame}")

    # iframe의 실제 Frame 객체 얻기
    frame = await content_area_frame.content_frame()
    print(f"frame: {frame}")

    # iframe 안에서 #isolatedWorkArea 선택
    work_area_frame_element = await frame.query_selector("#isolatedWorkArea")
    print(f"work area element: {work_area_frame_element}")

    # isolatedWorkArea도 iframe일 경우, 다시 content_frame() 호출
    work_area_frame = await work_area_frame_element.content_frame()
    await work_area_frame.wait_for_load_state("domcontentloaded", timeout=8 * 1000)

    return work_area_frame


class ClickArgs(BaseModel):
    session_id: str = Field(description="Session ID for the browser session")
    selector: str = Field(description="CSS selector or XPath of element to click")


@tool(args_schema=ClickArgs)
async def click_in_iframe(session_id: str, selector: str):
    """iframe안에 있는 HTML 요소를 클릭합니다."""
    return await _click_in_iframe(session_id, selector)


async def _click_in_iframe(session_id: str, selector: str):
    """iframe 내부의 요소를 클릭합니다."""
    session = session_manager.get_session(session_id)
    work_area_frame = await _get_frame(session)

    await session.page.screenshot(path="screen.png")
    await work_area_frame.wait_for_selector(selector, timeout=4 * 1000)
    await work_area_frame.click(selector=selector, timeout=4 * 1000)

    return True


class QuerySelectorArgs(BaseModel):
    session_id: str = Field(description="Session ID for the browser session")
    selector: str = Field(description="CSS selector or XPath of element to click")


@tool(args_schema=QuerySelectorArgs)
async def query_select(session_id: str, selector: str):
    """Find a element for the given selector"""
    session = session_manager.get_session(session_id)
    return await session.page.query_selector(selector=selector)


class InsertTextArgs(BaseModel):
    session_id: str = Field(description="Session ID for the browser session")
    content: str = Field(description="Text content to insert")


@tool
async def insert_text(session_id: str, content: str):
    """simulate keyboard typing"""
    session = session_manager.get_session(session_id)
    await session.page.keyboard.insert_text(content)

    return True


async def usaint_login(session: Session, id: str, password: str):
    await session.page.goto("https://saint.ssu.ac.kr/irj/portal")

    login_button = await session.page.query_selector('//*[@id="s_btnLogin"]')
    if login_button is None:
        return True

    await session.page.click('//*[@id="s_btnLogin"]')

    await session.page.click('//*[@id="userid"]')
    await session.page.keyboard.insert_text(id)

    await session.page.click('//*[@id="pwd"]')
    await session.page.keyboard.insert_text(password)

    await session.page.click('//*[@id="sLogin"]/div/div[1]/form/div/div[2]')

    await session.page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)
    await session.page.reload(wait_until="domcontentloaded")


async def main():
    session_id = "test1234"
    session = session_manager.get_session(session_id)

    async with async_playwright() as playwright:
        await session.start(playwright)
        await usaint_login(session, get_env("USAINT_ID"), get_env("USAINT_PASSWORD"))

        # frame = document.querySelector('iframe#contentAreaFrame')
        # work_area = frame.contentDocument.querySelector('#isolatedWorkArea')
        # work_area.contentDocument.querySelector('table')

        menu = session.page.get_by_role("link", name="학사관리")
        print(f"학사관리 menu: {menu}")
        await menu.click()
        await session.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        menu = session.page.get_by_role("link", name="수강신청/교과과정")
        print(f"수강신청/교과과정 menu: {menu}")
        await menu.click()
        await session.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        menu = session.page.get_by_role("link", name="개인수업시간표조회")
        print(f"개인수업시간표조회 menu: {menu}")
        await menu.click()
        await session.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        content = await _get_iframe_text_content(session_id)
        print(f"content: {content}")

        interactive = await _get_iframe_interactive_element(session_id)
        print(f"interactive: {interactive}")

        await _click_in_iframe(session_id, "#WDA7")

        # # locator 방식
        # content_area = session.page.frame_locator("iframe#contentAreaFrame")
        # work_area = content_area.frame_locator("#isolatedWorkArea")

        # search = work_area.get_by_role(role="button", name="조회", exact=True)
        # await search.click(timeout=5 * 1000)

        await asyncio.sleep(1000)
        await session.close()  # WD9F


if __name__ == "__main__":
    asyncio.run(main())
