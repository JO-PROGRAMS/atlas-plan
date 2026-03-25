import json

with open('session_history.jsonl', 'r') as f:
    for line in f:
        if 'patch_glass.py' in line:
            try:
                data = json.loads(line)
                def find_text(d):
                    if isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, str) and 'patch_glass.py' in v:
                                print(v)
                            find_text(v)
                    elif isinstance(d, list):
                        for i in d:
                            find_text(i)
                find_text(data)
            except:
                pass
