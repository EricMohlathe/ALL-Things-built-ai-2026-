//! godmode-replay — CLI tool for replaying a CSV bar feed through the engine.
//!
//! Usage:
//!     godmode-replay --bars path/to/bars.csv [--config path/to/cfg.json]
//!
//! Outputs a newline-delimited JSON stream of `EngineEvent`s on stdout, so
//! the caller can pipe through `jq`, write to a file, or feed into the
//! conformance comparator.

use std::path::PathBuf;

use clap::Parser;
use godmode_engine::{
    common::{AccountState, OpMode},
    engine::{Engine, EngineConfig},
    replay::{read_bars, replay_bars, ReplayConfig},
};

#[derive(Parser, Debug)]
#[command(name = "godmode-replay")]
#[command(about = "Replay bar CSV through the godmode_engine and emit JSON events")]
struct Cli {
    /// Path to bar CSV with columns: ts,open,high,low,close,volume
    #[arg(long)]
    bars: PathBuf,

    /// Optional engine config JSON. Defaults to EngineConfig::default().
    #[arg(long)]
    config: Option<PathBuf>,

    /// Account equity to seed the risk manager with.
    #[arg(long, default_value_t = 10_000.0)]
    equity: f64,

    /// Pip size (e.g. 0.0001 for EURUSD on 5-digit broker).
    #[arg(long, default_value_t = 0.0001)]
    pip_size: f64,

    /// Tick size (e.g. 0.00001 on 5-digit broker).
    #[arg(long, default_value_t = 0.00001)]
    tick_size: f64,

    /// Pip value per 1.00 lot in account currency.
    #[arg(long, default_value_t = 10.0)]
    pip_value: f64,

    /// Override mode: manual or auto.
    #[arg(long, default_value = "manual")]
    mode: String,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let mut config: EngineConfig = if let Some(p) = &cli.config {
        let s = std::fs::read_to_string(p)?;
        serde_json::from_str(&s)?
    } else {
        EngineConfig::default()
    };
    config.mode = match cli.mode.to_lowercase().as_str() {
        "auto" => OpMode::Auto,
        _ => OpMode::Manual,
    };

    let bars = read_bars(&cli.bars)?;
    if bars.is_empty() {
        anyhow::bail!("bar file empty: {}", cli.bars.display());
    }
    let now = bars[0].ts_close;
    let account = AccountState {
        equity: cli.equity,
        balance: cli.equity,
        spread: cli.tick_size * 2.0,
        pip_size: cli.pip_size,
        tick_size: cli.tick_size,
        pip_value: cli.pip_value,
        volume_step: 0.01,
        volume_min: 0.01,
    };
    let mut engine = Engine::new(config, account, now);
    let cfg = ReplayConfig {
        account,
        atr14: cli.pip_size * 50.0, // crude default; shell should pass real ATR
        correlated_cvd_slope: 0.0,
    };
    let events = replay_bars(&mut engine, &bars, cfg);

    let stdout = std::io::stdout();
    let mut out = stdout.lock();
    use std::io::Write;
    for ev in &events {
        writeln!(out, "{}", serde_json::to_string(ev)?)?;
    }
    eprintln!(
        "godmode-replay: emitted {} events from {} bars",
        events.len(),
        bars.len()
    );
    Ok(())
}
