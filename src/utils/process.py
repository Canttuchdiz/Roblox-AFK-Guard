from __future__ import annotations

import psutil


def kill_pid(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    try:
        proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    try:
        proc.wait(timeout=2)
    except psutil.TimeoutExpired:
        pass
    return True
