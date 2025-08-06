#!/bin/bash

# Comprehensive test script for all cubbi images with different model combinations
# Tests single prompt/response functionality for each tool

set -e

# Configuration
TIMEOUT="180s"
TEST_PROMPT="What is 2+2?"
LOG_FILE="test_results.log"
TEMP_DIR="/tmp/cubbi_test_$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test matrix
declare -a IMAGES=("goose" "aider" "claudecode" "opencode" "crush")
declare -a MODELS=(
    "anthropic/claude-sonnet-4-20250514"
    "openai/gpt-4o"
    "openrouter/openai/gpt-4o"
    "litellm/gpt-oss:120b"
)

# Command templates for each tool (based on research)
declare -A COMMANDS=(
    ["goose"]="goose run -t '$TEST_PROMPT' --no-session --quiet"
    ["aider"]="aider --message '$TEST_PROMPT' --yes-always --no-fancy-input --no-check-update --no-auto-commits"
    ["claudecode"]="claude -p '$TEST_PROMPT'"
    ["opencode"]="opencode run -m %MODEL% '$TEST_PROMPT'"
    ["crush"]="crush run '$TEST_PROMPT'"
)

# Initialize results tracking
declare -A RESULTS
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Setup
echo -e "${BLUE}=== Cubbi Plugin Configuration Test Suite ===${NC}"
echo "Starting comprehensive test at $(date)"
echo "Test prompt: '$TEST_PROMPT'"
echo "Timeout: $TIMEOUT"
echo ""

mkdir -p "$TEMP_DIR"
> "$LOG_FILE"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# Function to run a single test
run_test() {
    local image="$1"
    local model="$2"
    local command="$3"

    # Replace %MODEL% placeholder in command
    command="${command//%MODEL%/$model}"

    local test_name="${image}_${model//\//_}"
    local log_file="${TEMP_DIR}/${test_name}.log"

    echo -ne "Testing ${BLUE}$image${NC} with ${YELLOW}$model${NC}... "

    log "Starting test: $test_name"
    log "Command: $command"

    # Run the test with timeout
    local start_time=$(date +%s)
    if timeout "$TIMEOUT" uv run -m cubbi.cli session create \
        -i "$image" \
        -m "$model" \
        --no-connect \
        --no-shell \
        --run "$command" > "$log_file" 2>&1; then

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        # Check if we got a meaningful response
        if grep -q "Initial command finished (exit code: 0)" "$log_file" &&
           grep -q "Command execution complete" "$log_file"; then
            echo -e "${GREEN}PASS${NC} (${duration}s)"
            RESULTS["$test_name"]="PASS"
            ((PASSED_TESTS++))
            log "Test passed in ${duration}s"
        else
            echo -e "${RED}FAIL${NC} (no valid output)"
            RESULTS["$test_name"]="FAIL_NO_OUTPUT"
            ((FAILED_TESTS++))
            log "Test failed - no valid output"
        fi
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}FAIL${NC} (timeout/error after ${duration}s)"
        RESULTS["$test_name"]="FAIL_TIMEOUT"
        ((FAILED_TESTS++))
        log "Test failed - timeout or error after ${duration}s"
    fi

    ((TOTAL_TESTS++))

    # Save detailed log
    log "=== Test output for $test_name ==="
    cat "$log_file" >> "$LOG_FILE"
    log "=== End test output ==="
    log ""
}

# Function to print test matrix header
print_matrix_header() {
    echo ""
    echo -e "${BLUE}=== Test Results Matrix ===${NC}"
    printf "%-15s" "Image/Model"
    for model in "${MODELS[@]}"; do
        # Shorten model name for display
        short_model=$(echo "$model" | sed 's/.*\///')
        printf "%-20s" "$short_model"
    done
    echo ""
    printf "%-15s" "==============="
    for model in "${MODELS[@]}"; do
        printf "%-20s" "===================="
    done
    echo ""
}

# Function to print test matrix row
print_matrix_row() {
    local image="$1"
    printf "%-15s" "$image"

    for model in "${MODELS[@]}"; do
        local test_name="${image}_${model//\//_}"
        local result="${RESULTS[$test_name]}"

        case "$result" in
            "PASS")
                printf "%-20s" "$(echo -e "${GREEN}PASS${NC}")"
                ;;
            "FAIL_NO_OUTPUT")
                printf "%-20s" "$(echo -e "${RED}FAIL (no output)${NC}")"
                ;;
            "FAIL_TIMEOUT")
                printf "%-20s" "$(echo -e "${RED}FAIL (timeout)${NC}")"
                ;;
            *)
                printf "%-20s" "$(echo -e "${YELLOW}UNKNOWN${NC}")"
                ;;
        esac
    done
    echo ""
}

# Main test execution
echo -e "${YELLOW}Running ${#IMAGES[@]} images × ${#MODELS[@]} models = $((${#IMAGES[@]} * ${#MODELS[@]})) total tests${NC}"
echo ""

for image in "${IMAGES[@]}"; do
    echo -e "${BLUE}--- Testing $image ---${NC}"

    for model in "${MODELS[@]}"; do
        command="${COMMANDS[$image]}"
        run_test "$image" "$model" "$command"
    done
    echo ""
done

# Print results summary
print_matrix_header
for image in "${IMAGES[@]}"; do
    print_matrix_row "$image"
done

echo ""
echo -e "${BLUE}=== Final Summary ===${NC}"
echo "Total tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed! 🎉${NC}"
    exit_code=0
else
    echo -e "${RED}$FAILED_TESTS tests failed${NC}"
    exit_code=1
fi

echo ""
echo "Detailed logs saved to: $LOG_FILE"
echo "Test completed at $(date)"

# Cleanup
rm -rf "$TEMP_DIR"

log "Test suite completed. Total: $TOTAL_TESTS, Passed: $PASSED_TESTS, Failed: $FAILED_TESTS"

exit $exit_code