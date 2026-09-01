import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("DecisionReceiptRegistryModule", (module) => {
  const registry = module.contract("DecisionReceiptRegistry");

  return { registry };
});
