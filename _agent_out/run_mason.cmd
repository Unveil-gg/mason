@echo off
cd /d c:\Users\edgar\Documents\Unveil\mason
".venv\Scripts\python.exe" "c:\Users\edgar\Documents\Unveil\mason\_agent_out\run_mason.py" > "c:\Users\edgar\Documents\Unveil\mason\_agent_out\runner_console.txt" 2>&1
echo EXIT=%ERRORLEVEL%> "c:\Users\edgar\Documents\Unveil\mason\_agent_out\runner_exit.txt"
