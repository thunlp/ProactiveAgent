#!/bin/bash

cd "$(dirname "$0")"

# Define the location of the log folder
trace_folder="traces_new"

save_folder="judged"

# Create the judged folder if it doesn't exist
mkdir -p "$save_folder"

# Use the find command to recursively find all .json files in the log folder
find "$trace_folder" -type f -name "*.json" | while read json_file; do
    # Get the relative path of the json file
    relative_path="${json_file#$trace_folder/}"

    # Create the corresponding directory structure in the judged folder
    mkdir -p "$save_folder/$(dirname "$relative_path")"

    # Get the destination file path
    destination_file="$save_folder/$relative_path"

    # Check if the destination file already exists
    if [ -e "$destination_file" ]; then
        echo "Warning: File $destination_file already exists. Skipping..."
        continue
    fi

    # Execute the Python script and pass the json file path as a parameter
    python judge_agent_prediction.py "$json_file" -o "$destination_file"
done