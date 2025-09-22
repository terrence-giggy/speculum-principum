#!/bin/bash

# check-issues.sh
# Helper script for discovering GitHub issues that need processing
# Used by GitHub Actions workflow and available for local testing

set -euo pipefail

# Configuration
DEFAULT_LABEL="site-monitor"
GITHUB_API_URL="https://api.github.com"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-github-actions}"  # github-actions, json, or text

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        echo -e "${color}${message}${NC}"
    else
        echo "$message"
    fi
}

# Function to print help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Discover GitHub issues that need automated processing.

OPTIONS:
    -h, --help              Show this help message
    -r, --repo REPO         Repository name (owner/repo format)
    -t, --token TOKEN       GitHub API token
    -l, --label LABEL       Primary label to filter by (default: site-monitor)
    -f, --format FORMAT     Output format: github-actions, json, or text (default: github-actions)
    -v, --verbose           Enable verbose output
    --dry-run              Show what would be checked without making API calls
    --check-single ISSUE   Check a specific issue number
    --exclude-assigned     Exclude issues already assigned to the bot

ENVIRONMENT VARIABLES:
    GITHUB_TOKEN           GitHub API token (required if not provided via --token)
    GITHUB_REPOSITORY      Repository name (required if not provided via --repo)
    GITHUB_EVENT_PATH      Path to GitHub event data (used in Actions context)

EXAMPLES:
    # Basic usage in GitHub Actions (uses environment variables)
    $0

    # Local usage with explicit parameters
    $0 --repo owner/repo --token ghp_xxx --format text

    # Check a specific issue
    $0 --check-single 123 --format json

    # Verbose output for debugging
    $0 --verbose --format text
EOF
}

# Function to make GitHub API calls
github_api() {
    local endpoint=$1
    local method=${2:-GET}
    
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        print_color "$RED" "Error: GITHUB_TOKEN not set"
        exit 1
    fi
    
    if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
        print_color "$RED" "Error: GITHUB_REPOSITORY not set"
        exit 1
    fi
    
    local url="${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}${endpoint}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        print_color "$YELLOW" "DRY RUN: Would call $method $url"
        echo "[]"  # Return empty array for dry run
        return
    fi
    
    curl -s \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        -X "$method" \
        "$url"
}

# Function to check if an issue matches processing criteria
should_process_issue() {
    local issue_json=$1
    
    # Extract issue details
    local number=$(echo "$issue_json" | jq -r '.number')
    local state=$(echo "$issue_json" | jq -r '.state')
    local labels=$(echo "$issue_json" | jq -r '.labels[].name')
    local assignee=$(echo "$issue_json" | jq -r '.assignee.login // empty')
    
    # Check if issue is open
    if [[ "$state" != "open" ]]; then
        if [[ "${VERBOSE:-false}" == "true" ]]; then
            print_color "$YELLOW" "Skipping issue #$number: not open (state: $state)"
        fi
        return 1
    fi
    
    # Check if issue has required label
    if ! echo "$labels" | grep -q "^${LABEL}$"; then
        if [[ "${VERBOSE:-false}" == "true" ]]; then
            print_color "$YELLOW" "Skipping issue #$number: missing '$LABEL' label"
        fi
        return 1
    fi
    
    # Check if issue is already assigned to bot (if exclude-assigned is set)
    if [[ "${EXCLUDE_ASSIGNED:-false}" == "true" && "$assignee" == "github-actions[bot]" ]]; then
        if [[ "${VERBOSE:-false}" == "true" ]]; then
            print_color "$YELLOW" "Skipping issue #$number: already assigned to github-actions[bot]"
        fi
        return 1
    fi
    
    # Check if issue is a pull request (has pull_request field)
    local pr_url=$(echo "$issue_json" | jq -r '.pull_request.url // empty')
    if [[ -n "$pr_url" ]]; then
        if [[ "${VERBOSE:-false}" == "true" ]]; then
            print_color "$YELLOW" "Skipping issue #$number: is a pull request"
        fi
        return 1
    fi
    
    return 0
}

# Function to get issue details for processing
get_issue_details() {
    local issue_json=$1
    
    local number=$(echo "$issue_json" | jq -r '.number')
    local title=$(echo "$issue_json" | jq -r '.title')
    local labels=$(echo "$issue_json" | jq -r '[.labels[].name]')
    local created_at=$(echo "$issue_json" | jq -r '.created_at')
    local updated_at=$(echo "$issue_json" | jq -r '.updated_at')
    
    jq -n \
        --arg number "$number" \
        --arg title "$title" \
        --argjson labels "$labels" \
        --arg created_at "$created_at" \
        --arg updated_at "$updated_at" \
        '{
            number: ($number | tonumber),
            title: $title,
            labels: $labels,
            created_at: $created_at,
            updated_at: $updated_at
        }'
}

# Function to check issues from GitHub event (when triggered by issue events)
check_event_issue() {
    if [[ -z "${GITHUB_EVENT_PATH:-}" ]] || [[ ! -f "${GITHUB_EVENT_PATH}" ]]; then
        return 1
    fi
    
    local event_data=$(cat "$GITHUB_EVENT_PATH")
    local action=$(echo "$event_data" | jq -r '.action // empty')
    local issue_json=$(echo "$event_data" | jq '.issue // empty')
    
    if [[ "$issue_json" == "null" || "$issue_json" == "empty" ]]; then
        return 1
    fi
    
    # Only process certain actions
    case "$action" in
        "labeled"|"assigned"|"opened"|"reopened")
            if should_process_issue "$issue_json"; then
                get_issue_details "$issue_json"
                return 0
            fi
            ;;
        *)
            if [[ "${VERBOSE:-false}" == "true" ]]; then
                print_color "$YELLOW" "Ignoring event action: $action"
            fi
            ;;
    esac
    
    return 1
}

# Function to check a specific issue number
check_single_issue() {
    local issue_number=$1
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        print_color "$BLUE" "Checking issue #$issue_number"
    fi
    
    local issue_json=$(github_api "/issues/$issue_number")
    
    if echo "$issue_json" | jq -e '.message' > /dev/null 2>&1; then
        local error_message=$(echo "$issue_json" | jq -r '.message')
        print_color "$RED" "Error fetching issue #$issue_number: $error_message"
        return 1
    fi
    
    if should_process_issue "$issue_json"; then
        get_issue_details "$issue_json"
        return 0
    fi
    
    return 1
}

# Function to discover all processable issues
discover_issues() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        print_color "$BLUE" "Discovering issues with label '$LABEL'"
    fi
    
    # Build query parameters
    local query_params="state=open&labels=${LABEL}&per_page=100"
    
    local issues_json=$(github_api "/issues?$query_params")
    
    if echo "$issues_json" | jq -e '.message' > /dev/null 2>&1; then
        local error_message=$(echo "$issues_json" | jq -r '.message')
        print_color "$RED" "Error fetching issues: $error_message"
        return 1
    fi
    
    local processable_issues="[]"
    local total_issues=$(echo "$issues_json" | jq length)
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        print_color "$BLUE" "Found $total_issues issues with '$LABEL' label"
    fi
    
    # Process each issue
    for i in $(seq 0 $((total_issues - 1))); do
        local issue_json=$(echo "$issues_json" | jq ".[$i]")
        
        if should_process_issue "$issue_json"; then
            local issue_details=$(get_issue_details "$issue_json")
            processable_issues=$(echo "$processable_issues" | jq ". + [$issue_details]")
        fi
    done
    
    echo "$processable_issues"
}

# Function to output results in specified format
output_results() {
    local issues_json=$1
    local count=$(echo "$issues_json" | jq length)
    
    case "$OUTPUT_FORMAT" in
        "github-actions")
            # GitHub Actions output format
            echo "::set-output name=issues::$issues_json"
            if [[ $count -gt 0 ]]; then
                echo "::set-output name=should_process::true"
            else
                echo "::set-output name=should_process::false"
            fi
            
            if [[ "${VERBOSE:-false}" == "true" ]]; then
                print_color "$GREEN" "Found $count issues to process"
            fi
            ;;
        
        "json")
            # JSON output
            jq -n \
                --argjson issues "$issues_json" \
                --arg count "$count" \
                '{
                    issues: $issues,
                    count: ($count | tonumber),
                    should_process: ($count | tonumber > 0)
                }'
            ;;
        
        "text")
            # Human-readable text output
            print_color "$GREEN" "Issues to process: $count"
            
            if [[ $count -gt 0 ]]; then
                echo
                print_color "$BLUE" "Processable issues:"
                echo "$issues_json" | jq -r '.[] | "  #\(.number): \(.title)"'
            else
                print_color "$YELLOW" "No issues need processing"
            fi
            ;;
    esac
}

# Main function
main() {
    local CHECK_SINGLE=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -r|--repo)
                GITHUB_REPOSITORY="$2"
                shift 2
                ;;
            -t|--token)
                GITHUB_TOKEN="$2"
                shift 2
                ;;
            -l|--label)
                LABEL="$2"
                shift 2
                ;;
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --check-single)
                CHECK_SINGLE="$2"
                shift 2
                ;;
            --exclude-assigned)
                EXCLUDE_ASSIGNED="true"
                shift
                ;;
            *)
                print_color "$RED" "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set defaults
    LABEL="${LABEL:-$DEFAULT_LABEL}"
    VERBOSE="${VERBOSE:-false}"
    DRY_RUN="${DRY_RUN:-false}"
    EXCLUDE_ASSIGNED="${EXCLUDE_ASSIGNED:-false}"
    
    # Validate required parameters
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        print_color "$RED" "Error: GitHub token required (set GITHUB_TOKEN or use --token)"
        exit 1
    fi
    
    if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
        print_color "$RED" "Error: Repository required (set GITHUB_REPOSITORY or use --repo)"
        exit 1
    fi
    
    # Validate output format
    case "$OUTPUT_FORMAT" in
        "github-actions"|"json"|"text")
            ;;
        *)
            print_color "$RED" "Error: Invalid output format '$OUTPUT_FORMAT'"
            print_color "$RED" "Valid formats: github-actions, json, text"
            exit 1
            ;;
    esac
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        print_color "$BLUE" "Configuration:"
        print_color "$BLUE" "  Repository: $GITHUB_REPOSITORY"
        print_color "$BLUE" "  Label: $LABEL"
        print_color "$BLUE" "  Format: $OUTPUT_FORMAT"
        print_color "$BLUE" "  Dry run: ${DRY_RUN:-false}"
        echo
    fi
    
    local issues_json
    
    if [[ -n "$CHECK_SINGLE" ]]; then
        # Check a specific issue
        if issue_details=$(check_single_issue "$CHECK_SINGLE"); then
            issues_json="[$issue_details]"
        else
            issues_json="[]"
        fi
    elif [[ "${GITHUB_EVENT_NAME:-}" == "issues" ]]; then
        # Try to get issue from GitHub event first
        if issue_details=$(check_event_issue); then
            issues_json="[$issue_details]"
        else
            issues_json="[]"
        fi
    else
        # Discover all issues
        issues_json=$(discover_issues)
    fi
    
    # Output results
    output_results "$issues_json"
}

# Check for required tools
for tool in curl jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        print_color "$RED" "Error: Required tool '$tool' not found"
        print_color "$RED" "Please install $tool and try again"
        exit 1
    fi
done

# Run main function
main "$@"