import os
import re

directory = r"C:\ProjectAI\chess_academy\frontend\src"

replacements = {
    r"bg-gradient-to-r": "bg-linear-to-r",
    r"bg-gradient-to-l": "bg-linear-to-l",
    r"bg-gradient-to-t": "bg-linear-to-t",
    r"bg-gradient-to-b": "bg-linear-to-b",
    r"bg-gradient-to-tr": "bg-linear-to-tr",
    r"bg-gradient-to-tl": "bg-linear-to-tl",
    r"bg-gradient-to-br": "bg-linear-to-br",
    r"bg-gradient-to-bl": "bg-linear-to-bl",
    r"flex-grow": "grow",
    r"flex-shrink-0": "shrink-0",
    r"max-w-\[80px\]": "max-w-20",
    r"max-w-\[500px\]": "max-w-125",
    r"min-w-\[260px\]": "min-w-65",
    r"max-w-\[180px\]": "max-w-45",
    r"min-h-\[64px\]": "min-h-16",
    r"-top-\[20%\]": "top-[-20%]",
    r"-left-\[10%\]": "left-[-10%]",
    r"-right-\[10%\]": "right-[-10%]",
    r"-bottom-\[20%\]": "bottom-[-20%]"
}

for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename.endswith(".tsx") or filename.endswith(".ts"):
            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = re.sub(old, new, new_content)
                
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
