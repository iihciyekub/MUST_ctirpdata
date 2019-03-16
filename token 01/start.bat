tasklist /nh|find /i "python.exe"
if ERRORLEVEL 1 (echo ²»´æÔÚ) else taskkill /im python.exe /f
python domain.py