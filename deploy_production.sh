#!/bin/bash

# Deploy script for Raspberry Pi 5
# Pulls latest from production branch, runs install script, and starts monitoring service

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository. Please run this script from your project directory."
    exit 1
fi

# Check if install_script.sh exists
if [ ! -f "install_script.sh" ]; then
    print_error "install_script.sh not found in current directory."
    exit 1
fi

print_status "Starting deployment process..."

# Fetch latest changes from remote
print_status "Fetching latest changes from remote..."
if ! git fetch origin; then
    print_error "Failed to fetch from remote repository."
    exit 1
fi

# Check if production branch exists
if ! git show-ref --verify --quiet refs/heads/production; then
    # Check if production branch exists on remote
    if git show-ref --verify --quiet refs/remotes/origin/production; then
        print_status "Production branch not found locally, creating from origin/production..."
        git checkout -b production origin/production
        NEW_COMMITS=true
    else
        print_error "Production branch does not exist locally or on remote."
        exit 1
    fi
else
    # Switch to production branch
    print_status "Switching to production branch..."
    if ! git checkout production; then
        print_error "Failed to checkout production branch."
        exit 1
    fi
    
    # Get current local commit hash
    LOCAL_COMMIT=$(git rev-parse HEAD)
    print_status "Current local commit: ${LOCAL_COMMIT:0:8}"
    
    # Get remote commit hash
    REMOTE_COMMIT=$(git rev-parse origin/production)
    print_status "Current remote commit: ${REMOTE_COMMIT:0:8}"
    
    # Compare commits
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        print_status "Already up to date. No new commits found."
        print_status "Skipping deployment. ✅"
    else
        print_status "New commits detected!"
        NEW_COMMITS=true
    fi
fi

# Pull latest changes only if there are new commits
if [ "$NEW_COMMITS" = true ]; then
    print_status "Pulling latest changes from production branch..."
    if ! git pull origin production; then
        print_error "Failed to pull latest changes from production branch."
        exit 1
    fi

    # Show current commit info
    print_status "Updated to commit: $(git log -1 --pretty=format:'%h - %s (%an, %ar)')"

    # Make install script executable
    print_status "Making install_script.sh executable..."
    chmod +x install_script.sh

    # Execute install script
    print_status "Executing install_script.sh..."
    if ./install_script.sh; then
        print_status "Deployment completed successfully!"
    else
        print_error "install_script.sh failed with exit code $?"
        exit 1
    fi

    print_status "All done! 🎉"
fi

# Step 2: Start monitoring service
print_status "Starting monitoring service..."

# Check if monitoring script exists
MONITOR_SCRIPT="./exam_monitor/start_monitor_web.sh"
if [ ! -f "$MONITOR_SCRIPT" ]; then
    print_error "Monitoring script not found: $MONITOR_SCRIPT"
    exit 1
fi

# Make monitoring script executable
print_status "Making start_monitor_web.sh executable..."
chmod +x "$MONITOR_SCRIPT"

# Change to the exam_monitor directory and run the script
print_status "Changing to /exam_monitor directory..."
cd ./exam_monitor || {
    print_error "Failed to change to /exam_monitor directory"
    exit 1
}

print_status "Executing start_monitor_web.sh..."
if ./start_monitor_web.sh; then
    print_status "Monitoring service started successfully!"
else
    print_error "Failed to start monitoring service (exit code: $?)"
    exit 1
fi

print_status "🚀 Complete! Deployment and monitoring service are both running!"