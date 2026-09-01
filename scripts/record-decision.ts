import { network } from "hardhat";

const VERDICTS = {
  ALLOW: 0,
  WARN: 1,
  BLOCK: 2,
} as const;

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

const { ethers } = await network.create({ network: "baseSepolia" });
const chainId = (await ethers.provider.getNetwork()).chainId;
if (chainId !== 84532n) {
  throw new Error(`Refusing to record on unexpected chain ${chainId}`);
}

const contractAddress = required("BASE_RECEIPT_REGISTRY");
const decisionHash = required("DECISION_HASH");
const memoryEvidenceHash = required("MEMORY_EVIDENCE_HASH");
const policyVersion = required("POLICY_VERSION");
const verdictName = required("VERDICT").toUpperCase() as keyof typeof VERDICTS;
const verdict = VERDICTS[verdictName];
if (verdict === undefined) throw new Error("VERDICT must be ALLOW, WARN, or BLOCK");
if (!ethers.isHexString(decisionHash, 32)) throw new Error("DECISION_HASH must be bytes32");
if (!ethers.isHexString(memoryEvidenceHash, 32)) {
  throw new Error("MEMORY_EVIDENCE_HASH must be bytes32");
}

const registry = await ethers.getContractAt(
  "DecisionReceiptRegistry",
  contractAddress,
);
if (await registry.hasReceipt(decisionHash)) {
  throw new Error(`Decision ${decisionHash} is already recorded`);
}

const transaction = await registry.recordDecision(
  decisionHash,
  memoryEvidenceHash,
  verdict,
  policyVersion,
);
const receipt = await transaction.wait();
if (receipt?.status !== 1) throw new Error("Base receipt transaction failed");

console.log(
  JSON.stringify(
    {
      chainId: chainId.toString(),
      contractAddress,
      transactionHash: transaction.hash,
      explorerUrl: `https://sepolia-explorer.base.org/tx/${transaction.hash}`,
      decisionHash,
      memoryEvidenceHash,
      verdict: verdictName,
      policyVersion,
    },
    null,
    2,
  ),
);
