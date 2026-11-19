/* ============================================================================
 * MERIDIAN OMEGA CORE — ZERO-ALLOCATION C99 / BARE-METAL / ROS 2 ABI HEADER
 * File: packages/omega-core/omega_hal.h
 *
 * Compatible with:
 *   - Bare-metal / no_std Rust (`#[repr(C)]`) & STM32 / Zephyr RTOS
 *   - Drone Flight Companion Computers (PX4 / ArduPilot / NVIDIA Jetson Orin)
 *   - Humanoid Real-Time Control Loops (ROS 2 Jazzy + PREEMPT_RT 500Hz-1000Hz)
 *   - Smart Camera ISPs (ARM Cortex-A / Ambarella / Hailo)
 *   - macOS / Linux Native Host Daemons
 * ============================================================================ */

#ifndef MERIDIAN_OMEGA_HAL_H
#define MERIDIAN_OMEGA_HAL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OMEGA_CAPSULE_MAX_BYTES 4096U
#define OMEGA_SHA256_HEX_LEN    65U

typedef enum {
  OMEGA_SAFETY_PERMIT_NOMINAL        = 0,
  OMEGA_SAFETY_CLAMPED_BY_GEBURAH    = 1,
  OMEGA_SAFETY_HALT_KINETIC_ENVELOPE = 2,
  OMEGA_SAFETY_HALT_SESSION_UNOWNED  = 3
} omega_safety_verdict_t;

typedef struct {
  float max_contact_force_n;
  float max_velocity_mps;
  float min_battery_pct;
  float geofence_radius_m;
  float human_estop_distance_m;
  bool  require_e1_session;
} omega_safety_envelope_t;

typedef struct {
  const char* device_id;
  uint64_t    lamport_seq;
  uint64_t    observed_at_us;
  const char* modality;
  float       force_newtons;
  float       velocity_mps;
  float       battery_pct;
  float       human_distance_m;
} omega_observation_t;

typedef struct {
  char                   intent_id[40];
  char                   session_id[48];
  char                   actor_did[64];
  char                   target_actuator[48];
  char                   command_op[48];
  float                  command_magnitude;
  omega_safety_verdict_t safety_verdict;
  char                   failsafe_mode[32];
  char                   proof_sha256[OMEGA_SHA256_HEX_LEN];
} omega_verified_intent_t;

typedef struct {
  uint32_t byte_length;
  uint64_t lamport_clock;
  char     capsule_sha256[OMEGA_SHA256_HEX_LEN];
  uint8_t  bytes[OMEGA_CAPSULE_MAX_BYTES];
} omega_capsule_4kb_t;

/* 3-Function Hardware Transducer Table (Implemented per device, < 120 LOC) */
typedef struct {
  omega_observation_t (*sense)(void* hw_ctx);
  bool                (*actuate)(void* hw_ctx, const omega_verified_intent_t* intent);
  bool                (*link)(void* hw_ctx, const omega_capsule_4kb_t* capsule);
} omega_hal_vtable_t;

/* Ring-0 Kernel Entrypoints (Compiled once, runs identically on every device) */
omega_verified_intent_t omega_kernel_step(
  const omega_observation_t*     obs,
  const omega_safety_envelope_t* envelope,
  const char*                    active_session_id,
  const char*                    steward_did
);

bool omega_capsule_pack(omega_capsule_4kb_t* out_capsule, const char* target_device_id);
bool omega_capsule_hydrate(const omega_capsule_4kb_t* in_capsule);

#ifdef __cplusplus
}
#endif

#endif /* MERIDIAN_OMEGA_HAL_H */
