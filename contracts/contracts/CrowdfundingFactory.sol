// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * =============================================================================
 * Dual-Engine Crowdfunding Platform - Crowdfunding Factory Contract
 * =============================================================================
 * Factory pattern contract that deploys individual EquityCampaign and
 * LendingCampaign instances to the Ethereum blockchain.
 * Maintains a public registry of all deployed campaign contract addresses.
 * =============================================================================
 */

import "./EquityCampaign.sol";
import "./LendingCampaign.sol";

contract CrowdfundingFactory {
    // Array of deployed campaign addresses
    address[] public deployedCampaigns;

    // Struct summarizing deployed campaign info
    struct CampaignInfo {
        address campaignAddress;
        string title;
        string modelType; // "Equity" or "Lending"
        address owner;
    }

    CampaignInfo[] public campaignRegistry;

    event CampaignDeployed(address indexed campaignAddress, string modelType, string title, address owner);

    /**
     * @dev Deploys a new Equity Campaign smart contract.
     */
    function createEquityCampaign(
        string memory _title,
        string memory _description,
        uint256 _fundingGoal,
        uint256 _durationInDays
    ) external returns (address) {
        EquityCampaign newCampaign = new EquityCampaign(
            payable(msg.sender),
            _title,
            _description,
            _fundingGoal,
            _durationInDays
        );

        address campaignAddr = address(newCampaign);
        deployedCampaigns.push(campaignAddr);
        campaignRegistry.push(CampaignInfo(campaignAddr, _title, "Equity", msg.sender));

        emit CampaignDeployed(campaignAddr, "Equity", _title, msg.sender);
        return campaignAddr;
    }

    /**
     * @dev Deploys a new Lending Campaign smart contract.
     */
    function createLendingCampaign(
        string memory _title,
        string memory _description,
        uint256 _fundingGoal,
        uint256 _durationInDays,
        uint256 _interestRatePercent
    ) external returns (address) {
        LendingCampaign newCampaign = new LendingCampaign(
            payable(msg.sender),
            _title,
            _description,
            _fundingGoal,
            _durationInDays,
            _interestRatePercent
        );

        address campaignAddr = address(newCampaign);
        deployedCampaigns.push(campaignAddr);
        campaignRegistry.push(CampaignInfo(campaignAddr, _title, "Lending", msg.sender));

        emit CampaignDeployed(campaignAddr, "Lending", _title, msg.sender);
        return campaignAddr;
    }

    /**
     * @dev Returns all deployed campaign contract addresses.
     */
    function getDeployedCampaigns() external view returns (address[] memory) {
        return deployedCampaigns;
    }

    /**
     * @dev Returns full campaign registry info.
     */
    function getCampaignRegistry() external view returns (CampaignInfo[] memory) {
        return campaignRegistry;
    }
}
