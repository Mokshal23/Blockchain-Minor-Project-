@echo off
echo =========================================================
echo Starting Dual-Engine Blockchain Crowdfunding Platform
echo =========================================================

echo Starting Python Flask Backend...
start "Python Backend" cmd /k "cd backend && python app.py"

echo Starting Hardhat Local Ethereum Blockchain...
start "Hardhat Ethereum Node" cmd /k "cd contracts && .\node_modules\.bin\hardhat node"

echo Waiting 5 seconds for nodes to initialize...
timeout /t 5 /nobreak > nul

echo Deploying Smart Contracts to Localhost...
cd contracts
.\node_modules\.bin\hardhat run scripts/deploy.js --network localhost
cd ..

echo =========================================================
echo All services launched successfully!
echo Opening frontend in your web browser...
echo =========================================================
start "" "%~dp0frontend\index.html"
