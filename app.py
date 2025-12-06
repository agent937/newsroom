import streamlit as st
import feedparser
import google.generativeai as genai
import json
import time
from github import Github, GithubException
from datetime import datetime
import pytz
from urllib.parse import urlparse

# --- 설정 및 비밀키 가져오기 ---
# Streamlit Cloud의 secrets 혹은 로컬의 .env에서 가져옵니다.
# 로컬 실행 시 .streamlit/secrets.toml 파일을 만들어야 합니다.
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]  # 예: "username/repo-name"
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError as e:
    st.error(f"필수 설정이 누락되었습니다: {e}. secrets.toml 파일을 확인해주세요.")
    st.stop()

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# --- GitHub 스토리지 매니저 (DB 대체) ---
class GithubStorage:
    def __init__(self, token, repo_name):
        try:
            self.g = Github(token)
            self.repo = self.g.get_repo(repo_name)
        except GithubException as e:
            st.error(f"GitHub 리포지토리 연결 실패: {e}")
            st.stop()
        except Exception as e:
            st.error(f"초기화 오류: {e}")
            st.stop()

    def load_json(self, file_path, default_value):
        """GitHub에서 JSON 파일을 로드합니다."""
        try:
            content = self.repo.get_contents(file_path)
            return json.loads(content.decoded_content.decode())
        except GithubException as e:
            if e.status == 404:
                # 파일이 없으면 기본값 반환
                return default_value
            else:
                st.warning(f"데이터 로드 실패 ({file_path}): {e}")
                return default_value
        except json.JSONDecodeError as e:
            st.warning(f"JSON 파싱 오류 ({file_path}): {e}")
            return default_value
        except Exception as e:
            st.warning(f"데이터 로드 중 오류 발생 ({file_path}): {e}")
            return default_value

    def save_json(self, file_path, data, commit_message):
        """GitHub에 JSON 파일을 저장합니다. Rate limit 처리 포함."""
        max_retries = 3
        wait_time = 60  # 초
        
        for attempt in range(max_retries):
            try:
                # 기존 파일이 있는지 확인
                try:
                    content = self.repo.get_contents(file_path)
                    # 파일 업데이트
                    self.repo.update_file(
                        path=content.path,
                        message=commit_message,
                        content=json.dumps(data, indent=4, ensure_ascii=False),
                        sha=content.sha
                    )
                    return True
                except GithubException as e:
                    if e.status == 404:
                        # 파일이 없으면 생성
                        self.repo.create_file(
                            path=file_path,
                            message=commit_message,
                            content=json.dumps(data, indent=4, ensure_ascii=False)
                        )
                        return True
                    elif e.status == 403 and "rate limit" in str(e).lower():
                        # Rate limit 초과 시 재시도
                        if attempt < max_retries - 1:
                            st.warning(f"API Rate Limit 초과. {wait_time}초 후 재시도합니다...")
                            time.sleep(wait_time)
                            continue
                        else:
                            st.error("API Rate Limit 초과. 잠시 후 다시 시도해주세요.")
                            return False
                    else:
                        raise
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    if attempt < max_retries - 1:
                        st.warning(f"API Rate Limit 초과. {wait_time}초 후 재시도합니다...")
                        time.sleep(wait_time)
                        continue
                    else:
                        st.error("API Rate Limit 초과. 잠시 후 다시 시도해주세요.")
                        return False
                else:
                    st.error(f"저장 실패: {e}")
                    return False
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")
                return False
        
        return False

# 스토리지 초기화
@st.cache_resource
def init_storage():
    """스토리지 초기화 (캐싱)"""
    return GithubStorage(GITHUB_TOKEN, REPO_NAME)

db = init_storage()

# --- 페이지 설정 ---
st.set_page_config(page_title="My AI Newsroom", layout="wide")

# 데이터 로드 (세션 캐싱)
@st.cache_data(ttl=300)  # 5분 캐시
def load_data():
    """데이터를 로드합니다."""
    feeds = db.load_json("feeds.json", [
        {"name": "구글뉴스 IT", "url": "https://news.google.com/rss/search?q=IT&hl=ko&gl=KR&ceid=KR:ko"}
    ])
    news_history = db.load_json("news_data.json", {})
    stats = db.load_json("stats.json", {"visits": 0, "last_updated": ""})
    return feeds, news_history, stats

feeds, news_history, stats = load_data()

# 방문자 카운트 (새로고침 시마다 증가하면 너무 잦은 커밋이 발생하므로 세션 확인)
if "visited" not in st.session_state:
    stats["visits"] += 1
    # 통계 저장은 너무 자주 일어나지 않게 실제 배포 시에는 로직 조정 필요
    # 여기서는 주석 처리 (필요시 주석 해제)
    # db.save_json("stats.json", stats, "Update visitor count")
    st.session_state["visited"] = True

# --- UI 구성 ---
st.title("📰 나만의 IT 뉴스룸")

tab1, tab2 = st.tabs(["📅 데일리 브리핑", "⚙️ 대시보드 (관리자)"])

# [탭 1] 메인 뉴스룸
with tab1:
    today = datetime.now(KST)
    today_str = today.strftime('%Y-%m-%d')
    
    st.header(f"오늘의 브리핑 ({today_str})")
    
    if today_str in news_history:
        daily_data = news_history[today_str]
        st.info(f"생성 시간: {daily_data.get('created_at', '알 수 없음')}")
        
        # AI 분석 결과 표시
        st.markdown("### 🧠 AI 인사이트")
        st.markdown(daily_data.get('analysis', '분석 내용이 없습니다.'))
        
        st.markdown("---")
        st.markdown("### 🔗 수집된 주요 기사")
        
        articles = daily_data.get('articles', [])
        if articles:
            for article in articles:
                with st.expander(f"{article.get('title', '제목 없음')}"):
                    st.write(f"출처: {article.get('source', '알 수 없음')}")
                    link = article.get('link', '#')
                    if link != '#':
                        st.markdown(f"[원문 보기]({link})")
        else:
            st.info("수집된 기사가 없습니다.")
    else:
        st.warning("아직 오늘의 뉴스가 생성되지 않았습니다. 대시보드에서 '뉴스 수집 및 분석'을 실행해주세요.")

# [탭 2] 관리자 대시보드
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📡 RSS 피드 관리")
        
        # 피드 목록 표시
        if feeds:
            for i, feed in enumerate(feeds):
                c1, c2 = st.columns([4, 1])
                feed_name = feed.get('name', '이름 없음')
                feed_url = feed.get('url', 'URL 없음')
                c1.text(f"{feed_name} ({feed_url})")
                if c2.button("삭제", key=f"del_{i}"):
                    feeds.pop(i)
                    if db.save_json("feeds.json", feeds, "Delete RSS feed"):
                        st.success(f"피드 '{feed_name}' 삭제 완료")
                        st.cache_data.clear()  # 캐시 초기화
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("삭제 실패")
        else:
            st.info("등록된 피드가 없습니다.")
        
        st.markdown("---")
        
        # 피드 추가
        with st.form("add_feed"):
            new_name = st.text_input("피드 이름", placeholder="예: 구글뉴스 IT")
            new_url = st.text_input("RSS URL", placeholder="https://...")
            if st.form_submit_button("피드 추가"):
                # 유효성 검사
                if not new_name or not new_url:
                    st.error("피드 이름과 URL을 모두 입력해주세요.")
                elif not new_url.startswith(('http://', 'https://')):
                    st.error("올바른 URL 형식을 입력해주세요. (http:// 또는 https://로 시작)")
                else:
                    # URL 형식 검증
                    try:
                        parsed = urlparse(new_url)
                        if not parsed.scheme or not parsed.netloc:
                            st.error("올바른 URL 형식이 아닙니다.")
                        else:
                            feeds.append({"name": new_name, "url": new_url})
                            if db.save_json("feeds.json", feeds, "Add RSS feed"):
                                st.success(f"피드 '{new_name}' 추가 완료")
                                st.cache_data.clear()  # 캐시 초기화
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("추가 실패")
                    except Exception as e:
                        st.error(f"URL 검증 오류: {e}")

    with col2:
        st.subheader("🤖 AI 분석 실행")
        st.metric("총 누적 방문자", stats.get("visits", 0))
        
        if not feeds:
            st.warning("먼저 RSS 피드를 추가해주세요.")
        elif st.button("🚀 뉴스 수집 및 AI 분석 시작", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_articles = []
            failed_feeds = []
            
            # 1. RSS 수집
            status_text.text("RSS 피드 수집 중...")
            total_feeds = len(feeds)
            
            for idx, feed_info in enumerate(feeds):
                feed_name = feed_info.get('name', '알 수 없음')
                feed_url = feed_info.get('url', '')
                
                try:
                    f = feedparser.parse(feed_url)
                    
                    # 피드 유효성 검사
                    if hasattr(f, 'bozo') and f.bozo:
                        st.warning(f"피드 '{feed_name}' 파싱 경고: {f.bozo_exception}")
                    
                    if not f.entries:
                        st.warning(f"피드 '{feed_name}'에서 기사를 찾을 수 없습니다.")
                        failed_feeds.append(feed_name)
                        continue
                    
                    # 각 피드에서 최신 3개만 가져오기
                    for entry in f.entries[:3]:
                        all_articles.append({
                            "title": entry.get('title', '제목 없음'),
                            "link": entry.get('link', '#'),
                            "source": feed_name
                        })
                    
                    progress_bar.progress(int((idx + 1) / total_feeds * 50))
                    
                except Exception as e:
                    st.warning(f"피드 '{feed_name}' 수집 실패: {e}")
                    failed_feeds.append(feed_name)
                    continue
            
            if not all_articles:
                status_text.error("수집된 기사가 없습니다. RSS 피드를 확인해주세요.")
                progress_bar.empty()
            else:
                progress_bar.progress(50)
                
                # 2. Gemini 분석
                status_text.text(f"Gemini가 {len(all_articles)}개 기사를 분석 중입니다...")
                
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
                    
                    progress_bar.progress(75)
                    
                    # 3. GitHub에 저장
                    today_key = datetime.now(KST).strftime('%Y-%m-%d')
                    news_history[today_key] = {
                        "created_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
                        "analysis": analysis_text,
                        "articles": all_articles
                    }
                    
                    if db.save_json("news_data.json", news_history, f"Update news for {today_key}"):
                        progress_bar.progress(100)
                        status_text.success("분석 완료! 메인 화면을 확인하세요.")
                        if failed_feeds:
                            st.info(f"일부 피드 수집 실패: {', '.join(failed_feeds)}")
                        st.cache_data.clear()  # 캐시 초기화
                        time.sleep(1)
                        st.rerun()
                    else:
                        status_text.error("저장 실패. 다시 시도해주세요.")
                        progress_bar.empty()
                        
                except Exception as e:
                    status_text.error(f"분석 중 오류 발생: {e}")
                    progress_bar.empty()
                    st.exception(e)  # 상세한 에러 정보 표시

