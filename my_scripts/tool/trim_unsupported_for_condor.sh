#!/bin/bash

# Directory specified as the first argument to the script
DIRECTORY=$1

# Check if the directory exists
if [ ! -d "$DIRECTORY" ]; then
    echo "Directory does not exist: $DIRECTORY"
    exit 1
fi

# Loop through each file in the directory
for file in "$DIRECTORY"/*; do
    # Check if it's a regular file
    if [ -f "$file" ]; then
        # Replace the string in the file
        sed -i 's/from loguru import logger//g' "$file"
        sed -i 's/logger.error/print/g' "$file"
        sed -i 's/logger.warning/print/g' "$file"
        sed -i 's/logger.info/print/g' "$file"
        sed -i 's/nohup time /nohup /g' "$file"
        

        echo "Processed: $file"
    fi
done

echo "All files in $1 processed."
