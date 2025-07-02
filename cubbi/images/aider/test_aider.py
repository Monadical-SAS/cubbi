#!/usr/bin/env python3
"""
Comprehensive test script for Aider Cubbi image
Tests Docker image build, API key configuration, and Cubbi CLI integration
"""

import subprocess
import sys
import tempfile
import re


def run_command(cmd, description="", check=True):
    """Run a shell command and return result"""
    print(f"\n🔍 {description}")
    print(f"Running: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        if check:
            raise
        return e


def test_docker_image_exists():
    """Test if the Aider Docker image exists"""
    print("\n" + "=" * 60)
    print("🧪 Testing Docker Image Existence")
    print("=" * 60)

    result = run_command(
        "docker images monadical/cubbi-aider:latest --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'",
        "Checking if Aider Docker image exists",
    )

    if "monadical/cubbi-aider" in result.stdout:
        print("✅ Aider Docker image exists")
    else:
        print("❌ Aider Docker image not found")
        assert False, "Aider Docker image not found"


def test_aider_version():
    """Test basic Aider functionality in container"""
    print("\n" + "=" * 60)
    print("🧪 Testing Aider Version")
    print("=" * 60)

    result = run_command(
        "docker run --rm monadical/cubbi-aider:latest bash -c 'aider --version'",
        "Testing Aider version command",
    )

    assert (
        "aider" in result.stdout and result.returncode == 0
    ), "Aider version command failed"
    print("✅ Aider version command works")


def test_api_key_configuration():
    """Test API key configuration and environment setup"""
    print("\n" + "=" * 60)
    print("🧪 Testing API Key Configuration")
    print("=" * 60)

    # Test with multiple API keys
    test_keys = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "DEEPSEEK_API_KEY": "test-deepseek-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "OPENROUTER_API_KEY": "test-openrouter-key",
    }

    env_flags = " ".join([f'-e {key}="{value}"' for key, value in test_keys.items()])

    result = run_command(
        f"docker run --rm {env_flags} monadical/cubbi-aider:latest bash -c 'cat ~/.aider/.env'",
        "Testing API key configuration in .env file",
    )

    success = True
    for key, value in test_keys.items():
        if f"{key}={value}" not in result.stdout:
            print(f"❌ {key} not found in .env file")
            success = False
        else:
            print(f"✅ {key} configured correctly")

    # Test default configuration values
    if "AIDER_AUTO_COMMITS=true" in result.stdout:
        print("✅ Default AIDER_AUTO_COMMITS configured")
    else:
        print("❌ Default AIDER_AUTO_COMMITS not found")
        success = False

    if "AIDER_DARK_MODE=false" in result.stdout:
        print("✅ Default AIDER_DARK_MODE configured")
    else:
        print("❌ Default AIDER_DARK_MODE not found")
        success = False

    assert success, "API key configuration test failed"


def test_cubbi_cli_integration():
    """Test Cubbi CLI integration"""
    print("\n" + "=" * 60)
    print("🧪 Testing Cubbi CLI Integration")
    print("=" * 60)

    # Test image listing
    result = run_command(
        "uv run -m cubbi.cli image list | grep aider",
        "Testing Cubbi CLI can see Aider image",
    )

    if "aider" in result.stdout and "Aider AI pair" in result.stdout:
        print("✅ Cubbi CLI can list Aider image")
    else:
        print("❌ Cubbi CLI cannot see Aider image")
        return False

    # Test session creation with test command
    with tempfile.TemporaryDirectory() as temp_dir:
        test_env = {
            "OPENAI_API_KEY": "test-session-key",
            "ANTHROPIC_API_KEY": "test-anthropic-session-key",
        }

        env_vars = " ".join([f"{k}={v}" for k, v in test_env.items()])

        result = run_command(
            f"{env_vars} uv run -m cubbi.cli session create --image aider {temp_dir} --no-shell --run \"aider --version && echo 'Cubbi CLI test successful'\"",
            "Testing Cubbi CLI session creation with Aider",
        )

        assert (
            result.returncode == 0
            and re.search(r"aider \d+\.\d+\.\d+", result.stdout)
            and "Cubbi CLI test successful" in result.stdout
        ), "Cubbi CLI session creation failed"
        print("✅ Cubbi CLI session creation works")


def test_persistent_configuration():
    """Test persistent configuration directories"""
    print("\n" + "=" * 60)
    print("🧪 Testing Persistent Configuration")
    print("=" * 60)

    # Test that persistent directories are created
    result = run_command(
        "docker run --rm -e OPENAI_API_KEY='test-key' monadical/cubbi-aider:latest bash -c 'ls -la /home/cubbi/.aider/ && ls -la /home/cubbi/.cache/'",
        "Testing persistent configuration directories",
    )

    success = True

    if ".env" in result.stdout:
        print("✅ .env file created in ~/.aider/")
    else:
        print("❌ .env file not found in ~/.aider/")
        success = False

    if "aider" in result.stdout:
        print("✅ ~/.cache/aider directory exists")
    else:
        print("❌ ~/.cache/aider directory not found")
        success = False

    assert success, "API key configuration test failed"


def test_plugin_functionality():
    """Test the Aider plugin functionality"""
    print("\n" + "=" * 60)
    print("🧪 Testing Plugin Functionality")
    print("=" * 60)

    # Test plugin without API keys (should still work)
    result = run_command(
        "docker run --rm monadical/cubbi-aider:latest bash -c 'echo \"Plugin test without API keys\"'",
        "Testing plugin functionality without API keys",
    )

    if "No API keys found - Aider will run without pre-configuration" in result.stdout:
        print("✅ Plugin handles missing API keys gracefully")
    else:
        # This might be in stderr or initialization might have changed
        print("ℹ️ Plugin API key handling test - check output above")

    # Test plugin with API keys
    result = run_command(
        "docker run --rm -e OPENAI_API_KEY='test-plugin-key' monadical/cubbi-aider:latest bash -c 'echo \"Plugin test with API keys\"'",
        "Testing plugin functionality with API keys",
    )

    if "Aider environment configured successfully" in result.stdout:
        print("✅ Plugin configures environment successfully")
    else:
        print("❌ Plugin environment configuration failed")
        assert False, "Plugin environment configuration failed"


def main():
    """Run all tests"""
    print("🚀 Starting Aider Cubbi Image Tests")
    print("=" * 60)

    tests = [
        ("Docker Image Exists", test_docker_image_exists),
        ("Aider Version", test_aider_version),
        ("API Key Configuration", test_api_key_configuration),
        ("Persistent Configuration", test_persistent_configuration),
        ("Plugin Functionality", test_plugin_functionality),
        ("Cubbi CLI Integration", test_cubbi_cli_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            test_func()
            results[test_name] = True
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    total_tests = len(tests)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nTotal: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")

    if failed_tests == 0:
        print("\n🎉 All tests passed! Aider image is ready for use.")
        return 0
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
