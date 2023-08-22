start "South" /D . TMGib.exe -s South -n GIBNS -p 2002  -t 10
start "North" /D . TMGib.exe -s North -n GIBNS -p 2000 -t 10
start "West" /D . TMGib.exe -s West -n GIBEW -p 2003 -t 10
start "East" /D . TMGib.exe -s East -n GIBEW -p 2001 -t 10

:: We will replay the 4 boards with switched seats

start "South" /D . TMGib.exe -s South -n GIBEW -p 2002 -t 10
start "North" /D . TMGib.exe -s North -n GIBEW -p 2000 -t 10
start "West" /D . TMGib.exe -s West -n GIBNS -p 2003 -t 10
start "East" /D . TMGib.exe -s East -n GIBNS -p 2001 -t 10


:: Translate rpt-file using cscript TextConvert.wsf

:: Use TMPbn2Lin.exe to create a .lin file withthe result