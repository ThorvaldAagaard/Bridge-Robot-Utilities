@echo off
cls
echo.
echo To create a ZRD file of up to 10,485,760 Random Solved Deals
echo enter the number of blocks desired (64K deals each):
echo.
echo 1 = 64K   2 = 128K ...  16 = 1M   32 = 2M ...  160 = 10M (all)
echo.
set /P N="Number of 64K blocks (1-160): "
echo.
if %N% LSS 1 goto 2
if %N% GTR 160 goto 2
echo File rpdd.zrd will be created with %N% blocks of 64K deals
echo.
choice /C YN /N /M "Build it now? Y/N "
echo.
if errorlevel 2 goto 2
xrsd %N%
echo.
echo.
if errorlevel 1 goto 2
echo Done! File rpdd.zrd contains %N% blocks of 64K deals each
goto end

:1
echo File access error (rpdd.zdd missing or other)

:2
echo Nothing done

:end
echo.
pause

