"""HTTP pre-sign API for the RugBuster Memory Firewall."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from sibyl_memory_client import MemoryClient

from .firewall import Decision, MemoryFirewall
from .resolver import DeployerResolver, ResolutionError, ResolvedDeployer, same_deployer
from .seed import seed_verified_case
from .x402 import X402Settings, install_x402_middleware


class PreSignRequest(BaseModel):
    chain: Literal["avax", "solana"]
    token_address: str = Field(min_length=32, max_length=64)
    deployer_address: str | None = Field(default=None, min_length=32, max_length=64)
    current_risk: Literal["clean", "warning", "critical"]
    action: dict[str, Any]
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class PreSignResponse(BaseModel):
    verdict: str
    chain: str
    token_address: str
    deployer_address: str
    current_risk: str
    action_hash: str
    reason_codes: list[str]
    evidence_count: int
    history: list[dict[str, Any]]
    evidence_sources: list[str]
    resolver_source: str
    resolver_evidence_uri: str
    memory_evidence_hash: str | None
    decision_hash: str
    policy_version: str
    base_tx_url: str | None


def _response(decision: Decision, resolved: ResolvedDeployer) -> PreSignResponse:
    return PreSignResponse(
        verdict=decision.verdict,
        chain=resolved.chain,
        token_address=resolved.token_address,
        deployer_address=resolved.deployer_address,
        current_risk=decision.current_risk,
        action_hash=decision.action_hash,
        reason_codes=list(decision.reason_codes),
        evidence_count=decision.evidence_count,
        history=list(decision.history),
        evidence_sources=list(dict.fromkeys((resolved.evidence_uri, *decision.evidence_sources))),
        resolver_source=resolved.source,
        resolver_evidence_uri=resolved.evidence_uri,
        memory_evidence_hash=decision.memory_evidence_hash,
        decision_hash=decision.decision_hash,
        policy_version=decision.policy_version,
        base_tx_url=decision.base_tx_url,
    )


def create_app(
    *,
    memory: MemoryClient | None = None,
    resolver: DeployerResolver | None = None,
    x402_settings: X402Settings | None = None,
    x402_server: Any | None = None,
) -> FastAPI:
    if memory is None:
        db_path = Path(os.getenv("RUGBUSTER_MEMORY_DB", "~/.sibyl-memory/memory.db")).expanduser()
        memory = MemoryClient.local(str(db_path))
    seed_path = os.getenv("RUGBUSTER_SEED_VERIFIED_CASE", "").strip()
    if seed_path:
        seed_verified_case(memory, Path(seed_path))

    settings = x402_settings or X402Settings.from_env()
    facilitator: Any | None = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        if facilitator is not None:
            await facilitator.aclose()
        storage = getattr(memory, "_storage", None)
        if storage is not None:
            storage.close()

    app = FastAPI(
        title="RugBuster Memory Firewall",
        version="0.1.0",
        lifespan=lifespan,
    )
    firewall = MemoryFirewall(memory)
    deployer_resolver = resolver or DeployerResolver()

    def evaluate(request: PreSignRequest) -> PreSignResponse:
        try:
            resolved = deployer_resolver.resolve(
                chain=request.chain, token_address=request.token_address
            )
        except ResolutionError as error:
            raise HTTPException(status_code=424, detail={"code": "DEPLOYER_UNRESOLVED"}) from error

        if request.deployer_address and not same_deployer(
            request.chain, request.deployer_address, resolved.deployer_address
        ):
            raise HTTPException(status_code=409, detail={"code": "DEPLOYER_MISMATCH"})

        decision = firewall.pre_sign(
            chain=request.chain,
            token_address=resolved.token_address,
            deployer=resolved.deployer_address,
            current_risk=request.current_risk,
            action=request.action,
            session_id=request.session_id,
        )
        return _response(decision, resolved)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "memory_policy": "required"}

    @app.post("/v1/pre-sign", response_model=PreSignResponse)
    def pre_sign(request: PreSignRequest) -> PreSignResponse:
        return evaluate(request)

    @app.post("/v1/x402/pre-sign", response_model=PreSignResponse)
    def paid_pre_sign(request: PreSignRequest, response: Response) -> PreSignResponse:
        if not settings.enabled:
            raise HTTPException(status_code=503, detail={"code": "X402_NOT_ENABLED"})
        result = evaluate(request)
        response.headers["X-RugBuster-Decision-Hash"] = result.decision_hash
        if result.memory_evidence_hash:
            response.headers["X-RugBuster-Memory-Evidence-Hash"] = result.memory_evidence_hash
        return result

    @app.get("/.well-known/x402")
    def x402_status() -> dict[str, Any]:
        return settings.public_status()

    facilitator = install_x402_middleware(app, settings, server=x402_server)

    return app
