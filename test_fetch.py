import urllib.request
import time
import subprocess
import sys

proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", "5006"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(4)
try:
    req = urllib.request.Request("http://localhost:5006/api/tasks")
    with urllib.request.urlopen(req) as response:
        print("HTTP", response.status)
        data = response.read()
        print("Length:", len(data))
        print("Data preview:", data[:200])
except Exception as e:
    print("Error:", e)
finally:
    proc.terminate()
    out, _ = proc.communicate()
    print("Server output:")
    print(out.decode('utf-8'))
