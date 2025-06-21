# Checkpoint 3: Ollama 연동 테스트

## 목표
Ollama API와의 통신이 정상적으로 작동하고 AI 분석 기능이 동작하는지 확인합니다.

## 사전 요구사항
- Checkpoint 1, 2 완료
- Ollama 설치 및 실행 중
- 최소 하나의 모델 다운로드 완료 (codellama:7b 권장)

## 테스트 항목

### 1. Ollama 서버 연결
- [ ] Ollama 서버 상태 확인 (health check)
- [ ] 사용 가능한 모델 목록 조회
- [ ] API 엔드포인트 응답 확인
- [ ] 타임아웃 처리 작동

### 2. 텍스트 생성
- [ ] 간단한 프롬프트로 응답 생성
- [ ] 스트리밍 응답 수신
- [ ] 한글 프롬프트 처리
- [ ] 에러 처리 (모델 없음, 서버 다운 등)

### 3. 컨텍스트 분석
- [ ] 터미널 컨텍스트 전달
- [ ] 구조화된 응답 파싱
- [ ] 제안사항 추출
- [ ] 경고 및 에러 분류

### 4. 트리거 시스템
- [ ] 에러 트리거 감지
- [ ] 패턴 매칭 작동
- [ ] 우선순위 처리
- [ ] 중복 트리거 방지

## 테스트 실행

### 1. Ollama 서버 확인
```bash
# Ollama 서버 시작 (별도 터미널)
ollama serve

# API 확인
curl http://localhost:11434/api/tags
```

### 2. Python 테스트
```bash
python test_ollama.py
```

## 예상 출력

```
=== Ollama 연결 테스트 ===

Ollama 서버 상태: 정상
사용 가능한 모델: ['codellama:7b', 'mistral:7b']

=== 텍스트 생성 테스트 ===

프롬프트: Write a simple Python hello world function
응답: def hello_world():
    """Print Hello, World! to the console."""
    print("Hello, World!")

=== 컨텍스트 분석 테스트 ===

분석 중...

모델: codellama:7b
처리 시간: 2.34초

제안사항:
  - Run 'git pull origin main' to sync with remote
  - Use 'git push --force' with caution
  - Check remote branch status with 'git branch -r'

경고:
  - Remote repository has diverged from local

에러 해결:
  - Pull remote changes before pushing
  - Resolve conflicts if any exist

=== 트리거 시스템 테스트 ===

에러 트리거: 트리거됨 - 명령어 실행 실패 (우선순위: 10)
위험 명령어: 트리거됨 - 위험한 삭제 명령어 (우선순위: 10)
Git 에러: 트리거됨 - Git 에러 (우선순위: 8)
일반 명령어: 트리거 없음

모든 테스트 완료!
```

## 성능 벤치마크

### 응답 시간 목표
- Health check: < 100ms
- 텍스트 생성 시작: < 500ms
- 컨텍스트 분석: < 3s
- 캐시 히트: < 50ms

### 테스트 시나리오

#### 1. Git 에러 분석
```python
context = {
    "command": "git push origin main",
    "error": "error: failed to push some refs",
    "exit_code": 1
}
# 예상: Git 관련 해결책 제시
```

#### 2. 파일 없음 에러
```python
context = {
    "command": "cat config.json",
    "error": "cat: config.json: No such file or directory",
    "exit_code": 1
}
# 예상: 파일 확인 방법 제안
```

#### 3. 권한 에러
```python
context = {
    "command": "npm install -g package",
    "error": "permission denied",
    "exit_code": 1
}
# 예상: sudo 사용 또는 권한 설정 제안
```

## 문제 해결

### Ollama 연결 실패
```bash
# 서버 실행 확인
ps aux | grep ollama

# 포트 확인
lsof -i :11434

# 로그 확인
ollama serve --verbose
```

### 모델 응답 없음
```bash
# 모델 다시 다운로드
ollama pull codellama:7b

# 다른 모델 시도
ollama pull mistral:7b
```

### 느린 응답
```python
# 설정 조정
config = OllamaConfig(
    model="mistral:7b",  # 더 작은 모델
    max_tokens=200,      # 토큰 수 제한
    temperature=0.5      # 낮은 temperature
)
```

### 파싱 오류
```python
# 응답 형식 확인
print(f"Raw response: {response}")

# JSON 파싱 실패 시 폴백
try:
    parsed = json.loads(response)
except:
    # 휴리스틱 파싱 사용
    parsed = heuristic_parse(response)
```

## 통합 확인

- [ ] Ollama 클라이언트가 앱에 통합됨
- [ ] AI 사이드바에 응답 표시됨
- [ ] 에러 발생 시 자동 분석 시작
- [ ] 비동기 처리로 UI 블로킹 없음

## 다음 단계
Ollama 통합이 완료되면 [05-context-management.md](../05-context-management.md)로 진행합니다.
