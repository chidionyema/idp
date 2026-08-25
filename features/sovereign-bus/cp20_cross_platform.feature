@cp20
Feature: Cross-platform — macOS and Windows, one trust anchor, one presence gateway
  Founder, 2026-08-25: the OS is platform-agnostic. Root of trust, HUD, haptic
  and voice are backends behind one interface; the kernel never branches on
  the OS outside that boundary.

  Scenario: One trust anchor, three backends
    When I run "python -c 'from sovereign.trust import HardwareTrustAnchor; print(HardwareTrustAnchor().backend)'"
    Then the output is one of "secure_enclave", "windows_hello", "fido2", "software_key"
    And the chosen backend is recorded in every signed receipt

  Scenario: No OS branching outside the boundary
    When I run "grep -rln 'platform.system\|sys.platform' sovereign --include=*.py"
    Then the output lists only files under sovereign/trust and sovereign/presence

  Scenario: Windows paths do not change hashes
    Given a state diff computed on Windows for "src\kernel\main.py"
    Then its hash equals the hash computed on macOS for "src/kernel/main.py"

  Scenario: The engine runs on Windows
    Given a Windows machine with Python and the Temporal CLI
    When I run "bin/sb.ps1 up" and "bin/sb.ps1 start --runner echo --task x --budget 100 --json"
    Then the session reaches "done"
