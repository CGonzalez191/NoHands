' NoHands - Lanzador invisible
' Al hacer doble clic, ejecuta el lanzador por voz sin mostrar ventana
' Escucha "NoHands" en segundo plano y abre la app automáticamente

Dim shell, pythonExe, scriptPath, desktopPath, fso

Set fso = CreateObject("Scripting.FileSystemObject")
desktopPath = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = desktopPath & "\lanzador_voz.py"

' Intentar encontrar Python verificando tanto Err.Number como el código de salida (exit code)
' Err.Number solo detecta si el shell pudo lanzar el proceso; el exit code detecta si Python es válido.
Dim pythonCandidates, candidate
pythonCandidates = Array( _
    "py -3", _
    "python", _
    "python3" _
)

Dim found
found = False
For Each candidate In pythonCandidates
    Set shell = CreateObject("WScript.Shell")
    Dim result
    On Error Resume Next
    result = shell.Run(candidate & " --version", 0, True)
    Dim launchErr
    launchErr = Err.Number
    On Error GoTo 0
    ' Solo considerar válido si no hubo error de lanzamiento Y el proceso terminó con exit code 0
    If launchErr = 0 And result = 0 Then
        pythonExe = candidate
        found = True
        Exit For
    End If
Next

If Not found Then
    MsgBox "No se encontró Python instalado." & vbCrLf & _
           "Instalá Python desde https://python.org y asegurate de que esté en el PATH.", _
           vbCritical, "NoHands - Python no encontrado"
    WScript.Quit 1
End If

Set shell = CreateObject("WScript.Shell")
' 0 = ocultar ventana, False = no esperar a que termine
shell.Run pythonExe & " """ & scriptPath & """", 0, False
