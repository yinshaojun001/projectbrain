from __future__ import annotations

import sqlite3
from pathlib import Path


def create_payment_mini_codegraph_project(root: Path) -> dict[str, Path]:
    project_path = root / "payment-mini"
    db_path = project_path / ".codegraph" / "codegraph.db"
    db_path.parent.mkdir(parents=True)
    _write_codegraph_db(db_path)

    seed_path = project_path / "experience-seed.md"
    seed_path.write_text(
        "\n".join(
            [
                "# Payment Mini Experience Seed",
                "",
                "| id | claim_type | review_state | risk_level | applies_to | statement | confidence | source |",
                "| --- | --- | --- | --- | --- | --- | ---: | --- |",
                "| exp_settlement_contract | HUMAN_REVIEW_REQUIRED | pending | high | settlement; SettlementService | Settlement contract changes should be reviewed for API compatibility. | 0.8 | demo |",
            ]
        ),
        encoding="utf-8",
    )
    return {"project_path": project_path, "db_path": db_path, "experience_seed": seed_path}


def _write_codegraph_db(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(
            """
            create table files (
                path text primary key,
                language text,
                node_count integer,
                size integer
            );

            create table nodes (
                id text primary key,
                kind text,
                name text,
                qualified_name text,
                file_path text,
                language text,
                start_line integer,
                end_line integer,
                start_column integer,
                end_column integer,
                signature text,
                visibility text
            );

            create table edges (
                id text primary key,
                kind text,
                metadata text,
                line integer,
                col integer,
                provenance text,
                source text,
                target text
            );
            """
        )
        conn.executemany(
            "insert into files values (?, ?, ?, ?)",
            [
                ("contract/src/main/java/example/payment/settlement/SettlementService.java", "java", 2, 240),
                ("service/src/main/java/example/payment/settlement/SettlementServiceImpl.java", "java", 2, 360),
                ("service/src/test/java/example/payment/settlement/SettlementFlowTest.java", "java", 1, 180),
            ],
        )
        conn.executemany(
            "insert into nodes values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "interface:settlement-service",
                    "interface",
                    "SettlementService",
                    "example.payment.settlement::SettlementService",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                    "java",
                    1,
                    4,
                    1,
                    1,
                    None,
                    "public",
                ),
                (
                    "method:request-settlement",
                    "method",
                    "requestSettlement",
                    "example.payment.settlement::SettlementService::requestSettlement",
                    "contract/src/main/java/example/payment/settlement/SettlementService.java",
                    "java",
                    2,
                    3,
                    3,
                    1,
                    "SettlementResult requestSettlement(SettlementRequest request)",
                    "public",
                ),
                (
                    "class:settlement-service-impl",
                    "class",
                    "SettlementServiceImpl",
                    "example.payment.settlement::SettlementServiceImpl",
                    "service/src/main/java/example/payment/settlement/SettlementServiceImpl.java",
                    "java",
                    1,
                    8,
                    1,
                    1,
                    None,
                    "public",
                ),
                (
                    "method:impl-request-settlement",
                    "method",
                    "requestSettlement",
                    "example.payment.settlement::SettlementServiceImpl::requestSettlement",
                    "service/src/main/java/example/payment/settlement/SettlementServiceImpl.java",
                    "java",
                    3,
                    7,
                    3,
                    1,
                    "SettlementResult requestSettlement(SettlementRequest request)",
                    "public",
                ),
                (
                    "method:settlement-flow-test",
                    "method",
                    "requestSettlement",
                    "example.payment.settlement::SettlementFlowTest::requestSettlement",
                    "service/src/test/java/example/payment/settlement/SettlementFlowTest.java",
                    "java",
                    3,
                    6,
                    3,
                    1,
                    "void requestSettlement()",
                    "public",
                ),
            ],
        )
        conn.executemany(
            "insert into edges values (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "edge:contract-to-impl",
                    "calls",
                    "{}",
                    2,
                    3,
                    "synthetic",
                    "method:request-settlement",
                    "method:impl-request-settlement",
                ),
                (
                    "edge:test-to-contract",
                    "calls",
                    "{}",
                    4,
                    5,
                    "synthetic",
                    "method:settlement-flow-test",
                    "method:request-settlement",
                ),
                (
                    "edge:impl-interface",
                    "implements",
                    "{}",
                    1,
                    1,
                    "synthetic",
                    "class:settlement-service-impl",
                    "interface:settlement-service",
                ),
            ],
        )
