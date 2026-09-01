// SPDX-License-Identifier: MIT
pragma solidity 0.8.34;

/// @title DecisionReceiptRegistry
/// @notice Immutable audit receipts for offchain RugBuster policy decisions.
contract DecisionReceiptRegistry {
    enum Verdict {
        ALLOW,
        WARN,
        BLOCK
    }

    struct Receipt {
        bytes32 memoryEvidenceHash;
        uint64 recordedAt;
        Verdict verdict;
        address submitter;
        string policyVersion;
    }

    error DecisionHashRequired();
    error PolicyVersionRequired();
    error DecisionAlreadyRecorded(bytes32 decisionHash);

    event DecisionRecorded(
        bytes32 indexed decisionHash,
        address indexed submitter,
        Verdict indexed verdict,
        bytes32 memoryEvidenceHash,
        uint64 recordedAt,
        string policyVersion
    );

    mapping(bytes32 decisionHash => Receipt receipt) public receipts;

    function recordDecision(
        bytes32 decisionHash,
        bytes32 memoryEvidenceHash,
        Verdict verdict,
        string calldata policyVersion
    ) external {
        if (decisionHash == bytes32(0)) revert DecisionHashRequired();
        if (bytes(policyVersion).length == 0) revert PolicyVersionRequired();
        if (receipts[decisionHash].recordedAt != 0) {
            revert DecisionAlreadyRecorded(decisionHash);
        }

        uint64 recordedAt = uint64(block.timestamp);
        receipts[decisionHash] = Receipt({
            memoryEvidenceHash: memoryEvidenceHash,
            recordedAt: recordedAt,
            verdict: verdict,
            submitter: msg.sender,
            policyVersion: policyVersion
        });

        emit DecisionRecorded(
            decisionHash,
            msg.sender,
            verdict,
            memoryEvidenceHash,
            recordedAt,
            policyVersion
        );
    }

    function hasReceipt(bytes32 decisionHash) external view returns (bool) {
        return receipts[decisionHash].recordedAt != 0;
    }
}
