#!/bin/bash

# change work dir
cd "$(dirname "$0")"

# Define the location of the log folder
save_folder="judged"

find "$save_folder" -mindepth 1 -type d | while read -r folder; do
    echo "Processing $folder..."
    python calculate_agent_performance.py "$folder"
done
    