import asyncio
import json
import logging
from pprint import pprint
import sys
import os

# Put app directory in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import _task_snapshot, init_atlas, config_manager, agent

def test():
    init_atlas()
    snap = _task_snapshot()
    print("TASK COUNT:", snap.get("task_count"))
    print("TASKS LENGTH:", len(snap.get("tasks", [])))
    if snap.get("tasks"):
        print("FIRST TASK:", snap["tasks"][0])
    
if __name__ == "__main__":
    test()
