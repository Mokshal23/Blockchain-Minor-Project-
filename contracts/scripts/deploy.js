/**
 * =============================================================================
 * Hardhat Deployment Script for Solidity Smart Contracts
 * =============================================================================
 * Deploys CrowdfundingFactory.sol to local Hardhat network,
 * creates initial Equity and Lending campaigns for testing,
 * and saves contract addresses to a json file for frontend use.
 * =============================================================================
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("=================================================");
  console.log("Deploying Dual-Engine Solidity Smart Contracts...");
  console.log("=================================================");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // 1. Deploy Factory Contract
  const Factory = await hre.ethers.getContractFactory("CrowdfundingFactory");
  const factory = await Factory.deploy();
  await factory.waitForDeployment();

  const factoryAddress = await factory.getAddress();
  console.log("\n[+] CrowdfundingFactory deployed to:", factoryAddress);

  // 2. Create Sample Equity Campaign via Factory
  console.log("\nCreating Sample Equity Campaign (GreenTech Solar)...");
  const tx1 = await factory.createEquityCampaign(
    "GreenTech Solar Energy",
    "Community solar farm project offering 10% equity shares.",
    hre.ethers.parseEther("10"), // 10 ETH goal
    30 // 30 days
  );
  await tx1.wait();

  // 3. Create Sample Lending Campaign via Factory
  console.log("Creating Sample Lending Campaign (EcoFarm Equipment Loan)...");
  const tx2 = await factory.createLendingCampaign(
    "EcoFarm Equipment Loan",
    "Micro-lending campaign to buy sustainable farm tractors.",
    hre.ethers.parseEther("5"), // 5 ETH goal
    30, // 30 days
    5   // 5% interest rate
  );
  await tx2.wait();

  const registry = await factory.getCampaignRegistry();
  console.log("\n[+] Initial Deployed Campaigns:");
  registry.forEach((item, idx) => {
    console.log(`  ${idx + 1}. [${item.modelType}] "${item.title}" at Address: ${item.campaignAddress}`);
  });

  // 4. Export Address Information for Frontend app.js
  const deployInfo = {
    factoryAddress: factoryAddress,
    network: hre.network.name,
    chainId: 31337,
    deployedAt: new Date().toISOString()
  };

  const outputDir = path.join(__dirname, "../../frontend");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(outputDir, "contract_address.json"),
    JSON.stringify(deployInfo, null, 2)
  );

  console.log("\n[+] Saved contract address configuration to frontend/contract_address.json");
  console.log("=================================================");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
