#!/bin/bash
# File Converter GUI Integration Test Script
# Filename: test_gui.sh
# Tests all aspects of the GUI integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" 
PROJECT_ROOT="$SCRIPT_DIR"  # Scripts are in the same directory 
FILE_CONVERTER_SCRIPT="$PROJECT_ROOT/gui.py"

# Output functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
} 

print_test() {
    echo -n "Testing $1... "
    TESTS_RUN=$((TESTS_RUN + 1))
} 

print_pass() {
    echo -e "${GREEN}PASS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
} 

print_fail() {
    echo -e "${RED}FAIL${NC}"
    if [ -n "$1" ]; then
        echo -e "${RED} Error: $1${NC}"
    fi
    TESTS_FAILED=$((TESTS_FAILED + 1))
} 

print_skip() {
    echo -e "${YELLOW}SKIP${NC} ($1)"
} 

# Test functions
test_file_converter_script() {
    print_header "Testing File Converter Script"
    
    print_test "File Converter script exists" 
    if [ -f "$FILE_CONVERTER_SCRIPT" ]; then 
        print_pass
    else
        print_fail "Script not found at $FILE_CONVERTER_SCRIPT" 
        return 1
    fi
    
    print_test "File Converter script is executable" 
    if [ -x "$FILE_CONVERTER_SCRIPT" ]; then 
        print_pass
    else
        print_fail "Script is not executable" 
    fi
    
    print_test "File Converter script parses cleanly"
    if python3 -m py_compile "$FILE_CONVERTER_SCRIPT" >/dev/null 2>&1; then
        print_pass
    else
        print_fail "Script has Python syntax errors"
    fi

    print_test "File Converter imports converter_logic"
    if python3 -c "import ast,sys; t=ast.parse(open('$FILE_CONVERTER_SCRIPT').read()); sys.exit(0 if any(isinstance(n, ast.ImportFrom) and n.module=='converter_logic' for n in ast.walk(t)) else 1)" 2>/dev/null; then
        print_pass
    else
        print_fail "converter_logic import missing"
    fi
} 

test_nautilus_integration() {
    print_header "Testing Nautilus Integration" 
    
    NAUTILUS_SCRIPT="$HOME/.local/share/nautilus/scripts/Convert with File Converter" 
    
    print_test "Nautilus scripts directory exists" 
    if [ -d "$HOME/.local/share/nautilus/scripts" ]; then 
        print_pass
    else
        print_fail "Directory not found" 
    fi
    
    print_test "Nautilus script exists" 
    if [ -f "$NAUTILUS_SCRIPT" ]; then 
        print_pass
    else
        print_fail "Script not found" 
    fi
    
    print_test "Nautilus script is executable" 
    if [ -x "$NAUTILUS_SCRIPT" ]; then 
        print_pass
    else
        print_fail "Script is not executable" 
    fi
    
    print_test "Nautilus script syntax" 
    if bash -n "$NAUTILUS_SCRIPT" 2>/dev/null; then 
        print_pass
    else
        print_fail "Syntax errors in script" 
    fi
    
    print_test "Nautilus is available"
    if command -v nautilus >/dev/null 2>&1; then
        print_pass
    else
        print_skip "Nautilus not installed"
        TESTS_RUN=$((TESTS_RUN - 1))
    fi

    NAUTILUS_EXT_LINK="$HOME/.local/share/nautilus-python/extensions/file_converter_extension.py"

    print_test "Nautilus submenu extension symlink"
    if [ -L "$NAUTILUS_EXT_LINK" ] && [ -e "$NAUTILUS_EXT_LINK" ]; then
        print_pass
    else
        print_fail "Extension not symlinked into ~/.local/share/nautilus-python/extensions/"
    fi

    print_test "Nautilus Python bindings importable"
    if python3 -c "import gi; gi.require_version('Nautilus','4.0')" 2>/dev/null \
       || python3 -c "import gi; gi.require_version('Nautilus','3.0')" 2>/dev/null; then
        print_pass
    else
        print_fail "python3-nautilus not installed"
    fi
}

test_desktop_entry() {
    print_header "Testing Desktop Entry" 
    
    DESKTOP_ENTRY="$HOME/.local/share/applications/file-converter.desktop" 
    
    print_test "Applications directory exists" 
    if [ -d "$HOME/.local/share/applications" ]; then 
        print_pass
    else
        print_fail "Directory not found" 
    fi
    
    print_test "Desktop entry file exists" 
    if [ -f "$DESKTOP_ENTRY" ]; then 
        print_pass
    else
        print_fail "Desktop entry not found" 
    fi
    
    print_test "Desktop entry syntax" 
    if grep -q "^\[Desktop Entry\]" "$DESKTOP_ENTRY" 2>/dev/null; then 
        print_pass
    else
        print_fail "Invalid desktop entry format" 
    fi
    
    print_test "Desktop entry has required fields" 
    local required_fields=("Name=" "Exec=" "Type=Application") 
    local all_present=true 
    
    for field in "${required_fields[@]}"; do
        if ! grep -q "^$field" "$DESKTOP_ENTRY" 2>/dev/null; then 
            all_present=false 
            break
        fi
    done
    
    if [ "$all_present" = true ]; then 
        print_pass
    else
        print_fail "Missing required fields" 
    fi
    
    print_test "Desktop entry references correct File Converter path" 
    if grep -q "$FILE_CONVERTER_SCRIPT" "$DESKTOP_ENTRY" 2>/dev/null; then 
        print_pass
    else
        print_fail "Incorrect File Converter path in desktop entry" 
    fi
} 

test_command_line_access() {
    print_header "Testing Command Line Access" 
    
    FILE_CONVERTER_LINK="$HOME/.local/bin/file-converter" 
    
    print_test "Local bin directory exists" 
    if [ -d "$HOME/.local/bin" ]; then 
        print_pass
    else
        print_fail "Directory not found" 
    fi
    
    print_test "File Converter command link exists" 
    if [ -L "$FILE_CONVERTER_LINK" ]; then 
        print_pass
    else
        print_fail "Symbolic link not found" 
    fi
    
    print_test "File Converter command link is valid" 
    if [ -L "$FILE_CONVERTER_LINK" ] && [ -f "$(readlink "$FILE_CONVERTER_LINK")" ]; then 
        print_pass
    else
        print_fail "Symbolic link is broken" 
    fi
    
    print_test "~/.local/bin is in PATH" 
    if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then 
        print_pass
    else
        print_fail "~/.local/bin not in PATH (may require terminal restart)" 
    fi
    
    print_test "File Converter command resolves"
    if command -v file-converter >/dev/null 2>&1; then
        print_pass
    else
        print_skip "Command not accessible (PATH issue or requires restart)"
        TESTS_RUN=$((TESTS_RUN - 1))
    fi
} 

test_dependencies() {
    print_header "Testing GUI Dependencies" 
    
    print_test "Terminal emulator available" 
    if command -v gnome-terminal >/dev/null 2>&1 || command -v xterm >/dev/null 2>&1; then 
        print_pass
    else
        print_fail "No suitable terminal emulator found" 
    fi
    
    print_test "Zenity available for dialogs" 
    if command -v zenity >/dev/null 2>&1; then 
        print_pass
    else
        print_fail "Zenity not installed" 
    fi
    
    print_test "Python 3 available" 
    if command -v python3 >/dev/null 2>&1; then 
        print_pass
    else
        print_fail "Python 3 not found" 
    fi
    
    print_test "File Converter dependencies (pandoc, libreoffice, ffmpeg)" 
    local deps_ok=true 
    
    if ! command -v pandoc >/dev/null 2>&1; then 
        deps_ok=false 
    fi
    
    if ! command -v libreoffice >/dev/null 2>&1; then 
        deps_ok=false 
    fi
    
    if ! command -v ffmpeg >/dev/null 2>&1; then 
        deps_ok=false 
    fi
    
    if [ "$deps_ok" = true ]; then 
        print_pass
    else
        print_fail "Missing pandoc, libreoffice, or ffmpeg" 
    fi
} 

test_file_associations() {
    print_header "Testing File Associations" 
    
    MIMEAPPS_FILE="$HOME/.config/mimeapps.list" 
    
    print_test "mimeapps.list exists" 
    if [ -f "$MIMEAPPS_FILE" ]; then 
        print_pass
    else
        print_fail "File not found" 
    fi
    
    print_test "File Converter associations present" 
    if [ -f "$MIMEAPPS_FILE" ] && grep -q "file-converter.desktop" "$MIMEAPPS_FILE" 2>/dev/null; then 
        print_pass
    else
        print_fail "File Converter associations not found" 
    fi
} 

create_test_files() {
    print_header "Creating Test Files" 
    
    # Create temporary test directory
    TEST_DIR="/tmp/cmda_gui_test_$$" 
    mkdir -p "$TEST_DIR" 
    
    # Create test markdown file
    cat > "$TEST_DIR/test.md" << 'EOF'
# Test Document

This is a test markdown file for CMDA GUI integration testing.

## Features
- **Bold text**
- *Italic text*
- `Code`

This should convert to various formats.
EOF
    
    # Create test text file
    echo "This is a simple text file for testing CMDA GUI integration." > "$TEST_DIR/test.txt" 
    
    echo "Created test files in: $TEST_DIR"
} 

cleanup_test_files() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then 
        rm -rf "$TEST_DIR" 
        echo "Cleaned up test files"
    fi
} 

# Test CMDA with test file (interactive test)
test_interactive() {
    print_header "Interactive Test (Optional)" 
    
    echo "Would you like to run an interactive test? (y/N): "
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then 
        create_test_files
        
        print_test "Interactive file conversion test" 
        echo
        echo "A file manager window will open. Please:"
        echo "1. Navigate to $TEST_DIR"
        echo "2. Right-click on test.md"
        echo "3. Select Scripts → Convert with File Converter"
        echo "4. Follow the conversion process"
        echo
        echo "Press Enter when ready to start the test..."
        read
        
        if command -v nautilus >/dev/null 2>&1; then 
            nautilus "$TEST_DIR" &
            echo "File manager opened. Please test the right-click menu."
            echo "Press Enter when you've completed the test..."
            read
            print_pass
        else
            print_skip "Nautilus not available" 
            TESTS_RUN=$((TESTS_RUN - 1)) 
        fi
        
        cleanup_test_files
    else
        print_skip "Interactive test skipped by user" 
    fi
} 

# Main test runner
main() {
    echo "File Converter GUI Integration Test Suite"
    echo "=========================================="
    echo
    
    # Run test suites
    test_file_converter_script || {
        echo -e "\n${RED}Critical: File Converter script issues detected. Cannot continue.${NC}"
        exit 1
    } 
    
    test_dependencies
    test_nautilus_integration
    test_desktop_entry
    test_command_line_access
    test_file_associations
    
    # Optional interactive test
    test_interactive
    
    # Summary
    print_header "Test Summary" 
    echo "Tests run: $TESTS_RUN" 
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}" 
    if [ $TESTS_FAILED -gt 0 ]; then 
        echo -e "Failed: ${RED}$TESTS_FAILED${NC}" 
    else
        echo -e "Failed: $TESTS_FAILED" 
    fi
    echo
    
    # Calculate success rate
    if [ $TESTS_RUN -gt 0 ]; then 
        SUCCESS_RATE=$((TESTS_PASSED * 100 / TESTS_RUN)) 
        echo "Success rate: $SUCCESS_RATE%"
        
        if [ $SUCCESS_RATE -ge 90 ]; then 
            echo -e "\n${GREEN}✓ File Converter GUI integration is working correctly!${NC}"
            echo "You can now:"
            echo " • Right-click files in Nautilus to convert with File Converter"
            echo " • Find File Converter in your application menu"
            echo " • Use 'file-converter' command in terminal"
            exit_code=0
        elif [ $SUCCESS_RATE -ge 70 ]; then 
            echo -e "\n${YELLOW}⚠ File Converter GUI integration has some issues but basic functionality works${NC}"
            echo "Check the failed tests above for details."
            exit_code=1
        else
            echo -e "\n${RED}✗ File Converter GUI integration has significant issues${NC}"
            echo "Please check the installation and try running the setup script again."
            exit_code=2
        fi
    else
        echo -e "\n${RED}✗ No tests could be run${NC}"
        exit_code=3
    fi
    
    exit $exit_code
} 

# Handle script interruption
trap cleanup_test_files EXIT INT TERM 

# Show usage if requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then 
    echo "File Converter GUI Integration Test Script"
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --no-interactive  Skip interactive tests"
    echo
    echo "This script tests all aspects of File Converter GUI integration including:"
    echo "  • File Converter script functionality"
    echo "  • Nautilus right-click integration"
    echo "  • Desktop application entry"
    echo "  • Command-line access"
    echo "  • File associations"
    echo "  • Required dependencies"
    exit 0
fi

# Run main function
main "$@"
