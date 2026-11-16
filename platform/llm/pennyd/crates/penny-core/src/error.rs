use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum PennyError {
    BudgetExceeded {
        key: String,
    },
    Unauthorized,
    /// Per-key model ACL denial (403). The escape hatch budgets can't close.
    ModelNotAllowed {
        key: String,
        model: String,
    },
    AllLanesFailed,
    /// HTTP 429 from a lane. Carries Retry-After so the breaker opens for
    /// the provider-advertised window instead of a blind cooldown.
    RateLimited {
        lane: String,
        retry_after_s: Option<u64>,
    },
    Upstream {
        lane: String,
        status: u16,
        body: String,
    },
    BadRequest(String),
    Config(String),
}

impl fmt::Display for PennyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BudgetExceeded { key } => write!(f, "budget exceeded for key {key}"),
            Self::Unauthorized => write!(f, "unknown API key"),
            Self::ModelNotAllowed { key, model } => {
                write!(f, "key {key} is not allowed to use model {model}")
            }
            Self::AllLanesFailed => write!(f, "all lanes failed"),
            Self::RateLimited {
                lane,
                retry_after_s,
            } => match retry_after_s {
                Some(s) => write!(f, "lane {lane} rate limited; retry after {s}s"),
                None => write!(f, "lane {lane} rate limited"),
            },
            Self::Upstream { lane, status, body } => {
                write!(f, "lane {lane} returned status {status}: {body}")
            }
            Self::BadRequest(m) => write!(f, "bad request: {m}"),
            Self::Config(m) => write!(f, "config: {m}"),
        }
    }
}

impl std::error::Error for PennyError {}
