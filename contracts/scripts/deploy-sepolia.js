/**
 * =============================================================================
 * Hardhat Sepolia Deployment Script
 * =============================================================================
 * Deploys CrowdfundingFactory.sol to Sepolia Ethereum Testnet,
 * creates initial sample campaigns, and saves the address to frontend/contract_address.json
 * =============================================================================
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("=================================================");
  console.log("Deploying Crowdfunding Contracts to Sepolia Testnet...");
  console.log("=================================================");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer Account Address:", deployer.address);
  
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Deployer Sepolia ETH Balance:", hre.ethers.formatEther(balance), "ETH");

  if (balance === 0n) {
    console.error("\n[!] ERROR: Deployer account has 0 Sepolia ETH.");
    console.error("[!] Please get free Sepolia ETH from a faucet: https://sepoliafaucet.com or https://sepoliadrop.com");
    process.exit(1);
  }

  // 1. Deploy Factory Contract
  const Factory = await hre.ethers.getContractFactory("CrowdfundingFactory");
  const factory = await Factory.deploy();
  await factory.waitForDeployment();

  const factoryAddress = await factory.getAddress();
  console.log("\n[+] CrowdfundingFactory deployed to Sepolia at Address:", factoryAddress);

  // 2. Create Sample Equity Campaign
  console.log("\nCreating Sample Equity Campaign on Sepolia...");
  const tx1 = await factory.createEquityCampaign(
    "GreenTech Solar Energy",
    "Community solar farm project offering 10% equity shares.",
    hre.ethers.parseEther("0.01"), // 0.01 Sepolia ETH goal
    30
  );
  await tx1.wait();

  // 3. Save info to frontend/contract_address.json
  const deployInfo = {
    factoryAddress: factoryAddress,
    network: "sepolia",
    chainId: 11155111,
    deployedAt: new Date().toISOString()
  };

  const outputDir = path.join(__dirname, "../../frontend");
  fs.writeFileSync(
    path.join(outputDir, "contract_address.json"),
    JSON.stringify(deployInfo, null, 2)
  );

  console.log("\n[+] Saved Sepolia contract configuration to frontend/contract_address.json");
  console.log("=================================================");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
