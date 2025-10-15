#!/bin/zsh
echo "Running in: $0"
echo "Current shell: $SHELL"
echo "Detected shell process: $(ps -p $$ -o comm=)"
