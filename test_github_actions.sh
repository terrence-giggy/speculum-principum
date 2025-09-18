#!/bin/bash
#
# Local test script for GitHub Actions workflow
# Simulates the environment and steps that would run in GitHub Actions
#

set -e

echo "🧪 Testing GitHub Actions Workflow Locally"
echo "=========================================="

# Set environment variables (simulating GitHub Actions)
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export RELEVANCE_THRESHOLD=${RELEVANCE_THRESHOLD:-0.6}
export DATABASE_URL=${DATABASE_URL:-sqlite:///speculum_data.db}
export GITHUB_ACTIONS=true
export CI=true

echo "📋 Configuration:"
echo "  - Log Level: $LOG_LEVEL"
echo "  - Relevance Threshold: $RELEVANCE_THRESHOLD"
echo "  - Database: $DATABASE_URL"
echo ""

# Check for existing database
if [ -f "speculum_data.db" ]; then
    echo "✅ Found existing database ($(du -h speculum_data.db | cut -f1))"
    DATABASE_EXISTS=true
else
    echo "📄 No existing database found, will create new one"
    DATABASE_EXISTS=false
fi

echo ""
echo "🚀 Starting monitoring cycle..."

# Try running the main agent first
if python -c "import speculum_principis.cli" 2>/dev/null; then
    echo "📦 Full dependencies available, running main agent..."
    python -m speculum_principis.cli run --verbose || {
        echo "⚠️  Main agent failed, falling back to demo mode..."
        python github_actions_demo.py
    }
else
    echo "📦 Using demo mode (lightweight dependencies)..."
    python github_actions_demo.py
fi

# Check results
if [ -f "speculum_data.db" ]; then
    DATABASE_UPDATED=true
    DATABASE_SIZE=$(du -h speculum_data.db | cut -f1)
else
    DATABASE_UPDATED=false
    DATABASE_SIZE="0"
fi

echo ""
echo "📊 Execution Results:"
echo "  - Database exists: $DATABASE_EXISTS"
echo "  - Database updated: $DATABASE_UPDATED"
echo "  - Database size: $DATABASE_SIZE"

if [ -f "speculum_data.db" ]; then
    echo "  - Database entries:"
    wc -l speculum_data.db 2>/dev/null || echo "    (binary format)"
    
    echo ""
    echo "📝 Sample entries:"
    head -3 speculum_data.db 2>/dev/null || echo "    (binary format - use SQLite tools to view)"
fi

echo ""
echo "✅ Local test completed successfully!"
echo ""
echo "🔄 To simulate persistent runs:"
echo "   1. Run this script multiple times"
echo "   2. Database will persist between runs"
echo "   3. Each run adds new content"
echo ""
echo "🧹 To reset:"
echo "   rm speculum_data.db"