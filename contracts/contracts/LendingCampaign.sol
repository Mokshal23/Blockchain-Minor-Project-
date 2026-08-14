// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * =============================================================================
 * Dual-Engine Crowdfunding Platform - Lending Campaign Smart Contract
 * =============================================================================
 */

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract LendingCampaign is ReentrancyGuard {
    address payable public owner; // Borrower
    string public title;
    string public description;
    uint256 public fundingGoal;
    uint256 public currentAmount;
    uint256 public deadline;
    uint256 public interestRatePercent; // e.g. 5 for 5% interest
    uint256 public totalRepaidPool;
    bool public isClosed;

    mapping(address => uint256) public lenderPrincipal;
    mapping(address => uint256) public lenderWithdrawn;
    address[] public lenderList;

    struct Milestone {
        uint256 id;
        string description;
        uint256 releasePercent;
        uint256 votesFor;
        uint256 votesAgainst;
        bool isApproved;
        bool isExecuted;
    }

    Milestone[] public milestones;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event ContributionReceived(address indexed lender, uint256 amount);
    event RepaymentDeposited(address indexed borrower, uint256 amount);
    event RepaymentWithdrawn(address indexed lender, uint256 amount);
    event MilestoneCreated(uint256 indexed milestoneId, string description, uint256 releasePercent);
    event VoteCast(address indexed voter, uint256 indexed milestoneId, bool approve, uint256 weight);
    event MilestoneApproved(uint256 indexed milestoneId, uint256 amountReleased);

    constructor(
        address payable _owner,
        string memory _title,
        string memory _description,
        uint256 _fundingGoal,
        uint256 _durationInDays,
        uint256 _interestRatePercent
    ) {
        owner = _owner;
        title = _title;
        description = _description;
        fundingGoal = _fundingGoal;
        deadline = block.timestamp + (_durationInDays * 1 days);
        interestRatePercent = _interestRatePercent;
        isClosed = false;

        milestones.push(Milestone({
            id: 0,
            description: "Milestone 1: Equipment Acquisition & Setup (50% Funds)",
            releasePercent: 50,
            votesFor: 0,
            votesAgainst: 0,
            isApproved: false,
            isExecuted: false
        }));
        emit MilestoneCreated(0, "Milestone 1: Equipment Acquisition & Setup (50% Funds)", 50);
    }

    function addMilestone(string memory _description, uint256 _releasePercent) external {
        require(msg.sender == owner, "Only borrower can add milestones");
        uint256 mId = milestones.length;
        milestones.push(Milestone({
            id: mId,
            description: _description,
            releasePercent: _releasePercent,
            votesFor: 0,
            votesAgainst: 0,
            isApproved: false,
            isExecuted: false
        }));
        emit MilestoneCreated(mId, _description, _releasePercent);
    }

    function contribute() external payable nonReentrant {
        require(block.timestamp < deadline, "Deadline passed");
        require(!isClosed, "Campaign closed");
        require(msg.value > 0, "Amount must be > 0");

        if (lenderPrincipal[msg.sender] == 0) {
            lenderList.push(msg.sender);
        }
        lenderPrincipal[msg.sender] += msg.value;
        currentAmount += msg.value;

        emit ContributionReceived(msg.sender, msg.value);
    }

    function voteMilestone(uint256 _milestoneId, bool _approve) external {
        require(_milestoneId < milestones.length, "Invalid milestone");
        require(lenderPrincipal[msg.sender] > 0, "Only lenders can vote");
        require(!hasVoted[_milestoneId][msg.sender], "Already voted");

        Milestone storage m = milestones[_milestoneId];
        require(!m.isExecuted, "Milestone already executed");

        uint256 weight = lenderPrincipal[msg.sender];
        hasVoted[_milestoneId][msg.sender] = true;

        if (_approve) {
            m.votesFor += weight;
        } else {
            m.votesAgainst += weight;
        }

        emit VoteCast(msg.sender, _milestoneId, _approve, weight);

        if (m.votesFor > (currentAmount / 2) && !m.isApproved) {
            m.isApproved = true;
            _executeMilestoneRelease(_milestoneId);
        }
    }

    function _executeMilestoneRelease(uint256 _milestoneId) internal nonReentrant {
        Milestone storage m = milestones[_milestoneId];
        require(m.isApproved && !m.isExecuted, "Cannot execute");

        m.isExecuted = true;
        uint256 releaseAmount = (fundingGoal * m.releasePercent) / 100;
        if (releaseAmount > address(this).balance) {
            releaseAmount = address(this).balance;
        }

        (bool success, ) = owner.call{value: releaseAmount}("");
        require(success, "ETH transfer failed");

        emit MilestoneApproved(_milestoneId, releaseAmount);
    }

    function depositRepayment() external payable nonReentrant {
        require(msg.value > 0, "Repayment must be > 0");
        totalRepaidPool += msg.value;
        emit RepaymentDeposited(msg.sender, msg.value);
    }

    function withdrawRepayment() external nonReentrant {
        require(lenderPrincipal[msg.sender] > 0, "Not a lender");

        uint256 principal = lenderPrincipal[msg.sender];
        uint256 maxShareFromPool = (totalRepaidPool * principal) / currentAmount;
        uint256 alreadyWithdrawn = lenderWithdrawn[msg.sender];

        require(maxShareFromPool > alreadyWithdrawn, "No new repayments available to withdraw");
        uint256 claimable = maxShareFromPool - alreadyWithdrawn;

        lenderWithdrawn[msg.sender] += claimable;

        (bool success, ) = msg.sender.call{value: claimable}("");
        require(success, "Withdrawal transfer failed");

        emit RepaymentWithdrawn(msg.sender, claimable);
    }

    function getVoterStatus(uint256 _milestoneId, address _voter) external view returns (uint256 contributionAmount, bool voted) {
        if (_milestoneId >= milestones.length) {
            return (lenderPrincipal[_voter], false);
        }
        return (lenderPrincipal[_voter], hasVoted[_milestoneId][_voter]);
    }

    function getLendingDetails(address _lender) external view returns (
        uint256 totalRepaid,
        uint256 principal,
        uint256 withdrawn,
        uint256 claimable
    ) {
        totalRepaid = totalRepaidPool;
        principal = lenderPrincipal[_lender];
        withdrawn = lenderWithdrawn[_lender];
        
        if (currentAmount > 0 && principal > 0) {
            uint256 maxShare = (totalRepaidPool * principal) / currentAmount;
            if (maxShare > withdrawn) {
                claimable = maxShare - withdrawn;
            }
        }
        return (totalRepaid, principal, withdrawn, claimable);
    }

    function getMilestoneCount() external view returns (uint256) {
        return milestones.length;
    }
}
