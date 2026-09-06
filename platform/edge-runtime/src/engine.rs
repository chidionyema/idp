//! One task, one GGUF, one forward pass per call: the next-token logits for each label's
//! first token, softmax over those candidates only, abstain under the margin in the card.
use anyhow::{anyhow, Context, Result};
use candle_core::quantized::gguf_file;
use candle_core::{Device, Tensor};
use candle_transformers::models::quantized_qwen2::ModelWeights;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::Path;
use std::time::Instant;
use tokenizers::Tokenizer;

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ModelCard {
    pub task: String,
    pub base: String,
    pub kind: String,
    pub prompt_template: String,
    pub labels: BTreeMap<String, String>,
    pub abstain_below: f32,
    #[serde(default)]
    pub kv_cache_prefix: bool,
}

#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct Verdict {
    pub abstain: bool,
    pub label: Option<String>,
    pub p: f32,
    pub margin: f32,
    pub latency_ms: u64,
}

/// Softmax over the candidates only. Returns (top candidate index, p, margin to the second).
pub fn rank(logits: &[f32]) -> (usize, f32, f32) {
    let max = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    let exps: Vec<f32> = logits.iter().map(|l| (l - max).exp()).collect();
    let z: f32 = exps.iter().sum();
    let mut ranked: Vec<(f32, usize)> = exps.iter().enumerate().map(|(i, e)| (e / z, i)).collect();
    ranked.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    let second = ranked.get(1).map_or(0.0, |x| x.0);
    (ranked[0].1, ranked[0].0, ranked[0].0 - second)
}

pub struct Engine {
    model: ModelWeights,
    tokenizer: Tokenizer,
    pub card: ModelCard,
    label_ids: Vec<(String, u32)>,
    device: Device,
}

impl Engine {
    pub fn load(dir: &Path) -> Result<Self> {
        let card: ModelCard = serde_yaml::from_str(&std::fs::read_to_string(dir.join("model-card.yaml"))?)?;
        let tokenizer = Tokenizer::from_file(dir.join("tokenizer.json")).map_err(|e| anyhow!("tokenizer: {e}"))?;
        let device = Device::Cpu;
        let mut file = std::fs::File::open(dir.join("model.gguf")).context("model.gguf")?;
        let content = gguf_file::Content::read(&mut file).context("gguf header")?;
        let model = ModelWeights::from_gguf(content, &mut file, &device).context("gguf tensors")?;
        let mut label_ids = Vec::new();
        for label in card.labels.keys() {
            let enc = tokenizer.encode(label.as_str(), false).map_err(|e| anyhow!("encode {label}: {e}"))?;
            let id = *enc.get_ids().first().ok_or_else(|| anyhow!("label {label} has no token"))?;
            label_ids.push((label.clone(), id));
        }
        Ok(Self { model, tokenizer, card, label_ids, device })
    }

    pub fn classify(&mut self, input: &str) -> Result<Verdict> {
        let start = Instant::now();
        let prompt = self.card.prompt_template.replace("{input}", input);
        let enc = self.tokenizer.encode(prompt, true).map_err(|e| anyhow!("encode: {e}"))?;
        let tensor = Tensor::new(enc.get_ids(), &self.device)?.unsqueeze(0)?;
        // index_pos 0 starts a fresh sequence; candle's quantized attention drops its cache then.
        let logits = self.model.forward(&tensor, 0)?.squeeze(0)?.to_vec1::<f32>()?;
        let candidates: Vec<f32> = self.label_ids.iter().map(|(_, id)| logits[*id as usize]).collect();
        let (top, p, margin) = rank(&candidates);
        let latency_ms = start.elapsed().as_millis() as u64;
        let abstain = margin < self.card.abstain_below;
        let key = &self.label_ids[top].0;
        let label = (!abstain).then(|| self.card.labels.get(key).cloned().unwrap_or_else(|| key.clone()));
        Ok(Verdict { abstain, label, p, margin, latency_ms })
    }
}

#[cfg(test)]
mod tests {
    use super::rank;

    #[test]
    fn equal_logits_have_zero_margin() {
        let (_, p, margin) = rank(&[1.0, 1.0]);
        assert!((p - 0.5).abs() < 1e-6 && margin.abs() < 1e-6);
    }

    #[test]
    fn a_clear_winner_has_a_wide_margin() {
        let (top, _, margin) = rank(&[0.0, 6.0]);
        assert_eq!(top, 1);
        assert!(margin > 0.99);
    }
}
