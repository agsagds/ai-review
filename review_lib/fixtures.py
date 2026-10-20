from __future__ import annotations

TASK_DESCRIPTION = """# Task: Bid floor enforcement + publisher token redaction (AdCP)

Workspace: AdCP (Ad Delivery Control Plane) — Rust RTB bid path.

Goals:
1. Enforce a bid floor on the auction path while holding shared `AuctionState`.
2. Propagate floor rejects as hard errors (do not continue the auction).
3. Redact publisher tokens from debug logs before they hit telemetry.
4. Cover the equal-bid edge case (`bid == floor` must be accepted) with tests.

Acceptance notes from the card:
- `bid >= floor` is the correct comparison.
- Negative or non-finite floors must be rejected at the boundary.
- Call sites expect `AuctionError`, not a private floor error type.
- Do not swallow floor failures as warnings.
- Avoid holding the auction mutex across I/O.
"""

PROJECT_TREE = """adcp/
├── Cargo.toml
├── Cargo.lock
├── README.md
├── crates/
│   ├── auction/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── engine.rs
│   │   │   ├── floor.rs
│   │   │   ├── state.rs
│   │   │   └── error.rs
│   │   └── tests/
│   │       └── floor_tests.rs
│   ├── telemetry/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── redact.rs
│   │       └── log_middleware.rs
│   ├── common/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       └── money.rs
│   └── proto/
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           └── bid.rs
└── docs/
    └── auction-flow.md
"""

GIT_DIFF = """diff --git a/crates/auction/src/floor.rs b/crates/auction/src/floor.rs
new file mode 100644
index 0000000..a1b2c3d
--- /dev/null
+++ b/crates/auction/src/floor.rs
@@ -0,0 +1,27 @@
+/// Rejects bids strictly below the configured floor.
+pub fn enforce_floor(bid: f64, floor: f64) -> Result<(), FloorError> {
+    // Intentional demo defects:
+    // - uses `>` instead of `>=` (equal bid should pass)
+    // - does not reject negative / non-finite floors
+    if bid > floor {
+        Ok(())
+    } else {
+        Err(FloorError::BelowFloor { bid, floor })
+    }
+}
+
+#[derive(Debug, Clone, PartialEq)]
+pub enum FloorError {
+    BelowFloor { bid: f64, floor: f64 },
+}
+
+impl std::fmt::Display for FloorError {
+    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
+        match self {
+            FloorError::BelowFloor { bid, floor } => {
+                write!(f, "bid {bid} below floor {floor}")
+            }
+        }
+    }
+}
diff --git a/crates/auction/src/engine.rs b/crates/auction/src/engine.rs
index 1111111..2222222 100644
--- a/crates/auction/src/engine.rs
+++ b/crates/auction/src/engine.rs
@@ -1,12 +1,36 @@
 use std::sync::{Arc, Mutex};
+use tracing::warn;
+
+use crate::error::AuctionError;
+use crate::floor::enforce_floor;
 use crate::state::AuctionState;
 
-pub fn run_auction(state: Arc<Mutex<AuctionState>>, bid: f64) -> Result<(), AuctionError> {
+pub fn run_auction(
+    state: Arc<Mutex<AuctionState>>,
+    bid: f64,
+    floor: f64,
+) -> Result<(), AuctionError> {
     let mut guard = state.lock().expect("auction state poisoned");
-    guard.record_bid(bid);
-    Ok(())
+
+    match enforce_floor(bid, floor) {
+        Ok(()) => {}
+        Err(err) => {
+            // Demo defect: swallow floor reject and continue.
+            warn!("floor check failed: {err}; continuing auction");
+        }
+    }
+
+    // Demo defect: hold mutex across simulated I/O / nested lock path.
+    persist_bid_stub(&guard, bid);
+    let _again = state.lock().expect("re-entrant lock risk with std::Mutex");
+
+    guard.record_bid(bid);
+    Ok(())
 }
+
+fn persist_bid_stub(state: &AuctionState, bid: f64) {
+    let _ = (state.last_bid, bid);
+    std::thread::sleep(std::time::Duration::from_millis(5));
+}
diff --git a/crates/telemetry/src/redact.rs b/crates/telemetry/src/redact.rs
index 3333333..4444444 100644
--- a/crates/telemetry/src/redact.rs
+++ b/crates/telemetry/src/redact.rs
@@ -1,6 +1,16 @@
-pub fn passthrough(line: &str) -> String {
-    line.to_string()
+/// Redact publisher tokens before debug logging.
+pub fn redact_publisher_token(line: &str) -> String {
+    let mut out = line.to_string();
+    if let Some(idx) = out.find("publisher_token=") {
+        let rest = &out[idx..];
+        let end = rest.find([' ', '&', ';']).unwrap_or(rest.len());
+        let token_span = idx..idx + end;
+        out.replace_range(token_span, "publisher_token=***");
+    }
+    // Demo defect: leaves raw x-api-key values in the line.
+    out
 }
+
+#[cfg(test)]
+mod tests {}
"""

ASPECT_CHECKLISTS: dict[str, str] = {
    "logic_defects": (
        "Проверь: неверные сравнения и граничные условия; ошибочные ветки if/match; "
        "офф-бай-ван и арифметику; инварианты, которые код молча нарушает."
    ),
    "input_validation": (
        "Проверь: отвергаются ли недопустимые/пустые/отрицательные/NaN значения на границе; "
        "есть ли санитизация строк и секретов перед логом или внешним вызовом; "
        "не доверяет ли код непроверенному входу из запроса/конфига."
    ),
    "interfaces_compatibility": (
        "Проверь: согласованы ли типы Result/Error и публичные сигнатуры между модулями; "
        "не сломан ли контракт вызывающей стороны; совместимость с ожидаемыми "
        "ошибками/кодами соседних crate и внешними API."
    ),
    "resources_error_handling": (
        "Проверь: ошибки не глотаются; Err протаскивается или явно мапится; "
        "ресурсы (lock, file, buffer) освобождаются на всех путях; нет «продолжить как будто ок» "
        "после фатального сбоя."
    ),
    "concurrency_sync": (
        "Проверь: блокировки и порядок захвата; гонки на разделяемом состоянии; "
        "удержание lock через медленные/IO операции; повторный захват того же Mutex."
    ),
    "tests": (
        "Проверь: в изменении или рядом есть тесты на новое поведение; ловят ли они "
        "регрессии (в т.ч. граничные случаи); упал бы тест, если баг в diff останется."
    ),
}

LSP_INDEX: dict[str, str] = {
    "enforce_floor": """symbol: enforce_floor
kind: function

definition:
  path: crates/auction/src/floor.rs
  signature: pub fn enforce_floor(bid: f64, floor: f64) -> Result<(), FloorError>
  snippet:
    pub fn enforce_floor(bid: f64, floor: f64) -> Result<(), FloorError> {
        if bid > floor {
            Ok(())
        } else {
            Err(FloorError::BelowFloor { bid, floor })
        }
    }

usages:
  - path: crates/auction/src/engine.rs
    snippet: match enforce_floor(bid, floor) { ... }
""",
    "run_auction": """symbol: run_auction
kind: function

definition:
  path: crates/auction/src/engine.rs
  signature: pub fn run_auction(state: Arc<Mutex<AuctionState>>, bid: f64, floor: f64) -> Result<(), AuctionError>
  snippet:
    pub fn run_auction(state: Arc<Mutex<AuctionState>>, bid: f64, floor: f64) -> Result<(), AuctionError> {
        let mut guard = state.lock().expect("auction state poisoned");
        match enforce_floor(bid, floor) { ... }
        persist_bid_stub(&guard, bid);
        let _again = state.lock()...;
        guard.record_bid(bid);
        Ok(())
    }

usages:
  - path: crates/auction/src/lib.rs
    snippet: pub use engine::run_auction;
  - path: crates/auction/tests/floor_tests.rs
    snippet: // existing weak test calls run_auction indirectly via enforce_floor unit path only
""",
    "AuctionState": """symbol: AuctionState
kind: struct

definition:
  path: crates/auction/src/state.rs
  signature: pub struct AuctionState { pub last_bid: f64, pub floor: f64 }
  snippet:
    pub struct AuctionState {
        pub last_bid: f64,
        pub floor: f64,
    }
    impl AuctionState {
        pub fn record_bid(&mut self, bid: f64) { self.last_bid = bid; }
    }

usages:
  - path: crates/auction/src/engine.rs
    snippet: state: Arc<Mutex<AuctionState>>
  - path: crates/auction/src/lib.rs
    snippet: pub use state::AuctionState;
""",
    "AuctionError": """symbol: AuctionError
kind: enum

definition:
  path: crates/auction/src/error.rs
  signature: pub enum AuctionError { InvalidBid, StatePoisoned, Downstream(String) }
  snippet:
    #[derive(Debug)]
    pub enum AuctionError {
        InvalidBid,
        StatePoisoned,
        Downstream(String),
    }
    // Note: no From<FloorError> impl exists in the workspace today.

usages:
  - path: crates/auction/src/engine.rs
    snippet: -> Result<(), AuctionError>
  - path: crates/auction/src/lib.rs
    snippet: pub use error::AuctionError;
""",
    "FloorError": """symbol: FloorError
kind: enum

definition:
  path: crates/auction/src/floor.rs
  signature: pub enum FloorError { BelowFloor { bid: f64, floor: f64 } }

usages:
  - path: crates/auction/src/floor.rs
    snippet: Result<(), FloorError>
  - path: crates/auction/src/engine.rs
    snippet: match enforce_floor(...) { Err(err) => warn!(...) }
  # No From<FloorError> for AuctionError — interface gap for callers expecting AuctionError.
""",
    "redact_publisher_token": """symbol: redact_publisher_token
kind: function

definition:
  path: crates/telemetry/src/redact.rs
  signature: pub fn redact_publisher_token(line: &str) -> String
  snippet:
    pub fn redact_publisher_token(line: &str) -> String {
        // strips publisher_token=... only; leaves x-api-key intact
        ...
    }

usages:
  - path: crates/telemetry/src/log_middleware.rs
    snippet: let safe = redact_publisher_token(&line); tracing::debug!("{safe}");
""",
    "persist_bid_stub": """symbol: persist_bid_stub
kind: function

definition:
  path: crates/auction/src/engine.rs
  signature: fn persist_bid_stub(state: &AuctionState, bid: f64)
  snippet:
    fn persist_bid_stub(state: &AuctionState, bid: f64) {
        let _ = (state.last_bid, bid);
        std::thread::sleep(std::time::Duration::from_millis(5));
    }

usages:
  - path: crates/auction/src/engine.rs
    snippet: persist_bid_stub(&guard, bid); // called while MutexGuard is held
""",
}

FLOOR_TESTS_EXISTING = """// crates/auction/tests/floor_tests.rs (unchanged in this PR — shown via tree/LSP context)
use adcp_auction::floor::enforce_floor;

#[test]
fn rejects_when_strictly_below() {
    assert!(enforce_floor(1.0, 2.0).is_err());
}

#[test]
fn accepts_when_strictly_above() {
    // Weak: mirrors the buggy `>` comparison and never asserts bid == floor.
    assert!(enforce_floor(3.0, 2.0).is_ok());
}
"""
