pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
PyInstaller TMPbn2LinVG.spec
PyInstaller MergePBNFiles.spec
PyInstaller CountPBNBoards.spec