# Terminal AI Assistant - 프로젝트 개요

## 프로젝트 목표

실시간으로 터미널 작업을 관찰하고 AI 기반의 지능적인 도움을 제공하는 TUI 애플리케이션 개발

## 핵심 기능

1. **완전한 터미널 에뮬레이션**: 기존 터미널의 모든 기능 유지
2. **실시간 AI 어시스턴트**: Ollama를 통한 로컬 LLM 활용
3. **스마트 컨텍스트 관리**: 관련성 높은 정보만 선별적 처리
4. **논블로킹 UI**: 터미널 작업에 영향 없는 비동기 처리

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

## 프로젝트 구조

```
terminal-ai-assistant/
├── main.py                  # 애플리케이션 진입점
├── terminal/               # 터미널 에뮬레이션 모듈
│   ├── __init__.py
│   ├── emulator.py         # PTY 터미널 래퍼
│   ├── buffer.py           # 입출력 버퍼 관리
│   └── parser.py           # ANSI 이스케이프 시퀀스 파서
├── ui/                     # TUI 인터페이스 모듈
│   ├── __init__.py
│   ├── app.py              # Textual 메인 애플리케이션
│   ├── terminal_widget.py  # 터미널 위젯
│   └── ai_sidebar.py       # AI 어시스턴트 사이드바
├── ai/                     # AI 통합 모듈
│   ├── __init__.py
│   ├── ollama_client.py    # Ollama API 클라이언트
│   ├── context.py          # 컨텍스트 관리자
│   ├── prompts.py          # 프롬프트 템플릿
│   └── triggers.py         # AI 트리거 로직
├── utils/                  # 유틸리티 모듈
│   ├── __init__.py
│   ├── config.py           # 설정 관리
│   ├── logger.py           # 로깅 설정
│   └── filters.py          # 민감 정보 필터
└── tests/                  # 테스트 코드
    ├── test_terminal.py
    ├── test_context.py
    └── test_ollama.py
```

## 개발 로드맵

1. **Phase 1**: 기본 터미널 에뮬레이션 (02-basic-terminal.md)
2. **Phase 2**: TUI 프레임워크 구축 (03-tui-framework.md)
3. **Phase 3**: Ollama 통합 (04-ollama-integration.md)
4. **Phase 4**: 스마트 컨텍스트 시스템 (05-context-management.md)
5. **Phase 5**: 실시간 기능 구현 (06-realtime-features.md)
6. **Phase 6**: 최적화 및 개선 (07-optimization.md)

각 단계별로 체크포인트를 통해 진행 상황을 확인하고 문제를 조기에 발견할 수 있습니다.