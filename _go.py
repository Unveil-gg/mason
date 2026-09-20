import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
mason = root / ".venv" / "Scripts" / "mason.exe"
out = root / ".mason" / "_build_fitted.json"
err = root / ".mason" / "_build_fitted.err"
pid_path = root / ".mason" / "_build_pid.txt"
out.write_text("", encoding="utf-8")
err.write_text("", encoding="utf-8")
proc = subprocess.Popen(
    [str(mason), "build", "examples/assets/fitted_shirt.yaml", "--json"],
    cwd=str(root),
    stdout=out.open("w", encoding="utf-8"),
    stderr=err.open("w", encoding="utf-8"),
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
pid_path.write_text(str(proc.pid), encoding="utf-8")
