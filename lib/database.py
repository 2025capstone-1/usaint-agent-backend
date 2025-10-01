from functools import wraps
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.orm.session import Session
from lib.env import get_env

pymysql.install_as_MySQLdb()

DB_USER = get_env("DB_USER")
DB_PASSWORD = get_env("DB_PASSWORD")
DB_HOST = get_env("DB_HOST")
DB_PORT = get_env("DB_PORT")
DB_NAME = get_env("DB_NAME")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Engine 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# 세션팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base: DeclarativeBase = declarative_base()


def transactional(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = kwargs.get("db") or next((a for a in args if isinstance(a, Session)), None)
        if db is None:
            raise ValueError("Session 객체(db)가 필요합니다")

        try:
            result = func(*args, **kwargs)
            db.commit()
            return result
        except:
            db.rollback()
            raise

    return wrapper


# 의존성 주입용 세션 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
