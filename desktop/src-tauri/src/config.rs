//! Connection profiles (non-secret, JSON on disk) and API tokens (OS keyring,
//! with a 0600 file fallback when no Secret Service is available).

use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::PathBuf;

const KEYRING_SERVICE: &str = "sarness";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ConnectionMode {
    Direct,
    Ssh,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SshOptions {
    pub user: String,
    pub host: String,
    #[serde(default = "default_ssh_port")]
    pub port: u16,
    #[serde(default)]
    pub key_path: Option<String>,
}

fn default_ssh_port() -> u16 {
    22
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Profile {
    pub id: String,
    pub name: String,
    /// Hostname, IP, Tailscale IP or MagicDNS name. For SSH mode this is the
    /// address the engine listens on *as seen from the server* (usually 127.0.0.1).
    pub host: String,
    pub port: u16,
    #[serde(default = "default_scheme")]
    pub scheme: String,
    pub mode: ConnectionMode,
    #[serde(default)]
    pub ssh: Option<SshOptions>,
    #[serde(default)]
    pub has_token: bool,
}

fn default_scheme() -> String {
    "http".into()
}

impl Profile {
    pub fn validate(&self) -> Result<(), String> {
        if self.name.trim().is_empty() {
            return Err("profile name is required".into());
        }
        if self.host.trim().is_empty() || self.host.contains(['/', ' ', '@']) {
            return Err("enter a hostname or IP address without scheme or path".into());
        }
        if self.port == 0 {
            return Err("port must be between 1 and 65535".into());
        }
        if !matches!(self.scheme.as_str(), "http" | "https") {
            return Err("scheme must be http or https".into());
        }
        if self.mode == ConnectionMode::Ssh {
            let ssh = self.ssh.as_ref().ok_or("SSH details are required for SSH mode")?;
            if ssh.user.trim().is_empty() || ssh.host.trim().is_empty() {
                return Err("SSH user and host are required".into());
            }
            if ssh.user.starts_with('-') || ssh.host.starts_with('-') {
                return Err("invalid SSH user or host".into());
            }
        }
        Ok(())
    }

    /// The engine base URL reachable from this machine (before any tunnel).
    pub fn direct_url(&self) -> String {
        let host = if self.host.contains(':') && !self.host.starts_with('[') {
            format!("[{}]", self.host)
        } else {
            self.host.clone()
        };
        format!("{}://{}:{}", self.scheme, host, self.port)
    }
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ProfileStore {
    #[serde(default)]
    pub profiles: Vec<Profile>,
    #[serde(default)]
    pub active: Option<String>,
}

pub fn config_dir() -> PathBuf {
    let d = dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")).join("sarness");
    let _ = fs::create_dir_all(&d);
    d
}

pub fn cache_dir() -> PathBuf {
    let d = dirs::cache_dir().unwrap_or_else(std::env::temp_dir).join("sarness");
    let _ = fs::create_dir_all(&d);
    d
}

fn profiles_path() -> PathBuf {
    config_dir().join("profiles.json")
}

impl ProfileStore {
    pub fn load() -> Self {
        fs::read_to_string(profiles_path())
            .ok()
            .and_then(|s| serde_json::from_str::<ProfileStore>(&s).ok())
            .map(|mut st| {
                for p in st.profiles.iter_mut() {
                    p.has_token = get_token(&p.id).is_some();
                }
                st
            })
            .unwrap_or_default()
    }

    pub fn save(&self) -> std::io::Result<()> {
        write_private(&profiles_path(), serde_json::to_string_pretty(self)?.as_bytes())
    }

    pub fn upsert(&mut self, p: Profile) {
        if let Some(existing) = self.profiles.iter_mut().find(|x| x.id == p.id) {
            *existing = p;
        } else {
            self.profiles.push(p);
        }
    }

    pub fn get(&self, id: &str) -> Option<&Profile> {
        self.profiles.iter().find(|p| p.id == id)
    }
}

pub fn write_private(path: &PathBuf, data: &[u8]) -> std::io::Result<()> {
    let tmp = path.with_extension("tmp");
    {
        let mut opts = fs::OpenOptions::new();
        opts.write(true).create(true).truncate(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            opts.mode(0o600);
        }
        let mut f = opts.open(&tmp)?;
        f.write_all(data)?;
        f.sync_all()?;
    }
    fs::rename(&tmp, path)
}

// ------------------------------------------------------------------ secrets
fn fallback_path() -> PathBuf {
    config_dir().join("secrets.json")
}

fn fallback_load() -> serde_json::Map<String, serde_json::Value> {
    fs::read_to_string(fallback_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn set_token(profile_id: &str, token: &str) -> Result<(), String> {
    match keyring::Entry::new(KEYRING_SERVICE, profile_id).and_then(|e| e.set_password(token)) {
        Ok(()) => {
            // Make sure no stale fallback copy lingers.
            let mut m = fallback_load();
            if m.remove(profile_id).is_some() {
                let _ = write_private(&fallback_path(), serde_json::to_string(&m).unwrap().as_bytes());
            }
            Ok(())
        }
        Err(e) => {
            log::warn!("keyring unavailable ({e}); storing token in a private file");
            let mut m = fallback_load();
            m.insert(profile_id.to_string(), serde_json::Value::String(token.to_string()));
            write_private(&fallback_path(), serde_json::to_string(&m).unwrap().as_bytes()).map_err(|e| e.to_string())
        }
    }
}

pub fn get_token(profile_id: &str) -> Option<String> {
    if let Ok(e) = keyring::Entry::new(KEYRING_SERVICE, profile_id) {
        if let Ok(t) = e.get_password() {
            return Some(t);
        }
    }
    fallback_load().get(profile_id).and_then(|v| v.as_str().map(String::from))
}

pub fn delete_token(profile_id: &str) {
    if let Ok(e) = keyring::Entry::new(KEYRING_SERVICE, profile_id) {
        let _ = e.delete_credential();
    }
    let mut m = fallback_load();
    if m.remove(profile_id).is_some() {
        let _ = write_private(&fallback_path(), serde_json::to_string(&m).unwrap().as_bytes());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn profile() -> Profile {
        Profile {
            id: "p1".into(),
            name: "AI server".into(),
            host: "100.64.0.5".into(),
            port: 8742,
            scheme: "http".into(),
            mode: ConnectionMode::Direct,
            ssh: None,
            has_token: false,
        }
    }

    #[test]
    fn validates_hosts() {
        assert!(profile().validate().is_ok());
        let mut p = profile();
        p.host = "http://x".into();
        assert!(p.validate().is_err());
        p.host = "ai-box.tailnet.ts.net".into();
        assert!(p.validate().is_ok());
        p.mode = ConnectionMode::Ssh;
        assert!(p.validate().is_err());
        p.ssh = Some(SshOptions { user: "-oProxyCommand=x".into(), host: "h".into(), port: 22, key_path: None });
        assert!(p.validate().is_err());
    }

    #[test]
    fn formats_ipv6() {
        let mut p = profile();
        p.host = "fd7a:115c::1".into();
        assert_eq!(p.direct_url(), "http://[fd7a:115c::1]:8742");
    }
}
