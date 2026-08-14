@echo off
title Dual-Engine Platform Launcher
echo =========================================================
echo Starting Dual-Engine Blockchain Crowdfunding Platform
echo =========================================================

cd /d "%~dp0backend"
echo [1/3] Launching Python Flask Backend Server...
start "Python Backend Server" cmd /k "python app.py"

cd /d "%~dp0contracts"
echo [2/3] Launching Hardhat Local Ethereum Node...
start "Hardhat Ethereum Node" cmd /k "..\node_modules\.bin\hardhat node"

echo [3/3] Waiting 6 seconds for local blockchain to initialize...
timeout /t 6 /nobreak

echo Deploying Smart Contracts...
cd /d "%~dp0contracts"
call node_modules\.bin\hardhat run scripts/deploy.js --network localhost

echo =========================================================
echo All services are running! Opening frontend...
echo =========================================================
start "" "%~dp0frontend\index.html"
pause
