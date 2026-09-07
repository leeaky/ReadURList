' Launch the ReadURList worker with no console window (Windows Task Scheduler).
' Point the task Action at: wscript.exe
' Arguments:  "C:\PATH\TO\ReadURList\docs\run-worker-hidden.vbs"
' General: Run only when user is logged on (no account password needed).

Option Explicit
Dim fso, shell, repo, exe, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

repo = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
exe = repo & "\.venv\Scripts\readurlist.exe"

If Not fso.FileExists(exe) Then
  WScript.Echo "Missing: " & exe
  WScript.Quit 1
End If

shell.CurrentDirectory = repo
' 0 = hidden window; False = do not wait
cmd = """" & exe & """"
shell.Run cmd, 0, False
