call pkg -t node16 ..\src\TMGib.js -o dist/TMGib.exe
call pkg -t node16 ..\src\TMMediator.js -o dist/TMMediator.exe
python -m PyInstaller TMPbn2LinVG.spec 
python -m PyInstaller MergePBNFiles.spec
python -m PyInstaller CountPBNBoards.spec
python -m PyInstaller TMPbn2Cleaner.spec
python -m PyInstaller TMPbn2DDS.spec 
python -m PyInstaller comparematchpbnashtml.spec
python -m PyInstaller listmatchpbnashtml.spec
python -m PyInstaller printmatchpbnashtml.spec
python -m PyInstaller CalculateMatch.spec
python -m PyInstaller ResetAndRenumberPBNBoards.spec
python -m PyInstaller PBN2LinUI.spec
python -m PyInstaller PBN2Lin.spec
python -m PyInstaller Split_PBN.spec