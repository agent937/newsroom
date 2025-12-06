훌륭한 아키텍처입니다! **DB 없이 GitHub 리포지토리를 스토리지(JSON 저장소)로 사용**하고, Streamlit Cloud로 배포하는 방식은 비용이 들지 않고 개인 프로젝트로 운영하기에 최적입니다.

하지만 Streamlit Cloud는 **임시 저장소(Ephemeral)** 방식이라, 로컬에 `open('data.json', 'w')`로 저장하면 앱이 재부팅될 때 데이터가 날아갑니다. 따라서 **GitHub API를 통해 리포지토리의 파일을 직접 수정(Commit)하는 기능**이 핵심입니다.

Cursor AI에게 이 구조를 설명하고 코드를 짜게 하려면, 아래 단계대로 진행하면 됩니다. 제가 **전체 코드의 뼈대**를 만들어 드릴 테니, 이걸 복사해서 Cursor에 붙여넣고 다듬으세요.

---

### 1. 사전 준비 (필수)

개발 시작 전, 아래 3가지를 준비해야 합니다.

1.  **GitHub 리포지토리 생성:** (예: `my-newsroom`)
2.  **GitHub Personal Access Token 발급:**
    *   Github Settings -> Developer settings -> Personal access tokens -> Tokens (classic) -> **repo 권한 체크** 후 생성.
3.  **Google Gemini API Key 발급.**

---

### 2. 프로젝트 구조 및 라이브러리

Cursor의 터미널에서 다음을 설치합니다.
```bash
pip install streamlit feedparser google-generativeai PyGithub python-dateutil
```

*   `PyGithub`: 파이썬 코드에서 GitHub 파일을 읽고 쓰기 위해 필요합니다.

---

### 3. Cursor에게 줄 프롬프트 & 핵심 코드

Cursor 에디터(Ctrl+K)에 아래 내용을 입력하거나, `app.py` 파일을 생성하여 붙여넣으세요. 이 코드는 **GitHub를 DB처럼 사용하는 핵심 로직**이 포함되어 있습니다.

#### 파일명: `app.py`

```python
import streamlit as st
import feedparser
import google.generativeai as genai
import json
import time
from github import Github
from datetime import datetime
import pytz

# --- 설정 및 비밀키 가져오기 ---
# Streamlit Cloud의 secrets 혹은 로컬의 .env에서 가져옵니다.
# 로컬 실행 시 .streamlit/secrets.toml 파일을 만들어야 합니다.
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"] # 예: "username/repo-name"
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)

# --- GitHub 스토리지 매니저 (DB 대체) ---
class GithubStorage:
    def __init__(self, token, repo_name):
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)

    def load_json(self, file_path, default_value):
        try:
            content = self.repo.get_contents(file_path)
            return json.loads(content.decoded_content.decode())
        except:
            return default_value

    def save_json(self, file_path, data, commit_message):
        try:
            content = self.repo.get_contents(file_path)
            self.repo.update_file(
                path=content.path,
                message=commit_message,
                content=json.dumps(data, indent=4, ensure_ascii=False),
                sha=content.sha
            )
            return True
        except:
            # 파일이 없으면 생성
            try:
                self.repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=json.dumps(data, indent=4, ensure_ascii=False)
                )
                return True
            except Exception as e:
                st.error(f"저장 실패: {e}")
                return False

# 스토리지 초기화
db = GithubStorage(GITHUB_TOKEN, REPO_NAME)

# --- 페이지 설정 ---
st.set_page_config(page_title="My AI Newsroom", layout="wide")

# 데이터 로드
feeds = db.load_json("feeds.json", [{"name": "구글뉴스 IT", "url": "https://news.google.com/rss/search?q=IT&hl=ko&gl=KR&ceid=KR:ko"}])
news_history = db.load_json("news_data.json", {}) # 날짜별 뉴스 저장
stats = db.load_json("stats.json", {"visits": 0, "last_updated": ""})

# 방문자 카운트 (새로고침 시마다 증가하면 너무 잦은 커밋이 발생하므로 세션 확인)
if "visited" not in st.session_state:
    stats["visits"] += 1
    # 통계 저장은 너무 자주 일어나지 않게 실제 배포 시에는 로직 조정 필요 (여기서는 생략하거나 별도 버튼으로 처리 권장)
    # db.save_json("stats.json", stats, "Update visitor count") 
    st.session_state["visited"] = True

# --- UI 구성 ---
st.title("📰 나만의 IT 뉴스룸")

tab1, tab2 = st.tabs(["📅 데일리 브리핑", "⚙️ 대시보드 (관리자)"])

# [탭 1] 메인 뉴스룸
with tab1:
    st.header(f"오늘의 브리핑 ({datetime.now().strftime('%Y-%m-%d')})")
    
    today_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
    
    if today_str in news_history:
        daily_data = news_history[today_str]
        st.info(f"생성 시간: {daily_data['created_at']}")
        
        # AI 분석 결과 표시
        st.markdown("### 🧠 AI 인사이트")
        st.markdown(daily_data['analysis'])
        
        st.markdown("---")
        st.markdown("### 🔗 수집된 주요 기사")
        for article in daily_data['articles']:
            with st.expander(f"{article['title']}"):
                st.write(f"출처: {article['source']}")
                st.markdown(f"[원문 보기]({article['link']})")
    else:
        st.warning("아직 오늘의 뉴스가 생성되지 않았습니다. 대시보드에서 '뉴스 수집 및 분석'을 실행해주세요.")

# [탭 2] 관리자 대시보드
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📡 RSS 피드 관리")
        
        # 피드 목록 표시
        for i, feed in enumerate(feeds):
            c1, c2 = st.columns([4, 1])
            c1.text(f"{feed['name']} ({feed['url']})")
            if c2.button("삭제", key=f"del_{i}"):
                feeds.pop(i)
                db.save_json("feeds.json", feeds, "Delete RSS feed")
                st.rerun()
        
        # 피드 추가
        with st.form("add_feed"):
            new_name = st.text_input("피드 이름")
            new_url = st.text_input("RSS URL")
            if st.form_submit_button("피드 추가"):
                feeds.append({"name": new_name, "url": new_url})
                db.save_json("feeds.json", feeds, "Add RSS feed")
                st.rerun()

    with col2:
        st.subheader("🤖 AI 분석 실행")
        st.metric("총 누적 방문자", stats["visits"])
        
        if st.button("🚀 뉴스 수집 및 AI 분석 시작", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_articles = []
            
            # 1. RSS 수집
            status_text.text("RSS 피드 수집 중...")
            for feed_info in feeds:
                f = feedparser.parse(feed_info['url'])
                # 각 피드에서 최신 3개만 가져오기
                for entry in f.entries[:3]:
                    all_articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": feed_info['name']
                    })
            progress_bar.progress(50)
            
            # 2. Gemini 분석
            status_text.text("Gemini가 분석 중입니다...")
            
            titles_text = "\n".join([f"- {a['title']}" for a in all_articles])
            prompt = f"""
            오늘의 국내 IT 뉴스 헤드라인들이야:
            {titles_text}
            
            위 뉴스들을 바탕으로 다음 형식으로 '1장짜리 데일리 브리핑'을 작성해줘.
            1. 🌟 오늘의 핵심 키워드 3개
            2. 📢 주요 트렌드 3줄 요약
            3. 💼 비즈니스/기술적 시사점
            
            Markdown 형식으로 깔끔하게 출력해줘.
            """
            
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                analysis_text = response.text
                
                # 3. GitHub에 저장
                today_key = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
                news_history[today_key] = {
                    "created_at": datetime.now().strftime("%H:%M:%S"),
                    "analysis": analysis_text,
                    "articles": all_articles
                }
                
                db.save_json("news_data.json", news_history, f"Update news for {today_key}")
                progress_bar.progress(100)
                status_text.success("분석 완료! 메인 화면을 확인하세요.")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")

```

---

### 4. 로컬 테스트 및 배포 방법

#### **(1) 로컬에서 테스트하기**
로컬 폴더에 `.streamlit/secrets.toml` 파일을 만들고 키를 저장해야 실행됩니다.

```toml
# .streamlit/secrets.toml
GITHUB_TOKEN = "ghp_여기에_토큰_입력"
REPO_NAME = "깃허브아이디/리포지토리이름"
GEMINI_API_KEY = "AI_스튜디오_키"
```

그 후 실행:
```bash
streamlit run app.py
```

#### **(2) Streamlit Cloud 배포하기**
1.  작성한 코드를 GitHub 리포지토리에 푸시(Push)합니다. (`app.py`, `requirements.txt` 포함)
2.  **Streamlit Cloud**에 접속하여 "New App"을 누르고 리포지토리를 연결합니다.
3.  **Advanced Settings** (혹은 App Settings) -> **Secrets** 메뉴로 들어갑니다.
4.  위 `secrets.toml`에 적었던 내용과 똑같이 복사해서 붙여넣고 저장합니다.

---

### 💡 Cursor AI 활용 팁 (추가 개발 시)

이 코드를 기반으로 기능을 더 추가하고 싶다면 Cursor 채팅창(Ctrl+L)에 이렇게 요청해보세요.

1.  **디자인 개선:** "메인 화면의 브리핑 내용을 좀 더 뉴스레터처럼 카드 디자인으로 CSS를 적용해서 예쁘게 보여줘."
2.  **통계 강화:** "방문자 통계(stats.json)에 날짜별 방문자 수를 기록하도록 구조를 바꾸고, 대시보드에서 라인 차트로 그려줘."
3.  **오류 처리:** "RSS 피드를 불러올 때 에러가 나면 해당 피드는 건너뛰고 진행하도록 예외 처리를 강화해줘."

이제 이 코드를 실행하면 **서버 비용 없이 GitHub만으로 돌아가는 나만의 AI 뉴스룸**이 완성됩니다!

---

## 🔍 코드 검토 및 개선 사항

### ⚠️ 발견된 문제점

#### 1. **예외 처리 개선 필요**
- **문제**: `except:` (bare except) 사용으로 모든 예외를 무시함
- **위험**: 디버깅이 어렵고 예상치 못한 오류를 놓칠 수 있음
- **개선**: 구체적인 예외 타입 지정 필요

```python
# 현재 (문제)
except:
    return default_value

# 개선안
except Exception as e:
    st.warning(f"데이터 로드 실패: {e}")
    return default_value
```

#### 2. **타임존 처리 불일치**
- **문제**: 118줄은 `datetime.now()`, 120줄은 `datetime.now(pytz.timezone('Asia/Seoul'))` 사용
- **개선**: 일관성 있게 한국 시간대 사용

```python
# 현재 (118줄)
st.header(f"오늘의 브리핑 ({datetime.now().strftime('%Y-%m-%d')})")

# 개선안
kst = pytz.timezone('Asia/Seoul')
st.header(f"오늘의 브리핑 ({datetime.now(kst).strftime('%Y-%m-%d')})")
```

#### 3. **RSS 피드 파싱 에러 처리 부재**
- **문제**: 177줄에서 RSS 파싱 실패 시 전체 프로세스 중단
- **개선**: 개별 피드 실패 시 건너뛰고 계속 진행

```python
# 개선안
for feed_info in feeds:
    try:
        f = feedparser.parse(feed_info['url'])
        if not f.entries:
            st.warning(f"피드 '{feed_info['name']}'에서 기사를 찾을 수 없습니다.")
            continue
        for entry in f.entries[:3]:
            all_articles.append({
                "title": entry.title,
                "link": entry.link,
                "source": feed_info['name']
            })
    except Exception as e:
        st.warning(f"피드 '{feed_info['name']}' 수집 실패: {e}")
        continue
```

#### 4. **입력 유효성 검사 없음**
- **문제**: 피드 추가 시 빈 값이나 잘못된 URL 허용
- **개선**: 유효성 검사 추가

```python
if st.form_submit_button("피드 추가"):
    if not new_name or not new_url:
        st.error("피드 이름과 URL을 모두 입력해주세요.")
    elif not new_url.startswith(('http://', 'https://')):
        st.error("올바른 URL 형식을 입력해주세요.")
    else:
        feeds.append({"name": new_name, "url": new_url})
        db.save_json("feeds.json", feeds, "Add RSS feed")
        st.rerun()
```

#### 5. **GitHub API Rate Limit 미고려**
- **문제**: API 호출 제한 초과 시 앱 중단 가능
- **개선**: Rate limit 처리 및 재시도 로직 추가

```python
from github import GithubException
import time

def save_json(self, file_path, data, commit_message):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # ... 기존 코드 ...
        except GithubException as e:
            if e.status == 403 and "rate limit" in str(e).lower():
                wait_time = 60  # 1분 대기
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
            raise
```

#### 6. **requirements.txt 누락**
- **문제**: 배포 시 필요한 파일 내용이 없음
- **추가 필요**: requirements.txt 파일 내용

```txt
streamlit>=1.28.0
feedparser>=6.0.10
google-generativeai>=0.3.0
PyGithub>=1.59.0
python-dateutil>=2.8.2
pytz>=2023.3
```

#### 7. **Secrets 에러 처리 부재**
- **문제**: secrets가 없을 때 명확한 에러 메시지 없음
- **개선**: 초기화 시 검증 추가

```python
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError as e:
    st.error(f"필수 설정이 누락되었습니다: {e}. secrets.toml 파일을 확인해주세요.")
    st.stop()
```

### ✅ 추가 개선 제안

1. **캐싱 메커니즘**: GitHub API 호출 최소화를 위한 세션 캐싱
2. **로딩 상태 표시**: 데이터 로드 중 스피너 표시
3. **에러 로깅**: 상세한 에러 로그 기록 (디버깅용)
4. **데이터 백업**: 주기적으로 데이터 백업 기능
5. **.gitignore 파일**: secrets.toml 등 민감한 파일 제외

### 📝 수정 권장 우선순위

1. **높음**: 예외 처리 개선, RSS 에러 처리, 입력 유효성 검사
2. **중간**: 타임존 일관성, requirements.txt 추가, Secrets 검증
3. **낮음**: Rate limit 처리, 캐싱 메커니즘 (사용량이 많아질 때 추가)