use serde_json::{json, Map, Value};

const BACKENDS: &[&str] = &["java", "llvm", "wasm", "forge", "net"];

fn lower_hex(value: &str, len: usize) -> bool {
    value.len() == len
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn classify(report: &Value) -> Result<&'static str, &'static str> {
    let object = report
        .as_object()
        .ok_or("unknown backend/receipt")?;
    let backend = object
        .get("backend")
        .and_then(Value::as_str)
        .ok_or("unknown backend/receipt")?;
    if !BACKENDS.contains(&backend) {
        return Err("unknown backend/receipt");
    }

    if object.get("supported").and_then(Value::as_bool) != Some(true) {
        return Ok("REFERENCE_ONLY");
    }

    let steps = object
        .get("executed_steps")
        .and_then(Value::as_i64)
        .ok_or("invalid step count")?;
    if !(0..=100_000).contains(&steps) {
        return Err("invalid step count");
    }
    if steps == 0 {
        return Ok("NO_STEPS");
    }

    for (key, len) in [
        ("checkout_sha", 40),
        ("compiler_binary_sha256", 64),
        ("guest_source_sha256", 64),
    ] {
        let value = object
            .get(key)
            .and_then(Value::as_str)
            .ok_or("invalid or missing digest")?;
        if !lower_hex(value, len) {
            return Err("invalid or missing digest");
        }
    }

    let guest_exit_is_zero = object
        .get("guest_exit")
        .and_then(Value::as_i64)
        == Some(0);
    let timeout_is_false = object
        .get("timeout")
        .and_then(Value::as_bool)
        == Some(false);
    if !guest_exit_is_zero || !timeout_is_false {
        return Ok("EXECUTED_UNATTESTED");
    }

    let tests_passed = object
        .get("tests_passed")
        .and_then(Value::as_bool)
        == Some(true);
    let tests_skipped_zero = object
        .get("tests_skipped")
        .and_then(Value::as_i64)
        == Some(0);
    if !tests_passed || !tests_skipped_zero {
        return Ok("EXECUTED_UNATTESTED");
    }

    // Integrity of self-reported fields is not independent source-to-binary
    // authentication. A trusted builder, immutable provenance and independent
    // review are still required before any VERIFIED_BACKEND classification.
    Ok("EXECUTED_UNATTESTED")
}

fn good() -> Value {
    json!({
        "backend": "java",
        "supported": true,
        "executed_steps": 3,
        "checkout_sha": "a".repeat(40),
        "compiler_binary_sha256": "b".repeat(64),
        "guest_source_sha256": "c".repeat(64),
        "guest_exit": 0,
        "timeout": false,
        "tests_passed": true,
        "tests_skipped": 0
    })
}

fn patched(mut base: Value, key: &str, value: Value) -> Value {
    base.as_object_mut().unwrap().insert(key.to_owned(), value);
    base
}

#[test]
fn never_promotes_unattested_execution() {
    for backend in BACKENDS {
        assert_eq!(
            classify(&patched(good(), "backend", json!(backend))).unwrap(),
            "EXECUTED_UNATTESTED"
        );
    }
}

#[test]
fn zero_step_is_not_test_failure_or_success() {
    assert_eq!(
        classify(&patched(good(), "executed_steps", json!(0))).unwrap(),
        "NO_STEPS"
    );
}

#[test]
fn unsupported_is_reference_only() {
    assert_eq!(
        classify(&patched(good(), "supported", json!(false))).unwrap(),
        "REFERENCE_ONLY"
    );
}

#[test]
fn missing_digests_and_fake_steps_fail_closed() {
    let invalid = [
        ("executed_steps", json!(true)),
        ("executed_steps", json!(-1)),
        ("checkout_sha", json!("z".repeat(40))),
        ("compiler_binary_sha256", json!("b")),
        ("guest_source_sha256", json!("c".repeat(40))),
        ("checkout_sha", Value::Null),
        ("compiler_binary_sha256", json!([])),
    ];
    for (key, value) in invalid {
        assert!(classify(&patched(good(), key, value)).is_err(), "{key}");
    }
}

#[test]
fn skips_and_runtime_failure_cannot_upgrade() {
    let changes = [
        ("tests_skipped", json!(1)),
        ("guest_exit", json!(1)),
        ("timeout", json!(true)),
        ("tests_passed", json!(false)),
        ("guest_exit", json!(false)),
        ("tests_skipped", json!(false)),
    ];
    for (key, value) in changes {
        assert_eq!(
            classify(&patched(good(), key, value)).unwrap(),
            "EXECUTED_UNATTESTED",
            "{key}"
        );
    }
}

#[test]
fn unknown_backend_and_non_object_fail_closed() {
    assert!(classify(&patched(good(), "backend", json!("cuda"))).is_err());
    assert!(classify(&json!([])).is_err());
}
