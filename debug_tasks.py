import sys
import os
import app
app.init_system()
print("app._task_snapshot() =>", app._task_snapshot()["task_count"])
