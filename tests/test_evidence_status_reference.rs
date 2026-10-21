use std::collections::BTreeMap;

const BACKENDS: &[&str] = &["java", "llvm", "wasm", "forge", "net"];

#[derive(Clone, Debug, PartialEq, Eq)]
enum Value {
    Bool(bool),
    Int(i64),
    Str(String),
    List,
}

type Report = BTreeMap<&'static str, Value>;

fn valid_hex(value: &str, len: usize) -> bool {
    value.len() == len
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn string_field<'a>(report: &'a Report, key: &str) -> Option<&'a str> {
    match report.get(key) {
        Some(Value::Str(value)) => Some(value),
        _ => None,
    }
}

fn int_field(report: &Report, key: &str) -> Option<i64> {
    match report.get(key) {
        Some(Value::Int(value)) => Some(*value),
        _ => None,
    }
}

fn bool_field(report: &Report, key: &str) -> Option<bool> {
    match report.get(key) {
        Some(Value::Bool(value)) => Some(*value),
        _ => None,
    }
}

fn classify(report: &Report) -> Result<&'static str, String> {
    let backend = string_field(report, "backend").ok_or("unknown backend/receipt")?;
    if !BACKENDS.contains(&backend) {
        return Err("unknown backend/receipt".into());
    }

    if bool_field(report, "supported") != Some(true) {
        return Ok("REFERENCE_ONLY");
    }

    let steps = int_field(report, "executed_steps").ok_or("invalid step count")?;
    if !(0..=100_000).contains(&steps) {
        return Err("invalid step count".into());
    }
    if steps == 0 {
        return Ok("NO_STEPS");
    }

    for (key, len) in [
        ("checkout_sha", 40_usize),
        ("compiler_binary_sha256", 64),
        ("guest_source_sha256", 64),
    ] {
        let value = string_field(report, key)
            .ok_or_else(|| format!("invalid or missing {key}"))?;
        if !valid_hex(value, len) {
            return Err(format!("invalid or missing {key}"));
        }
    }

    if int_field(report, "guest_exit") != Some(0)
        || bool_field(report, "timeout") != Some(false)
    {
        return Ok("EXECUTED_UNATTESTED");
    }

    if bool_field(report, "tests_passed") != Some(true)
        || int_field(report, "tests_skipped") != Some(0)
    {
        return Ok("EXECUTED_UNATTESTED");
    }

    // Integrity of self-reported fields is not independent authentication of
    // source-to-binary provenance. A trusted builder and pinned provenance are
    // still required before any stronger status could be introduced.
    Ok("EXECUTED_UNATTESTED")
}

fn good_report() -> Report {
    BTreeMap::from([
        ("backend", Value::Str("java".into())),
        ("supported", Value::Bool(true)),
        ("executed_steps", Value::Int(3)),
        ("checkout_sha", Value::Str("a".repeat(40))),
        ("compiler_binary_sha256", Value::Str("b".repeat(64))),
        ("guest_source_sha256", Value::Str("c".repeat(64))),
        ("guest_exit", Value::Int(0)),
        ("timeout", Value::Bool(false)),
        ("tests_passed", Value::Bool(true)),
        ("tests_skipped", Value::Int(0)),
    ])
}

#[test]
fn never_promotes_unattested_execution() {
    for backend in BACKENDS {
        let mut report = good_report();
        report.insert("backend", Value::Str((*backend).into()));
        assert_eq!(classify(&report).unwrap(), "EXECUTED_UNATTESTED");
    }
}

#[test]
fn zero_step_is_not_test_failure_or_success() {
    let mut report = good_report();
    report.insert("executed_steps", Value::Int(0));
    assert_eq!(classify(&report).unwrap(), "NO_STEPS");
}

#[test]
fn unsupported_is_not_passing() {
    let mut report = good_report();
    report.insert("supported", Value::Bool(false));
    assert_eq!(classify(&report).unwrap(), "REFERENCE_ONLY");
}

#[test]
fn missing_digests_and_fake_steps_fail_closed() {
    let changes = [
        ("executed_steps", Value::Bool(true)),
        ("executed_steps", Value::Int(-1)),
        ("checkout_sha", Value::Str("z".repeat(40))),
        ("compiler_binary_sha256", Value::Str("b".into())),
        ("guest_source_sha256", Value::Str("c".repeat(40))),
        ("checkout_sha", Value::List),
        ("compiler_binary_sha256", Value::List),
    ];

    for (key, value) in changes {
        let mut report = good_report();
        report.insert(key, value);
        assert!(classify(&report).is_err(), "{key}");
    }

    let mut missing = good_report();
    missing.remove("checkout_sha");
    assert!(classify(&missing).is_err());
}

#[test]
fn skips_and_runtime_failure_cannot_upgrade() {
    let changes = [
        ("tests_skipped", Value::Int(1)),
        ("guest_exit", Value::Int(1)),
        ("timeout", Value::Bool(true)),
        ("tests_passed", Value::Bool(false)),
        ("guest_exit", Value::Bool(false)),
        ("tests_skipped", Value::Bool(false)),
    ];

    for (key, value) in changes {
        let mut report = good_report();
        report.insert(key, value);
        assert_eq!(classify(&report).unwrap(), "EXECUTED_UNATTESTED", "{key}");
    }
}
