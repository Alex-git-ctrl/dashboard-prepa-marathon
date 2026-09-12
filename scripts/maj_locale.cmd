@echo off
REM Mise a jour complete du tableau de bord depuis cette machine.
REM Double-clic, ou tache planifiee de 23h. Les analyses sont redigees par
REM Claude Code, donc par l'abonnement : aucune clef API, aucune facturation.
setlocal
cd /d "%~dp0.."

REM Le PATH d'une tache planifiee n'est pas celui d'un terminal ouvert a la
REM main. On cherche donc l'interpreteur au lieu de supposer qu'il repond.
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py"
if not defined PY (
  echo Python est introuvable dans le PATH de cette session.
  exit /b 9
)

REM Une trace sur disque : a 23h personne ne regarde la fenetre.
if not exist "journaux" mkdir "journaux"
echo. >> "journaux\maj_locale.log"
echo ===== %DATE% %TIME% ===== >> "journaux\maj_locale.log"
%PY% scripts\maj_locale.py >> "journaux\maj_locale.log" 2>&1
set CODE=%ERRORLEVEL%
echo ----- fin, code %CODE% >> "journaux\maj_locale.log"

REM En double-clic on veut voir ; sous le planificateur, personne ne regarde.
if not "%1"=="/silencieux" (
  type "journaux\maj_locale.log" | more +1
  if not "%CODE%"=="0" pause
)
exit /b %CODE%
