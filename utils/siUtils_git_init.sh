#!/bin/zsh

# check if .git directory exists and initialize if not found
if [ ! -d ".git" ]; then
    echo "Git not initialized. Running git init..."
    git init
else
    echo "Git already initialized."
fi

# copyright 2025 Quality Measurement Group: si-software-lab

