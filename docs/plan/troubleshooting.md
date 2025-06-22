# 트러블슈팅 가이드

이 문서는 Terminal AI Assistant 사용 중 발생할 수 있는 일반적인 문제들과 해결 방법을 안내합니다.

**프로젝트 현재 상태**: ~85% 완성 (핵심 기능 작동 중)

## 빠른 문제 해결

### 가장 흔한 문제들

1. **Ollama 서버 연결 실패**
   ```bash
   # 해결: Ollama 서버 시작
   ollama serve
   ```

2. **모델 없음 오류**
   ```bash
   # 해결: 모델 다운로드
   ollama pull llama3.2:1b
   ```

3. **한글 깨짐**
   ```bash
   # 해결: 로케일 설정
   export LANG=ko_KR.UTF-8
   export LC_ALL=ko_KR.UTF-8
   ```

## 상세 문제 해결

### 1. 설치 및 환경 설정

#### uv 설치 실패
**문제**: "command not found: uv"

**해결**:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# PATH 추가
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Python 버전 오류
**문제**: `Python 3.12+ required`

**해결**:
```bash
# pyenv 사용
pyenv install 3.12.2
pyenv local 3.12.2

# uv로 Python 버전 지정
uv venv --python 3.12
```

#### 의존성 설치 실홈
**문제**: "Failed to install dependencies"

**해결**:
```bash
# 캐시 클리어
uv cache clean

# 가상환경 삭제 후 재설치
rm -rf .venv
uv sync

# 특정 패키지 문제 시
uv add --upgrade package-name
```

### 2. Ollama 관련 문제

#### Ollama 서버 연결 실패
**증상**: "Ollama server not available" 메시지

**해결방법**:
```bash
# Ollama 서버 시작
ollama serve

# 다른 터미널에서 확인
curl http://localhost:11434/api/tags

# 포트 충돌 확인
lsof -i :11434
```

#### 모델 없음 오류
**증상**: "No Ollama models found" 메시지

**해결방법**:
```bash
# 모델 다운로드
ollama pull llama3.2:1b

# 다른 모델 시도
ollama pull codellama:7b
ollama pull mistral:7b

# 모델 목록 확인
ollama list
```

#### AI 응답 느림
**증상**: AI 분석이 5초 이상 걸림

**해결방법**:
1. 더 작은 모델 사용 (llama3.2:1b)
2. GPU 가속 확인
3. 컨텍스트 길이 제한

#### AI가 트리거되지 않음
**증상**: 에러 발생 시에도 AI 분석이 시작되지 않음

**해결방법**:
1. AI 활성화 상태 확인 (Ctrl+A)
2. 트리거 설정 확인
3. 수동 분석 버튼 클릭

### 3. 터미널 관련 문제

#### 터미널이 시작되지 않음
**증상**: 앱 실행 시 터미널 영역이 비어있거나 응답 없음

**해결방법**:
```bash
# PTY 권한 확인
ls -la /dev/ptmx
# crw-rw-rw- 형태여야 함

# 필요시 권한 수정 (주의!)
sudo chmod 666 /dev/ptmx
```

#### 한글 깨짐 문제
**증상**: 한글 출력이 ?로 표시됨

**해결방법**:
```bash
# 로케일 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8

# .bashrc 또는 .zshrc에 추가
echo 'export LANG=ko_KR.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=ko_KR.UTF-8' >> ~/.bashrc
```

#### 키보드 입력 문제
**증상**: 키 입력이 터미널에 전달되지 않음

**해결방법**:
1. Tab 키로 터미널 영역에 포커스 이동
2. 터미널 영역 클릭하여 포커스
3. 키보드 단축키 충돌 확인

### 4. TUI 관련 문제

#### 화면 렌더링 문제
**증상**: UI가 깨지거나 텍스트가 이상하게 표시됨

**해결방법**:
```bash
# 터미널 타입 확인
echo $TERM
# xterm-256color이어야 함

# 강제 설정
export TERM=xterm-256color
```

#### 키보드 단축키 작동 안함
**증상**: Ctrl+L, Ctrl+A 등이 작동하지 않음

**해결방법**:
1. 터미널 에뮬레이터 설정 확인
2. 다른 프로그램과의 키 바인딩 충돌 확인
3. tmux/screen 사용 시 키 패스스루 설정

#### 마우스 스크롤 문제
**증상**: 마우스 휠로 스크롤이 되지 않음

**해결방법**:
1. 터미널 에뮬레이터의 마우스 지원 확인
2. SSH 접속 시 마우스 포워딩 설정
3. 키보드로 대체: Page Up/Down

### 5. 성능 문제

#### 높은 메모리 사용
**증상**: 메모리 사용량이 200MB 초과

**해결방법**:
1. 버퍼 크기 제한
2. 히스토리 길이 제한
3. 캐시 크기 조정

#### CPU 사용률 높음
**증상**: 유휴 상태에서도 CPU 10% 이상

**해결방법**:
1. 폴링 주기 조정
2. 불필요한 이벤트 필터링
3. 디버그 모드 비활성화

### 6. 디버깅 팁

#### 로그 확인
```bash
# 디버그 모드 실행
uv run python src/termai/main.py --debug --log-level=DEBUG

# 로그 파일 확인
tail -f app.log

# Ollama 로그
tail -f ~/.ollama/logs/server.log
```

#### 프로파일링
```bash
# CPU 프로파일링
python -m cProfile -o profile.stats src/termai/main.py

# 결과 분석
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('time').print_stats(20)"

# 메모리 프로파일링
mprof run src/termai/main.py
mprof plot
```

#### 네트워크 트래픽 모니터링
```bash
# Ollama API 호출 모니터링
tcpdump -i lo0 -A 'port 11434'

# 연결 상태 확인
netstat -an | grep 11434
```

## 자주 묻는 질문 (FAQ)

### Q: AI가 한글로 응답하지 않아요
**A**: 현재 사용 중인 llama3.2:1b 모델은 주로 영어로 응답합니다. 한글 지원이 더 좋은 모델을 사용하거나 프롬프트를 조정해보세요.

### Q: 시작이 너무 느려요
**A**: 초기 AI 시스템 로딩에 2-3초가 걸립니다. `--no-ai` 옵션으로 AI 없이 실행할 수 있습니다.

### Q: 터미널에서 특정 명령어가 작동하지 않아요
**A**: PTY 기반 터미널은 대부분의 명령어를 지원하지만, 일부 대화형 프로그램(vim, nano 등)은 제한적일 수 있습니다.

### Q: 설정을 변경하고 싶어요
**A**: 현재 `.env` 파일을 통한 기본 설정만 지원합니다. 고급 설정 기능은 개발 중입니다.

## 특정 오류 메시지 해결

### `ModuleNotFoundError: No module named 'termai'`
```bash
# 프로젝트 루트에서 실행
cd /path/to/prototype-termai
uv run python -m termai
```

### `asyncio.TimeoutError`
- Ollama 서버 응답 지연 문제
- 더 작은 모델 사용 권장

### `BrokenPipeError`
- 터미널 프로세스 비정상 종료
- 앱 재시작 필요

## 플랫폼별 주의사항

### macOS
- M1/M2 칩: Ollama ARM64 버전 사용
- 터미널 앱: iTerm2 또는 Terminal.app

### Windows
- WSL2 환경에서 실행 권장
- Windows Terminal 사용

### Linux
- 대부분의 배포판에서 정상 작동
- SSH 접속 시 tmux/screen 사용 권장

## 문제 보고

GitHub Issues에서 문제를 보고해주세요:
https://github.com/cagojeiger/prototype-termai/issues

보고 시 포함할 정보:
1. 오류 메시지 전체
2. 실행 환경 (OS, Python 버전)
3. 재현 단계
4. 로그 파일 (가능한 경우)

## 추가 리소스

- [Textual 문서](https://textual.textualize.io/)
- [Ollama 문서](https://ollama.ai/docs)
- [Python asyncio 가이드](https://docs.python.org/3/library/asyncio.html)
- [프로젝트 README](../README.md)
- [현재 구현 상태](../status.md)
