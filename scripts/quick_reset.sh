#!/bin/bash
# Quick reset script for testing
# Usage: ./scripts/quick_reset.sh

echo "🗑️  Quick Database Reset"
echo "======================================"
echo ""

# Run reset with automatic YES for both prompts
# First YES for confirmation, then 'y' for sequence reset
(echo "YES"; echo "y") | python scripts/reset_database.py

echo ""
echo "✅ Reset complete! Ready for testing."
echo ""
echo "Quick test commands:"
echo "  python scripts/fetch_yts_data.py --max-pages 5"
echo "  python scripts/monitor_progress.py"
echo ""

