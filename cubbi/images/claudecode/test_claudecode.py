#!/usr/bin/env python3
"""
Automated test suite for Claude Code Cubbi integration
"""

import subprocess


def run_test(description: str, command: list, timeout: int = 30) -> bool:
    """Run a test command and return success status"""
    print(f"🧪 Testing: {description}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            print("   ✅ PASS")
            return True
        else:
            print(f"   ❌ FAIL: {result.stderr}")
            if result.stdout:
                print(f"   📋 stdout: {result.stdout}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ TIMEOUT: Command exceeded {timeout}s")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False


def test_suite():
    """Run complete test suite"""
    tests_passed = 0
    total_tests = 0

    print("🚀 Starting Claude Code Cubbi Integration Test Suite")
    print("=" * 60)

    # Test 1: Build image
    total_tests += 1
    if run_test(
        "Build Claude Code image",
        ["docker", "build", "-t", "cubbi-claudecode:test", "cubbi/images/claudecode/"],
        timeout=180,
    ):
        tests_passed += 1

    # Test 2: Tag image for Cubbi
    total_tests += 1
    if run_test(
        "Tag image for Cubbi",
        ["docker", "tag", "cubbi-claudecode:test", "monadical/cubbi-claudecode:latest"],
    ):
        tests_passed += 1

    # Test 3: Basic container startup
    total_tests += 1
    if run_test(
        "Container startup with test API key",
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "ANTHROPIC_API_KEY=test-key",
            "cubbi-claudecode:test",
            "bash",
            "-c",
            "claude --version",
        ],
    ):
        tests_passed += 1

    # Test 4: Cubbi image list
    total_tests += 1
    if run_test(
        "Cubbi image list includes claudecode",
        ["uv", "run", "-m", "cubbi.cli", "image", "list"],
    ):
        tests_passed += 1

    # Test 5: Cubbi session creation
    total_tests += 1
    session_result = subprocess.run(
        [
            "uv",
            "run",
            "-m",
            "cubbi.cli",
            "session",
            "create",
            "--image",
            "claudecode",
            "--name",
            "test-automation",
            "--no-connect",
            "--env",
            "ANTHROPIC_API_KEY=test-key",
            "--run",
            "claude --version",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if session_result.returncode == 0:
        print("🧪 Testing: Cubbi session creation")
        print("   ✅ PASS")
        tests_passed += 1

        # Extract session ID for cleanup
        session_id = None
        for line in session_result.stdout.split("\n"):
            if "Session ID:" in line:
                session_id = line.split("Session ID: ")[1].strip()
                break

        if session_id:
            # Test 6: Session cleanup
            total_tests += 1
            if run_test(
                "Clean up test session",
                ["uv", "run", "-m", "cubbi.cli", "session", "close", session_id],
            ):
                tests_passed += 1
        else:
            print("🧪 Testing: Clean up test session")
            print("   ⚠️  SKIP: Could not extract session ID")
            total_tests += 1
    else:
        print("🧪 Testing: Cubbi session creation")
        print(f"   ❌ FAIL: {session_result.stderr}")
        total_tests += 2  # This test and cleanup test both fail

    # Test 7: Session without API key
    total_tests += 1
    no_key_result = subprocess.run(
        [
            "uv",
            "run",
            "-m",
            "cubbi.cli",
            "session",
            "create",
            "--image",
            "claudecode",
            "--name",
            "test-no-key",
            "--no-connect",
            "--run",
            "claude --version",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if no_key_result.returncode == 0:
        print("🧪 Testing: Session without API key")
        print("   ✅ PASS")
        tests_passed += 1

        # Extract session ID and close
        session_id = None
        for line in no_key_result.stdout.split("\n"):
            if "Session ID:" in line:
                session_id = line.split("Session ID: ")[1].strip()
                break

        if session_id:
            subprocess.run(
                ["uv", "run", "-m", "cubbi.cli", "session", "close", session_id],
                capture_output=True,
                timeout=30,
            )
    else:
        print("🧪 Testing: Session without API key")
        print(f"   ❌ FAIL: {no_key_result.stderr}")

    # Test 8: Persistent configuration test
    total_tests += 1
    persist_result = subprocess.run(
        [
            "uv",
            "run",
            "-m",
            "cubbi.cli",
            "session",
            "create",
            "--image",
            "claudecode",
            "--name",
            "test-persist-auto",
            "--project",
            "test-automation",
            "--no-connect",
            "--env",
            "ANTHROPIC_API_KEY=test-key",
            "--run",
            "echo 'automation test' > ~/.claude/automation.txt && cat ~/.claude/automation.txt",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if persist_result.returncode == 0:
        print("🧪 Testing: Persistent configuration")
        print("   ✅ PASS")
        tests_passed += 1

        # Extract session ID and close
        session_id = None
        for line in persist_result.stdout.split("\n"):
            if "Session ID:" in line:
                session_id = line.split("Session ID: ")[1].strip()
                break

        if session_id:
            subprocess.run(
                ["uv", "run", "-m", "cubbi.cli", "session", "close", session_id],
                capture_output=True,
                timeout=30,
            )
    else:
        print("🧪 Testing: Persistent configuration")
        print(f"   ❌ FAIL: {persist_result.stderr}")

    print("=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Claude Code integration is working correctly.")
        return True
    else:
        print(
            f"❌ {total_tests - tests_passed} test(s) failed. Please check the output above."
        )
        return False


def main():
    """Main test entry point"""
    success = test_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
