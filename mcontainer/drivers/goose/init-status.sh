#!/bin/bash
# Script to check and display initialization status - optimized version

# Quick check instead of full logic
if grep -q "INIT_COMPLETE=true" "/init.status" 2>/dev/null; then
    echo "MC initialization has completed."
else
    echo "MC initialization is still in progress."
    # Only follow logs if initialization is incomplete
    if [ -f "/init.log" ]; then
        echo "Initialization is still in progress. Showing logs:"
        echo "----------------------------------------"
        tail -f /init.log &
        tail_pid=$!
        
        # Check every second if initialization has completed
        while true; do
            if grep -q "INIT_COMPLETE=true" "/init.status" 2>/dev/null; then
                kill $tail_pid 2>/dev/null
                echo "----------------------------------------"
                echo "Initialization completed."
                break
            fi
            sleep 1
        done
    else
        echo "No initialization logs found."
    fi
fi