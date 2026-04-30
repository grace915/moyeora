# Moyeora 🗓️ — 친구들과 약속 잡기

여러 명의 친구가 함께 모임 일정을 정할 수 있는 가벼운 웹앱입니다.
**모여라(Moyeora)** — "다 같이 모여라!"

## 주요 기능

- 모임을 만들고 후보 일시를 여러 개 등록
- 공유 링크로 친구들을 초대
- 친구별로 각 후보에 **가능 / 애매 / 불가** 응답
- 점수(가능 2점, 애매 1점) 기준으로 최적 시간 자동 표시 🏆
- 응답 후에도 같은 이름으로 들어가 갱신 가능
- 누구나 새 후보 일시 추가 가능

## 빠른 시작

```powershell
cd moyeora
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

브라우저에서 http://localhost:5001 접속.

## 프로젝트 구조

```
moyeora/
├── app.py              # Flask 라우트
├── db.py               # SQLite 데이터 액세스 계층
├── requirements.txt
├── moyeora.db          # (자동 생성) SQLite DB
├── templates/
│   ├── base.html
│   ├── index.html      # 모임 생성 폼
│   ├── event.html      # 모임 상세 / 응답 / 현황
│   └── 404.html
└── static/
    └── style.css
```

## 데이터 모델

- **events** `(id, slug, title, description, organizer, created_at)`
- **options** `(id, event_id, starts_at, label)`
- **responses** `(id, option_id, name, status [yes|maybe|no], created_at)`
  - `UNIQUE(option_id, name)` — 같은 사람이 같은 옵션에 한 번의 응답

## 향후 확장 아이디어

- 마감 시간 설정
- 주최자 토큰 기반 옵션 삭제
- ICS 캘린더 다운로드
- 댓글 / 메모 기능
