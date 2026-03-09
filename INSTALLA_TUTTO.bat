@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  INSTALLA_TUTTO.bat
::  Estrattore P7M - Installer completo
::
::  Cosa fa questo script:
::  1. Si riavvia automaticamente come Amministratore
::  2. Crea la cartella C:\Programmi\P7MExtractor\
::  3. Copia i file del programma
::  4. Installa la libreria Python necessaria (asn1crypto)
::  5. Aggiunge la voce "Estrai contenuto P7M" al tasto destro
::     su tutti i file .p7m
:: ============================================================

:: --- Riavvia come Amministratore se necessario ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Riavvio come Amministratore...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo  ============================================
echo   Estrattore P7M - Installazione
echo  ============================================
echo.

set SOURCE_DIR=%~dp0
set DEST_DIR=C:\Programmi\P7MExtractor

:: --- Crea cartella destinazione ---
if not exist "%DEST_DIR%" (
    mkdir "%DEST_DIR%"
    echo  [OK] Cartella creata: %DEST_DIR%
) else (
    echo  [OK] Cartella già esistente: %DEST_DIR%
)

:: --- Copia i file ---
echo.
echo  Copia file in corso...
copy /Y "%SOURCE_DIR%p7m_extractor.py" "%DEST_DIR%\p7m_extractor.py" >nul
echo  [OK] p7m_extractor.py copiato
copy /Y "%SOURCE_DIR%DISINSTALLA.bat" "%DEST_DIR%\DISINSTALLA.bat" >nul
echo  [OK] DISINSTALLA.bat copiato

:: --- Trova Python ---
echo.
echo  Ricerca Python...
set PYTHONW=
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do (
    if "!PYTHONW!"=="" set PYTHONW=%%i
)

if "%PYTHONW%"=="" (
    for %%V in (313 312 311 310 39 38) do (
        for %%P in (
            "%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
            "%PROGRAMFILES%\Python%%V\pythonw.exe"
            "C:\Python%%V\pythonw.exe"
        ) do (
            if "!PYTHONW!"=="" if exist %%P set PYTHONW=%%~P
        )
    )
)

if "%PYTHONW%"=="" (
    echo.
    echo  [ERRORE] Python non trovato sul sistema.
    echo.
    echo  Installa Python da: https://www.python.org/downloads/
    echo  Durante l'installazione spunta "Add Python to PATH"
    echo  Poi rilancia questo installer.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python trovato: %PYTHONW%

:: --- Installa asn1crypto se mancante ---
echo.
echo  Verifica libreria asn1crypto...
"%PYTHONW%" -c "import asn1crypto" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installazione asn1crypto in corso...
    set PYTHON_EXE=%PYTHONW:pythonw.exe=python.exe%
    "!PYTHON_EXE!" -m pip install asn1crypto
    if !errorlevel! neq 0 (
        echo  [ERRORE] Impossibile installare asn1crypto.
        echo  Prova manualmente: pip install asn1crypto
        pause
        exit /b 1
    )
    echo  [OK] asn1crypto installata.
) else (
    echo  [OK] asn1crypto già presente.
)

:: --- Scrivi menu tasto destro nel registro ---
echo.
echo  Installazione menu tasto destro...

set SCRIPT_PATH=%DEST_DIR%\p7m_extractor.py
set PYTHONW_ESC=%PYTHONW:\=\\%
set SCRIPT_ESC=%SCRIPT_PATH:\=\\%

:: Rimuovi eventuali installazioni precedenti
reg delete "HKEY_CURRENT_USER\Software\Classes\.p7m" /f >nul 2>&1
reg delete "HKEY_CURRENT_USER\Software\Classes\P7MFile" /f >nul 2>&1
reg delete "HKEY_CLASSES_ROOT\*\shell\EstraiP7M" /f >nul 2>&1

:: Scrivi la chiave universale (funziona anche con InfoCamere, GoSign, Dike, ecc.)
reg add "HKEY_CLASSES_ROOT\*\shell\EstraiP7M" /ve /d "Estrai contenuto P7M" /f >nul
reg add "HKEY_CLASSES_ROOT\*\shell\EstraiP7M" /v "Icon" /d "shell32.dll,1" /f >nul
reg add "HKEY_CLASSES_ROOT\*\shell\EstraiP7M" /v "AppliesTo" /d "System.FileName:\"*.p7m\"" /f >nul
reg add "HKEY_CLASSES_ROOT\*\shell\EstraiP7M\command" /ve /d "\"%PYTHONW_ESC%\" \"%SCRIPT_ESC%\" \"%%1\"" /f >nul

echo  [OK] Menu tasto destro installato.

:: --- Riavvia Esplora File ---
echo.
echo  Aggiornamento Esplora File...
powershell -NoProfile -Command ^
  "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; Start-Process explorer" >nul
echo  [OK] Esplora File aggiornato.

echo.
echo  ============================================
echo   Installazione completata con successo!
echo.
echo   Fai clic DESTRO su qualsiasi file .p7m
echo   e scegli: "Estrai contenuto P7M"
echo.
echo   Funziona anche selezionando piu' file
echo   contemporaneamente: si apre una sola
echo   finestra che li elabora tutti insieme.
echo  ============================================
echo.
pause
