/**
 * =============================================================================
 * Dual-Engine Crowdfunding Platform - Frontend Logic (app.js)
 * =============================================================================
 * Optimized for Vercel Deployment & Local Testing:
 *   1. Python REST API (/api) for Donation & Reward models (Works 24/7 on Vercel)
 *   2. MetaMask / Ethers.js for Solidity Smart Contracts (Equity & Lending models)
 * =============================================================================
 */

// Auto-detect API URL for local vs Vercel deployment
const PYTHON_API_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.protocol === "file:")
    ? "http://127.0.0.1:5000/api"
    : "/api";

// Default Hardhat / Sepolia Contract Address
let factoryContractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
let userAccount = null;
let provider = null;
let signer = null;

// Minimal Contract ABIs
const FACTORY_ABI = [
    "function createEquityCampaign(string _title, string _description, uint256 _fundingGoal, uint256 _durationInDays) returns (address)",
    "function createLendingCampaign(string _title, string _description, uint256 _fundingGoal, uint256 _durationInDays, uint256 _interestRatePercent) returns (address)",
    "function getCampaignRegistry() external view returns (tuple(address campaignAddress, string title, string modelType, address owner)[])"
];

const CAMPAIGN_ABI = [
    "function title() view returns (string)",
    "function description() view returns (string)",
    "function fundingGoal() view returns (uint256)",
    "function currentAmount() view returns (uint256)",
    "function contribute() payable",
    "function voteMilestone(uint256 _milestoneId, bool _approve)",
    "function milestones(uint256) view returns (uint256 id, string description, uint256 releasePercent, uint256 votesFor, uint256 votesAgainst, bool isApproved, bool isExecuted)",
    "function getMilestoneCount() view returns (uint256)"
];

// =============================================================================
// 1. INITIALIZATION & METAMASK CONNECTION
// =============================================================================

window.addEventListener("DOMContentLoaded", async () => {
    // Try loading deployed contract configuration if available
    try {
        const resp = await fetch("contract_address.json");
        if (resp.ok) {
            const config = await resp.json();
            if (config.factoryAddress) {
                factoryContractAddress = config.factoryAddress;
            }
        }
    } catch (e) {
        console.log("Using default contract configuration.");
    }

    loadCampaigns();
    checkBlockchainStatus();
});

async function connectMetaMask() {
    if (window.ethereum) {
        try {
            provider = new ethers.BrowserProvider(window.ethereum);
            signer = await provider.getSigner();
            userAccount = await signer.getAddress();

            document.getElementById("connectWalletBtn").innerText = "🦊 Connected";
            document.getElementById("walletAddressDisplay").innerText = `Wallet: ${userAccount.slice(0,6)}...${userAccount.slice(-4)}`;
            console.log("MetaMask Connected:", userAccount);
            loadCampaigns();
        } catch (err) {
            console.error("User rejected wallet connection:", err);
            alert("MetaMask connection request was cancelled.");
        }
    } else {
        if (confirm("MetaMask extension is not installed in your browser!\n\nDo you want to install MetaMask to interact with Equity/Lending smart contracts?\n(Note: Donation & Reward campaigns work 100% without MetaMask!)")) {
            window.open("https://metamask.io/download/", "_blank");
        }
    }
}

function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    document.getElementById(tabId).classList.add("active");
    if (event && event.target) {
        event.target.classList.add("active");
    }

    if (tabId === 'adminTab') {
        loadBlockchainLedger();
        checkBlockchainStatus();
        loadAdminMilestones();
    }
}

function updateEngineNotice() {
    const model = document.getElementById("campModel").value;
    const box = document.getElementById("engineNoticeBox");

    if (model === "Donation" || model === "Reward") {
        box.className = "info-box python-box";
        box.innerHTML = `<strong>Engine Notice:</strong> ${model} campaigns run on the <span>Python Engine</span> (SHA-256 Ledger + Admin Approval). Works 100% in cloud!`;
    } else {
        box.className = "info-box";
        box.style.background = "#fffbe6";
        box.style.borderLeft = "4px solid #f59e0b";
        box.innerHTML = `<strong>Engine Notice:</strong> ${model} campaigns run on the <span>Solidity Engine</span> (Ethereum Smart Contract). Requires MetaMask connected to Sepolia or Hardhat.`;
    }
}

// =============================================================================
// 2. BROWSE & DISPLAY CAMPAIGNS
// =============================================================================

async function loadCampaigns() {
    const grid = document.getElementById("campaignListGrid");

    let campaigns = [];

    // 1. Fetch Python Campaigns from REST API (Works on Vercel)
    try {
        const resp = await fetch(`${PYTHON_API_URL}/campaigns`);
        if (resp.ok) {
            const pyCampaigns = await resp.json();
            campaigns = campaigns.concat(pyCampaigns);
        }
    } catch (err) {
        console.warn("Python Flask API offline:", err);
    }

    // 2. Fetch Solidity Campaigns from Web3 provider if available
    if (window.ethereum && factoryContractAddress) {
        try {
            const readProvider = new ethers.BrowserProvider(window.ethereum);
            const factory = new ethers.Contract(factoryContractAddress, FACTORY_ABI, readProvider);
            const registry = await factory.getCampaignRegistry();

            for (let item of registry) {
                const cContract = new ethers.Contract(item.campaignAddress, CAMPAIGN_ABI, readProvider);
                const goal = ethers.formatEther(await cContract.fundingGoal());
                const raised = ethers.formatEther(await cContract.currentAmount());

                campaigns.push({
                    id: item.campaignAddress,
                    title: item.title,
                    description: `Solidity On-Chain ${item.modelType} Campaign`,
                    owner: item.owner,
                    funding_type: item.modelType,
                    engine: "Solidity",
                    funding_goal: parseFloat(goal),
                    current_amount: parseFloat(raised),
                    contract_address: item.campaignAddress
                });
            }
        } catch (err) {
            // Silently handle if Web3 node is not connected to avoid scary popups
            console.log("Solidity network query skipped (node not connected).");
        }
    }

    // Filter campaigns based on UI dropdown
    const filter = document.getElementById("modelFilter").value;
    if (filter !== "ALL") {
        campaigns = campaigns.filter(c => c.funding_type === filter);
    }

    if (campaigns.length === 0) {
        grid.innerHTML = `
            <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
                <h3>No active ${filter === 'ALL' ? '' : filter} campaigns found</h3>
                <p>Launch your first campaign in the <strong>Create Campaign</strong> tab above!</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = "";
    campaigns.forEach(c => {
        const percent = Math.min(100, Math.round((c.current_amount / c.funding_goal) * 100));
        const engineClass = c.engine === "Python" ? "badge-python" : "badge-solidity";

        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <div class="card-header">
                <h3>${c.title}</h3>
                <span class="badge ${engineClass}">${c.engine} Engine</span>
            </div>
            <p style="color: #64748b; font-size: 0.9rem;">Model: <strong>${c.funding_type}</strong></p>
            <p>${c.description}</p>
            
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${percent}%;"></div>
            </div>
            <p><strong>${c.current_amount}</strong> of ${c.funding_goal} ETH raised (${percent}%)</p>

            <button class="btn-primary" onclick="contributePrompt('${c.id}', '${c.engine}')">
                Contribute to Campaign
            </button>

            ${c.engine === "Solidity" ? `
                <button class="btn-secondary" style="width:100%; margin-top:0.4rem;" onclick="voteOnSolidityMilestonePrompt('${c.contract_address}')">
                    🗳️ Contributor Vote on Milestone
                </button>
            ` : ""}
        `;
        grid.appendChild(card);
    });
}

// =============================================================================
// 3. CREATE & FUND CAMPAIGN LOGIC
// =============================================================================

async function handleCreateCampaign(e) {
    e.preventDefault();

    const title = document.getElementById("campTitle").value;
    const description = document.getElementById("campDescription").value;
    const model = document.getElementById("campModel").value;
    const goal = document.getElementById("campGoal").value;
    const duration = document.getElementById("campDuration").value;
    const m1Desc = document.getElementById("milestone1Desc").value;

    if (model === "Donation" || model === "Reward") {
        // Python Engine Flow (Runs on Vercel Serverless)
        try {
            const resp = await fetch(`${PYTHON_API_URL}/campaigns`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: title,
                    description: description,
                    owner: "Platform Startup Owner",
                    funding_type: model,
                    funding_goal: parseFloat(goal),
                    deadline: "2026-12-31",
                    milestones: [{ description: m1Desc, target_percent: 50.0 }]
                })
            });

            if (resp.ok) {
                alert(`Success! Created ${model} Campaign on Python Engine (SHA-256 Ledger).`);
                document.getElementById("createCampaignForm").reset();
                showTab("browseTab");
                loadCampaigns();
            } else {
                alert("Failed to create campaign.");
            }
        } catch (err) {
            alert("Error connecting to Python server.");
        }
    } else {
        // Solidity Engine Flow
        if (!signer) {
            alert("Equity & Lending campaigns run on Solidity smart contracts.\n\nPlease click '🦊 Connect MetaMask' at top right first!");
            await connectMetaMask();
            if (!signer) return;
        }

        try {
            // Check network before sending transaction
            const net = await provider.getNetwork();
            if (net.chainId !== 31337n && net.chainId !== 1337n) {
                alert("Network Mismatch:\nYour MetaMask is currently set to Sepolia or Mainnet.\n\nPlease switch your MetaMask network to 'Hardhat Localhost' (http://127.0.0.1:8545) at top left of MetaMask!");
                return;
            }

            const factory = new ethers.Contract(factoryContractAddress, FACTORY_ABI, signer);
            let tx;
            const goalWei = ethers.parseEther(goal.toString());


            if (model === "Equity") {
                tx = await factory.createEquityCampaign(title, description, goalWei, parseInt(duration));
            } else {
                tx = await factory.createLendingCampaign(title, description, goalWei, parseInt(duration), 5);
            }

            alert("Sending transaction to Ethereum network... Please confirm in MetaMask.");
            await tx.wait();
            alert(`Success! Deployed ${model} Smart Contract on Ethereum blockchain!`);

            document.getElementById("createCampaignForm").reset();
            showTab("browseTab");
            loadCampaigns();
        } catch (err) {
            console.error("Solidity deployment error:", err);
            alert("Smart contract transaction failed or was cancelled in MetaMask.");
        }
    }
}

async function contributePrompt(campaignId, engine) {
    const amountStr = prompt("Enter contribution amount (in ETH / USD):", "1.0");
    if (!amountStr || isNaN(amountStr) || parseFloat(amountStr) <= 0) return;

    if (engine === "Python") {
        try {
            const resp = await fetch(`${PYTHON_API_URL}/campaigns/${campaignId}/contribute`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    contributor_name: userAccount ? `Wallet ${userAccount.slice(0,6)}` : "Anonymous Supporter",
                    amount: parseFloat(amountStr)
                })
            });

            if (resp.ok) {
                const resData = await resp.json();
                alert(`Contribution Successful!\nBlock #${resData.block_index} appended to SHA-256 ledger.\nReward Tier: ${resData.reward_tier}`);
                loadCampaigns();
            }
        } catch (err) {
            alert("Failed to send contribution to Python backend.");
        }
    } else {
        // Solidity Contribution
        if (!signer) {
            alert("Please connect MetaMask wallet first!");
            await connectMetaMask();
            if (!signer) return;
        }

        try {
            const cContract = new ethers.Contract(campaignId, CAMPAIGN_ABI, signer);
            const valWei = ethers.parseEther(amountStr);

            const tx = await cContract.contribute({ value: valWei });
            alert("Sending contribution transaction... Please confirm in MetaMask.");
            await tx.wait();

            alert("Contribution confirmed on Ethereum blockchain!");
            loadCampaigns();
        } catch (err) {
            console.error("Solidity contribution failed:", err);
            alert("Transaction failed.");
        }
    }
}

async function voteOnSolidityMilestonePrompt(contractAddress) {
    if (!signer) {
        alert("Connect MetaMask wallet to vote on Smart Contract milestones!");
        await connectMetaMask();
        if (!signer) return;
    }

    const vote = confirm("Click OK to Vote YES (Approve Milestone & Release Funds), or Cancel to Vote NO.");
    try {
        const cContract = new ethers.Contract(contractAddress, CAMPAIGN_ABI, signer);
        const tx = await cContract.voteMilestone(0, vote);
        alert("Submitting vote transaction... Please confirm in MetaMask.");
        await tx.wait();
        alert("Vote registered on-chain! If majority threshold was met, smart contract automatically released milestone funds!");
        loadCampaigns();
    } catch (err) {
        console.error("Voting failed:", err);
        alert("Voting failed. Make sure you are a contributor and haven't voted already!");
    }
}

// =============================================================================
// 4. ADMIN PANEL & PYTHON SHA-256 TAMPER DEMO
// =============================================================================

async function loadAdminMilestones() {
    const list = document.getElementById("adminMilestoneList");
    if (!list) return;
    list.innerHTML = "<p>Loading pending milestones...</p>";

    try {
        const resp = await fetch(`${PYTHON_API_URL}/campaigns`);
        if (!resp.ok) return;

        const campaigns = await resp.json();
        list.innerHTML = "";

        for (let c of campaigns) {
            const cResp = await fetch(`${PYTHON_API_URL}/campaigns/${c.id}`);
            if (cResp.ok) {
                const data = await cResp.json();
                data.milestones.forEach(m => {
                    if (m.status === "PENDING") {
                        const item = document.createElement("div");
                        item.style.padding = "0.6rem";
                        item.style.borderBottom = "1px solid #e2e8f0";
                        item.innerHTML = `
                            <p><strong>${c.title}</strong> - Milestone: ${m.description}</p>
                            <button class="btn-primary" style="width:auto; padding:0.4rem 0.8rem;" onclick="adminApproveMilestone(${c.id}, ${m.id})">
                                Approve Milestone & Release Funds (Admin Key)
                            </button>
                        `;
                        list.appendChild(item);
                    }
                });
            }
        }

        if (list.children.length === 0) {
            list.innerHTML = "<p>No pending milestones found. Create a Donation/Reward campaign first!</p>";
        }
    } catch (err) {
        list.innerHTML = "<p style='color:red;'>Could not fetch milestones from Python backend.</p>";
    }
}

async function adminApproveMilestone(campaignId, milestoneId) {
    try {
        const resp = await fetch(`${PYTHON_API_URL}/campaigns/${campaignId}/milestones/${milestoneId}/approve`, {
            method: "POST"
        });

        if (resp.ok) {
            alert("Admin Approved Milestone! Block added to Python SHA-256 ledger.");
            loadAdminMilestones();
            loadBlockchainLedger();
        }
    } catch (err) {
        alert("Failed to approve milestone.");
    }
}

async function checkBlockchainStatus() {
    const badge = document.getElementById("chainValidationStatus");
    const msg = document.getElementById("chainValidationMsg");

    if (!badge || !msg) return;

    try {
        const resp = await fetch(`${PYTHON_API_URL}/blockchain/validate`);
        if (resp.ok) {
            const data = await resp.json();
            if (data.is_valid) {
                badge.className = "status-badge valid";
                badge.innerText = "Chain Status: VALID";
                msg.innerText = data.message;
            } else {
                badge.className = "status-badge tampered";
                badge.innerText = "Chain Status: TAMPERED / INVALID";
                msg.innerText = data.message;
            }
        }
    } catch (err) {
        badge.className = "status-badge tampered";
        badge.innerText = "Python API Server Offline";
        msg.innerText = "Could not connect to Python API server.";
    }
}

async function loadBlockchainLedger() {
    const viewer = document.getElementById("blockchainViewer");
    if (!viewer) return;

    try {
        const resp = await fetch(`${PYTHON_API_URL}/blockchain`);
        if (resp.ok) {
            const blocks = await resp.json();
            viewer.innerText = JSON.stringify(blocks, null, 2);
        }
    } catch (err) {
        viewer.innerText = "Error loading ledger blocks from Python backend.";
    }
}

async function triggerAdminTamper() {
    if (!confirm("Are you sure you want to run the Admin Tamper Script? This will modify a past block in SQLite and recalculate downstream SHA-256 hashes.")) return;

    try {
        const resp = await fetch(`${PYTHON_API_URL}/tamper`, { method: "POST" });
        if (resp.ok) {
            const result = await resp.json();
            alert(`TAMPER SUCCESSFUL!\n\n${result.message}\n\nNotice that the chain STILL VALIDATES as 'True' because the admin recalculated all hashes!`);
            loadBlockchainLedger();
            checkBlockchainStatus();
        } else {
            const errData = await resp.json();
            alert(`Tamper Failed: ${errData.error}`);
        }
    } catch (err) {
        alert("Could not reach Python API server.");
    }
}
