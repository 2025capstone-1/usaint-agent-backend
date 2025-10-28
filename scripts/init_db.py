import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy import text
from lib.database import Base, engine

# SQLAlchemy가 테이블 구조를 인식할 수 있도록 모든 모델(Entity)을 임포트합니다.
from apps.user_api.domain.user.entity import User
from apps.user_api.domain.usaint_account.entity import UsaintAccount
from apps.user_api.domain.chat_room.entity import ChatRoom
from apps.user_api.domain.chat.entity import Chat
from apps.user_api.domain.schedule.entity import Schedule

def reset_database():
    """
    단일 DB 연결을 사용하여 외래 키 제약을 비활성화하고,
    모든 테이블을 삭제한 뒤 최신 모델 기준으로 다시 생성합니다.
    """
    print("경고: 데이터베이스의 모든 데이터가 영구적으로 삭제됩니다.")
    choice = input("계속하시겠습니까? (y/n): ").lower()
    
    if choice != 'y':
        print("작업이 취소되었습니다.")
        return

    print("DB 초기화 시작...")
    try:
        with engine.connect() as conn:
            # 트랜잭션을 시작합니다.
            trans = conn.begin()
            try:
                # 1. 외래 키 제약 조건 비활성화
                conn.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
                
                # 2. 'conn'을 사용하여 모든 테이블 삭제
                print("테이블 삭제 중...")
                Base.metadata.drop_all(conn)
                
                # 3. 'conn'을 사용하여 모든 테이블 생성
                print("테이블 생성 중...")
                Base.metadata.create_all(conn)
                
                # 4. 외래 키 제약 조건 다시 활성화
                conn.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
                
                # 트랜잭션 커밋
                trans.commit()
                print("DB 초기화 성공")
            except Exception:
                # 오류 발생 시 롤백
                trans.rollback()
                raise
    except Exception as e:
        print(f"DB 초기화 중 오류 발생: {e}")

if __name__ == "__main__":
    reset_database()