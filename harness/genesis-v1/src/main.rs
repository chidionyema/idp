mod schema;
mod tools;

use crate::schema::InstructionEnvelopeV1;
use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    if let Err(e) = io::stdin().read_to_string(&mut input) {
        eprintln!("failed to read stdin: {}", e);
        std::process::exit(2);
    }

    let envelope: InstructionEnvelopeV1 = match serde_json::from_str(&input) {
        Ok(env) => env,
        Err(e) => {
            eprintln!("invalid InstructionEnvelope.v1: {}", e);
            std::process::exit(2);
        }
    };

    let receipt = tools::dispatch(&envelope);
    match serde_json::to_string_pretty(&receipt) {
        Ok(json) => println!("{}", json),
        Err(e) => {
            eprintln!("failed to serialize StepReceipt.v1: {}", e);
            std::process::exit(3);
        }
    }
}
