@echo off

:: --- Riavvia come Amministratore se necessario ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo  ============================================
echo   Estrattore P7M - Disinstallazione
echo  ============================================
echo.
echo  Questo script rimuovera':
echo  - La voce "Estrai contenuto P7M" dal tasto destro
echo  - La cartella C:\Programmi\P7MExtractor\
echo.
set /p CONFIRM=Continuare? (S/N): 
if /i not "%CONFIRM%"=="S" (
    echo  Annullato.
    pause
    exit /b
)

echo.
echo  Rimozione menu tasto destro...
reg delete "HKEY_CLASSES_ROOT\*\shell\EstraiP7M" /f >nul 2>&1
echo  [OK] Voce rimossa dal registro.

echo  Rimozione cartella programma...
if exist "C:\Programmi\P7MExtractor\" (
    rmdir /s /q "C:\Programmi\P7MExtractor\"
    echo  [OK] Cartella rimossa.
) else (
    echo  [INFO] Cartella non trovata, niente da rimuovere.
)

echo  Aggiornamento Esplora File...
powershell -NoProfile -Command ^
  "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; Start-Process explorer" >nul

echo.
echo  [OK] Disinstallazione completata.
echo.
pause
