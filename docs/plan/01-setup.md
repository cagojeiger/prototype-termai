# 01. 환경 설정 및 프로젝트 초기화

## 목표
Terminal AI Assistant 개발을 위한 환경을 설정하고 필요한 도구들을 설치합니다.

## 사전 요구사항

- Python 3.8 이상
- macOS, Linux, 또는 Windows (WSL2 권장)
- Git
- 터미널 환경

## Step 1: Python 환경 설정 (uv 사용)

### uv 설치
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는 pip로 설치 (uv가 없는 경우)
pip install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 프로젝트 초기화
```bash
# 프로젝트 디렉토리로 이동
cd ~/project/prototype-termai

# uv로 프로젝트 초기화 (pyproject.toml 기반)
uv init --python 3.8

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

## Step 2: Ollama 설치

### macOS
```bash
# Homebrew를 통한 설치
brew install ollama

# 또는 공식 인스톨러 다운로드
curl -fsSL https://ollama.ai/install.sh | sh
```

### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
[Ollama 공식 사이트](https://ollama.ai)에서 Windows 인스톨러 다운로드

## Step 3: Ollama 모델 다운로드

```bash
# Ollama 서비스 시작
ollama serve

# 새 터미널에서 모델 다운로드
# CodeLlama (코드 특화 모델)
ollama pull codellama:7b

# 또는 Mistral (빠른 범용 모델)
ollama pull mistral:7b

# 모델 테스트
ollama run codellama:7b "Hello, can you help with Python?"
```

## Step 4: 프로젝트 의존성 설치 (uv 사용)

### 핵심 의존성 설치
```bash
# 핵심 의존성 설치
uv add textual==0.47.1 httpx==0.25.2 pydantic==2.5.2 pydantic-settings==2.1.0 rich==13.7.0 python-dotenv==1.0.0

# 개발 의존성 설치
uv add --dev pytest==7.4.3 pytest-asyncio==0.23.2 black==23.12.1 ruff==0.1.8 mypy==1.7.1 pre-commit==3.6.0

# 설치 확인
uv pip list

# pre-commit 설정
uv run pre-commit install
```

### 기존 프로젝트에서 uv로 마이그레이션 (선택사항)
```bash
# 기존 requirements.txt가 있는 경우
# pyproject.toml로 수동 변환 후 uv sync 사용

# 또는 기존 환경에서 의존성 확인
uv pip list  # 현재 설치된 패키지 확인
uv sync      # pyproject.toml 기반으로 동기화
```

## Step 5: 프로젝트 구조 생성

```bash
# 디렉토리 구조 생성
mkdir -p terminal ui ai utils tests
mkdir -p .vscode

# __init__.py 파일 생성
touch terminal/__init__.py
touch ui/__init__.py
touch ai/__init__.py
touch utils/__init__.py
touch tests/__init__.py

# 기본 설정 파일 생성
touch .env
touch .env.example
touch .gitignore
```

## Step 6: 기본 설정 파일 작성

### .gitignore
```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Project specific
.env
*.log
.DS_Store
*.db

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Build
build/
dist/
*.egg-info/
EOF
```

### .env.example
```bash
cat > .env.example << 'EOF'
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=codellama:7b
OLLAMA_TIMEOUT=30

# Application Settings
APP_LOG_LEVEL=INFO
APP_THEME=dark
APP_SIDEBAR_WIDTH=40

# AI Settings
AI_MAX_CONTEXT_LENGTH=20
AI_RESPONSE_MAX_TOKENS=500
AI_TEMPERATURE=0.7
EOF
```

### pyproject.toml (자동 생성됨)
uv를 사용하면 `pyproject.toml` 파일이 자동으로 생성되며, 프로젝트 메타데이터와 의존성이 관리됩니다.

```toml
# pyproject.toml 예시 (uv가 자동 생성)
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "prototype-termai"
version = "0.1.0"
description = "Terminal AI Assistant"
requires-python = ">=3.8"
dependencies = [
    "textual==0.47.1",
    "httpx==0.25.2",
    # ... 기타 의존성
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "black==23.12.1",
    # ... 개발 의존성
]

[tool.black]
line-length = 88
target-version = ['py38']

[tool.ruff]
select = ["E", "F", "W", "B", "I", "N", "UP", "C90"]
ignore = ["E501"]
line-length = 88
target-version = "py38"

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Step 7: VS Code 설정 (선택사항)

### .vscode/settings.json
```bash
cat > .vscode/settings.json << 'EOF'
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "python.terminal.activateEnvironment": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
EOF
```

## Step 8: 설치 검증

### 1. Python 환경 확인
```bash
python --version  # Python 3.8+ 확인
pip --version     # pip 설치 확인
```

### 2. Ollama 확인
```bash
# Ollama 버전 확인
ollama --version

# API 응답 테스트
curl http://localhost:11434/api/tags
```

### 3. Textual 테스트
```bash
# Textual 데모 실행
python -m textual
```

## Step 9: Hello World 테스트

### test_setup.py 생성
```python
# test_setup.py
import asyncio
import httpx
from textual.app import App
from textual.widgets import Header, Footer, Static

class TestApp(App):
    """기본 Textual 앱 테스트"""

    def compose(self):
        yield Header()
        yield Static("Terminal AI Assistant - Setup Test")
        yield Footer()

async def test_ollama():
    """Ollama 연결 테스트"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:11434/api/tags")
            print(f"Ollama 상태: {response.status_code}")
            print(f"사용 가능한 모델: {response.json()}")
        except Exception as e:
            print(f"Ollama 연결 실패: {e}")

if __name__ == "__main__":
    # Textual 앱 테스트
    print("1. Textual 테스트 (종료: Ctrl+C)")
    app = TestApp()
    app.run()

    # Ollama 테스트
    print("\n2. Ollama 연결 테스트")
    asyncio.run(test_ollama())
```

### 테스트 실행
```bash
# uv를 사용한 실행
uv run python test_setup.py

# 또는 가상환경 활성화 후
source .venv/bin/activate
python test_setup.py
```

## Checkpoint: 환경 설정 완료

- [ ] Python 3.8+ 설치 및 가상환경 활성화
- [ ] Ollama 설치 및 모델 다운로드
- [ ] 모든 Python 패키지 설치 완료
- [ ] 프로젝트 디렉토리 구조 생성
- [ ] 설정 파일 작성 완료
- [ ] Textual 데모 실행 성공
- [ ] Ollama API 응답 확인

## 문제 해결

### Ollama 연결 실패
```bash
# Ollama 서비스 상태 확인
ollama serve

# 포트 사용 중인지 확인
lsof -i :11434
```

### 권한 문제
```bash
# macOS/Linux에서 PTY 권한 문제 시
ls -la /dev/ptmx
sudo chmod 666 /dev/ptmx
```

### Python 패키지 설치 실패
```bash
# uv 캐시 삭제 후 재설치
uv cache clean
uv sync --reinstall
```

## 다음 단계

환경 설정이 완료되면 [02-basic-terminal.md](02-basic-terminal.md)로 진행하여 기본 터미널 래퍼를 구현합니다.
