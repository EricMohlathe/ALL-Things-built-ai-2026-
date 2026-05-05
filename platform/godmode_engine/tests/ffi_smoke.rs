//! FFI smoke test — only runs when the `ffi` feature is enabled.
//!
//! Verifies the round-trip: alloc → write JSON config → engine_new →
//! push a bar → read events bytes → drop. This is the path the WASM and
//! cdylib hosts exercise.

#![cfg(feature = "ffi")]

use godmode_engine::engine::EngineConfig;
use godmode_engine::ffi::*;

#[test]
fn ffi_round_trip_emits_events_for_a_bar() {
    let cfg = EngineConfig::default();
    let json = serde_json::to_string(&cfg).expect("serialise config");
    let bytes = json.as_bytes();
    let ptr = gme_alloc(bytes.len());
    assert!(!ptr.is_null());
    unsafe { std::ptr::copy_nonoverlapping(bytes.as_ptr(), ptr, bytes.len()) };
    let h = unsafe { gme_engine_new(ptr, bytes.len()) };
    assert!(h != 0, "gme_engine_new returned zero handle");

    let events = gme_engine_on_bar(
        h,
        1714900000,
        1.0830, 1.0833, 1.0828, 1.0832, 1000.0,
        10_000.0,
    );
    assert!(events >= 1, "expected at least one event; got {events}");

    let len = gme_events_len(h);
    assert!(len > 0, "events buffer empty");
    let p = gme_events_ptr(h);
    let slice = unsafe { std::slice::from_raw_parts(p, len) };
    let s = std::str::from_utf8(slice).expect("events utf8");
    assert!(s.contains("\"Gate\""), "expected at least one Gate event in: {s}");

    gme_events_clear(h);
    assert_eq!(gme_events_len(h), 0);

    gme_engine_drop(h);
    unsafe { gme_free(ptr, bytes.len()) };
    assert_eq!(gme_version(), 0x0001_0000);
}
