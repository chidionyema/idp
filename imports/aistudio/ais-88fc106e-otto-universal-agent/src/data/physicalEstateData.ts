import { PhysicalEndpoint, PhysicalHardwareCategory } from '../types/otto';

export const INITIAL_PHYSICAL_ENDPOINTS: PhysicalEndpoint[] = [
  // 1. Wearable - Apple Watch Ultra 2
  {
    id: 'ep-watch-ultra-2',
    name: 'Apple Watch Ultra 2 (Wrist Node)',
    category: 'wearable',
    model: 'Apple Watch Ultra 2 (Titanium 49mm, Cellular + GPS)',
    serialNumber: 'WATCH-U2-9941X-KY',
    physicalLocation: "Founder's Left Wrist (Mobile Transit)",
    firmwareVersion: 'watchOS 11.2 (Build 22S5089c)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 79,
      charging: false,
      cpuTempC: 31.4,
      cpuLoadPct: 14.2,
      memoryUsedMb: 612,
      memoryTotalMb: 1024,
      signalRssiDbm: -54,
      connectionProtocol: 'BLE 5.3 + Ultra Wideband (U1/U2) + LTE-M',
      roundtripLatencyMs: 31,
      lastHeartbeatEpoch: Date.now() - 420,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-watch-haptic',
        name: 'Dual-Engine Haptic Alert Bus',
        category: 'haptic',
        verified: true,
        latencyMicros: 340,
        proofSignature: 'ed25519:haptic-tap-latch-98124',
        description: 'Instant 2-tap discreet VIP triage and 1-tap CAPTCHA emergency approvals without pulling out phone.'
      },
      {
        id: 'cap-watch-complication',
        name: 'Real-Time Complication Refresh (<1s)',
        category: 'display',
        verified: true,
        latencyMicros: 820,
        proofSignature: 'ed25519:complication-refresh-10492',
        description: 'Displays current estate execution verb and open PR gate counts directly on watch face dial.'
      },
      {
        id: 'cap-watch-ppg',
        name: 'Stress & Heart Rate Telemetry Invariant',
        category: 'biometric',
        verified: true,
        latencyMicros: 510,
        proofSignature: 'ed25519:biometric-sync-55410',
        description: 'Monitors founder heart rate variability; auto-muffles non-critical notifications if stress spikes >110 bpm.'
      }
    ],
    ipOrMacAddress: 'F4:D4:88:AC:32:01 (Direct Peer UWB)',
    meshNodeId: 'mesh.node.wearable.wrist.01',
    securityEnclaveStatus: 'ATTESTED',
    lastAttestationProof: 'sha256:7a9f8c12b94e33d8a1c90034e4f1a288cde98371a2b0c1e2d3f4a5b6c7d8e9f0'
  },

  // 2. Spatial Glasses - Orion Neural AR Glasses
  {
    id: 'ep-glasses-orion',
    name: 'Orion Neural AR Glasses (HUD Node)',
    category: 'spatial-glasses',
    model: 'Orion Neural AR Glass (Bespoke Retinal Waveguide)',
    serialNumber: 'ORION-HUD-7721A-Z9',
    physicalLocation: "Founder's Field of View (Primary Spatial Surface)",
    firmwareVersion: 'Neural-AR-OS v2.4.1 (Micro-LED Engine)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 64,
      charging: false,
      cpuTempC: 36.8,
      cpuLoadPct: 22.8,
      memoryUsedMb: 1480,
      memoryTotalMb: 2048,
      signalRssiDbm: -48,
      connectionProtocol: '60GHz Wi-Fi 7 Millimeter-Wave Link',
      roundtripLatencyMs: 11,
      lastHeartbeatEpoch: Date.now() - 180,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-glasses-retinal',
        name: 'Micro-LED Retinal Projection Engine',
        category: 'display',
        verified: true,
        latencyMicros: 290,
        proofSignature: 'ed25519:retinal-glyph-pass-88210',
        description: 'Projects floating high-contrast telemetry glyphs into peripheral vision with 0 perceptible latency.'
      },
      {
        id: 'cap-glasses-gaze',
        name: 'Optical Gaze Raycasting & Attention Tracking',
        category: 'sensing',
        verified: true,
        latencyMicros: 420,
        proofSignature: 'ed25519:gaze-vector-lock-99124',
        description: 'Detects what physical screen or robotics workspace the founder is looking at for contextual agent hands injection.'
      },
      {
        id: 'cap-glasses-neural-emg',
        name: 'Sub-Vocal & Micro-Gesture EMG Interface',
        category: 'sensing',
        verified: true,
        latencyMicros: 180,
        proofSignature: 'ed25519:emg-subvocal-token-33120',
        description: 'Reads micro-finger pinches and silent jaw movements to issue founder commands without vocalizing.'
      }
    ],
    ipOrMacAddress: '3C:06:30:19:B2:FF (mmWave Direct)',
    meshNodeId: 'mesh.node.spatial.retinal.01',
    securityEnclaveStatus: 'HARDWARE_KEY_BOUND',
    lastAttestationProof: 'sha256:3e4d5c6b7a890123456789abcdef0123456789abcdef0123456789abcdef0123'
  },

  // 3. Industrial Robotics Arm - Universal Robots UR5e
  {
    id: 'ep-robot-ur5e',
    name: 'Universal Robots UR5e (Robotics Lab Arm)',
    category: 'robotics',
    model: 'Universal Robots UR5e (6-DOF, 5kg Payload, 850mm Reach)',
    serialNumber: 'UR5E-2026-981244',
    physicalLocation: 'Robotics Prototyping Bay (Workbench A4)',
    firmwareVersion: 'Polyscope 5.16 + ROS2 Jazzy CycloneDDS',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 100,
      charging: true,
      cpuTempC: 41.2,
      cpuLoadPct: 34.5,
      memoryUsedMb: 3200,
      memoryTotalMb: 8192,
      signalRssiDbm: -28,
      connectionProtocol: '10GbE Industrial Ethernet + Cyclone DDS Mesh',
      roundtripLatencyMs: 4,
      lastHeartbeatEpoch: Date.now() - 95,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-ur5e-ros2',
        name: 'ROS2 JointTrajectoryController & MoveIt 2',
        category: 'actuation',
        verified: true,
        latencyMicros: 140,
        proofSignature: 'ed25519:joint-trajectory-pass-44120',
        description: 'Direct 500Hz real-time torque and joint position loop control for precise physical hardware interactions.'
      },
      {
        id: 'cap-ur5e-ft-sensor',
        name: 'Integrated 6-Axis Tool Flange Force/Torque Sensor',
        category: 'sensing',
        verified: true,
        latencyMicros: 85,
        proofSignature: 'ed25519:force-torque-calibrated-9912',
        description: 'Sensory feedback detects subtle mechanical resistance (0.1N sensitivity) during physical button pressing or board testing.'
      },
      {
        id: 'cap-ur5e-estop',
        name: 'Hardware E-Stop Dual-Channel Safety Circuit',
        category: 'actuation',
        verified: true,
        latencyMicros: 45,
        proofSignature: 'ed25519:safety-estop-latch-11209',
        description: 'Category 4, PL e fail-safe hardware interlock: trips within 5ms if boundary or torque exceeds safety envelope.'
      }
    ],
    ipOrMacAddress: '192.168.10.45 / 00:1B:C5:02:19:F8',
    meshNodeId: 'mesh.node.robotics.manipulator.01',
    securityEnclaveStatus: 'LOCKED_SECURE',
    lastAttestationProof: 'sha256:9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b'
  },

  // 4. Mobile Quadruped Robot - Unitree B2
  {
    id: 'ep-robot-unitree',
    name: 'Unitree B2 Quadruped (Estate Perimeter & Lab Node)',
    category: 'robotics',
    model: 'Unitree B2 Industrial Heavy-Duty Quadruped',
    serialNumber: 'UNITREE-B2-IND-00441',
    physicalLocation: 'Estate Courtyard & Hardware Charging Dock 1',
    firmwareVersion: 'Unitree SDK 2.3 / Ubuntu 22.04 LTS RT Kernel',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 91,
      charging: false,
      cpuTempC: 43.7,
      cpuLoadPct: 41.2,
      memoryUsedMb: 6140,
      memoryTotalMb: 16384,
      signalRssiDbm: -42,
      connectionProtocol: 'Private 5G SA Sub-6GHz + Wi-Fi 6E',
      roundtripLatencyMs: 9,
      lastHeartbeatEpoch: Date.now() - 110,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-unitree-lidar',
        name: '360° 3D 4D LiDAR SLAM & Obstacle Avoidance',
        category: 'sensing',
        verified: true,
        latencyMicros: 310,
        proofSignature: 'ed25519:lidar-pointcloud-lock-7721',
        description: 'Real-time spatial point cloud generation of estate perimeter; navigates stairs, outdoors, and uneven terrain.'
      },
      {
        id: 'cap-unitree-payload',
        name: 'Autonomous Hardware Carrier & Mobile Charging Hub',
        category: 'actuation',
        verified: true,
        latencyMicros: 220,
        proofSignature: 'ed25519:payload-dock-status-8841',
        description: 'Carries physical laptops, test benches, or emergency medkits to any estate coordinate autonomously.'
      },
      {
        id: 'cap-unitree-cams',
        name: 'Dual Intel RealSense D435i Depth & Infrared Cameras',
        category: 'sensing',
        verified: true,
        latencyMicros: 195,
        proofSignature: 'ed25519:depth-camera-feed-verified',
        description: 'Night-vision infrared perimeter patrols with zero cloud exfiltration; local edge YOLOv10 object recognition.'
      }
    ],
    ipOrMacAddress: '10.200.4.18 / 48:21:0B:44:09:A1',
    meshNodeId: 'mesh.node.robotics.mobile.quadruped.01',
    securityEnclaveStatus: 'ATTESTED',
    lastAttestationProof: 'sha256:4f5e6d7c8b9a0123456789abcdef0123456789abcdef0123456789abcdef4f5e'
  },

  // 5. Workstation - Founder's M4 Max MacBook Pro
  {
    id: 'ep-mac-m4-max',
    name: "Founder's MacBook Pro 16\" (M4 Max)",
    category: 'workstation',
    model: 'Apple MacBook Pro 16\" (M4 Max 16-Core CPU, 40-Core GPU, 128GB RAM)',
    serialNumber: 'MBP16-M4M-00892-Z',
    physicalLocation: 'Founder Private Study (Argon Command Desk)',
    firmwareVersion: 'macOS 15.1 Sequoia (Darwin Kernel 24.1.0)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 92,
      charging: true,
      cpuTempC: 38.2,
      cpuLoadPct: 18.4,
      memoryUsedMb: 42100,
      memoryTotalMb: 131072,
      signalRssiDbm: -31,
      connectionProtocol: 'Thunderbolt 5 / 10GbE SFP+ Fiber to Core Switch',
      roundtripLatencyMs: 14,
      lastHeartbeatEpoch: Date.now() - 340,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-mac-accessibility',
        name: 'macOS Accessibility Driver & CGEvent Synthesizer',
        category: 'actuation',
        verified: true,
        latencyMicros: 120,
        proofSignature: 'ed25519:cgevent-injection-clean-01',
        description: 'Native window inspection, keyboard typing, and sub-pixel mouse clicks with differential screenshot verifiers.'
      },
      {
        id: 'cap-mac-local-r1',
        name: 'Local Bedrock: DeepSeek-R1 70B Quantized on Metal',
        category: 'mesh',
        verified: true,
        latencyMicros: 480,
        proofSignature: 'ed25519:metal-mps-inference-pass',
        description: 'Executes 100% offline reasoning at 38 tok/s over Unified Memory; permanent zero-cloud escape hatch.'
      },
      {
        id: 'cap-mac-enclave',
        name: 'Apple Silicon Secure Enclave & Touch ID Biometrics',
        category: 'biometric',
        verified: true,
        latencyMicros: 95,
        proofSignature: 'ed25519:secure-enclave-attestation-99',
        description: 'Cryptographically seals estate master root keys; hardware tamper-resistant key storage.'
      }
    ],
    ipOrMacAddress: '10.0.1.10 / E4:E0:C5:11:88:20',
    meshNodeId: 'mesh.node.workstation.macbook.01',
    securityEnclaveStatus: 'HARDWARE_KEY_BOUND',
    lastAttestationProof: 'sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff'
  },

  // 6. Mobile - Google Pixel 9 Pro
  {
    id: 'ep-pixel-9-pro',
    name: 'Google Pixel 9 Pro (Tensor G4)',
    category: 'mobile',
    model: 'Google Pixel 9 Pro (16GB RAM, Tensor G4, Titan M2)',
    serialNumber: 'PIXEL9P-US-449102',
    physicalLocation: "Founder's Pocket (Active Mobile Transit)",
    firmwareVersion: 'Android 15 (Vanilla Ice Cream / AP3A.241105.008)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 88,
      charging: false,
      cpuTempC: 33.1,
      cpuLoadPct: 15.6,
      memoryUsedMb: 7200,
      memoryTotalMb: 16384,
      signalRssiDbm: -58,
      connectionProtocol: '5G Ultra Wideband + Wi-Fi 7',
      roundtripLatencyMs: 22,
      lastHeartbeatEpoch: Date.now() - 410,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-pixel-maestro',
        name: 'adb + UI Automator 2.0 + Maestro Flow Engine',
        category: 'actuation',
        verified: true,
        latencyMicros: 210,
        proofSignature: 'ed25519:maestro-flow-engine-verified',
        description: 'Taps, swipes, types, and inspects view trees across all native Android apps with zero root required.'
      },
      {
        id: 'cap-pixel-titan',
        name: 'Titan M2 Security Chip Hardware Attestation',
        category: 'biometric',
        verified: true,
        latencyMicros: 140,
        proofSignature: 'ed25519:titan-m2-cryptokey-valid',
        description: 'Key attestation signs every mobile adb command before execution.'
      }
    ],
    ipOrMacAddress: '10.0.1.44 / 70:28:8B:20:94:11',
    meshNodeId: 'mesh.node.mobile.android.01',
    securityEnclaveStatus: 'ATTESTED',
    lastAttestationProof: 'sha256:8899aabbccddeeff00112233445566778899aabbccddeeff0011223344556677'
  },

  // 7. Mobile - Apple iPhone 16 Pro
  {
    id: 'ep-iphone-16-pro',
    name: 'iPhone 16 Pro (A18 Pro)',
    category: 'mobile',
    model: 'Apple iPhone 16 Pro (Titanium Black, 256GB, A18 Pro)',
    serialNumber: 'IPHONE16P-0982-K1',
    physicalLocation: 'Founder Briefcase / Desk Stand',
    firmwareVersion: 'iOS 18.2 (22C150)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 85,
      charging: false,
      cpuTempC: 32.5,
      cpuLoadPct: 12.1,
      memoryUsedMb: 4100,
      memoryTotalMb: 8192,
      signalRssiDbm: -51,
      connectionProtocol: '5G Sub-6GHz + Thread Mesh',
      roundtripLatencyMs: 28,
      lastHeartbeatEpoch: Date.now() - 620,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-iphone-xcuitest',
        name: 'xcrun devicectl + XCUITest Domain Socket Runner',
        category: 'actuation',
        verified: true,
        latencyMicros: 240,
        proofSignature: 'ed25519:xcrun-devicectl-clean-44',
        description: 'Automates iOS native applications, system settings, and camera feeds over encrypted local loopback.'
      },
      {
        id: 'cap-iphone-faceid',
        name: 'TrueDepth Camera Hardware Passkey Vault',
        category: 'biometric',
        verified: true,
        latencyMicros: 110,
        proofSignature: 'ed25519:faceid-passkey-vault-01',
        description: 'Handles 1-tap passkey biometric auth for banking and estate domain logins.'
      }
    ],
    ipOrMacAddress: '10.0.1.48 / 62:10:9C:19:D4:55',
    meshNodeId: 'mesh.node.mobile.iphone.01',
    securityEnclaveStatus: 'ATTESTED',
    lastAttestationProof: 'sha256:2233445566778899aabbccddeeff00112233445566778899aabbccddeeff0011'
  },

  // 8. Ambient Hub - Apple TV & Thread Border Router
  {
    id: 'ep-ambient-appletv',
    name: 'Living & Convent Ambient Hub (Apple TV 4K)',
    category: 'ambient-hub',
    model: 'Apple TV 4K 128GB (Ethernet + Thread Border Router)',
    serialNumber: 'ATV4K-CONVENT-4412',
    physicalLocation: 'Convent Cottage & Main Living Room',
    firmwareVersion: 'tvOS 18.1 (22J580)',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 100,
      charging: true,
      cpuTempC: 34.0,
      cpuLoadPct: 8.9,
      memoryUsedMb: 1200,
      memoryTotalMb: 4096,
      signalRssiDbm: -22,
      connectionProtocol: 'Gigabit Ethernet + Thread Matter 1.3 Mesh',
      roundtripLatencyMs: 12,
      lastHeartbeatEpoch: Date.now() - 210,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-atv-airplay',
        name: 'Lossless Spatial Audio Chants & Kin Announcements',
        category: 'display',
        verified: true,
        latencyMicros: 380,
        proofSignature: 'ed25519:airplay-spatial-chant-pass',
        description: 'Streams Benedictine Vespers and daily encouragement letters directly to Sister Beatrice in gentle, warm acoustic tones.'
      },
      {
        id: 'cap-atv-thread-mesh',
        name: 'Matter / Thread Low-Power Mesh Coordinator',
        category: 'mesh',
        verified: true,
        latencyMicros: 160,
        proofSignature: 'ed25519:thread-border-mesh-attested',
        description: 'Maintains zero-drop mesh for 42 environmental sensors and door security contacts across the estate.'
      }
    ],
    ipOrMacAddress: '10.0.1.2 / AC:DE:48:89:12:00',
    meshNodeId: 'mesh.node.ambient.hub.01',
    securityEnclaveStatus: 'LOCKED_SECURE',
    lastAttestationProof: 'sha256:556677889900aabbccddeeff11223344556677889900aabbccddeeff11223344'
  },

  // 9. Environmental Sensor Beacon - Argon Environmental Hub
  {
    id: 'ep-sensor-argon',
    name: 'Argon Environmental Telemetry & Air Beacon',
    category: 'ambient-hub',
    model: 'Argon Industrial Sensor Node (Sensirion SCD41 + PM2.5 + VOC)',
    serialNumber: 'ARGON-SENS-00918',
    physicalLocation: 'Robotics Bay & Server Rack Enclosure',
    firmwareVersion: 'Zephyr RTOS v3.7 / ESP32-S3',
    ottoPresenceState: 'VERIFIED_ACTIVE',
    telemetry: {
      batteryPct: 100,
      charging: true,
      cpuTempC: 28.6,
      cpuLoadPct: 4.1,
      memoryUsedMb: 180,
      memoryTotalMb: 512,
      signalRssiDbm: -35,
      connectionProtocol: 'PoE 802.3af + Thread Backup',
      roundtripLatencyMs: 6,
      lastHeartbeatEpoch: Date.now() - 140,
      healthStatus: 'optimal'
    },
    capabilities: [
      {
        id: 'cap-sensor-temp-air',
        name: 'Precision CO2, Temperature & Particulate Sampling',
        category: 'sensing',
        verified: true,
        latencyMicros: 90,
        proofSignature: 'ed25519:scd41-air-quality-valid',
        description: 'Monitors server rack thermals and battery storage room safety invariants 24/7.'
      }
    ],
    ipOrMacAddress: '10.0.1.99 / 24:DC:C3:98:A2:10',
    meshNodeId: 'mesh.node.ambient.sensor.01',
    securityEnclaveStatus: 'LOCKED_SECURE',
    lastAttestationProof: 'sha256:aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899'
  }
];

export const ESTATE_LOCATIONS = [
  { id: 'loc-all', name: 'All Locations (Entire Estate)', count: 9 },
  { id: 'loc-study', name: "Founder's Study & Command Desk", count: 2 },
  { id: 'loc-mobile', name: 'Mobile Transit & Founder Person', count: 3 },
  { id: 'loc-robotics', name: 'Robotics Lab & Prototyping Bay', count: 2 },
  { id: 'loc-convent', name: 'Convent Cottage & Ambient Living', count: 2 }
];

export const HARDWARE_CATEGORIES: { id: PhysicalHardwareCategory | 'all'; name: string; count: number }[] = [
  { id: 'all', name: 'All Hardware', count: 9 },
  { id: 'wearable', name: 'Wearables (Watches)', count: 1 },
  { id: 'spatial-glasses', name: 'Spatial AR (Glasses)', count: 1 },
  { id: 'robotics', name: 'Robotics & Physical Hands', count: 2 },
  { id: 'mobile', name: 'Mobile Devices (iOS/Android)', count: 2 },
  { id: 'workstation', name: 'Workstations & Edge', count: 1 },
  { id: 'ambient-hub', name: 'Ambient Hubs & Beacons', count: 2 }
];
