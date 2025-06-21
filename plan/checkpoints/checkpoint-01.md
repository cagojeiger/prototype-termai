# Checkpoint 1: 터미널 래퍼 테스트

## 목표
기본 터미널 래퍼가 올바르게 작동하는지 확인합니다.

## 사전 요구사항
- Python 가상환경 활성화
- 필요한 패키지 설치 완료
- 프로젝트 구조 생성 완료

## 테스트 항목

### 1. PTY 터미널 생성
- [ ] 터미널 프로세스가 정상적으로 시작됨
- [ ] 셸 환경이 올바르게 설정됨
- [ ] 작업 디렉토리가 현재 디렉토리로 설정됨

### 2. 명령어 실행
- [ ] `echo "Hello World"` 실행 및 출력 확인
- [ ] `pwd` 명령어로 현재 디렉토리 확인
- [ ] `ls -la` 명령어로 파일 목록 출력
- [ ] `python3 --version` 실행 확인

### 3. 출력 캡처
- [ ] 명령어 출력이 버퍼에 저장됨
- [ ] ANSI 이스케이프 시퀀스가 포함된 출력 처리
- [ ] 한글 출력이 깨지지 않음
- [ ] 멀티라인 출력 올바르게 처리

### 4. 입력 처리
- [ ] 키보드 입력이 터미널로 전달됨
- [ ] 백스페이스 처리 작동
- [ ] Ctrl+C 인터럽트 처리
- [ ] Enter 키로 명령어 실행

### 5. 히스토리 관리
- [ ] 실행된 명령어가 히스토리에 기록됨
- [ ] 명령어 실행 시간이 기록됨
- [ ] 종료 코드가 올바르게 저장됨
- [ ] 히스토리 검색 기능 작동

## 테스트 실행

```bash
cd ~/project/prototype-termai
# uv를 사용한 실행 (권장)
uv run python test_terminal.py

# 또는 가상환경 활성화 후 실행
source .venv/bin/activate
python test_terminal.py
```

## 예상 결과

```
=== 터미널 에뮬레이터 테스트 ===

터미널이 시작되었습니다.

실행할 명령어: echo 'Hello from Terminal Emulator!'
[실행 시작] echo 'Hello from Terminal Emulator!'
[실행 완료] echo 'Hello from Terminal Emulator!' (exit: 0)
출력:
  Hello from Terminal Emulator!

실행할 명령어: pwd
[실행 시작] pwd
[실행 완료] pwd (exit: 0)
출력:
  /Users/username/project/test-tui

=== 명령어 히스토리 ===
- echo 'Hello from Terminal Emulator!' (실행시간: 0.05초)
- pwd (실행시간: 0.03초)
- ls -la (실행시간: 0.08초)

터미널이 종료되었습니다.
```

## 문제 해결

### PTY 권한 오류
```bash
# 오류: [Errno 13] Permission denied: '/dev/ptmx'
ls -la /dev/ptmx
# 권한이 crw-rw-rw- 형태여야 함

# 필요시 권한 수정 (주의!)
sudo chmod 666 /dev/ptmx
```

### 인코딩 오류
```python
# terminal/emulator.py에서
text = data.decode('utf-8', errors='replace')  # 'replace' 옵션 확인
```

### 프로세스 종료 안됨
```python
# 강제 종료 추가
import signal
os.kill(self.process.pid, signal.SIGTERM)
time.sleep(0.5)
if self.process.poll() is None:
    os.kill(self.process.pid, signal.SIGKILL)
```

## 다음 단계
모든 테스트가 통과하면 [03-tui-framework.md](../03-tui-framework.md)로 진행합니다.
