Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.OpenTextFile("D:\MaxFlash\dashboard.log", 2, True)
logFile.WriteLine "MaxFlash Dashboard started at " & Now()
logFile.Close

WshShell.Run "cmd /c cd /d D:\MaxFlash\web_interface && C:\Users\LERA\AppData\Local\Programs\Python\Python314\pythonw.exe app_simple.py >> D:\MaxFlash\dashboard.log 2>&1", 0, False
Set WshShell = Nothing
Set fso = Nothing
