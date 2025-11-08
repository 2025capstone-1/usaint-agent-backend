import json
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.utils import embedding_functions
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 한국어 임베딩 함수 설정
korean_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="jhgan/ko-sroberta-multitask"  # 한국어 특화 모델
)

# chroma db - persistent client로 변경
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def add_notices_to_chromadb(
    json_path: str = "data/ssu_notice.json",
    collection_name: str = "ssu_notice",
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    data/ssu_notice.json 파일을 읽어서 ChromaDB의 컬렉션에 데이터를 추가합니다.

    Args:
        json_path: JSON 파일 경로
        collection_name: ChromaDB 컬렉션 이름
        batch_size: 한 번에 추가할 데이터 개수

    Returns:
        처리 결과 딕셔너리 (총 개수, 성공/실패 등)
    """
    try:
        # JSON 파일 읽기
        json_file = Path(json_path)

        if not json_file.exists():
            return {"error": f"JSON 파일이 존재하지 않습니다: {json_path}"}

        print(f"JSON 파일을 읽는 중: {json_path}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        posts = data.get("posts", [])
        total_posts = len(posts)

        print(f"총 {total_posts}개의 게시글을 처리합니다...")

        # ChromaDB 컬렉션 가져오기 또는 생성 (한국어 임베딩 함수 사용)
        try:
            collection = chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "숭실대학교 공지사항"},
                embedding_function=korean_ef,
            )
            print(f"컬렉션 '{collection_name}' 준비 완료 (한국어 임베딩)")
        except Exception as e:
            return {"error": f"컬렉션 생성/가져오기 실패: {e}"}

        # 데이터 준비
        documents = []
        metadatas = []
        ids = []

        success_count = 0
        skip_count = 0

        for idx, post in enumerate(posts, 1):
            try:
                # 문서 텍스트 구성 (제목 + 내용)
                title = post.get("title", "")
                content = post.get("content", "")
                category = post.get("category", "")
                department = post.get("department", "")

                # 임베딩을 위한 문서 텍스트
                doc_text = f"[{category}] {title}\n\n{content}"

                # 내용이 너무 짧으면 건너뛰기
                if len(doc_text.strip()) < 10:
                    skip_count += 1
                    continue

                # 메타데이터 구성
                metadata = {
                    "title": title,
                    "category": category,
                    "date": post.get("date", ""),
                    "status": post.get("status", ""),
                    "department": department,
                    "url": post.get("url", ""),
                    "views": post.get("views", ""),
                    "content_length": post.get("content_length", 0),
                    "has_attachments": post.get("has_attachments", False),
                }

                # ID 생성 (URL의 slug 사용 또는 인덱스)
                url = post.get("url", "")
                if "slug=" in url:
                    post_id = url.split("slug=")[1].split("&")[0]
                else:
                    post_id = f"post_{idx}"

                documents.append(doc_text)
                metadatas.append(metadata)
                ids.append(post_id)

                # 배치 크기만큼 모이면 추가
                if len(documents) >= batch_size:
                    collection.add(documents=documents, metadatas=metadatas, ids=ids)
                    success_count += len(documents)
                    print(f"진행: {success_count}/{total_posts} 게시글 추가됨")

                    # 리스트 초기화
                    documents = []
                    metadatas = []
                    ids = []

            except Exception as e:
                print(f"게시글 {idx} 처리 중 오류: {e}")
                skip_count += 1
                continue

        # 남은 데이터 추가
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            success_count += len(documents)

        result = {
            "collection_name": collection_name,
            "total_posts": total_posts,
            "success_count": success_count,
            "skip_count": skip_count,
            "collection_count": collection.count(),
        }

        print("\n=== 완료 ===")
        print(f"성공: {success_count}개")
        print(f"건너뜀: {skip_count}개")
        print(f"컬렉션 총 문서 수: {collection.count()}개")

        return result

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": f"처리 중 오류 발생: {e}"}


def reset_collection(collection_name: str = "ssu_notice") -> Dict[str, str]:
    """
    ChromaDB 컬렉션을 삭제하여 초기화합니다.

    Args:
        collection_name: 삭제할 컬렉션 이름

    Returns:
        결과 메시지
    """
    try:
        chroma_client.delete_collection(name=collection_name)
        print(f"컬렉션 '{collection_name}'이(가) 삭제되었습니다.")
        return {"status": "success", "message": f"컬렉션 '{collection_name}' 삭제 완료"}
    except Exception as e:
        print(f"컬렉션 삭제 중 오류: {e}")
        return {"status": "error", "message": str(e)}


def reset_chromadb() -> Dict[str, str]:
    """
    ChromaDB 전체를 초기화합니다. (모든 컬렉션 삭제)

    Returns:
        결과 메시지
    """
    try:
        collections = chroma_client.list_collections()
        deleted_count = 0

        for collection in collections:
            chroma_client.delete_collection(name=collection.name)
            print(f"컬렉션 '{collection.name}' 삭제됨")
            deleted_count += 1

        print(f"\n총 {deleted_count}개의 컬렉션이 삭제되었습니다.")
        return {
            "status": "success",
            "message": f"{deleted_count}개 컬렉션 삭제 완료",
        }
    except Exception as e:
        print(f"ChromaDB 초기화 중 오류: {e}")
        return {"status": "error", "message": str(e)}


def get_collection_info(collection_name: str = "ssu_notice") -> Dict[str, Any]:
    """
    컬렉션 정보를 조회합니다.

    Args:
        collection_name: 조회할 컬렉션 이름

    Returns:
        컬렉션 정보
    """
    try:
        collection = chroma_client.get_collection(
            name=collection_name, embedding_function=korean_ef
        )
        count = collection.count()
        metadata = collection.metadata

        info = {
            "name": collection_name,
            "count": count,
            "metadata": metadata,
        }

        print(f"컬렉션: {collection_name}")
        print(f"문서 수: {count}")
        print(f"메타데이터: {metadata}")

        return info
    except Exception as e:
        print(f"컬렉션 정보 조회 중 오류: {e}")
        return {"error": str(e)}


def list_collections() -> List[str]:
    """
    모든 컬렉션 목록을 조회합니다.

    Returns:
        컬렉션 이름 리스트
    """
    try:
        collections = chroma_client.list_collections()
        collection_names = [col.name for col in collections]

        print(f"총 {len(collection_names)}개의 컬렉션:")
        for name in collection_names:
            col = chroma_client.get_collection(name=name)
            print(f"  - {name} ({col.count()}개 문서)")

        return collection_names
    except Exception as e:
        print(f"컬렉션 목록 조회 중 오류: {e}")
        return []


class SearchNoticeRequest(BaseModel):
    query: str = Field(description="검색어")


@tool(args_schema=SearchNoticeRequest)
def search_ssu_notice(query: str):
    """ChromaDB에서 공지사항을 검색합니다."""
    return search_notices(query=query, n_results=3, date_weight=0.2)


def search_notices(
    query: str,
    collection_name: str = "ssu_notice",
    n_results: int = 5,
    date_weight: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    ChromaDB에서 공지사항을 검색합니다.

    Args:
        query: 검색 쿼리
        collection_name: 컬렉션 이름
        n_results: 반환할 결과 개수
        date_weight: 날짜 가중치 (0.0~1.0, 0이면 날짜 무시, 1이면 날짜만 고려)

    Returns:
        검색 결과 리스트
    """
    try:
        collection = chroma_client.get_collection(
            name=collection_name, embedding_function=korean_ef
        )

        # 더 많은 결과를 가져와서 날짜 기반 재정렬
        fetch_count = n_results * 3 if date_weight > 0 else n_results
        results = collection.query(query_texts=[query], n_results=fetch_count)

        # 결과 포맷팅
        formatted_results = []

        if results and results["documents"]:
            from datetime import datetime

            for i in range(len(results["documents"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                result = {
                    "document": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": distance,
                    "similarity_score": 1 / (1 + distance),  # 거리를 유사도로 변환
                }

                # 날짜 점수 계산
                if date_weight > 0 and metadata.get("date"):
                    try:
                        # 날짜 파싱 (형식: 2025.10.29)
                        date_str = metadata["date"]
                        date_obj = datetime.strptime(date_str, "%Y.%m.%d")

                        # 현재 날짜와의 차이 (일 단위)
                        days_diff = (datetime.now() - date_obj).days

                        # 날짜 점수: 최근일수록 높은 점수 (0~1 사이로 정규화)
                        # 180일(6개월) 이내는 점수가 높게, 그 이후는 점수가 낮게
                        date_score = max(0, 1 - (days_diff / 180))

                        result["date_score"] = date_score

                        # 최종 점수: 유사도와 날짜 점수의 가중 평균
                        result["final_score"] = (1 - date_weight) * result[
                            "similarity_score"
                        ] + date_weight * date_score
                    except:
                        result["date_score"] = 0
                        result["final_score"] = result["similarity_score"]
                else:
                    result["date_score"] = 0
                    result["final_score"] = result["similarity_score"]

                formatted_results.append(result)

            # 날짜 가중치가 있으면 final_score로 재정렬
            if date_weight > 0:
                formatted_results.sort(key=lambda x: x["final_score"], reverse=True)
                formatted_results = formatted_results[:n_results]

        return formatted_results

    except Exception as e:
        print(f"검색 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    # === 사용 예제 ===

    # 0. ChromaDB에 데이터 추가 (처음 한 번만 실행)
    # print("\n=== 데이터 추가 ===")
    # result = add_notices_to_chromadb()
    # print("결과:", result)

    # 1. 모든 컬렉션 목록 조회
    # print("=== 컬렉션 목록 ===")
    # list_collections()

    # 2. 특정 컬렉션 정보 조회
    # print("\n=== 컬렉션 정보 ===")
    # get_collection_info("ssu_notice")

    # 4. 검색 테스트 (날짜 가중치 없음 - 유사도만)
    print("\n=== 검색 테스트 (유사도만) ===")
    search_results = search_notices("장학금", n_results=5, date_weight=0.0)

    for i, res in enumerate(search_results, 1):
        print(f"\n{i}. {res['metadata'].get('title', 'N/A')}")
        print(f"   카테고리: {res['metadata'].get('category', 'N/A')}")
        print(f"   날짜: {res['metadata'].get('date', 'N/A')}")
        print(f"   거리: {res['distance']:.4f}")

    # 4-2. 검색 테스트 (날짜 가중치 30% - 최신 글 우선)
    print("\n\n=== 검색 테스트 (유사도 70% + 날짜 30%) ===")
    search_results = search_notices("장학금", n_results=5, date_weight=0.3)

    for i, res in enumerate(search_results, 1):
        print(f"\n{i}. {res['metadata'].get('title', 'N/A')}")
        print(f"   카테고리: {res['metadata'].get('category', 'N/A')}")
        print(f"   날짜: {res['metadata'].get('date', 'N/A')}")
        print(
            f"   유사도: {res['similarity_score']:.4f}, 날짜: {res.get('date_score', 0):.4f}, 최종: {res['final_score']:.4f}"
        )

    # 5. 특정 컬렉션 초기화 (삭제)
    # print("\n=== 컬렉션 초기화 ===")
    # reset_collection("ssu_notice")

    # 6. ChromaDB 전체 초기화 (모든 컬렉션 삭제) - 주의!
    # print("\n=== ChromaDB 전체 초기화 ===")
    # reset_chromadb()
