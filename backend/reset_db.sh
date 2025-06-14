#!/bin/bash
# Database Reset Script Wrapper

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}Relevia Database Reset Tool${NC}"
echo -e "${YELLOW}================================${NC}"

# Check if we're in the backend directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory${NC}"
    echo "Please cd to the backend directory and try again."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "It's recommended to activate your virtual environment first."
    echo ""
fi

# Find python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found${NC}"
    echo "Please ensure Python is installed and in your PATH"
    exit 1
fi

echo -e "Using Python: ${GREEN}$PYTHON_CMD${NC}"

# Run the reset script
if [ "$1" == "--force" ]; then
    echo -e "${RED}Force mode enabled - skipping confirmation${NC}"
    $PYTHON_CMD reset_database.py --force
else
    $PYTHON_CMD reset_database.py
fi

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Database reset completed successfully!${NC}"
    echo -e "${GREEN}You can now start the server with: python main.py${NC}"
else
    echo -e "\n${RED}❌ Database reset failed!${NC}"
    echo -e "${RED}Check the error messages above for details.${NC}"
    exit 1
fi