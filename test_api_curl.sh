#!/bin/bash
# Simple API test script using curl
# Run this on your Pi to test all endpoints

BASE_URL="http://localhost:5000"
PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%H:%M:%S')
    
    case $level in
        "ERROR")
            echo -e "[${timestamp}] ${RED}ERROR${NC}: $message"
            ;;
        "WARN")
            echo -e "[${timestamp}] ${YELLOW}WARN${NC}: $message"
            ;;
        "PASS")
            echo -e "[${timestamp}] ${GREEN}PASS${NC}: $message"
            ;;
        "INFO")
            echo -e "[${timestamp}] ${BLUE}INFO${NC}: $message"
            ;;
        *)
            echo -e "[${timestamp}] INFO: $message"
            ;;
    esac
}

test_endpoint() {
    local endpoint=$1
    local test_name=$2
    local url="${BASE_URL}${endpoint}"
    
    log "INFO" "Testing ${test_name}: ${endpoint}"
    
    # Test HTTP status and response
    local response=$(curl -s -w "%{http_code}" -o /tmp/test_response.json "${url}" 2>/dev/null)
    local http_code="${response: -3}"
    
    if [ "$http_code" != "200" ]; then
        log "ERROR" "❌ ${test_name} failed: HTTP ${http_code}"
        ((FAILED++))
        return 1
    fi
    
    # Check if response is valid JSON
    if ! jq empty /tmp/test_response.json 2>/dev/null; then
        log "ERROR" "❌ ${test_name} failed: Invalid JSON response"
        ((FAILED++))
        return 1
    fi
    
    log "PASS" "✅ ${test_name} passed (HTTP 200, valid JSON)"
    ((PASSED++))
    return 0
}

test_endpoint_with_data() {
    local endpoint=$1
    local test_name=$2
    local expected_field=$3
    local url="${BASE_URL}${endpoint}"
    
    log "INFO" "Testing ${test_name}: ${endpoint}"
    
    # Test HTTP status and response
    local response=$(curl -s -w "%{http_code}" -o /tmp/test_response.json "${url}" 2>/dev/null)
    local http_code="${response: -3}"
    
    if [ "$http_code" != "200" ]; then
        log "ERROR" "❌ ${test_name} failed: HTTP ${http_code}"
        ((FAILED++))
        return 1
    fi
    
    # Check if response is valid JSON
    if ! jq empty /tmp/test_response.json 2>/dev/null; then
        log "ERROR" "❌ ${test_name} failed: Invalid JSON response"
        ((FAILED++))
        return 1
    fi
    
    # Check for expected field if provided
    if [ -n "$expected_field" ]; then
        if ! jq -e ".$expected_field" /tmp/test_response.json > /dev/null 2>&1; then
            log "ERROR" "❌ ${test_name} failed: Missing expected field '${expected_field}'"
            ((FAILED++))
            return 1
        fi
    fi
    
    log "PASS" "✅ ${test_name} passed"
    ((PASSED++))
    return 0
}

show_sample_data() {
    local endpoint=$1
    local test_name=$2
    local url="${BASE_URL}${endpoint}"
    
    log "INFO" "Sample data from ${test_name}:"
    echo "----------------------------------------"
    curl -s "${url}" | jq '.' 2>/dev/null | head -20
    echo "----------------------------------------"
    echo
}

main() {
    echo -e "${BLUE}Pi Air Monitor API Test Suite${NC}"
    echo "========================================"
    echo
    
    log "INFO" "Starting API endpoint tests..."
    log "INFO" "Target server: ${BASE_URL}"
    
    # Test basic connectivity
    log "INFO" "Testing basic connectivity..."
    if curl -s --connect-timeout 5 "${BASE_URL}" > /dev/null; then
        log "PASS" "✅ Server is reachable"
    else
        log "ERROR" "❌ Cannot reach server at ${BASE_URL}"
        exit 1
    fi
    
    echo
    log "INFO" "Testing all API endpoints..."
    echo
    
    # Test all endpoints
    test_endpoint_with_data "/api/system" "System Information" "platform"
    test_endpoint_with_data "/api/stats" "Real-time Stats" "cpu_percent"
    test_endpoint_with_data "/api/air-quality-latest" "Air Quality Latest" "latest_reading"
    test_endpoint_with_data "/api/air-quality-worst-24h" "Worst Air Quality 24h" "worst_reading"
    test_endpoint_with_data "/api/air-quality-history" "Air Quality History (24h)" "interval_averages"
    test_endpoint_with_data "/api/air-quality-history?range=1h" "Air Quality History (1h)" "time_range"
    test_endpoint_with_data "/api/air-quality-history?range=6h" "Air Quality History (6h)" "time_range"
    test_endpoint_with_data "/api/temperature-history" "Temperature History" "real_time_history"
    test_endpoint_with_data "/api/system-history" "System History" "hourly_averages"
    
    echo
    log "INFO" "=== TEST SUMMARY ==="
    local total=$((PASSED + FAILED))
    log "INFO" "Total tests: ${total}"
    log "INFO" "Passed: ${PASSED}"
    log "INFO" "Failed: ${FAILED}"
    
    if [ $FAILED -eq 0 ]; then
        log "PASS" "🎉 All tests passed!"
        
        echo
        log "INFO" "Showing sample data from key endpoints..."
        echo
        show_sample_data "/api/stats" "Real-time Stats"
        show_sample_data "/api/air-quality-latest" "Air Quality Latest"
        show_sample_data "/api/air-quality-worst-24h" "Worst Air Quality 24h"
        
        exit 0
    else
        log "ERROR" "❌ ${FAILED} test(s) failed"
        exit 1
    fi
    
    # Clean up
    rm -f /tmp/test_response.json
}

# Check for required tools
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Install with: sudo apt install jq"
    exit 1
fi

main "$@"