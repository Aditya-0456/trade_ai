import os

output_file = "full_project.txt"
project_dir = os.getcwd()

with open(output_file, "w", encoding="utf-8") as outfile:
    
    # 🔹 Folder Structure
    outfile.write("===== PROJECT STRUCTURE =====\n\n")
    
    for root, dirs, files in os.walk(project_dir):
        level = root.replace(project_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        outfile.write(f"{indent}{os.path.basename(root)}/\n")
        
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            if file == "nsc.csv":
                continue
            outfile.write(f"{subindent}{file}\n")
    
    outfile.write("\n\n===== FILE CONTENTS =====\n\n")
    
    # 🔹 File Contents
    for root, dirs, files in os.walk(project_dir):
        for file in files:
            
            # ✅ SKIP ONLY THIS FILE
            if file == "NSE.csv":
                continue
            
            filepath = os.path.join(root, file)
            
            outfile.write(f"\n===== {filepath} =====\n")
            
            try:
                with open(filepath, "rb") as infile:
                    content = infile.read()
                    
                    try:
                        text = content.decode("utf-8")
                    except:
                        text = "[BINARY FILE - CONTENT NOT READABLE]"
                    
                    outfile.write(text)
            
            except Exception as e:
                outfile.write(f"[ERROR: {e}]")
            
            outfile.write("\n\n")