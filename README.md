# 📰 나만의 AI 뉴스룸

GitHub를 스토리지로 사용하는 무료 AI 뉴스룸 애플리케이션입니다. Streamlit Cloud로 배포하여 서버 비용 없이 운영할 수 있습니다.

🔗 **리포지토리**: [https://github.com/agent937/newsroom](https://github.com/agent937/newsroom)

## ✨ 주요 기능

- 📡 **RSS 피드 수집**: 여러 RSS 피드에서 뉴스를 자동으로 수집
- 🤖 **AI 분석**: Google Gemini를 활용한 뉴스 분석 및 데일리 브리핑 생성
- 💾 **GitHub 스토리지**: 데이터베이스 없이 GitHub 리포지토리를 스토리지로 사용
- 📊 **대시보드**: RSS 피드 관리 및 분석 실행

## 🚀 빠른 시작

### 1. 사전 준비

1. **GitHub 리포지토리**
   - 리포지토리: `agent937/newsroom`
   - 또는 새 리포지토리를 생성합니다

2. **GitHub Personal Access Token 발급**
   - GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - `repo` 권한을 체크하고 토큰을 생성합니다

3. **Google Gemini API Key 발급**
   - [Google AI Studio](https://makersuite.google.com/app/apikey)에서 API 키를 발급받습니다

### 2. 로컬 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# secrets.toml 파일 생성
# .streamlit/secrets.toml.example을 복사하여 secrets.toml로 이름 변경
# 실제 값으로 채워주세요

# 애플리케이션 실행
streamlit run app.py
```

### 3. Streamlit Cloud 배포

1. 코드를 GitHub 리포지토리에 푸시합니다
2. [Streamlit Cloud](https://streamlit.io/cloud)에 접속하여 "New App" 클릭
3. 리포지토리를 연결합니다
4. **Secrets** 메뉴에서 다음 값들을 입력합니다:
   ```
   GITHUB_TOKEN = "ghp_..."
   REPO_NAME = "agent937/newsroom"
   GEMINI_API_KEY = "..."
   ```

## 📁 프로젝트 구조

```
Newsroom/
├── app.py                      # 메인 애플리케이션
├── requirements.txt            # Python 의존성
├── .gitignore                 # Git 제외 파일
├── .streamlit/
│   ├── secrets.toml.example   # Secrets 템플릿
│   └── secrets.toml          # 실제 secrets (Git에 커밋되지 않음)
└── README.md                  # 이 파일
```

## 🔧 주요 개선 사항

이 버전은 다음 개선 사항을 포함합니다:

- ✅ 구체적인 예외 처리 (bare except 제거)
- ✅ 타임존 처리 일관성
- ✅ RSS 피드 파싱 에러 처리
- ✅ 입력 유효성 검사
- ✅ GitHub API Rate Limit 처리
- ✅ 세션 캐싱을 통한 성능 최적화
- ✅ 상세한 에러 메시지

## 📝 사용 방법

1. **RSS 피드 추가**: 대시보드에서 RSS 피드를 추가합니다
2. **뉴스 수집 및 분석**: "뉴스 수집 및 AI 분석 시작" 버튼을 클릭합니다
3. **데일리 브리핑 확인**: 메인 화면에서 오늘의 브리핑을 확인합니다

## ⚠️ 주의사항

- GitHub API는 시간당 5,000회 요청 제한이 있습니다
- Streamlit Cloud는 무료 플랜에서 앱이 1시간 동안 비활성화되면 재시작됩니다
- Secrets 파일은 절대 Git에 커밋하지 마세요

## 📄 라이선스

이 프로젝트는 개인 사용 목적으로 자유롭게 사용할 수 있습니다.

