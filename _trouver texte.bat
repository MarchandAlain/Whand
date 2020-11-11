echo off
set target="masterto"
echo _______ on trouve %target% dans:
echo .
findstr /M %target% *.py
findstr /M %target% ..\whand_V2_7.py
echo .
pause