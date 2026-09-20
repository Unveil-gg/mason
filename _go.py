import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
mason = root / ".venv" / "Scripts" / "mason.exe"
out = root / ".mason" / "_build_btn.json"
err = root / ".mason" / "_build_btn.err"
pid_path = root / ".mason" / "_build_pid.txt"
proc = subprocess.Popen(
    [
        str(mason),
        "build",
        "examples/assets/button_down_shirt.yaml",
        "--json",
    ],
    cwd=str(root),
    stdout=out.open("w", encoding="utf-8"),
    stderr=err.open("w", encoding="utf-8"),
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
pid_path.write_text(str(proc.pid), encoding="utf-8")
print(f"pid={proc.pid}")
