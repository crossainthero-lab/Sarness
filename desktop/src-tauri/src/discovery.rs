//! Safe local discovery: reads `tailscale status --json` and probes only the
//! Sarness health endpoint of online peers (and localhost). No port scanning.

use serde::Serialize;
use std::time::Duration;

pub const ENGINE_PORT: u16 = 8742;

#[derive(Debug, Serialize, Clone)]
pub struct Candidate {
    pub name: String,
    pub dns_name: Option<String>,
    pub address: String,
    pub os: Option<String>,
    pub source: String,
    pub online: bool,
    pub engine: Option<serde_json::Value>,
}

pub async fn tailscale_peers() -> Vec<Candidate> {
    let out = match tokio::process::Command::new("tailscale").args(["status", "--json"]).output().await {
        Ok(o) if o.status.success() => o.stdout,
        _ => return vec![],
    };
    let Ok(v) = serde_json::from_slice::<serde_json::Value>(&out) else { return vec![] };
    let mut res = vec![];
    if let Some(peers) = v.get("Peer").and_then(|p| p.as_object()) {
        for p in peers.values() {
            let ip = p.get("TailscaleIPs").and_then(|a| a.as_array()).and_then(|a| {
                a.iter().filter_map(|x| x.as_str()).find(|s| !s.contains(':')).map(String::from)
            });
            let Some(ip) = ip else { continue };
            let dns = p.get("DNSName").and_then(|d| d.as_str()).map(|s| s.trim_end_matches('.').to_string()).filter(|s| !s.is_empty());
            res.push(Candidate {
                name: p.get("HostName").and_then(|h| h.as_str()).unwrap_or("peer").to_string(),
                dns_name: dns,
                address: ip,
                os: p.get("OS").and_then(|o| o.as_str()).map(String::from),
                source: "tailscale".into(),
                online: p.get("Online").and_then(|o| o.as_bool()).unwrap_or(false),
                engine: None,
            });
        }
    }
    res
}

pub async fn probe(client: &reqwest::Client, address: &str, port: u16) -> Option<serde_json::Value> {
    let host = if address.contains(':') { format!("[{address}]") } else { address.to_string() };
    let r = client
        .get(format!("http://{host}:{port}/v1/health"))
        .timeout(Duration::from_millis(1800))
        .send()
        .await
        .ok()?;
    let v: serde_json::Value = r.json().await.ok()?;
    (v.get("service").and_then(|s| s.as_str()) == Some("sarness-engine")).then_some(v)
}

pub async fn discover() -> Vec<Candidate> {
    let client = reqwest::Client::new();
    let mut cands = vec![Candidate {
        name: "This computer".into(),
        dns_name: Some("localhost".into()),
        address: "127.0.0.1".into(),
        os: None,
        source: "local".into(),
        online: true,
        engine: None,
    }];
    cands.extend(tailscale_peers().await);
    let futs = cands.iter().map(|c| {
        let client = client.clone();
        let addr = c.address.clone();
        let online = c.online;
        async move { if online { probe(&client, &addr, ENGINE_PORT).await } else { None } }
    });
    let results = futures_util::future::join_all(futs).await;
    for (c, r) in cands.iter_mut().zip(results) {
        c.engine = r;
    }
    // Engines first, then online peers, then the rest.
    cands.sort_by_key(|c| (c.engine.is_none(), !c.online, c.name.to_lowercase()));
    cands
}
