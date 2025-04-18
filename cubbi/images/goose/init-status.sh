#!/bin/bash
# Script to check and display initialization status

# Only proceed if running as root
if [ "$(id -u)" != "0" ]; then
    exit 0
fi

# Quick check instead of full logic
if ! grep -q "INIT_COMPLETE=true" "/init.status" 2>/dev/null; then
    # Only follow logs if initialization is incomplete
    if [ -f "/init.log" ]; then
        echo "----------------------------------------"
        tail -f /init.log &
        tail_pid=$!

        # Check every second if initialization has completed
        while true; do
            if grep -q "INIT_COMPLETE=true" "/init.status" 2>/dev/null; then
                kill $tail_pid 2>/dev/null
                echo "----------------------------------------"
                break
            fi
            sleep 1
        done
    else
        echo "No initialization logs found."
    fi
fi

exec gosu cubbi /bin/bash -il
