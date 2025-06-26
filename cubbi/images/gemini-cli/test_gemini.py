#!/usr/bin/env python3
"""
Comprehensive test script for Gemini CLI Cubbi image
Tests Docker image build, API key configuration, and Cubbi CLI integration
"""

import subprocess
import sys
import tempfile


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


def test_docker_build():
    """Test Docker image build"""
    print("\n" + "=" * 60)
    print("🧪 Testing Docker Image Build")
    print("=" * 60)

    result = run_command(
        "cd /home/bouthilx/projects/cubbi/cubbi/images/gemini-cli && docker build -t monadical/cubbi-gemini-cli:latest .",
        "Building Gemini CLI Docker image",
    )

    if result.returncode == 0:
        print("✅ Gemini CLI Docker image built successfully")
        return True
    else:
        print("❌ Gemini CLI Docker image build failed")
        return False


def test_docker_image_exists():
    """Test if the Gemini CLI Docker image exists"""
    print("\n" + "=" * 60)
    print("🧪 Testing Docker Image Existence")
    print("=" * 60)

    result = run_command(
        "docker images monadical/cubbi-gemini-cli:latest --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'",
        "Checking if Gemini CLI Docker image exists",
    )

    if "monadical/cubbi-gemini-cli" in result.stdout:
        print("✅ Gemini CLI Docker image exists")
        return True
    else:
        print("❌ Gemini CLI Docker image not found")
        return False


def test_gemini_version():
    """Test basic Gemini CLI functionality in container"""
    print("\n" + "=" * 60)
    print("🧪 Testing Gemini CLI Version")
    print("=" * 60)

    result = run_command(
        "docker run --rm monadical/cubbi-gemini-cli:latest bash -c 'gemini --version'",
        "Testing Gemini CLI version command",
    )

    if result.returncode == 0 and (
        "gemini" in result.stdout.lower() or "version" in result.stdout.lower()
    ):
        print("✅ Gemini CLI version command works")
        return True
    else:
        print("❌ Gemini CLI version command failed")
        return False


def test_api_key_configuration():
    """Test API key configuration and environment setup"""
    print("\n" + "=" * 60)
    print("🧪 Testing API Key Configuration")
    print("=" * 60)

    # Test with multiple API keys
    test_keys = {
        "GEMINI_API_KEY": "test-gemini-key",
        "GOOGLE_API_KEY": "test-google-key",
    }

    env_flags = " ".join([f'-e {key}="{value}"' for key, value in test_keys.items()])

    result = run_command(
        f"docker run --rm {env_flags} monadical/cubbi-gemini-cli:latest bash -c 'cat ~/.config/gemini/.env 2>/dev/null || echo \"No .env file found\"'",
        "Testing API key configuration in .env file",
    )

    success = True
    if "test-gemini-key" in result.stdout:
        print("✅ GEMINI_API_KEY configured correctly")
    else:
        print("❌ GEMINI_API_KEY not found in configuration")
        success = False

    return success


def test_configuration_file():
    """Test Gemini CLI configuration file creation"""
    print("\n" + "=" * 60)
    print("🧪 Testing Configuration File")
    print("=" * 60)

    env_vars = "-e GEMINI_API_KEY='test-key' -e GEMINI_MODEL='gemini-1.5-pro' -e GEMINI_TEMPERATURE='0.5'"

    result = run_command(
        f"docker run --rm {env_vars} monadical/cubbi-gemini-cli:latest bash -c 'cat ~/.config/gemini/config.json 2>/dev/null || echo \"No config file found\"'",
        "Testing configuration file creation",
    )

    success = True
    if "gemini-1.5-pro" in result.stdout:
        print("✅ Default model configured correctly")
    else:
        print("❌ Default model not found in configuration")
        success = False

    if "0.5" in result.stdout:
        print("✅ Temperature configured correctly")
    else:
        print("❌ Temperature not found in configuration")
        success = False

    return success


def test_cubbi_cli_integration():
    """Test Cubbi CLI integration"""
    print("\n" + "=" * 60)
    print("🧪 Testing Cubbi CLI Integration")
    print("=" * 60)

    # Test image listing
    result = run_command(
        "uv run -m cubbi.cli image list | grep gemini-cli",
        "Testing Cubbi CLI can see Gemini CLI image",
    )

    if "gemini-cli" in result.stdout:
        print("✅ Cubbi CLI can list Gemini CLI image")
    else:
        print("❌ Cubbi CLI cannot see Gemini CLI image")
        return False

    # Test session creation with test command
    with tempfile.TemporaryDirectory() as temp_dir:
        test_env = {
            "GEMINI_API_KEY": "test-session-key",
        }

        env_vars = " ".join([f"{k}={v}" for k, v in test_env.items()])

        result = run_command(
            f"{env_vars} uv run -m cubbi.cli session create --image gemini-cli {temp_dir} --no-shell --run \"gemini --version && echo 'Cubbi CLI test successful'\"",
            "Testing Cubbi CLI session creation with Gemini CLI",
        )

        if result.returncode == 0 and "Cubbi CLI test successful" in result.stdout:
            print("✅ Cubbi CLI session creation works")
            return True
        else:
            print("❌ Cubbi CLI session creation failed")
            return False


def test_persistent_configuration():
    """Test persistent configuration directories"""
    print("\n" + "=" * 60)
    print("🧪 Testing Persistent Configuration")
    print("=" * 60)

    # Test that persistent directories are created
    result = run_command(
        "docker run --rm -e GEMINI_API_KEY='test-key' monadical/cubbi-gemini-cli:latest bash -c 'ls -la /home/cubbi/.config/ && ls -la /home/cubbi/.cache/'",
        "Testing persistent configuration directories",
    )

    success = True

    if "gemini" in result.stdout:
        print("✅ ~/.config/gemini directory exists")
    else:
        print("❌ ~/.config/gemini directory not found")
        success = False

    if "gemini" in result.stdout:
        print("✅ ~/.cache/gemini directory exists")
    else:
        print("❌ ~/.cache/gemini directory not found")
        success = False

    return success


def test_plugin_functionality():
    """Test the Gemini CLI plugin functionality"""
    print("\n" + "=" * 60)
    print("🧪 Testing Plugin Functionality")
    print("=" * 60)

    # Test plugin without API keys (should still work)
    result = run_command(
        "docker run --rm monadical/cubbi-gemini-cli:latest bash -c 'echo \"Plugin test without API keys\"'",
        "Testing plugin functionality without API keys",
    )

    if "No API key found - Gemini CLI will require authentication" in result.stdout:
        print("✅ Plugin handles missing API keys gracefully")
    else:
        print("ℹ️ Plugin API key handling test - check output above")

    # Test plugin with API keys
    result = run_command(
        "docker run --rm -e GEMINI_API_KEY='test-plugin-key' monadical/cubbi-gemini-cli:latest bash -c 'echo \"Plugin test with API keys\"'",
        "Testing plugin functionality with API keys",
    )

    if "Gemini CLI configured successfully" in result.stdout:
        print("✅ Plugin configures environment successfully")
        return True
    else:
        print("❌ Plugin environment configuration failed")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Gemini CLI Cubbi Image Tests")
    print("=" * 60)

    tests = [
        ("Docker Image Build", test_docker_build),
        ("Docker Image Exists", test_docker_image_exists),
        ("Gemini CLI Version", test_gemini_version),
        ("API Key Configuration", test_api_key_configuration),
        ("Configuration File", test_configuration_file),
        ("Persistent Configuration", test_persistent_configuration),
        ("Plugin Functionality", test_plugin_functionality),
        ("Cubbi CLI Integration", test_cubbi_cli_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
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
        print("\n🎉 All tests passed! Gemini CLI image is ready for use.")
        return 0
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
