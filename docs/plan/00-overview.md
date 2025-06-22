# Terminal AI Assistant - 프로젝트 개요

## 프로젝트 목표

실시간으로 터미널 작업을 관찰하고 AI 기반의 지능적인 도움을 제공하는 TUI 애플리케이션 개발

## 🚀 현재 상태: ~85% 완성

- ✅ **Checkpoint 1**: 터미널 에뮬레이션 완료
- ✅ **Checkpoint 2**: TUI 프레임워크 완료
- ✅ **Checkpoint 3**: Ollama AI 통합 완료
- 🔄 **Checkpoint 4**: 전체 통합 테스트 진행 중

## 핵심 기능

1. **완전한 터미널 에뮬레이션**: PTY 기반 완전한 셸 호환성 ✅
2. **실시간 AI 어시스턴트**: Ollama를 통한 로컬 LLM 활용 ✅
3. **스마트 컨텍스트 관리**: 관련성 점수 기반 선별적 처리 ✅
4. **논블로킹 UI**: 터미널 작업에 영향 없는 비동기 처리 ✅

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Terminal AI Assistant                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────┐     ┌─────────────────────┐  │
│  │                     │     │                     │  │
│  │   Terminal Panel    │     │   AI Assistant      │  │
│  │                     │     │     Sidebar         │  │
│  │  ┌──────────────┐  │     │                     │  │
│  │  │ PTY Process  │  │     │  ┌───────────────┐  │  │
│  │  │   (bash)     │  │     │  │  Suggestions  │  │  │
│  │  └──────┬───────┘  │     │  ├───────────────┤  │  │
│  │         │          │     │  │   Warnings    │  │  │
│  │  ┌──────▼───────┐  │     │  ├───────────────┤  │  │
│  │  │   Output     │  │     │  │    Errors     │  │  │
│  │  │   Buffer     │  │     │  ├───────────────┤  │  │
│  │  └──────┬───────┘  │     │  │   Context     │  │  │
│  │         │          │     │  │    Help       │  │  │
│  └─────────┼──────────┘     │  └───────▲───────┘  │  │
│            │                 │          │          │  │
│  ┌─────────▼──────────────────────────┼─────────┐ │  │
│  │          Context Manager            │         │ │  │
│  │  - Command History                  │         │ │  │
│  │  - Error Detection                  │         │ │  │
│  │  - State Tracking                   │         │ │  │
│  └─────────────────┬───────────────────┘         │ │  │
│                    │                             │ │  │
│  ┌─────────────────▼─────────────────────────────┐ │  │
│  │              Ollama Client                    │ │  │
│  │  - Async API Calls                           │ │  │
│  │  - Streaming Responses                       │ │  │
│  │  - Model Management                          │ │  │
│  └───────────────────────────────────────────────┘ │  │
│                                                     │  │
└─────────────────────────────────────────────────────┘
```

## 컴포넌트 설명

### 1. Terminal Panel (터미널 패널)
- **PTY Process**: 실제 셸 프로세스를 pseudo-terminal을 통해 실행
- **Output Buffer**: 명령어 출력을 캐싱하고 스크롤링 지원
- **Input Handler**: 키보드 입력을 PTY로 전달

### 2. AI Assistant Sidebar (AI 어시스턴트 사이드바)
- **Suggestions**: 현재 작업에 대한 제안
- **Warnings**: 위험한 명령어 경고
- **Errors**: 에러 발생 시 해결책 제시
- **Context Help**: 현재 명령어/도구에 대한 도움말

### 3. Context Manager (컨텍스트 관리자)
- **Command History**: 실행된 명령어와 결과 추적
- **Error Detection**: 에러 패턴 감지 및 분류
- **State Tracking**: 현재 디렉토리, 환경 변수 등 상태 관리
- **Smart Filtering**: 중요한 컨텍스트만 선별

### 4. Ollama Client (Ollama 클라이언트)
- **Async API Calls**: 비동기 API 호출로 UI 블로킹 방지
- **Streaming Responses**: 실시간 스트리밍 응답 처리
- **Model Management**: 작업 유형별 모델 전환

## 핵심 설계 원칙

### 1. **논블로킹 아키텍처**
- 모든 AI 처리는 백그라운드에서 비동기로 실행
- 터미널 입출력은 절대 지연되지 않음

### 2. **스마트 트리거링**
- 모든 명령에 반응하지 않고 필요한 순간에만 활성화
- 에러 발생, 특정 패턴, 사용자 요청 시에만 AI 개입

### 3. **컨텍스트 효율성**
- 제한된 컨텍스트 윈도우를 효과적으로 활용
- 중요도 기반 명령어 필터링
- 작업 세션 자동 구분

### 4. **프라이버시 우선**
- 모든 처리는 로컬에서 수행
- 민감한 정보 자동 필터링
- 외부 서버로 데이터 전송 없음

## 기술 스택

- **언어**: Python 3.8+
- **TUI Framework**: Textual
- **터미널 에뮬레이션**: pty (표준 라이브러리)
- **AI 모델**: Ollama (CodeLlama, Mistral 등)
- **비동기 처리**: asyncio
- **HTTP 클라이언트**: httpx
- **설정 관리**: pydantic

## 프로젝트 구조 (현재 구현 상태)

```
prototype-termai/
├── pyproject.toml           # 프로젝트 설정 ✅
├── uv.lock                  # 의존성 잠금 파일 ✅
├── src/
│   └── termai/
│       ├── __init__.py      # 패키지 초기화 ✅
│       ├── __main__.py      # 모듈 실행 진입점 ✅
│       ├── main.py          # 애플리케이션 진입점 ✅
│       ├── terminal/        # 터미널 에뮬레이션 모듈 ✅
│       │   ├── __init__.py
│       │   ├── emulator.py  # PTY 터미널 래퍼 ✅
│       │   ├── buffer.py    # 출력 버퍼 관리 ✅
│       │   ├── history.py   # 명령어 히스토리 ✅
│       │   └── manager.py   # 터미널 통합 관리 ✅
│       ├── ui/              # TUI 인터페이스 모듈 ✅
│       │   ├── __init__.py
│       │   ├── app.py       # Textual 메인 애플리케이션 ✅
│       │   ├── terminal_widget.py  # 터미널 위젯 ✅
│       │   └── ai_sidebar.py       # AI 어시스턴트 사이드바 ✅
│       ├── ai/              # AI 통합 모듈 ✅
│       │   ├── __init__.py
│       │   ├── ollama_client.py    # Ollama API 클라이언트 ✅
│       │   ├── context_manager.py  # 컨텍스트 관리자 ✅
│       │   ├── context.py          # 컨텍스트 윈도우 ✅
│       │   ├── prompts.py          # 프롬프트 템플릿 ✅
│       │   ├── triggers.py         # AI 트리거 로직 ✅
│       │   ├── filters.py          # 민감 정보 필터 ✅
│       │   └── realtime_analyzer.py # 실시간 분석기 ✅
│       ├── config/          # 설정 관리 ⚠️ (부분 구현)
│       │   ├── __init__.py
│       │   └── settings.py  # 환경 설정 ⚠️
│       └── utils/           # 유틸리티 모듈 ⚠️ (부분 구현)
│           ├── __init__.py
│           └── logger.py    # 로깅 설정 ⚠️
├── tests/                   # 테스트 코드 ✅
│   ├── test_terminal.py     # 터미널 테스트 ✅
│   ├── test_ui.py           # UI 테스트 ✅
│   ├── test_ollama.py       # AI 통합 테스트 ✅
│   └── test_integration.py  # 통합 테스트 ⚠️
└── examples/                # 사용 예제 ✅
    └── basic_usage.py       # 기본 사용법 ✅
```

## 개발 로드맵 및 현재 진행 상황

1. **Phase 1**: 기본 터미널 에뮬레이션 ✅ **완료**
   - PTY 기반 터미널 래퍼 구현
   - 명령어 실행 및 출력 캡처
   - ANSI 이스케이프 시퀀스 처리
   - 명령어 히스토리 관리

2. **Phase 2**: TUI 프레임워크 구축 ✅ **완료**
   - Textual 기반 UI (65%/35% 레이아웃)
   - 터미널 위젯 및 AI 사이드바
   - 키보드 단축키 (Ctrl+L, Ctrl+A, F1 등)
   - 한국어 지원

3. **Phase 3**: Ollama 통합 ✅ **완료**
   - Ollama 클라이언트 구현
   - 실시간 분석기 with 캐싱
   - 트리거 시스템 (에러, 위험 명령어)
   - 컨텍스트 관리자

4. **Phase 4**: 스마트 컨텍스트 시스템 ✅ **완료**
   - 관련성 점수 기반 필터링
   - 토큰 제한 관리 (4K-8K)
   - 세션 컨텍스트 추적

5. **Phase 5**: 실시간 기능 구현 ✅ **완료**
   - 비동기 이벤트 처리
   - 백그라운드 AI 분석
   - UI 논블로킹 업데이트

6. **Phase 6**: 최적화 및 개선 🔄 **진행 중**
   - 성능 최적화 필요
   - 설정 시스템 구현 필요
   - 통합 테스트 작성 필요
