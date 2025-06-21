#!/usr/bin/env python3
"""
Terminal AI Assistant - Checkpoint 1 테스트 스위트
uv run python test_terminal.py 로 실행하세요.

Comprehensive test suite for Checkpoint 1: Terminal Wrapper Testing

Tests PTY terminal creation, command execution, output capture,
input handling, and history management as specified in checkpoint-01.md
"""

import sys
import time

from terminal.manager import TerminalManager


def test_basic_terminal():
    """기본 터미널 기능 테스트"""
    print("=== 터미널 에뮬레이터 테스트 ===\n")

    tm = TerminalManager()

    def on_command_start(cmd):
        print(f"[실행 시작] {cmd}")

    def on_command_end(cmd, exit_code):
        print(f"[실행 완료] {cmd} (exit: {exit_code})")

    tm.on_command_start = on_command_start
    tm.on_command_end = on_command_end

    try:
        tm.start()
        print("터미널이 시작되었습니다.\n")

        time.sleep(0.5)

        if not tm.is_running():
            print("❌ 터미널 시작 실패")
            return False

        print("✅ PTY 터미널 생성 성공")

        test_commands = [
            "echo 'Hello from Terminal Emulator!'",
            "pwd",
            "ls -la",
            "python3 --version",
            "echo '한글 테스트: 안녕하세요'",  # 한글 출력 테스트
            "echo -e '\\033[31mRed Text\\033[0m'",  # ANSI 컬러 테스트
        ]

        for i, cmd in enumerate(test_commands, 1):
            print(f"\n{i}. 실행할 명령어: {cmd}")
            tm.execute(cmd)

            timeout = 5.0
            start_time = time.time()
            while tm.command_running and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if tm.command_running:
                print(f"⚠️  명령어 실행 시간 초과: {cmd}")
                continue

            output_lines = tm.get_output(10)
            if output_lines:
                print("출력:")
                for line in output_lines[-5:]:  # 마지막 5줄만 표시
                    if line.strip():  # 빈 줄 제외
                        print(f"  {line}")
            else:
                print("  (출력 없음)")

        print("\n\n=== 명령어 히스토리 ===")
        history = tm.get_command_history(10)
        if history:
            for cmd in history:
                duration_str = f"{cmd.duration:.2f}초" if cmd.duration else "N/A"
                exit_code_str = (
                    f"exit: {cmd.exit_code}" if cmd.exit_code is not None else "진행중"
                )
                print(f"- {cmd.command} (실행시간: {duration_str}, {exit_code_str})")
        else:
            print("히스토리가 비어있습니다.")

        stats = tm.get_history_statistics()
        print("\n=== 통계 정보 ===")
        print(f"총 명령어: {stats['total_commands']}")
        print(f"성공: {stats['success_count']}, 실패: {stats['error_count']}")
        print(f"평균 실행시간: {stats['average_duration']:.3f}초")

        print("\n=== 버퍼 정보 ===")
        buffer_info = tm.get_buffer_info()
        print(f"버퍼 라인 수: {buffer_info['total_lines']}")
        print(f"현재 라인 길이: {buffer_info['current_line_length']}")

        plain_output = tm.get_plain_output(5)
        if plain_output:
            print("\n=== ANSI 코드 제거된 출력 (마지막 5줄) ===")
            for line in plain_output.split("\n")[-5:]:
                if line.strip():
                    print(f"  {line}")

        print("\n✅ 모든 기본 테스트 완료")
        return True

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        tm.stop()
        print("\n터미널이 종료되었습니다.")


def test_input_handling():
    """입력 처리 테스트"""
    print("\n=== 입력 처리 테스트 ===")

    tm = TerminalManager()

    try:
        tm.start()
        time.sleep(0.5)

        if not tm.is_running():
            print("❌ 터미널 시작 실패")
            return False

        print("✅ 터미널 시작 성공")

        print("\n1. 텍스트 입력 테스트")
        tm.write_text("echo 'Input test'")
        time.sleep(0.2)
        tm.write_text("\n")  # Enter 키
        time.sleep(1)

        print("\n2. 백스페이스 테스트")
        tm.write_text("echo 'mistake")
        time.sleep(0.2)
        tm.write_text("\b" * 7)  # 'mistake' 삭제
        tm.write_text("correct'")
        time.sleep(0.2)
        tm.write_text("\n")
        time.sleep(1)

        print("\n3. Ctrl+C 인터럽트 테스트")
        tm.write_text("sleep 10")  # 긴 명령어 시작
        time.sleep(0.2)
        tm.write_text("\n")
        time.sleep(0.5)
        tm.interrupt_command()  # Ctrl+C 전송
        time.sleep(1)

        print("✅ 입력 처리 테스트 완료")
        return True

    except Exception as e:
        print(f"❌ 입력 처리 테스트 중 오류: {e}")
        return False

    finally:
        tm.stop()


def test_error_handling():
    """에러 처리 테스트"""
    print("\n=== 에러 처리 테스트 ===")

    tm = TerminalManager()

    try:
        tm.start()
        time.sleep(0.5)

        print("1. 존재하지 않는 명령어 테스트")
        tm.execute("nonexistent_command_12345")
        time.sleep(2)

        print("2. 잘못된 경로 접근 테스트")
        tm.execute("ls /nonexistent/path/12345")
        time.sleep(2)

        error_commands = tm.history.get_errors()
        print(f"\n에러 명령어 개수: {len(error_commands)}")
        for cmd in error_commands[-3:]:  # 최근 3개만
            print(f"- {cmd.command} (exit: {cmd.exit_code})")

        print("✅ 에러 처리 테스트 완료")
        return True

    except Exception as e:
        print(f"❌ 에러 처리 테스트 중 오류: {e}")
        return False

    finally:
        tm.stop()


def test_interactive():
    """대화형 테스트"""
    print("\n=== 대화형 터미널 테스트 ===")
    print("명령어를 입력하세요. 종료하려면 'exit' 또는 Ctrl+C를 입력하세요.\n")

    tm = TerminalManager()

    def handle_output(text: str):
        sys.stdout.write(text)
        sys.stdout.flush()

    tm.on_output = handle_output

    try:
        tm.start()
        time.sleep(0.5)

        if not tm.is_running():
            print("❌ 터미널 시작 실패")
            return False

        while True:
            try:
                user_input = input()

                if user_input.lower() in ["exit", "quit"]:
                    break

                tm.execute(user_input)

                timeout = 10.0
                start_time = time.time()
                while tm.command_running and (time.time() - start_time) < timeout:
                    time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\nCtrl+C 감지됨. 종료합니다.")
                break
            except EOFError:
                print("\nEOF 감지됨. 종료합니다.")
                break

    except Exception as e:
        print(f"❌ 대화형 테스트 중 오류: {e}")
        return False

    finally:
        tm.stop()
        print("\n대화형 테스트 종료")


def run_checkpoint_tests():
    """Checkpoint 1의 모든 테스트 실행"""
    print("🚀 Checkpoint 1: 터미널 래퍼 테스트 시작\n")

    test_results = []

    print("=" * 60)
    result1 = test_basic_terminal()
    test_results.append(("기본 터미널 기능", result1))

    print("=" * 60)
    result2 = test_input_handling()
    test_results.append(("입력 처리", result2))

    print("=" * 60)
    result3 = test_error_handling()
    test_results.append(("에러 처리", result3))

    print("\n" + "=" * 60)
    print("🏁 테스트 결과 요약")
    print("=" * 60)

    all_passed = True
    for test_name, result in test_results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과! Checkpoint 1 완료")
        print("다음 단계: 03-tui-framework.md로 진행 가능")
    else:
        print("⚠️  일부 테스트 실패. 문제를 해결한 후 다시 시도하세요.")

    return all_passed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            test_interactive()
        elif sys.argv[1] == "--basic":
            test_basic_terminal()
        elif sys.argv[1] == "--input":
            test_input_handling()
        elif sys.argv[1] == "--error":
            test_error_handling()
        else:
            print("사용법:")
            print("  python test_terminal.py           # 모든 테스트 실행")
            print("  python test_terminal.py --basic   # 기본 테스트만")
            print("  python test_terminal.py --input   # 입력 테스트만")
            print("  python test_terminal.py --error   # 에러 테스트만")
            print("  python test_terminal.py --interactive  # 대화형 테스트")
    else:
        success = run_checkpoint_tests()

        if success:
            print("\n대화형 테스트를 실행하시겠습니까? (y/n): ", end="")
            try:
                if input().lower() == "y":
                    test_interactive()
            except (KeyboardInterrupt, EOFError):
                print("\n프로그램을 종료합니다.")
