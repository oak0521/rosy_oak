@echo off
chcp 65001 >nul
title 1단계 - 영상 준비하기
setlocal

echo.
echo ==========================================================
echo   1단계. 촬영본에서 컨택트시트를 만듭니다
echo ==========================================================
echo.

set "TARGET=%~1"
if "%TARGET%"=="" (
  echo   영상이 들어있는 폴더를 이 창으로 끌어다 놓고 Enter 를 누르세요.
  echo   ^(예: D:\옥진작업\클로드코드\insta_siu^)
  echo.
  set /p TARGET="폴더: "
)
set "TARGET=%TARGET:"=%"

if not exist "%TARGET%\" (
  echo.
  echo [!] 폴더를 찾을 수 없습니다: %TARGET%
  echo.
  pause
  exit /b
)

where ffmpeg >nul 2>&1 || goto :noffmpeg
where python >nul 2>&1 || goto :nopython

python "%~dp0..\prep.py" "%TARGET%"
if errorlevel 1 goto :failed

echo.
echo   결과 폴더를 엽니다...
start "" "%TARGET%\_prep\sheets"
echo.
echo ==========================================================
echo   다음 순서
echo    1. 방금 열린 폴더의 jpg 파일들을 Claude 채팅에 끌어다 놓기
echo    2. _prep\inventory.json 을 메모장으로 열어 내용 복사 → 채팅에 붙여넣기
echo    3. 채팅에 이렇게 입력:
echo         /longform 그날 있었던 일을 편하게 설명 (총비용, 아이 컨디션 등)
echo ==========================================================
echo.
pause
exit /b

:noffmpeg
echo.
echo [!] FFmpeg 이 없습니다. 0_최초설치.bat 을 먼저 실행하세요.
echo     이미 설치했다면 컴퓨터를 재시작해야 인식됩니다.
echo.
pause
exit /b

:nopython
echo.
echo [!] Python 이 없습니다. 0_최초설치.bat 을 먼저 실행하세요.
echo     설치할 때 "Add python.exe to PATH" 체크가 필요합니다.
echo.
pause
exit /b

:failed
echo.
echo [!] 처리 중 문제가 생겼습니다. 위 메시지를 Claude 채팅에 그대로 붙여넣어 주세요.
echo.
pause
