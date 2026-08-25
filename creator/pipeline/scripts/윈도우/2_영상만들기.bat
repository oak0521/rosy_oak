@echo off
chcp 65001 >nul
title 2단계 - 영상 만들기
setlocal

echo.
echo ==========================================================
echo   2단계. 편집 설계도(json)를 실제 영상으로 만듭니다
echo ==========================================================
echo.

set "SPEC=%~1"
if "%SPEC%"=="" (
  echo   Claude 가 준 edl.json 또는 shorts.json 파일을
  echo   이 창으로 끌어다 놓고 Enter 를 누르세요.
  echo.
  set /p SPEC="파일: "
)
set "SPEC=%SPEC:"=%"

if not exist "%SPEC%" (
  echo.
  echo [!] 파일을 찾을 수 없습니다: %SPEC%
  echo.
  pause
  exit /b
)

where ffmpeg >nul 2>&1 || goto :noffmpeg
where python >nul 2>&1 || goto :nopython

rem 파일 이름으로 롱폼인지 숏폼인지 자동 판단
echo %SPEC% | find /i "shorts" >nul
if errorlevel 1 (set MODE=longform) else (set MODE=shorts)

echo   %MODE% 모드로 만듭니다. 영상 길이에 따라 몇 분 걸립니다...
echo.
python "%~dp0..\render.py" %MODE% "%SPEC%"
if errorlevel 1 goto :failed

for %%F in ("%SPEC%") do set "OUTDIR=%%~dpF"
echo.
echo   결과 폴더를 엽니다...
start "" "%OUTDIR%"
echo.
echo ==========================================================
echo   완성입니다.
echo    - 이름에 "_무음_인스타용" 이 붙은 것 → 인스타에 올리고
echo      앱 안에서 트렌딩 오디오를 얹으세요
echo    - 그냥 mp4 → 유튜브에 그대로 올리세요
echo    - "_master_자막없음" 은 숏폼 만들 때 쓰는 원본이라 올리지 마세요
echo ==========================================================
echo.
pause
exit /b

:noffmpeg
echo [!] FFmpeg 이 없습니다. 0_최초설치.bat 을 먼저 실행하세요.
pause
exit /b
:nopython
echo [!] Python 이 없습니다. 0_최초설치.bat 을 먼저 실행하세요.
pause
exit /b
:failed
echo.
echo [!] 문제가 생겼습니다. 위 메시지를 Claude 채팅에 그대로 붙여넣어 주세요.
echo.
pause
