import os

output_file = "project.txt"
project_dir = "."

# Folders to skip
skip_folders = ["venv", "node_modules", ".git", "__pycache__"]

with open(output_file, "w", encoding="utf-8") as outfile:
    for root, dirs, files in os.walk(project_dir):
        
        # Skip unwanted folders
        dirs[:] = [d for d in dirs if d not in skip_folders]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            try:
                outfile.write(f"===== {filepath} =====\n")
                
                with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                    outfile.write(infile.read())
                
                outfile.write("\n\n")
            
            except Exception as e:
                outfile.write(f"[Error reading file: {e}]\n\n")