On Error Resume Next
Set sh = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "pythonw """ & dir & "\kb.py""", 0, False
If Err.Number <> 0 Then
  Err.Clear
  sh.Run "py -3w """ & dir & "\kb.py""", 0, False
End If
If Err.Number <> 0 Then
  MsgBox "Hace falta Python. Instálalo desde python.org y marca Tcl/Tk.", 48, "Teclado"
End If
