#!/bin/bash

# Find all large files (>100MB) in the entire repository history
git rev-list --all --objects | \
    awk '{print $1}' | \
    git cat-file --batch-check | \
    grep ' blob ' | \
    awk '$3 > 100*1024*1024 {print $1,$3}' | \
    sort -k2 -n > large_files.txt

# Alternative that shows file paths (slower but more informative)
git rev-list --all --objects | \
    while read sha1 fname; do 
        size=$(git cat-file -s "$sha1" 2>/dev/null) || continue
        if [ "$size" -gt $((100*1024*1024)) ]; then
            echo "$size $sha1 $fname"
        fi
    done | sort -n > large_files_with_paths.txt


    
while read size sha1 fname; do
    # Escape special characters in filename for regex
    pattern=$(echo "$fname" | sed 's/[]\/$*.^[]/\\&/g')
    echo "$pattern filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
done < large_files_with_paths.txt

cat large_files_with_paths.txt | awk '{print $3}' | xargs git lfs migrate import --everything --include=
    
