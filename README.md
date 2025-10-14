## Getting Started
```
# MySQL8 설치.
https://hongong.hanbit.co.kr/mysql-%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-%EB%B0%8F-%EC%84%A4%EC%B9%98%ED%95%98%EA%B8%B0mysql-community-8-0/

## 아래와 같은 데이터베이스를 만들어주세요.
CREATE DATABASE usaint_agent_db;

## MySQL 사용자 생성. id: admin, password: temppassword인 예제.
CREATE USER 'admin'@'%'
IDENTIFIED WITH 'mysql_native_password' BY 'temppassword'
REQUIRE NONE
PASSWORD EXPIRE NEVER
ACCOUNT UNLOCK
PASSWORD HISTORY DEFAULT
PASSWORD REUSE INTERVAL DEFAULT
PASSWORD REQUIRE CURRENT DEFAULT;

## 권한 부여
GRANT ALL PRIVILEGES ON *.* to 'admin'@'%';
FLUSH PRIVILEGES;
```
```
git clone https://github.com/2025capstone-1/usaint-agent-backend.git
cd usaint-agent-backend

# 파이썬 uv 설치
https://tilnote.io/en/pages/67f2927b2a14e2a1ab482f5a

# 패키지 의존성 설치
uv sync

# 가상환경 활성화
source .venv/bin/activate

# .env 파일 생성
.env.sample을 참고해서 .env 파일을 만들어주세요.

# 실행 - DB 테이블이 자동으로 생성되며 8000번에서 실행됩니다.
uv run uvicorn main:app --reload --port 8000
```

### 인증 관련 시작을 위한 가이드
- http://localhost:8000/docs 에서 회원가입 api를 호출하여 사용자를 하나 만든 뒤, 그대로 로그인 api를 호출해서 access_token을 복사해주세요. 예를 들어, 아래는 user_id가 1번인 사용자를 위한 토큰입니다.
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiYXV0aG9yaXR5IjoiUk9MRV9VU0VSIiwiZXhwIjoxNzkwODUzNjkxfQ.nSb_uXqPbmYd3nvmcuPx5BhLCMyHyj8b0Uh3eUHVuEo
```
- 자물쇠 모양을 누르고, 이 token을 넣어서 로그인 한 뒤 로그인이 필요한 여러 api를 호출해볼 수 있습니다.
- 스웨거가 아닌 postman 등의 도구도 좋습니다.

### Commit Rules
- 커밋은 작업단위로 하여, 버전관리를 용이하도록 합니다.
- feat, chore, fix, docs 에서 적절한 것을 택해 "fix: 로그인 에러", "feat: 채팅 조회" 와 같은 식으로 작성합니다.
- 파이썬 스타일은 autopep8 extensions을 사용합니다.

### Directory
- 프로젝트에는 agent와 user_api 이렇게 2개의 애플리케이션이 있으며 user_api가 api 애플리케이션입니다. 
- `auth`, `chat`, `chat_room`, `schedule`, `usaint_account`, `user` 도메인으로 구성됩니다.
- 각 도메인은 기본적으로 `controller`, `service`, `entity`, `dto`, `exception`으로 구성되며, 요청/응답에 필요한 클래스는 `dto/request` 또는 `dto/response`에, 필요한 예외는 `exception.py`에 정의합니다. controller는 api 요청이 들어오는 일종의 라우터이며, 간단하지 않은 비즈니스 로직을 작성해야하는 경우, controller가 아닌 service에 작성하도록 합니다.
```
.
├── apps
│   ├── agent
│   └── user_api
│       ├── __init__.py
│       └── domain
│           ├── __init__.py
│           ├── auth
│           │   ├── controller.py
│           │   ├── dto
│           │   |    ├── request.py
│           │   |    └── response.py
│           │   ├── exception.py
│           │   └── service.py
│           ├── chat
│           │   ├── controller.py
│           │   ├── service.py
│           │   ├── dto
│           │   |    ├── request.py
│           │   |    └── response.py
│           │   ├── exception.py
│           │   └── entity.py
│           ├── chat_room
│           │   ├── controller.py
│           │   ├── service.py
│           │   ├── dto
│           │   |    ├── request.py
│           │   |    └── response.py
│           │   ├── exception.py
│           │   └── entity.py
│           ├── schedule
│           │   ├── controller.py
│           │   ├── service.py
│           │   ├── dto
│           │   |    ├── request.py
│           │   |    └── response.py
│           │   ├── exception.py
│           │   └── entity.py
│           ├── usaint_account
│           │   ├── controller.py
│           │   ├── service.py
│           │   ├── dto
│           │   |    ├── request.py
│           │   |    └── response.py
│           │   ├── exception.py
│           │   └── entity.py
│           └── user
│               ├── controller.py
│               ├── service.py
│               ├── dto
│               |    ├── request.py
│               |    └── response.py
│               ├── exception.py
│               └── entity.py
├── lib
│   ├── database.py
│   └── env.py
├── main.py
├── pyproject.toml
├── README.md
└── uv.lock
```

