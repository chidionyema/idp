//! Model-catalogue edits: explicit provider files, validated before they become live.

use crate::gateway::{registry_snapshot, App};
use crate::lanes::lanes_from_registry;
use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    Json,
};
use penny_core::{
    error::PennyError, keys::fingerprint, providers::Registry, router::Router as LaneRouter,
};
use serde_json::{json, Value};
use std::{
    fs,
    path::{Path as FsPath, PathBuf},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::{SystemTime, UNIX_EPOCH},
};

static EDIT_SEQ: AtomicU64 = AtomicU64::new(0);

fn key_fp(headers: &HeaderMap) -> Option<String> {
    headers
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .map(fingerprint)
}

fn authorized(app: &App, headers: &HeaderMap) -> Result<String, PennyError> {
    let key = headers
        .get("authorization")
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| PennyError::BadRequest("missing or malformed Authorization".into()))?;
    if !app.cfg.allow_unknown_keys && !app.cfg.keys.iter().any(|entry| entry.key == key) {
        return Err(PennyError::Unauthorized);
    }
    Ok(key.to_string())
}

fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'))
}

fn class_name(class: penny_core::config::LaneClass) -> &'static str {
    match class {
        penny_core::config::LaneClass::Local => "local",
        penny_core::config::LaneClass::Free => "free",
        penny_core::config::LaneClass::Paid => "paid",
    }
}

fn model_from_body(body: &Value, path_model: &str) -> Result<toml::Value, PennyError> {
    let object = body
        .as_object()
        .ok_or_else(|| PennyError::BadRequest("model body must be an object".into()))?;
    let id = object
        .get("id")
        .and_then(Value::as_str)
        .unwrap_or(path_model);
    if id != path_model || !valid_id(id) {
        return Err(PennyError::BadRequest(
            "model id must match the URL and contain only letters, digits, '.', '_' or '-'".into(),
        ));
    }
    let class = object
        .get("class")
        .and_then(Value::as_str)
        .ok_or_else(|| PennyError::BadRequest("class is required".into()))?;
    if !matches!(class, "local" | "free" | "paid") {
        return Err(PennyError::BadRequest(
            "class must be local, free or paid".into(),
        ));
    }
    let number = |field: &str, default: f64| {
        object
            .get(field)
            .map(|value| {
                value
                    .as_f64()
                    .ok_or_else(|| PennyError::BadRequest(format!("{field} must be a number")))
            })
            .unwrap_or(Ok(default))
    };
    let integer = |field: &str, default: i64| -> Result<i64, PennyError> {
        object
            .get(field)
            .map(|value| {
                value
                    .as_i64()
                    .ok_or_else(|| PennyError::BadRequest(format!("{field} must be an integer")))
            })
            .unwrap_or(Ok(default))
    };
    let list = |field: &str| -> Result<Vec<String>, PennyError> {
        let Some(value) = object.get(field) else {
            return Ok(Vec::new());
        };
        value
            .as_array()
            .ok_or_else(|| PennyError::BadRequest(format!("{field} must be an array")))?
            .iter()
            .map(|item| {
                item.as_str().map(str::to_string).ok_or_else(|| {
                    PennyError::BadRequest(format!("{field} values must be strings"))
                })
            })
            .collect()
    };

    let mut table = toml::map::Map::new();
    table.insert("id".into(), toml::Value::String(id.into()));
    table.insert("class".into(), toml::Value::String(class.into()));
    table.insert(
        "price_in_per_mtok".into(),
        toml::Value::Float(number("price_in_per_mtok", 0.0)?),
    );
    table.insert(
        "price_out_per_mtok".into(),
        toml::Value::Float(number("price_out_per_mtok", 0.0)?),
    );
    table.insert(
        "context_window".into(),
        toml::Value::Integer(integer("context_window", 0)?),
    );
    table.insert(
        "min_output_tokens".into(),
        toml::Value::Integer(integer("min_output_tokens", 0)?),
    );
    table.insert(
        "aliases".into(),
        toml::Value::Array(
            list("aliases")?
                .into_iter()
                .map(toml::Value::String)
                .collect(),
        ),
    );
    table.insert(
        "fallbacks".into(),
        toml::Value::Array(
            list("fallbacks")?
                .into_iter()
                .map(toml::Value::String)
                .collect(),
        ),
    );
    Ok(toml::Value::Table(table))
}

fn validate_candidate(
    providers: &FsPath,
    provider: &str,
    text: &str,
) -> Result<Registry, PennyError> {
    let temp = std::env::temp_dir().join(format!(
        "pennyd-edit-{}-{}",
        std::process::id(),
        EDIT_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&temp).map_err(|error| {
        PennyError::Config(format!("create validation directory {temp:?}: {error}"))
    })?;
    let result = (|| {
        for entry in fs::read_dir(providers)
            .map_err(|error| PennyError::Config(format!("read {providers:?}: {error}")))?
        {
            let entry = entry
                .map_err(|error| PennyError::Config(format!("read provider entry: {error}")))?;
            if entry.path().extension().and_then(|value| value.to_str()) != Some("toml") {
                continue;
            }
            let name = entry.file_name();
            if name.to_string_lossy() == format!("{provider}.toml") {
                continue;
            }
            fs::copy(entry.path(), temp.join(name))
                .map_err(|error| PennyError::Config(format!("copy provider file: {error}")))?;
        }
        fs::write(temp.join(format!("{provider}.toml")), text)
            .map_err(|error| PennyError::Config(format!("write candidate: {error}")))?;
        Registry::load_dir(&temp)
    })();
    let _ = fs::remove_dir_all(&temp);
    result
}

fn install_registry(app: &App, registry: Registry) -> Result<(), PennyError> {
    let lanes = lanes_from_registry(&registry, app.cfg.shaping.cache_control)?;
    let router = LaneRouter::new(
        lanes,
        app.cfg.router.breaker_threshold,
        app.cfg.router.breaker_cooldown_s,
        app.cfg.max_inflight_per_lane,
    );
    *app.registry
        .write()
        .unwrap_or_else(|poisoned| poisoned.into_inner()) = Arc::new(registry);
    *app.router
        .write()
        .unwrap_or_else(|poisoned| poisoned.into_inner()) = Arc::new(router);
    Ok(())
}

async fn audit(app: &App, headers: &HeaderMap, action: &str, fields: Value) {
    let mut decision = json!({
        "decision": action,
        "key_fp": key_fp(headers),
    });
    if let (Some(target), Some(source)) = (decision.as_object_mut(), fields.as_object()) {
        for (key, value) in source {
            target.insert(key.clone(), value.clone());
        }
    }
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    let mut log = app.log.lock().await;
    if log.append(now, &decision).is_err() {
        app.dropped_decisions.fetch_add(1, Ordering::Relaxed);
    }
}

fn api_error(error: PennyError) -> Response {
    let status = match error {
        PennyError::Unauthorized => StatusCode::UNAUTHORIZED,
        PennyError::ModelNotAllowed { .. } => StatusCode::FORBIDDEN,
        PennyError::BadRequest(_) => StatusCode::BAD_REQUEST,
        PennyError::Config(_) => StatusCode::UNPROCESSABLE_ENTITY,
        _ => StatusCode::BAD_GATEWAY,
    };
    (
        status,
        Json(json!({"ok": false, "error": error.to_string()})),
    )
        .into_response()
}

pub async fn list(State(app): State<Arc<App>>, headers: HeaderMap) -> Response {
    if let Err(error) = authorized(&app, &headers) {
        return api_error(error);
    }
    let registry = registry_snapshot(&app);
    let models: Vec<Value> = registry
        .models
        .iter()
        .map(|entry| {
            json!({
                "provider": entry.provider.id,
                "id": entry.model.id,
                "canonical": entry.canonical_name(),
                "class": class_name(entry.model.class),
                "aliases": entry.model.aliases,
                "fallbacks": entry.model.fallbacks,
                "context_window": entry.model.context_window,
                "min_output_tokens": entry.model.min_output_tokens,
                "price_in_per_mtok": entry.model.price_in_per_mtok,
                "price_out_per_mtok": entry.model.price_out_per_mtok,
            })
        })
        .collect();
    (StatusCode::OK, Json(json!({"ok": true, "models": models}))).into_response()
}

pub async fn upsert(
    State(app): State<Arc<App>>,
    Path((provider, model)): Path<(String, String)>,
    headers: HeaderMap,
    Json(body): Json<Value>,
) -> Response {
    if let Err(error) = authorized(&app, &headers) {
        return api_error(error);
    }
    let _guard = app.catalog_lock.lock().await;
    if !valid_id(&provider) || !valid_id(&model) {
        return api_error(PennyError::BadRequest(
            "invalid provider or model id".into(),
        ));
    }
    let providers = PathBuf::from(&app.cfg.providers_dir);
    let file = providers.join(format!("{provider}.toml"));
    let existing = match fs::read_to_string(&file) {
        Ok(value) => value,
        Err(error) => {
            return api_error(PennyError::BadRequest(format!(
                "provider {provider:?} does not exist: {error}"
            )))
        }
    };
    let candidate_model = match model_from_body(&body, &model) {
        Ok(value) => value,
        Err(error) => return api_error(error),
    };
    let mut document: toml::Value = match toml::from_str(&existing) {
        Ok(value) => value,
        Err(error) => return api_error(PennyError::Config(format!("{file:?}: {error}"))),
    };
    let Some(root) = document.as_table_mut() else {
        return api_error(PennyError::Config(format!("{file:?} is not a table")));
    };
    let models = root
        .entry("models")
        .or_insert_with(|| toml::Value::Array(Vec::new()));
    let Some(models) = models.as_array_mut() else {
        return api_error(PennyError::Config(
            "provider models must be an array".into(),
        ));
    };
    let found = models.iter_mut().find(|entry| {
        entry
            .get("id")
            .and_then(toml::Value::as_str)
            .is_some_and(|id| id == model)
    });
    if let Some(slot) = found {
        *slot = candidate_model;
    } else {
        models.push(candidate_model);
    }
    let text = match toml::to_string_pretty(&document) {
        Ok(value) => value,
        Err(error) => return api_error(PennyError::Config(error.to_string())),
    };
    let registry = match validate_candidate(&providers, &provider, &text) {
        Ok(value) => value,
        Err(error) => return api_error(error),
    };
    let temporary = providers.join(format!(".{provider}.toml.{}.tmp", std::process::id()));
    if let Err(error) = fs::write(&temporary, text).and_then(|_| fs::rename(&temporary, &file)) {
        let _ = fs::remove_file(&temporary);
        return api_error(PennyError::Config(format!("write {file:?}: {error}")));
    }
    if let Err(error) = install_registry(&app, registry) {
        return api_error(error);
    }
    audit(
        &app,
        &headers,
        "admin_model_upsert",
        json!({"provider": provider, "model": model}),
    )
    .await;
    (
        StatusCode::OK,
        Json(json!({"ok": true, "provider": provider, "model": model})),
    )
        .into_response()
}

pub async fn remove(
    State(app): State<Arc<App>>,
    Path((provider, model)): Path<(String, String)>,
    headers: HeaderMap,
) -> Response {
    if let Err(error) = authorized(&app, &headers) {
        return api_error(error);
    }
    let _guard = app.catalog_lock.lock().await;
    if !valid_id(&provider) || !valid_id(&model) {
        return api_error(PennyError::BadRequest(
            "invalid provider or model id".into(),
        ));
    }
    let providers = PathBuf::from(&app.cfg.providers_dir);
    let file = providers.join(format!("{provider}.toml"));
    let existing = match fs::read_to_string(&file) {
        Ok(value) => value,
        Err(error) => {
            return api_error(PennyError::BadRequest(format!(
                "provider {provider:?} does not exist: {error}"
            )))
        }
    };
    let mut document: toml::Value = match toml::from_str(&existing) {
        Ok(value) => value,
        Err(error) => return api_error(PennyError::Config(format!("{file:?}: {error}"))),
    };
    let Some(models) = document
        .get_mut("models")
        .and_then(toml::Value::as_array_mut)
    else {
        return api_error(PennyError::Config(
            "provider models must be an array".into(),
        ));
    };
    let before = models.len();
    models.retain(|entry| {
        entry
            .get("id")
            .and_then(toml::Value::as_str)
            .is_none_or(|id| id != model)
    });
    if models.len() == before {
        return api_error(PennyError::BadRequest(format!(
            "model {provider}/{model} does not exist"
        )));
    }
    let text = match toml::to_string_pretty(&document) {
        Ok(value) => value,
        Err(error) => return api_error(PennyError::Config(error.to_string())),
    };
    let registry = match validate_candidate(&providers, &provider, &text) {
        Ok(value) => value,
        Err(error) => return api_error(error),
    };
    let temporary = providers.join(format!(".{provider}.toml.{}.tmp", std::process::id()));
    if let Err(error) = fs::write(&temporary, text).and_then(|_| fs::rename(&temporary, &file)) {
        let _ = fs::remove_file(&temporary);
        return api_error(PennyError::Config(format!("write {file:?}: {error}")));
    }
    if let Err(error) = install_registry(&app, registry) {
        return api_error(error);
    }
    audit(
        &app,
        &headers,
        "admin_model_remove",
        json!({"provider": provider, "model": model}),
    )
    .await;
    (
        StatusCode::OK,
        Json(json!({"ok": true, "provider": provider, "model": model})),
    )
        .into_response()
}
