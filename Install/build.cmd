@echo off
setlocal

REM ===========================================================================
REM Build all Bridge-Robot-Utilities executables.
REM
REM The Python executables are built inside a dedicated virtual environment so
REM that PyInstaller only bundles the packages the utilities actually need.
REM Building against a polluted global Python pulls in scipy/pandas/Jupyter/etc.
REM and bloats every executable to ~99 MB.
REM ===========================================================================

set VENV=.buildenv

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating clean build environment in %VENV% ...
    python -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"

echo Installing build dependencies ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install build dependencies.
    exit /b 1
)

REM --- Node.js utilities (use globally installed pkg) ---
call pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
call pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
call pkg -t node16 ..\src\ExtractLinks.js -o dist/ExtractLinks.exe

REM --- Python utilities ---
python -m PyInstaller TMPbn2LinVG.spec
python -m PyInstaller MergePBNFiles.spec
python -m PyInstaller CountPBNBoards.spec
python -m PyInstaller TMPbn2Cleaner.spec
python -m PyInstaller TMPbn2DDS.spec
python -m PyInstaller comparematchpbnashtml.spec
python -m PyInstaller printmatchpbnashtml.spec
python -m PyInstaller CalculateMatch.spec
python -m PyInstaller RenumberPBNBoards.spec
python -m PyInstaller PBN2LinUI.spec
python -m PyInstaller PBN2Lin.spec
python -m PyInstaller Lin2PBNUI.spec
python -m PyInstaller LIN2PBN.spec
python -m PyInstaller Split_PBN.spec
python -m PyInstaller csvlin2pbn.spec
python -m PyInstaller ExtractDatumScore.spec
python -m PyInstaller PbnExtractBoards.spec
python -m PyInstaller listmatchpbnashtml.spec
python -m PyInstaller comparerobots.spec
