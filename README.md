# Terminal AI Assistant (prototype-termai)

실시간 AI 기반 터미널 어시스턴트 - Ollama를 통한 로컬 LLM 모델 사용

## 🚀 빠른 시작

### 사전 요구사항
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (Python 패키지 관리자)
- [Ollama](https://ollama.ai) (로컬 LLM 서버)

### 설치

1. **uv 설치**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. **프로젝트 클론 및 설정**
```bash
git clone https://github.com/cagojeiger/prototype-termai.git
cd prototype-termai

# 의존성 설치 (가상환경 자동 생성)
uv sync

# pre-commit 설정
uv run pre-commit install

# 가상환경 활성화 (선택사항)
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

3. **Ollama 설치 및 모델 다운로드**
```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull codellama:7b
```

### 실행

```bash
# 터미널 래퍼 테스트 (Checkpoint 1)
uv run python test_terminal.py

# 대화형 테스트
uv run python test_terminal.py --interactive

# 메인 애플리케이션 (구현 예정)
uv run python main.py
```

## 🏗️ 프로젝트 구조

```
prototype-termai/
├── terminal/           # 터미널 에뮬레이션
│   ├── emulator.py    # PTY 기반 터미널 에뮬레이터
│   ├── buffer.py      # 출력 버퍼 (ANSI 처리)
│   ├── history.py     # 명령어 히스토리
│   └── manager.py     # 터미널 통합 관리
├── ui/                # TUI 인터페이스
├── ai/                # AI 통합 (Ollama)
├── utils/             # 유틸리티
├── tests/             # 테스트
└── plan/              # 개발 계획 문서
```

## 🧪 테스트

```bash
# 전체 테스트 실행
uv run pytest

# 터미널 래퍼 테스트
uv run python test_terminal.py

# 개발 도구 실행
uv run black .          # 코드 포맷팅
uv run ruff check .     # 린팅
uv run mypy .           # 타입 체킹
uv run pre-commit run --all-files  # 모든 pre-commit 훅 실행
```

## 📋 개발 단계

- [x] **Checkpoint 1**: 터미널 래퍼 구현
- [ ] **Checkpoint 2**: TUI 프레임워크
- [ ] **Checkpoint 3**: Ollama 연동
- [ ] **Checkpoint 4**: 전체 통합

자세한 개발 계획은 [`plan/`](plan/) 디렉토리를 참조하세요.

## 🛠️ 개발 환경

### uv 명령어

```bash
# 의존성 추가
uv add package-name

# 개발 의존성 추가
uv add --dev package-name

# 의존성 업데이트
uv sync --upgrade

# 스크립트 실행
uv run python script.py

# 가상환경 정보
uv venv --python 3.8
```

### 환경 변수

`.env` 파일을 생성하여 설정:

```bash
cp .env.example .env
```

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 지원

문제가 발생하면 [Issues](https://github.com/cagojeiger/prototype-termai/issues)에 보고해 주세요.
