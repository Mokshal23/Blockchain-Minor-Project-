const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Dual-Engine Solidity Crowdfunding Contracts", function () {
  let Factory, factory;
  let owner, addr1, addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    Factory = await ethers.getContractFactory("CrowdfundingFactory");
    factory = await Factory.deploy();
    await factory.waitForDeployment();
  });

  it("Should deploy CrowdfundingFactory successfully", async function () {
    const address = await factory.getAddress();
    expect(address).to.be.properAddress;
  });

  it("Should create Equity Campaign and allow contributions & voting", async function () {
    const goal = ethers.parseEther("1.0");
    const tx = await factory.connect(owner).createEquityCampaign("Equity Test", "Desc", goal, 30);
    await tx.wait();

    const registry = await factory.getCampaignRegistry();
    expect(registry.length).to.equal(1);
    expect(registry[0].modelType).to.equal("Equity");

    const campaignAddress = registry[0].campaignAddress;
    const EquityCampaign = await ethers.getContractFactory("EquityCampaign");
    const equity = EquityCampaign.attach(campaignAddress);

    // Add milestone
    await equity.connect(owner).addMilestone("Milestone 1", 50);
    expect(await equity.getMilestoneCount()).to.equal(1);

    // Contribute from addr1
    const contrib = ethers.parseEther("0.6");
    await equity.connect(addr1).contribute({ value: contrib });
    expect(await equity.currentAmount()).to.equal(contrib);

    // Vote on milestone from addr1 (>50% raised funds voted YES -> should approve and release)
    const initialBalance = await ethers.provider.getBalance(owner.address);
    await equity.connect(addr1).voteMilestone(0, true);

    const milestone = await equity.milestones(0);
    expect(milestone.isApproved).to.be.true;
    expect(milestone.isExecuted).to.be.true;
  });

  it("Should create Lending Campaign and process pull withdrawal repayments", async function () {
    const goal = ethers.parseEther("2.0");
    const tx = await factory.connect(owner).createLendingCampaign("Lending Test", "Desc", goal, 30, 10);
    await tx.wait();

    const registry = await factory.getCampaignRegistry();
    const campaignAddress = registry[0].campaignAddress;
    const LendingCampaign = await ethers.getContractFactory("LendingCampaign");
    const lending = LendingCampaign.attach(campaignAddress);

    // Contribute 1 ETH from addr1
    const contrib = ethers.parseEther("1.0");
    await lending.connect(addr1).contribute({ value: contrib });

    // Borrower deposits repayment (1.1 ETH = Principal + 10% interest)
    const repayment = ethers.parseEther("1.1");
    await lending.connect(owner).depositRepayment({ value: repayment });

    // Lender (addr1) pulls repayment
    await expect(lending.connect(addr1).withdrawRepayment())
      .to.emit(lending, "RepaymentWithdrawn");
  });
});
