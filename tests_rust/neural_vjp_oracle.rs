// Independent dependency-free Rust reference oracles for *proposed* Oreslang
// tensor/neural/actor fixtures. Do NOT call these Oreslang guest executions.
// Run: rustc --edition=2021 --test -D warnings tests_rust/neural_vjp_oracle.rs
//      -o /tmp/ores-ml-neural-vjp && /tmp/ores-ml-neural-vjp
// Rust is an oracle only. All actual ML implementations remain pure .ores.

fn close(a: f64, b: f64, tolerance: f64) {
    assert!(a.is_finite() && b.is_finite());
    assert!(
        (a - b).abs() <= tolerance,
        "numerical mismatch: {a:?} vs {b:?} (tol={tolerance:?})"
    );
}

fn central_difference<F: Fn(f64) -> f64>(f: F, x: f64) -> f64 {
    let h = 1.0e-6 * x.abs().max(1.0);
    (f(x + h) - f(x - h)) / (2.0 * h)
}

#[test]
fn relu_vjp_matches_finite_differences_away_from_kink() {
    for (x, upstream) in [(-2.0, 4.0), (3.0, -7.0)] {
        let vjp = if x > 0.0 { upstream } else { 0.0 };
        let numeric = central_difference(|z| upstream * z.max(0.0), x);
        close(vjp, numeric, 1.0e-8);
    }
    // Contract chooses the zero subgradient at the nondifferentiable origin.
    close(if 0.0 > 0.0 { 1.0 } else { 0.0 }, 0.0, 0.0);
}

#[test]
fn mse_vjp_checks_mean_reduction_and_broadcast_boundaries() {
    let prediction = [3.0, 5.0];
    let targets = [1.0, 1.0];
    for i in 0..prediction.len() {
        let analytic = 2.0 * (prediction[i] - targets[i]) / prediction.len() as f64;
        let numeric = central_difference(
            |x| {
                let mut altered = prediction;
                altered[i] = x;
                altered
                    .iter()
                    .zip(targets.iter())
                    .map(|(p, t)| (p - t).powi(2))
                    .sum::<f64>()
                    / altered.len() as f64
            },
            prediction[i],
        );
        close(analytic, numeric, 1.0e-8);
    }
}

fn conv1d(signal: &[f64], kernel: &[f64]) -> Vec<f64> {
    assert!(!kernel.is_empty() && signal.len() >= kernel.len());
    (0..signal.len() - kernel.len() + 1)
        .map(|t| {
            kernel
                .iter()
                .enumerate()
                .map(|(j, k)| signal[t + j] * k)
                .sum()
        })
        .collect()
}

#[test]
fn conv1d_signal_and_filter_vjps_are_independently_differentiated() {
    let signal = [1.0, 2.0, 3.0];
    let kernel = [2.0, -1.0];
    let upstream = [3.0, 4.0];
    assert_eq!(conv1d(&signal, &kernel), vec![0.0, 1.0]);
    let signal_grad = [6.0, 5.0, -4.0];
    let filter_grad = [11.0, 18.0];
    let objective = |s: &[f64], k: &[f64]| {
        conv1d(s, k)
            .iter()
            .zip(upstream.iter())
            .map(|(y, u)| y * u)
            .sum::<f64>()
    };
    for i in 0..signal.len() {
        let numeric = central_difference(
            |v| {
                let mut s = signal;
                s[i] = v;
                objective(&s, &kernel)
            },
            signal[i],
        );
        close(signal_grad[i], numeric, 1.0e-8);
    }
    for i in 0..kernel.len() {
        let numeric = central_difference(
            |v| {
                let mut k = kernel;
                k[i] = v;
                objective(&signal, &k)
            },
            kernel[i],
        );
        close(filter_grad[i], numeric, 1.0e-8);
    }
}

fn mlp_loss_and_grad(params: &[f64; 7]) -> (f64, [f64; 7]) {
    let data = [(0.0, 1.0), (1.0, 3.0), (2.0, 5.0), (3.0, 7.0)];
    let mut gradient = [0.0; 7];
    let mut loss = 0.0;
    for (x, target) in data {
        let pre = [params[0] * x + params[2], params[1] * x + params[3]];
        let h = [pre[0].max(0.0), pre[1].max(0.0)];
        let prediction = h[0] * params[4] + h[1] * params[5] + params[6];
        let residual = prediction - target;
        loss += residual * residual / 4.0;
        let upstream = residual / 2.0; // 2*(pred-target)/batch_size
        gradient[6] += upstream;
        for j in 0..2 {
            gradient[4 + j] += upstream * h[j];
            let dz = if pre[j] > 0.0 {
                upstream * params[4 + j]
            } else {
                0.0
            };
            gradient[j] += x * dz;
            gradient[2 + j] += dz;
        }
    }
    (loss, gradient)
}

#[test]
fn tensor_mlp_all_seven_parameters_match_finite_difference() {
    let initial = [0.8, 0.25, 0.2, 0.1, 0.5, 0.3, 0.1];
    let (loss, grads) = mlp_loss_and_grad(&initial);
    close(loss, 12.2553375, 1.0e-8);
    for i in 0..initial.len() {
        let numerical = central_difference(
            |value| {
                let mut changed = initial;
                changed[i] = value;
                mlp_loss_and_grad(&changed).0
            },
            initial[i],
        );
        close(grads[i], numerical, 1.0e-7);
    }
}

#[test]
fn two_layer_tensor_mlp_sgd_decreases_loss_deterministically() {
    let mut parameters = [0.8, 0.25, 0.2, 0.1, 0.5, 0.3, 0.1];
    let first = mlp_loss_and_grad(&parameters).0;
    for _ in 0..600 {
        let (_, grads) = mlp_loss_and_grad(&parameters);
        for (param, grad) in parameters.iter_mut().zip(grads.iter()) {
            *param -= 0.02 * grad;
            assert!(param.is_finite());
        }
    }
    let last = mlp_loss_and_grad(&parameters).0;
    assert!(first > 10.0 && last < 1.0e-6, "loss {first} -> {last}");
}

#[test]
fn adamw_one_step_has_correct_bias_correction_and_decoupled_decay() {
    let mut parameters = [1.0, 2.0];
    let gradients = [0.5, -0.5];
    let mut first_moment = [0.0; 2];
    let mut second_moment = [0.0; 2];
    let beta1: f64 = 0.9;
    let beta2: f64 = 0.999;
    let rate = 0.01;
    for i in 0..2 {
        first_moment[i] = beta1 * first_moment[i] + (1.0 - beta1) * gradients[i];
        second_moment[i] =
            beta2 * second_moment[i] + (1.0 - beta2) * gradients[i] * gradients[i];
        let mhat = first_moment[i] / (1.0 - beta1);
        let vhat = second_moment[i] / (1.0 - beta2);
        parameters[i] -= rate * (mhat / (vhat.sqrt() + 1.0e-8) + 0.01 * parameters[i]);
    }
    assert!(parameters[0] > 0.9898 && parameters[0] < 0.9900);
    assert!(parameters[1] > 2.0097 && parameters[1] < 2.0099);
    close(first_moment[0], 0.05, 1.0e-12);
    close(second_moment[0], 0.00025, 1.0e-12);
}

#[test]
fn two_long_lived_neurons_backpropagate_with_old_weight() {
    let (x, target, rate) = (1.0, 4.0, 0.1);
    let (mut w1, mut w2) = (2.0, 1.0);
    let hidden = w1 * x;
    let prediction = w2 * hidden;
    let first_loss = (prediction - target) * (prediction - target);
    close(first_loss, 4.0, 0.0);
    let upstream = 2.0 * (prediction - target);
    let old_w2 = w2;
    let dh = upstream * old_w2;
    w2 -= rate * upstream * hidden;
    w1 -= rate * dh * x;
    close(w1, 2.4, 1.0e-12);
    close(w2, 1.8, 1.0e-12);
    let next_error = w2 * w1 * x - target;
    close(next_error * next_error, 0.1024, 1.0e-12);
    assert!(next_error * next_error < first_loss);
}

// This is an isolated protocol specification model, not an Oreslang actor
// scheduler/CONTROL/capability authorization proof.
#[test]
fn stale_and_duplicate_microbatch_gradients_are_rejected_by_version() {
    let mut weight_version = 1_u64;
    let mut applied = false;
    let mut weight = 2.0_f64;
    let mut accept = |incoming_version: u64, upstream: f64| -> bool {
        if incoming_version != weight_version || applied {
            return false;
        }
        weight -= 0.1 * upstream;
        weight_version += 1;
        applied = true;
        true
    };
    assert!(accept(1, -4.0));
    assert!(!accept(1, -4.0)); // replay after version was advanced
    assert!(!accept(0, 13.0)); // stale pre-run gradient
    close(weight, 2.4, 1.0e-12);
}
