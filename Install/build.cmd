call pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
call pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
PyInstaller TMPbn2LinVG.spec
PyInstaller MergePBNFiles.spec
PyInstaller CountPBNBoards.spec
PyInstaller TMPbn2Cleaner.spec
PyInstaller TMPbn2DDS.spec
