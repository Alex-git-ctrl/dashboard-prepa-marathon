@echo off
REM Mise a jour complete du tableau de bord depuis cette machine.
REM Double-clic, ou tache planifiee. Les analyses sont redigees par Claude
REM Code, donc par l'abonnement : aucune clef API, aucune facturation.
cd /d "%~dp0.."
python scripts\maj_locale.py
if errorlevel 1 (
  echo.
  echo Une etape a echoue. La fenetre reste ouverte pour que tu lises.
  pause
)
