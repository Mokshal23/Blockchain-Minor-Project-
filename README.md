# Dual-Engine Blockchain Crowdfunding Platform
**College Blockchain Minor Project**

A dual-engine startup crowdfunding platform comparing a **Centralized SHA-256 Hash-Chained Python Engine** (Donation & Reward models) against a **Decentralized Solidity Smart Contract Engine** (Equity & Lending models) on an Ethereum testnet.

---

## 📌 Project Architecture

```
minor project/
├── backend/               # Python SHA-256 Engine (Flask + SQLite)
│   ├── app.py             # Flask API server & SHA-256 blockchain module
│   ├── tamper.py          # Admin tamper script (demonstrates central DB vulnerability)
│   └── requirements.txt
├── contracts/             # Solidity Smart Contract Engine (Hardhat + Solidity ^0.8.20)
│   ├── contracts/
│   │   ├── CrowdfundingFactory.sol
│   │   ├── EquityCampaign.sol
│   │   └── LendingCampaign.sol
│   ├── scripts/deploy.js  # Hardhat contract deployment script
│   └── hardhat.config.js
└── frontend/              # Unified Web Frontend (HTML + CSS + JavaScript)
    ├── index.html         # Single-page user interface
    ├── style.css          # Clean CSS styling
    └── app.js             # API calls (Flask) + Ethers.js & MetaMask (Solidity)
```

---

## 🚀 How to Run the Project (Step-by-Step)

### Step 1: Start the Python Backend Engine
1. Open a terminal in the `backend/` folder:
   ```bash
   cd backend
   python -m pip install -r requirements.txt
   python app.py
   ```
2. The Python Flask server will start at `http://127.0.0.1:5000`.

---

### Step 2: Start the Hardhat Local Ethereum Blockchain
1. Open a second terminal in the `contracts/` folder:
   ```bash
   cd contracts
   npm install
   .\node_modules\.bin\hardhat node
   ```
2. This starts a local Ethereum testnet node at `http://127.0.0.1:8545` (Chain ID `31337`).

---

### Step 3: Deploy Smart Contracts to Hardhat Network
1. Open a third terminal in the `contracts/` folder:
   ```bash
   cd contracts
   .\node_modules\.bin\hardhat run scripts/deploy.js --network localhost
   ```
2. This deploys `CrowdfundingFactory.sol` and saves `contract_address.json` directly into the `frontend/` directory.

---

### Step 4: Open the Frontend Application
1. Simply double-click or open `frontend/index.html` in your web browser (Google Chrome or Brave recommended with MetaMask extension installed).
2. Connect MetaMask to Network: **Localhost 8545** (Chain ID `31337`).
3. Import one of Hardhat's private keys into MetaMask to get free test ETH balance!

---

## 🎓 College Presentation Demo Guide

1. **Browse & Create Campaigns**:
   - Create a **Donation** or **Reward** campaign $\rightarrow$ Stores record in SQLite and appends block to Python SHA-256 ledger.
   - Create an **Equity** or **Lending** campaign $\rightarrow$ Deploys smart contract on Hardhat testnet via MetaMask.

2. **Milestone Approvals & Voting**:
   - **Python Engine**: Go to **Admin Panel** tab $\rightarrow$ Click "Approve Milestone" (Admin unilaterally releases funds).
   - **Solidity Engine**: Click "Contributor Vote on Milestone" $\rightarrow$ Contributors vote weighted by contribution amount (Quorum + Majority auto-releases funds; no admin key exists!).

3. **Demonstrate Admin Tamper Vulnerability (Python Ledger)**:
   - Go to **Admin Panel** tab $\rightarrow$ Click **"⚠️ Run Admin Tamper Script"**.
   - Notice how Block #1 data is modified, downstream hashes are recalculated, and the chain **STILL VALIDATES as True**.
   - **Key Conclusion for Professors**: *SHA-256 hash chaining alone does not make a database immutable if a single central party holds full database control. This is why financial models like Equity and Lending require real smart contract blockchains.*
