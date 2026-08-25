@echo off
chcp 65001 >nul
title 최초 설치 - 한 번만 실행하세요
echo.
echo ==========================================================
echo   영상 편집에 필요한 프로그램을 설치합니다 (최초 1회)
echo   설치 중 "예" 또는 "Y" 를 물어보면 눌러주세요.
echo ==========================================================
echo.

where winget >nul 2>&1
if errorlevel 1 (
  echo [!] winget 이 없습니다. 윈도우 10 구버전일 수 있어요.
  echo     아래 두 개를 직접 설치한 뒤 이 창을 닫으세요.
  echo       1^) FFmpeg   : https://www.gyan.dev/ffmpeg/builds/  ^(release full 다운로드^)
  echo       2^) Python   : https://www.python.org/downloads/
  echo          ** Python 설치 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요 **
  echo.
  pause
  exit /b
)

echo [1/2] FFmpeg 설치 중...
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
echo.
echo [2/2] Python 설치 중...
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements

echo.
echo ==========================================================
echo   설치가 끝났습니다.
echo   ** 컴퓨터를 한 번 재시작한 뒤 1_준비하기.bat 을 쓰세요 **
echo ==========================================================
echo.
pause
