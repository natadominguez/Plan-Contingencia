// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PlanRegistry - Registro inmutable de planes de contingencia
/// @notice Almacena hashes SHA-256 de planes como prueba de existencia e
///         integridad en un momento dado (util para auditorias).
contract PlanRegistry {
    struct Record {
        string planId;
        address owner;
        uint256 version;
        uint256 timestamp;
    }

    /// planHash => lista de attestaciones (una por version)
    mapping(bytes32 => Record[]) private _records;

    /// owner => planHashes registrados
    mapping(address => bytes32[]) private _byOwner;

    event PlanRegistered(
        bytes32 indexed planHash,
        string planId,
        address indexed owner,
        uint256 version,
        uint256 timestamp
    );

    function registerPlan(
        bytes32 planHash,
        string calldata planId,
        uint256 version
    ) external {
        _records[planHash].push(
            Record({
                planId: planId,
                owner: msg.sender,
                version: version,
                timestamp: block.timestamp
            })
        );
        _byOwner[msg.sender].push(planHash);
        emit PlanRegistered(planHash, planId, msg.sender, version, block.timestamp);
    }

    function getRecord(
        bytes32 planHash,
        uint256 index
    ) external view returns (Record memory) {
        return _records[planHash][index];
    }

    function recordCount(bytes32 planHash) external view returns (uint256) {
        return _records[planHash].length;
    }

    function exists(bytes32 planHash) external view returns (bool) {
        return _records[planHash].length > 0;
    }

    function plansOf(address owner) external view returns (bytes32[] memory) {
        return _byOwner[owner];
    }
}
