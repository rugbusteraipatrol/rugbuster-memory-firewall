"""Deterministic, load-bearing policy gate backed by Sibyl Memory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.exceptions import NotFoundError

Verdict = Literal["ALLOW", "WARN", "BLOCK", "MEMORY_REQUIRED"]
RiskLevel = Literal["clean", "warning", "critical"]
ObservationKind = Literal["warning", "critical"]

POLICY_VERSION = "rugbuster-memory-firewall/0.1.0"
EVM_CHAINS = frozenset({"avax", "avalanche"})
SUPPORTED_CHAINS = EVM_CHAINS | {"solana"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "0x" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class VerifiedObservation:
    """A source-backed historical signal suitable for a policy decision."""

    kind: ObservationKind
    source: str
    evidence_uri: str
    observed_at: str
    details: str
    evidence_id: str

    @classmethod
    def now(
        cls,
        *,
        kind: ObservationKind,
        source: str,
        evidence_uri: str,
        details: str,
    ) -> "VerifiedObservation":
        if kind not in {"warning", "critical"}:
            raise ValueError("kind must be 'warning' or 'critical'")
        if not source.strip() or not evidence_uri.strip() or not details.strip():
            raise ValueError("source, evidence_uri, and details are required")
        observed_at = _utc_now()
        evidence_id = _canonical_hash(
            {
                "kind": kind,
                "source": source.strip(),
                "evidence_uri": evidence_uri.strip(),
                "details": details.strip(),
            }
        )
        return cls(
            kind=kind,
            source=source.strip(),
            evidence_uri=evidence_uri.strip(),
            observed_at=observed_at,
            details=details.strip(),
            evidence_id=evidence_id,
        )


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    deployer_key: str
    token_address: str
    action_hash: str
    current_risk: RiskLevel
    reason_codes: tuple[str, ...]
    evidence_count: int
    history: tuple[dict[str, Any], ...]
    evidence_sources: tuple[str, ...]
    memory_evidence_hash: str | None
    policy_version: str
    decided_at: str
    decision_hash: str
    base_tx_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryFirewall:
    """Persist verified history and gate actions using a mandatory memory read."""

    def __init__(self, memory: MemoryClient | None) -> None:
        self.memory = memory

    def _get_deployer(self, key: str) -> dict[str, Any] | None:
        if self.memory is None:
            raise RuntimeError("memory layer is disabled")
        try:
            return self.memory.get_entity("deployer", key)
        except NotFoundError:
            return None

    @staticmethod
    def deployer_key(chain: str, address: str) -> str:
        normalized_chain = chain.strip().lower()
        raw_address = address.strip()
        if normalized_chain not in SUPPORTED_CHAINS:
            raise ValueError(f"unsupported chain: {chain}")
        if not raw_address:
            raise ValueError("deployer address is required")
        canonical_chain = "avax" if normalized_chain == "avalanche" else normalized_chain
        canonical_address = raw_address.lower() if canonical_chain in EVM_CHAINS else raw_address
        return f"{canonical_chain}:{canonical_address}"

    @staticmethod
    def _build_decision(
        *,
        verdict: Verdict,
        deployer_key: str,
        token_address: str,
        action: dict[str, Any],
        current_risk: RiskLevel,
        reason_codes: tuple[str, ...],
        evidence: list[dict[str, Any]],
    ) -> Decision:
        decided_at = _utc_now()
        action_hash = _canonical_hash({"action": action})
        evidence_hash = _canonical_hash({"observations": evidence}) if evidence else None
        evidence_sources = tuple(
            dict.fromkeys(
                str(item.get("evidence_uri"))
                for item in evidence
                if item.get("evidence_uri")
            )
        )
        unsigned = {
            "verdict": verdict,
            "deployer_key": deployer_key,
            "token_address": token_address,
            "action_hash": action_hash,
            "current_risk": current_risk,
            "reason_codes": reason_codes,
            "evidence_count": len(evidence),
            "history": tuple(evidence),
            "evidence_sources": evidence_sources,
            "memory_evidence_hash": evidence_hash,
            "policy_version": POLICY_VERSION,
            "decided_at": decided_at,
        }
        return Decision(**unsigned, decision_hash=_canonical_hash(unsigned))

    def record_observation(
        self,
        *,
        chain: str,
        deployer: str,
        observation: VerifiedObservation,
    ) -> dict[str, Any]:
        """Persist one unique verified observation in WARM and COLD tiers."""
        if self.memory is None:
            raise RuntimeError("Sibyl Memory is required to record evidence")
        key = self.deployer_key(chain, deployer)
        existing = self._get_deployer(key)
        body = dict(existing.get("body", {})) if existing else {}
        observations = list(body.get("observations", []))
        if any(item.get("evidence_id") == observation.evidence_id for item in observations):
            return existing

        observations.append(asdict(observation))
        body.update(
            {
                "chain": key.split(":", 1)[0],
                "deployer": key.split(":", 1)[1],
                "observations": observations,
                "last_seen": observation.observed_at,
                "confidence": "verified",
            }
        )
        saved = self.memory.set_entity("deployer", key, body, status="active")
        self.memory.write_event(
            evaluated={"deployer_key": key, "observation": asdict(observation)},
            acted={"action": "persist_verified_observation"},
            extra={"policy_version": POLICY_VERSION},
        )
        return saved

    def pre_sign(
        self,
        *,
        chain: str,
        token_address: str,
        deployer: str,
        current_risk: RiskLevel,
        action: dict[str, Any],
        session_id: str,
    ) -> Decision:
        """Return no actionable verdict unless every required memory call succeeds."""
        key = self.deployer_key(chain, deployer)
        if current_risk not in {"clean", "warning", "critical"}:
            raise ValueError("current_risk must be clean, warning, or critical")
        if not session_id.strip():
            raise ValueError("session_id is required")

        try:
            if self.memory is None:
                raise RuntimeError("memory layer is disabled")
            self.memory.set_reference(
                "risk-policy-current",
                {
                    "version": POLICY_VERSION,
                    "critical_history_threshold": 1,
                    "warning_history_threshold": 2,
                },
            )
            self.memory.set_state(
                f"analysis:{session_id}",
                {
                    "deployer_key": key,
                    "token_address": token_address,
                    "action_hash": _canonical_hash({"action": action}),
                    "current_risk": current_risk,
                    "status": "reading_memory",
                },
            )
            record = self._get_deployer(key)
            observations = list(record.get("body", {}).get("observations", [])) if record else []

            critical_count = sum(item.get("kind") == "critical" for item in observations)
            warning_ids = {
                item.get("evidence_id")
                for item in observations
                if item.get("kind") == "warning" and item.get("evidence_id")
            }

            if current_risk == "critical":
                verdict: Verdict = "BLOCK"
                reason_codes = ("BLOCK_CURRENT_CRITICAL_RISK",)
            elif critical_count >= 1:
                verdict = "BLOCK"
                reason_codes = ("BLOCK_REPEAT_DEPLOYER",)
            elif current_risk == "warning":
                verdict = "WARN"
                reason_codes = ("WARN_CURRENT_RISK",)
            elif len(warning_ids) >= 2:
                verdict = "WARN"
                reason_codes = ("WARN_REPEATED_PATTERN",)
            else:
                verdict = "ALLOW"
                reason_codes = ("ALLOW_CLEAN_CURRENT_AND_HISTORY",)

            decision = self._build_decision(
                verdict=verdict,
                deployer_key=key,
                token_address=token_address,
                action=action,
                current_risk=current_risk,
                reason_codes=reason_codes,
                evidence=observations,
            )
            self.memory.write_event(
                evaluated={"deployer_key": key, "evidence_count": len(observations)},
                acted=decision.as_dict(),
                extra={"session_id": session_id},
            )
            self.memory.set_state(
                f"analysis:{session_id}",
                {"deployer_key": key, "status": "complete", "decision_hash": decision.decision_hash},
            )
            return decision
        except Exception as error:
            return self._build_decision(
                verdict="MEMORY_REQUIRED",
                deployer_key=key,
                token_address=token_address,
                action=action,
                current_risk=current_risk,
                reason_codes=("MEMORY_UNAVAILABLE", error.__class__.__name__),
                evidence=[],
            )
