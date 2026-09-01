import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.create({ network: "hardhatOp" });

describe("DecisionReceiptRegistry", function () {
  const decisionHash = `0x${"11".repeat(32)}`;
  const evidenceHash = `0x${"22".repeat(32)}`;
  const policyVersion = "rugbuster-memory-firewall/0.1.0";

  it("records an immutable BLOCK receipt with onchain provenance", async function () {
    const [submitter] = await ethers.getSigners();
    const registry = await ethers.deployContract("DecisionReceiptRegistry");
    const transaction = await registry.recordDecision(
      decisionHash,
      evidenceHash,
      2,
      policyVersion,
    );
    const mined = await transaction.wait();
    const block = await ethers.provider.getBlock(mined!.blockNumber);

    await expect(transaction)
      .to.emit(registry, "DecisionRecorded")
      .withArgs(
        decisionHash,
        submitter.address,
        2,
        evidenceHash,
        block!.timestamp,
        policyVersion,
      );

    const receipt = await registry.receipts(decisionHash);
    expect(receipt.memoryEvidenceHash).to.equal(evidenceHash);
    expect(receipt.recordedAt).to.equal(block!.timestamp);
    expect(receipt.verdict).to.equal(2);
    expect(receipt.submitter).to.equal(submitter.address);
    expect(receipt.policyVersion).to.equal(policyVersion);
    expect(await registry.hasReceipt(decisionHash)).to.equal(true);
  });

  it("rejects an empty decision hash", async function () {
    const registry = await ethers.deployContract("DecisionReceiptRegistry");

    await expect(
      registry.recordDecision(ethers.ZeroHash, evidenceHash, 0, policyVersion),
    ).to.be.revertedWithCustomError(registry, "DecisionHashRequired");
  });

  it("rejects an empty policy version", async function () {
    const registry = await ethers.deployContract("DecisionReceiptRegistry");

    await expect(
      registry.recordDecision(decisionHash, evidenceHash, 1, ""),
    ).to.be.revertedWithCustomError(registry, "PolicyVersionRequired");
  });

  it("cannot overwrite a decision receipt", async function () {
    const registry = await ethers.deployContract("DecisionReceiptRegistry");
    await registry.recordDecision(decisionHash, evidenceHash, 2, policyVersion);

    await expect(
      registry.recordDecision(decisionHash, ethers.ZeroHash, 0, "changed"),
    )
      .to.be.revertedWithCustomError(registry, "DecisionAlreadyRecorded")
      .withArgs(decisionHash);
  });
});
