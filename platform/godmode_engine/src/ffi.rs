//! Minimal `extern "C"` FFI surface.
//!
//! Goals:
//!   - Compile to `wasm32-unknown-unknown` and `cdylib` without pulling
//!     `wasm-bindgen` into the core crate.
//!   - Be callable from JS via the raw WebAssembly API, from Node.js via
//!     N-API loaders (e.g. `koffi`), and from C/C++ via a header file.
//!
//! Lifecycle:
//!   1. JS/host calls `gme_alloc(n)` to reserve `n` bytes in wasm memory.
//!   2. Host writes a JSON-encoded `EngineConfig` into that region.
//!   3. Host calls `gme_engine_new(ptr, len)` → returns an opaque handle (u32).
//!   4. Host calls `gme_engine_on_bar(handle, ts, o, h, l, c, v, equity)` once
//!      per closed bar; events are appended to an internal JSON buffer.
//!   5. Host calls `gme_events_ptr(handle)` and `gme_events_len(handle)` to
//!      copy the JSON events back out, then `gme_events_clear(handle)` to
//!      reset the buffer between bars.
//!   6. Host calls `gme_engine_drop(handle)` when finished.
//!
//! The FFI deliberately does not stream ticks — bar-close is the only
//! cross-boundary entry point for v0.1. Tick aggregation belongs to the
//! adapter layer (Phase 4); the host can pre-aggregate or use the CLI.

#![cfg(feature = "ffi")]

use std::collections::HashMap;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::sync::Mutex;

use chrono::{DateTime, TimeZone, Utc};
use once_cell::sync::Lazy;

use crate::common::{AccountState, Bar};
use crate::engine::{BarCloseInput, Engine, EngineConfig};

/// Run `f` and swallow any panic, returning `default` instead. Required at
/// every `extern "C"` boundary because unwinding across FFI is UB.
fn ffi_guard<T, F: FnOnce() -> T>(default: T, f: F) -> T {
    catch_unwind(AssertUnwindSafe(f)).unwrap_or(default)
}

/// Opaque handle handed back to the host. Host treats it as an integer.
pub type EngineHandle = u32;

struct Slot {
    engine: Engine,
    account: AccountState,
    bars: Vec<Bar>,
    pending_events: String,
}

static REGISTRY: Lazy<Mutex<HashMap<EngineHandle, Slot>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));
static NEXT_HANDLE: Lazy<Mutex<u32>> = Lazy::new(|| Mutex::new(1));

fn now_default() -> DateTime<Utc> {
    Utc.with_ymd_and_hms(2026, 5, 5, 0, 0, 0).unwrap()
}

/// Allocate `len` bytes inside the wasm module; host fills them, then passes
/// the pointer back to a function expecting `(ptr, len)`.
#[no_mangle]
pub extern "C" fn gme_alloc(len: usize) -> *mut u8 {
    let mut buf: Vec<u8> = Vec::with_capacity(len);
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

/// Free a buffer previously returned by `gme_alloc`.
///
/// # Safety
/// `ptr` and `len` must match a previous `gme_alloc` allocation.
#[no_mangle]
pub unsafe extern "C" fn gme_free(ptr: *mut u8, len: usize) {
    if ptr.is_null() {
        return;
    }
    let _ = Vec::from_raw_parts(ptr, len, len);
}

/// Construct an engine from a JSON-encoded `EngineConfig`. Returns 0 on error
/// (null pointer, zero length, invalid UTF-8, malformed JSON, or panic).
///
/// # Safety
/// `ptr` must be null or point to `len` bytes of valid UTF-8 JSON.
#[no_mangle]
pub unsafe extern "C" fn gme_engine_new(ptr: *const u8, len: usize) -> EngineHandle {
    if ptr.is_null() || len == 0 {
        return 0;
    }
    ffi_guard(0, || {
        // SAFETY: caller-asserted; null + zero-len already handled above.
        let bytes = unsafe { std::slice::from_raw_parts(ptr, len) };
        let cfg: EngineConfig = match std::str::from_utf8(bytes)
            .ok()
            .and_then(|s| serde_json::from_str(s).ok())
        {
            Some(c) => c,
            None => return 0,
        };
        let account = AccountState {
            equity: 10_000.0,
            balance: 10_000.0,
            spread: 0.00002,
            pip_size: 0.0001,
            tick_size: 0.00001,
            pip_value: 10.0,
            volume_step: 0.01,
            volume_min: 0.01,
        };
        let engine = Engine::new(cfg, account, now_default());
        let Ok(mut next) = NEXT_HANDLE.lock() else {
            return 0;
        };
        let handle = *next;
        // Avoid wrapping back to 0 (the "error" sentinel).
        *next = handle.wrapping_add(1);
        if *next == 0 {
            *next = 1;
        }
        let Ok(mut reg) = REGISTRY.lock() else {
            return 0;
        };
        reg.insert(
            handle,
            Slot {
                engine,
                account,
                bars: Vec::new(),
                pending_events: String::new(),
            },
        );
        handle
    })
}

/// Push a closed bar and run the gate pipeline. Events are appended (one JSON
/// object per line) to the internal buffer; read with `gme_events_*`.
///
/// `ts_unix` is the bar-close timestamp in seconds since UNIX epoch.
#[no_mangle]
pub extern "C" fn gme_engine_on_bar(
    handle: EngineHandle,
    ts_unix: i64,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    volume: f64,
    equity: f64,
) -> i32 {
    ffi_guard(-1, || {
        // Reject obviously-bogus inputs early. NaN/Inf in OHLC will produce
        // NaN comparisons inside the engine that propagate silently.
        if !(open.is_finite()
            && high.is_finite()
            && low.is_finite()
            && close.is_finite()
            && volume.is_finite()
            && equity.is_finite())
        {
            return -2;
        }
        let Ok(mut reg) = REGISTRY.lock() else {
            return -3;
        };
        let Some(slot) = reg.get_mut(&handle) else {
            return -1;
        };
        let ts = Utc
            .timestamp_opt(ts_unix, 0)
            .single()
            .unwrap_or_else(now_default);
        let bar = Bar {
            ts_open: ts,
            ts_close: ts,
            open,
            high,
            low,
            close,
            volume,
            bar_delta: None,
        };
        slot.bars.push(bar);
        let view: Vec<Bar> = slot.bars.iter().rev().copied().collect();
        let mut acct = slot.account;
        acct.equity = equity;
        let events = slot.engine.on_bar_close(BarCloseInput {
            bars: &view,
            h4_closes: &[],
            d1_closes: &[],
            atr14: 0.0006,
            correlated_cvd_slope: 0.0,
            account: acct,
        });
        for ev in &events {
            if let Ok(s) = serde_json::to_string(ev) {
                slot.pending_events.push_str(&s);
                slot.pending_events.push('\n');
            }
        }
        events.len() as i32
    })
}

#[no_mangle]
pub extern "C" fn gme_events_ptr(handle: EngineHandle) -> *const u8 {
    ffi_guard(std::ptr::null(), || {
        REGISTRY
            .lock()
            .ok()
            .and_then(|r| r.get(&handle).map(|s| s.pending_events.as_ptr()))
            .unwrap_or(std::ptr::null())
    })
}

#[no_mangle]
pub extern "C" fn gme_events_len(handle: EngineHandle) -> usize {
    ffi_guard(0, || {
        REGISTRY
            .lock()
            .ok()
            .and_then(|r| r.get(&handle).map(|s| s.pending_events.len()))
            .unwrap_or(0)
    })
}

#[no_mangle]
pub extern "C" fn gme_events_clear(handle: EngineHandle) {
    ffi_guard((), || {
        if let Ok(mut reg) = REGISTRY.lock() {
            if let Some(s) = reg.get_mut(&handle) {
                s.pending_events.clear();
            }
        }
    })
}

#[no_mangle]
pub extern "C" fn gme_engine_drop(handle: EngineHandle) {
    ffi_guard((), || {
        if let Ok(mut reg) = REGISTRY.lock() {
            reg.remove(&handle);
        }
    });
}

#[no_mangle]
pub extern "C" fn gme_version() -> u32 {
    // major.minor.patch packed: 0.1.0 = 0x000100
    0x0001_0000
}
