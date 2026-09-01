"""Optional live smoke test against public Routescan and RugCheck endpoints."""

from rugbuster_memory_firewall import DeployerResolver, ResolutionError

SAMPLES = (
    ("avax", "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"),
    ("solana", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
)


def main() -> None:
    resolver = DeployerResolver()
    failures = 0
    for chain, token in SAMPLES:
        try:
            result = resolver.resolve(chain=chain, token_address=token)
            print(f"{chain}_live_ok=true")
            print(f"{chain}_deployer={result.deployer_address}")
            print(f"{chain}_source={result.source}")
            print(f"{chain}_evidence={result.evidence_uri}")
        except ResolutionError as error:
            failures += 1
            print(f"{chain}_live_ok=false")
            print(f"{chain}_error={error}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

