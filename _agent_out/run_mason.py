"""Run mason doctor + three scrap builds; write JSON under _agent_out."""
import json
import os
import subprocess
import sys

ROOT = r"c:\Users\edgar\Documents\Unveil\mason"
OUT = os.path.join(ROOT, "_agent_out")
MASON = os.path.join(ROOT, ".venv", "Scripts", "mason.exe")
os.makedirs(OUT, exist_ok=True)

jobs = [
    ("doctor", [MASON, "doctor", "--json"]),
    ("scrap_tag", [MASON, "build", "examples/assets/scrap_tag.yaml", "--json"]),
    ("scrap_tag_q", [MASON, "build", "examples/assets/scrap_tag_q.yaml", "--json"]),
    ("scrap_icon", [MASON, "build", "examples/assets/scrap_icon.yaml", "--json"]),
]


def write(name, text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


write("_runner_started.txt", "started\n")

for name, argv in jobs:
    marker = os.path.join(OUT, f"{name}.running.txt")
    write(f"{name}.running.txt", "running\n")
    try:
        proc = subprocess.run(
            argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        write(f"{name}.stdout.json", "")
        write(f"{name}.stderr.txt", str(exc))
        write(f"{name}.exit.txt", "launch_error\n")
        write(f"{name}.done.txt", f"error:{exc}\n")
        continue
    write(f"{name}.stdout.json", proc.stdout or "")
    write(f"{name}.stderr.txt", proc.stderr or "")
    write(f"{name}.exit.txt", f"{proc.returncode}\n")
    write(f"{name}.done.txt", f"exit={proc.returncode}\n")
    if name != "doctor" and proc.returncode != 0:
        # Stop later builds if one fails; still record the failure.
        remaining = [j[0] for j in jobs if j[0] not in (
            "doctor", name
        ) and not os.path.exists(os.path.join(OUT, f"{j[0]}.done.txt"))]
        write("_stopped.txt", f"stopped after {name}: {remaining}\n")
        break

write("_runner_done.txt", "done\n")
print("runner_done")
