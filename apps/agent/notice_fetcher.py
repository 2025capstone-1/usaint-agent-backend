import chromadb
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup

# chroma db
chroma_client = chromadb.Client()


def fetch_ssu_notice_list(page: int = 1):
    """
    스캐치 공지사항 페이지에서 HTML을 가져와 파싱 후 JSON 파일로 저장합니다.
    """
    url = f"https://scatch.ssu.ac.kr/공지사항/page/{page}"

    try:
        # HTML 요청
        response = requests.get(url)
        response.raise_for_status()  # HTTP 에러 발생시 예외 발생

        # HTML 파싱
        soup = BeautifulSoup(response.text, "html.parser")

        # HTML 전체를 저장할 디렉토리 생성
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)

        # HTML 원본 저장
        html_file = output_dir / f"ssu_notice_list_{page}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(response.text)

        # 게시글 데이터 추출
        posts = []

        # notice-lists 클래스를 가진 ul 요소 찾기
        notice_lists = soup.find("ul", class_="notice-lists")

        if notice_lists:
            # 모든 li 요소 찾기 (첫 번째는 헤더이므로 제외)
            list_items = notice_lists.find_all("li")

            for li in list_items:
                # 헤더 행은 건너뛰기
                if "notice_head" in li.get("class", []):
                    continue

                # 각 컬럼 데이터 추출
                date_col = li.find("div", class_="notice_col1")
                status_col = li.find("div", class_="notice_col2")
                title_col = li.find("div", class_="notice_col3")
                dept_col = li.find("div", class_="notice_col4")
                views_col = li.find("div", class_="notice_col5")

                # 제목 컬럼에서 링크와 카테고리 추출
                title_link = title_col.find("a") if title_col else None
                category_label = (
                    title_col.find("span", class_="label") if title_col else None
                )

                # 게시글 데이터 구성
                post_data = {
                    "date": date_col.get_text(strip=True) if date_col else "",
                    "status": status_col.get_text(strip=True) if status_col else "",
                    "category": (
                        category_label.get_text(strip=True) if category_label else ""
                    ),
                    "title": title_link.get_text(strip=True) if title_link else "",
                    "url": title_link.get("href") if title_link else "",
                    "department": dept_col.get_text(strip=True) if dept_col else "",
                    "views": views_col.get_text(strip=True) if views_col else "",
                }

                # 카테고리를 제외한 순수 제목만 추출 및 정리
                if title_link and category_label:
                    # 카테고리 라벨을 제거한 제목
                    title_text = title_link.get_text(strip=True)
                    category_text = category_label.get_text(strip=True)
                    clean_title = title_text.replace(category_text, "").strip()
                    # 줄바꿈과 연속된 공백을 하나의 공백으로 변경
                    clean_title = " ".join(clean_title.split())
                    post_data["title"] = clean_title

                posts.append(post_data)

        # 파싱된 데이터를 JSON으로 저장
        data = {"url": url, "total_posts": len(posts), "posts": posts}

        json_file = output_dir / "ssu_notice.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"HTML이 저장되었습니다: {html_file}")
        print(f"JSON이 저장되었습니다: {json_file}")
        print(f"총 {len(posts)} 개의 요소를 추출했습니다.")

        return data

    except requests.exceptions.RequestException as e:
        print(f"HTTP 요청 중 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return None


def parse_ssu_notice_list():
    """
    저장된 ssu_notice_list_{page}.html 형태의 모든 HTML 파일에서 게시글 목록을 파싱합니다.
    """
    data_dir = Path("data")

    if not data_dir.exists():
        print(f"data 디렉토리가 존재하지 않습니다: {data_dir}")
        return None

    # ssu_notice_list_*.html 패턴의 모든 파일 찾기
    html_files = sorted(data_dir.glob("ssu_notice_list_*.html"))

    if not html_files:
        print(f"ssu_notice_list_*.html 형태의 파일을 찾을 수 없습니다.")
        return None

    try:
        all_posts = []

        # 각 HTML 파일 파싱
        for html_file in html_files:
            print(f"파싱 중: {html_file.name}")

            # HTML 파일 읽기
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # HTML 파싱
            soup = BeautifulSoup(html_content, "html.parser")

            # notice-lists 클래스를 가진 ul 요소 찾기
            notice_lists = soup.find("ul", class_="notice-lists")

            if notice_lists:
                # 모든 li 요소 찾기 (첫 번째는 헤더이므로 제외)
                list_items = notice_lists.find_all("li")

                for li in list_items:
                    # 헤더 행은 건너뛰기
                    if "notice_head" in li.get("class", []):
                        continue

                    # 각 컬럼 데이터 추출
                    date_col = li.find("div", class_="notice_col1")
                    status_col = li.find("div", class_="notice_col2")
                    title_col = li.find("div", class_="notice_col3")
                    dept_col = li.find("div", class_="notice_col4")
                    views_col = li.find("div", class_="notice_col5")

                    # 제목 컬럼에서 링크와 카테고리 추출
                    title_link = title_col.find("a") if title_col else None
                    category_label = (
                        title_col.find("span", class_="label") if title_col else None
                    )

                    # 게시글 데이터 구성
                    post_data = {
                        "date": date_col.get_text(strip=True) if date_col else "",
                        "status": status_col.get_text(strip=True) if status_col else "",
                        "category": (
                            category_label.get_text(strip=True)
                            if category_label
                            else ""
                        ),
                        "title": title_link.get_text(strip=True) if title_link else "",
                        "url": title_link.get("href") if title_link else "",
                        "department": dept_col.get_text(strip=True) if dept_col else "",
                        "views": views_col.get_text(strip=True) if views_col else "",
                    }

                    # 카테고리를 제외한 순수 제목만 추출 및 정리
                    if title_link and category_label:
                        # 카테고리 라벨을 제거한 제목
                        title_text = title_link.get_text(strip=True)
                        category_text = category_label.get_text(strip=True)
                        clean_title = title_text.replace(category_text, "").strip()
                        # 줄바꿈과 연속된 공백을 하나의 공백으로 변경
                        clean_title = " ".join(clean_title.split())
                        post_data["title"] = clean_title

                    all_posts.append(post_data)

        # 파싱된 데이터를 JSON으로 저장
        data = {"total_posts": len(all_posts), "posts": all_posts}

        json_file = data_dir / "ssu_notice.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n총 {len(html_files)}개의 HTML 파일 파싱 완료")
        print(f"JSON이 저장되었습니다: {json_file}")
        print(f"총 {len(all_posts)} 개의 게시글을 파싱했습니다.")

        # 처음 3개 게시글 출력 (샘플)
        if all_posts:
            print("\n=== 샘플 게시글 (처음 3개) ===")
            for i, post in enumerate(all_posts[:3], 1):
                print(f"\n{i}. {post['title']}")
                print(f"   날짜: {post['date']}")
                print(f"   카테고리: {post['category']}")
                print(f"   상태: {post['status']}")
                print(f"   부서: {post['department']}")
                print(f"   조회수: {post['views']}")

        return data

    except Exception as e:
        print(f"파싱 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return None


def fetch_notice_details():
    """
    ssu_notice.json에서 각 게시글의 URL을 읽어서 상세 페이지 HTML을 다운로드합니다.
    """
    data_dir = Path("data")
    json_file = data_dir / "ssu_notice.json"

    if not json_file.exists():
        print(f"JSON 파일이 존재하지 않습니다: {json_file}")
        return None

    try:
        # JSON 파일 읽기
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        posts = data.get("posts", [])
        total = len(posts)

        print(f"총 {total}개의 게시글 상세 페이지를 다운로드합니다...")

        # HTML을 저장할 서브 디렉토리 생성
        details_dir = data_dir / "notice_details"
        details_dir.mkdir(exist_ok=True)

        for idx, post in enumerate(posts, 1):
            url = post.get("url", "")
            if not url:
                print(f"[{idx}/{total}] URL이 없는 게시글 건너뜀")
                continue

            # URL에서 slug를 추출하여 ID로 사용
            try:
                from urllib.parse import urlparse, parse_qs

                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                slug = query_params.get("slug", [""])[0]

                if not slug:
                    # slug가 없으면 인덱스 사용
                    slug = f"post_{idx}"

                print(
                    f"[{idx}/{total}] 다운로드 중: {post.get('title', 'Unknown')[:50]}..."
                )

                # HTML 요청
                response = requests.get(url)
                response.raise_for_status()

                # HTML 저장
                html_file = details_dir / f"ssu_notice_{slug}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(response.text)

                print(f"  저장됨: {html_file.name}")

            except Exception as e:
                print(f"  오류 발생: {e}")
                continue

        print(f"\n모든 상세 페이지 다운로드 완료!")
        return True

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return None


def parse_notice_details():
    """
    저장된 ssu_notice_*.html 형태의 상세 페이지 HTML 파일들을 파싱하여
    기존 ssu_notice.json의 각 post에 상세 내용을 추가합니다.
    """
    data_dir = Path("data")
    details_dir = data_dir / "notice_details"
    json_file = data_dir / "ssu_notice.json"

    # ssu_notice.json 파일 확인
    if not json_file.exists():
        print(f"ssu_notice.json 파일이 존재하지 않습니다: {json_file}")
        return None

    if not details_dir.exists():
        print(f"상세 페이지 디렉토리가 존재하지 않습니다: {details_dir}")
        return None

    try:
        # 기존 ssu_notice.json 읽기
        with open(json_file, "r", encoding="utf-8") as f:
            notice_data = json.load(f)

        posts = notice_data.get("posts", [])

        if not posts:
            print("게시글이 없습니다.")
            return None

        print(f"총 {len(posts)}개의 게시글에 상세 내용을 추가합니다...")

        updated_count = 0
        failed_count = 0

        # 각 post에 대해 상세 내용 추가
        for idx, post in enumerate(posts, 1):
            url = post.get("url", "")

            if not url:
                print(f"[{idx}/{len(posts)}] URL이 없는 게시글 건너뜀")
                failed_count += 1
                continue

            try:
                # URL에서 slug 추출
                from urllib.parse import urlparse, parse_qs

                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                slug = query_params.get("slug", [""])[0]

                if not slug:
                    print(f"[{idx}/{len(posts)}] slug를 추출할 수 없음: {url}")
                    failed_count += 1
                    continue

                # 해당하는 HTML 파일 찾기
                html_file = details_dir / f"ssu_notice_{slug}.html"

                if not html_file.exists():
                    print(f"[{idx}/{len(posts)}] HTML 파일이 없음: {html_file.name}")
                    failed_count += 1
                    continue

                print(f"[{idx}/{len(posts)}] 파싱 중: {post.get('title', '')[:50]}...")

                # HTML 파일 읽기
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # HTML 파싱
                soup = BeautifulSoup(html_content, "html.parser")

                # 본문 내용 추출 - 다양한 셀렉터 시도
                content = ""

                content_elem = soup.find("div", class_="wpb_wrapper")
                if content_elem:
                    content = content_elem.get_text(separator="\n", strip=True)

                # 내용 정리 (연속된 공백과 줄바꿈 정리)
                if content:
                    lines = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]
                    content = "\n".join(lines)

                # 첨부파일 추출
                attachments = []
                attachment_download_ul = soup.find("ul", class_="download-list")
                print(f"ul: {attachment_download_ul}")

                if attachment_download_ul:
                    attachment_download_li = attachment_download_ul.find_all("li")

                    for li in attachment_download_li:
                        link = li.find("a", href=True)
                        file_name = link.get_text(strip=True)

                        parsed = urlparse(url)
                        base = f"{parsed.scheme}://{parsed.netloc}"

                        href = link.get("href", "")
                        if file_name:  # 빈 이름 제외
                            attachments.append(
                                {"name": file_name, "url": f"{base}{href}"}
                            )

                # post에 상세 내용 추가
                post["content"] = content
                post["content_length"] = len(content)
                post["attachments"] = attachments
                post["has_attachments"] = len(attachments) > 0

                updated_count += 1

                print(f"post: {post}")

            except Exception as e:
                print(f"[{idx}/{len(posts)}] 파싱 실패: {e}")
                failed_count += 1
                continue

        # 업데이트된 데이터를 다시 저장
        notice_data["posts"] = posts

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(notice_data, f, ensure_ascii=False, indent=2)

        print(f"\n=== 파싱 완료 ===")
        print(f"성공: {updated_count}개")
        print(f"실패: {failed_count}개")
        print(f"JSON이 업데이트되었습니다: {json_file}")

        # print(soup.prettify()[800:])

        # 샘플 출력
        if posts and updated_count > 0:
            print("\n=== 샘플 게시글 (상세 내용이 추가된 첫 번째 게시글) ===")
            for post in posts:
                if "content" in post and post["content"]:
                    print(f"제목: {post['title']}")
                    print(f"날짜: {post['date']}")
                    print(f"카테고리: {post['category']}")
                    print(f"부서: {post['department']}")
                    print(f"내용 길이: {post.get('content_length', 0)}자")
                    print(f"첨부파일: {len(post.get('attachments', []))}개")

                    break

        return notice_data

    except Exception as e:
        print(f"파싱 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return None


def fetch_all_pages(start_page: int = 1, end_page: int = 50):
    """
    지정된 범위의 페이지를 모두 가져옵니다.

    Args:
        start_page: 시작 페이지 번호
        end_page: 종료 페이지 번호 (포함)
    """
    print(f"페이지 {start_page}부터 {end_page}까지 데이터를 가져옵니다...")

    for page in range(start_page, end_page + 1):
        print(f"\n[{page}/{end_page}] 페이지 {page} 데이터를 가져오는 중...")
        try:
            fetch_ssu_notice_list(page)
        except Exception as e:
            print(f"페이지 {page} 처리 중 오류 발생: {e}")
            continue

    print(f"\n모든 페이지 데이터 수집 완료!")


if __name__ == "__main__":
    # === 1단계: 공지사항 목록 수집 ===
    # 1-1. 데이터 수집: 1~50페이지까지 공지사항 목록 가져오기
    # fetch_all_pages(1, 50)

    # 1-2. 데이터 파싱: 저장된 목록 HTML 파일들을 JSON으로 변환
    # parse_ssu_notice_list()

    # === 2단계: 각 공지사항의 상세 페이지 수집 ===
    # 2-1. 상세 페이지 다운로드: ssu_notice.json의 각 URL에서 HTML 다운로드
    # fetch_notice_details()

    # 2-2. 상세 페이지 파싱: 저장된 상세 HTML 파일들을 파싱하여 JSON으로 변환
    # parse_notice_details()

    pass
