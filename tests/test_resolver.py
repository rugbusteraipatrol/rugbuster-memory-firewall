from typing import Any

import pytest

from rugbuster_memory_firewall import DeployerResolver, ResolutionError

AVAX_TOKEN = "0x" + "1" * 40
AVAX_DEPLOYER = "0x" + "2" * 40
AVAX_TX = "0x" + "a" * 64
SOLANA_TOKEN = "A" * 32
SOLANA_DEPLOYER = "B" * 32


class FakeTransport:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self.payload


def test_avax_uses_verified_contract_creation_record() -> None:
    transport = FakeTransport(
        {
            "status": "1",
            "result": [
                {
                    "contractAddress": AVAX_TOKEN.upper().replace("0X", "0x"),
                    "contractCreator": AVAX_DEPLOYER.upper().replace("0X", "0x"),
                    "txHash": AVAX_TX,
                }
            ],
        }
    )
    result = DeployerResolver(transport).resolve(chain="avax", token_address=AVAX_TOKEN)

    assert result.deployer_address == AVAX_DEPLOYER
    assert result.creation_tx_hash == AVAX_TX
    assert result.evidence_uri.endswith(AVAX_TX)
    assert transport.calls[0]["params"]["action"] == "getcontractcreation"


def test_solana_uses_top_level_rugcheck_creator() -> None:
    transport = FakeTransport({"creator": SOLANA_DEPLOYER})
    result = DeployerResolver(transport).resolve(chain="solana", token_address=SOLANA_TOKEN)

    assert result.deployer_address == SOLANA_DEPLOYER
    assert result.source == "rugcheck_full_report"
    assert SOLANA_TOKEN in transport.calls[0]["url"]


def test_solana_does_not_trust_market_deployer_fallback() -> None:
    transport = FakeTransport({"markets": [{"deployer": SOLANA_DEPLOYER}]})

    with pytest.raises(ResolutionError, match="no valid creator"):
        DeployerResolver(transport).resolve(chain="solana", token_address=SOLANA_TOKEN)


@pytest.mark.parametrize(
    ("chain", "token"),
    [("avax", "not-an-address"), ("solana", "0OIl")],
)
def test_invalid_token_address_fails_closed(chain: str, token: str) -> None:
    with pytest.raises(ResolutionError, match="invalid"):
        DeployerResolver(FakeTransport({})).resolve(chain=chain, token_address=token)


def test_avax_rejects_mismatched_contract_record() -> None:
    transport = FakeTransport(
        {
            "status": "1",
            "result": [
                {
                    "contractAddress": "0x" + "3" * 40,
                    "contractCreator": AVAX_DEPLOYER,
                    "txHash": AVAX_TX,
                }
            ],
        }
    )

    with pytest.raises(ResolutionError, match="failed validation"):
        DeployerResolver(transport).resolve(chain="avax", token_address=AVAX_TOKEN)

