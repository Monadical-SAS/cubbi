#!/bin/bash
# Script to check and display initialization status

# Function to display initialization logs
show_init_logs() {
    if [ -f "/init.log" ]; then
        echo "Displaying initialization logs:"
        echo "----------------------------------------"
        cat /init.log
        echo "----------------------------------------"
    else
        echo "No initialization logs found."
    fi
}

# Function to follow logs until initialization completes
follow_init_logs() {
    if [ ! -f "/init.log" ]; then
        echo "No initialization logs found."
        return
    fi

    echo "Initialization is still in progress. Showing logs:"
    echo "----------------------------------------"
    tail -f /init.log &
    tail_pid=$!

    # Check every second if initialization has completed
    while true; do
        if [ -f "/init.status" ] && grep -q "INIT_COMPLETE=true" "/init.status"; then
            kill $tail_pid 2>/dev/null
            echo "----------------------------------------"
            echo "Initialization completed."
            break
        fi
        sleep 1
    done
}

# Check if we're in an interactive shell
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

# Check initialization status
if [ -f "/init.status" ]; then
    if grep -q "INIT_COMPLETE=true" "/init.status"; then
        echo "MC initialization has completed."
        # No longer prompt to show logs when initialization is complete
    else
        echo "MC initialization is still in progress."
        follow_init_logs
    fi
else
    echo "Cannot determine initialization status."
    # Ask if user wants to see logs if they exist (only in interactive mode)
    if [ -f "/init.log" ] && [ "$INTERACTIVE" = true ]; then
        read -p "Do you want to see initialization logs? (y/n): " show_logs
        if [[ "$show_logs" =~ ^[Yy] ]]; then
            show_init_logs
        fi
    fi
fi