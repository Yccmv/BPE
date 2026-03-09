@echo off
REM ═══════════════════════════════════════════════════════════════
REM  COMPILA_EXE.bat  —  Compila Estrattore P7M in un singolo .exe
REM  Esegui questo file nella stessa cartella di p7m_extractor.py
REM ═══════════════════════════════════════════════════════════════

echo Installazione dipendenze...
pip install pyinstaller asn1crypto

echo.
echo Compilazione in corso...
pyinstaller p7m_extractor.spec --clean

echo.
echo ─────────────────────────────────────────────────────
echo  Fatto! Il file si trova in:  dist\EstrattoreP7M.exe
echo.
echo  NOTA: l'exe e' standalone, non richiede Python.
echo  Puoi sostituire l'exe nell'installer (INSTALLA_TUTTO.bat)
echo  copiando EstrattoreP7M.exe al posto di p7m_extractor.py
echo  e adattando il comando nel registro di sistema.
echo ─────────────────────────────────────────────────────
pause
