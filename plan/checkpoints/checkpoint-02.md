# Checkpoint 2: TUI 기본 동작 확인

## 목표
Textual 기반 TUI가 올바르게 렌더링되고 상호작용이 가능한지 확인합니다.

## 사전 요구사항
- Checkpoint 1 완료
- Textual 패키지 설치 확인
- 터미널 타입이 xterm-256color로 설정됨

## 테스트 항목

### 1. 기본 레이아웃
- [ ] 앱이 정상적으로 실행됨
- [ ] 헤더와 푸터가 표시됨
- [ ] 화면이 65% / 35%로 분할됨
- [ ] 터미널 영역과 AI 사이드바가 구분됨

### 2. 키보드 단축키
- [ ] Ctrl+C로 앱 종료 (또는 Ctrl+Q)
- [ ] Ctrl+L로 터미널 클리어
- [ ] Ctrl+A로 AI 토글
- [ ] F1으로 도움말 표시
- [ ] Tab으로 포커스 이동

### 3. 터미널 위젯
- [ ] 터미널 출력이 표시됨
- [ ] 스크롤이 작동함 (마우스 휠)
- [ ] 키보드 입력이 가능함
- [ ] 컬러 출력이 올바르게 렌더링됨

### 4. AI 사이드바
- [ ] AI 상태가 표시됨 (Active/Disabled)
- [ ] 메시지 영역이 스크롤 가능함
- [ ] Clear 버튼이 작동함
- [ ] Analyze 버튼이 클릭 가능함

### 5. 반응형 UI
- [ ] 터미널 리사이즈 시 레이아웃 유지
- [ ] 최소 크기에서도 UI 깨지지 않음
- [ ] 버튼과 위젯이 올바르게 정렬됨

## 테스트 실행

```bash
# UI 컴포넌트 테스트
python test_ui.py

# 전체 앱 테스트 (터미널 통합 없이)
python main.py --test-mode
```

## 예상 화면

```
┌─ Terminal AI Assistant ─────────────────────────────────┐
│ File  Edit  View  Help                                  │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┬──────────────────────┐     │
│ │                         │ 🤖 AI Assistant      │     │
│ │  Terminal Area          │ 🟢 AI Active         │     │
│ │                         │                      │     │
│ │  $ ls -la              │ ┌──────────────────┐ │     │
│ │  total 24              │ │ Suggestions      │ │     │
│ │  drwxr-xr-x  5 user   │ │ will appear      │ │     │
│ │  -rw-r--r--  1 user   │ │ here...          │ │     │
│ │                         │ └──────────────────┘ │     │
│ │  $ _                   │                      │     │
│ │                         │ [Clear] [Analyze]    │     │
│ └─────────────────────────┴──────────────────────┘     │
│ Ctrl+C Quit │ Ctrl+L Clear │ Ctrl+A Toggle AI │ F1 Help│
└─────────────────────────────────────────────────────────┘
```

## 상호작용 테스트

### 1. 버튼 클릭
```python
# AI 사이드바에서
- Clear 버튼 클릭 → 메시지 영역 비워짐
- Analyze 버튼 클릭 → Processing 상태 표시
```

### 2. 포커스 이동
```python
# Tab 키로 이동
Terminal Widget → AI Sidebar → Buttons → Terminal Widget
```

### 3. 스크롤 테스트
```python
# 터미널 영역
- 마우스 휠로 위/아래 스크롤
- Page Up/Down 키 작동

# AI 사이드바
- 메시지가 많을 때 자동 스크롤
- 수동 스크롤 가능
```

## 문제 해결

### 렌더링 문제
```bash
# 터미널 타입 확인
echo $TERM
# xterm-256color이어야 함

# 강제 설정
export TERM=xterm-256color
```

### 한글 표시 문제
```bash
# 로케일 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8
```

### 키 바인딩 충돌
```python
# app.py에서 우선순위 조정
Binding("ctrl+c", "quit", "Quit", priority=True)
```

### 레이아웃 깨짐
```python
# CSS 확인
TerminalWidget {
    width: 65%;  # 퍼센트 단위 사용
    min-width: 40;  # 최소 너비 설정
}
```

## 성능 확인

- [ ] UI 응답성: 키 입력 즉시 반응
- [ ] 렌더링 속도: 부드러운 스크롤
- [ ] 메모리 사용: 100MB 이하
- [ ] CPU 사용: 유휴 시 5% 이하

## 다음 단계
TUI가 정상 작동하면 [04-ollama-integration.md](../04-ollama-integration.md)로 진행합니다.
