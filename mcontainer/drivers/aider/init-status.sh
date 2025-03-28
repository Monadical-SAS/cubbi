#!/bin/bash

# Script to check the initialization status of the Aider container

if [ -f "/init.status" ]; then
    source /init.status
    if [ "$INIT_COMPLETE" = "true" ]; then
        echo "Initialization complete."
        exit 0
    else
        if [ -n "$INIT_ERROR" ]; then
            echo "Initialization failed: $INIT_ERROR"
        else
            echo "Initialization in progress..."
        fi
        exit 1
    fi
else
    echo "Initialization has not started yet."
    exit 1
fi