// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * =============================================================================
 * Dual-Engine Crowdfunding Platform - Equity Campaign Smart Contract
 * =============================================================================
 * This contract handles Equity crowdfunding on Ethereum.
 * Key Features:
 *  1. OpenZeppelin ReentrancyGuard for safe ETH transfers.
 *  2. Internal mapping tracking contributor equity shares proportional to investment.
 *  3. Contributor Milestone Voting: Startup submits milestone proof, contributors
 *     vote weighted by their contribution amount. Quorum + majority triggers
 *     automatic fund release (NO ADMIN KEY EXISTS!).
 *  4. Pro-rata refund if deadline passes before reaching funding goal.
 * =============================================================================
 */

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract EquityCampaign is ReentrancyGuard {
    // Campaign Metadata
    address payable public owner;
    string public title;
    string public description;
    uint256 public fundingGoal;
    uint256 public currentAmount;
    uint256 public deadline;
    bool public isClosed;

    // Contributor Tracking
    mapping(address => uint256) public contributions;
    address[] public contributorList;

    // Milestone Structure
    struct Milestone {
        uint256 id;
        string description;
        uint256 releasePercent; // Percentage of goal to release (e.g. 50 = 50%)
        uint256 votesFor;
        uint256 votesAgainst;
        bool isApproved;
        bool isExecuted;
    }

    Milestone[] public milestones;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    // Events Emitted for Transparency
    event ContributionReceived(address indexed contributor, uint256 amount);
    event MilestoneCreated(uint256 indexed milestoneId, string description, uint256 releasePercent);
    event VoteCast(address indexed voter, uint256 indexed milestoneId, bool approve, uint256 weight);
    event MilestoneApproved(uint256 indexed milestoneId, uint256 amountReleased);
    event RefundIssued(address indexed contributor, uint256 amount);

    constructor(
        address payable _owner,
        string memory _title,
        string memory _description,
        uint256 _fundingGoal,
        uint256 _durationInDays
    ) {
        owner = _owner;
        title = _title;
        description = _description;
        fundingGoal = _fundingGoal;
        deadline = block.timestamp + (_durationInDays * 1 days);
        isClosed = false;
    }

    /**
     * @dev Allows campaign creator to add milestone breakdown (e.g. Milestone 1 = 50% funds)
     */
    function addMilestone(string memory _description, uint256 _releasePercent) external {
        require(msg.sender == owner, "Only campaign owner can add milestones");
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

    /**
     * @dev Contribute ETH to Equity Campaign.
     * Records contribution and tracks contributor for voting & equity mapping.
     */
    function contribute() external payable nonReentrant {
        require(block.timestamp < deadline, "Campaign deadline has passed");
        require(!isClosed, "Campaign is closed");
        require(msg.value > 0, "Contribution must be greater than 0");

        if (contributions[msg.sender] == 0) {
            contributorList.push(msg.sender);
        }
        contributions[msg.sender] += msg.value;
        currentAmount += msg.value;

        emit ContributionReceived(msg.sender, msg.value);
    }

    /**
     * @dev Contributor votes on a milestone approval.
     * Voting weight is directly proportional to the voter's contribution amount.
     */
    function voteMilestone(uint256 _milestoneId, bool _approve) external {
        require(_milestoneId < milestones.length, "Invalid milestone ID");
        require(contributions[msg.sender] > 0, "Only contributors can vote");
        require(!hasVoted[_milestoneId][msg.sender], "You have already voted on this milestone");

        Milestone storage m = milestones[_milestoneId];
        require(!m.isExecuted, "Milestone already executed");

        uint256 voteWeight = contributions[msg.sender];
        hasVoted[_milestoneId][msg.sender] = true;

        if (_approve) {
            m.votesFor += voteWeight;
        } else {
            m.votesAgainst += voteWeight;
        }

        emit VoteCast(msg.sender, _milestoneId, _approve, voteWeight);

        // Check if votes exceed Majority Threshold (e.g. >50% of current raised funds voted YES)
        if (m.votesFor > (currentAmount / 2) && !m.isApproved) {
            m.isApproved = true;
            _executeMilestoneRelease(_milestoneId);
        }
    }

    /**
     * @dev Internal function to release funds automatically once majority voting threshold is met.
     */
    function _executeMilestoneRelease(uint256 _milestoneId) internal nonReentrant {
        Milestone storage m = milestones[_milestoneId];
        require(m.isApproved, "Milestone not approved");
        require(!m.isExecuted, "Milestone already executed");

        m.isExecuted = true;
        uint256 releaseAmount = (fundingGoal * m.releasePercent) / 100;
        if (releaseAmount > address(this).balance) {
            releaseAmount = address(this).balance;
        }

        (bool success, ) = owner.call{value: releaseAmount}("");
        require(success, "ETH transfer failed");

        emit MilestoneApproved(_milestoneId, releaseAmount);
    }

    /**
     * @dev Pro-rata refund to contributors if campaign fails to reach goal by deadline.
     */
    function claimRefund() external nonReentrant {
        require(block.timestamp >= deadline, "Deadline not reached yet");
        require(currentAmount < fundingGoal, "Funding goal was met, refunds disabled");
        require(contributions[msg.sender] > 0, "No contribution to refund");

        uint256 refundAmount = contributions[msg.sender];
        contributions[msg.sender] = 0;

        (bool success, ) = msg.sender.call{value: refundAmount}("");
        require(success, "Refund transfer failed");

        emit RefundIssued(msg.sender, refundAmount);
    }

    /**
     * @dev Helper to get total number of milestones
     */
    function getMilestoneCount() external view returns (uint256) {
        return milestones.length;
    }
}
