import Foundation
import LocalAuthentication
import CryptoKit
import Security

func jprint(_ d: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: d),
       let s = String(data: data, encoding: .utf8) {
        print(s)
    } else {
        print("{}")
    }
}

let keychainService = "sovereign-trust-enclave"
let keychainAccount = "estate"

func keychainLoad() -> Data? {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: keychainService,
        kSecAttrAccount as String: keychainAccount,
        kSecReturnData as String: true,
    ]
    var item: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &item)
    guard status == errSecSuccess, let data = item as? Data else { return nil }
    return data
}

func keychainSave(_ data: Data) -> Bool {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: keychainService,
        kSecAttrAccount as String: keychainAccount,
    ]
    SecItemDelete(query as CFDictionary)
    var add = query
    add[kSecValueData as String] = data
    let status = SecItemAdd(add as CFDictionary, nil)
    return status == errSecSuccess
}

func loadOrCreateKey() -> SecureEnclave.P256.Signing.PrivateKey? {
    if let existing = keychainLoad() {
        return try? SecureEnclave.P256.Signing.PrivateKey(dataRepresentation: existing)
    }
    guard let key = try? SecureEnclave.P256.Signing.PrivateKey() else { return nil }
    _ = keychainSave(key.dataRepresentation)
    return key
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    jprint(["error": "usage"])
    exit(1)
}

switch args[1] {
case "--detect":
    let ctx = LAContext()
    var err: NSError?
    let biometry = ctx.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &err)
    jprint(["biometry": biometry, "secure_enclave": SecureEnclave.isAvailable])

case "--verify":
    let reason = args.count >= 3 ? args[2] : "estate action"
    let ctx = LAContext()
    let sem = DispatchSemaphore(value: 0)
    var ok = false
    var errMsg: String? = nil
    ctx.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, error in
        ok = success
        errMsg = error?.localizedDescription
        sem.signal()
    }
    sem.wait()
    jprint(["ok": ok, "error": errMsg as Any? ?? NSNull()])

case "--sign":
    guard args.count >= 3 else { jprint(["ok": false, "error": "missing digest"]); exit(1) }
    guard let key = loadOrCreateKey() else {
        jprint(["ok": false, "error": "secure enclave key unavailable"])
        exit(0)
    }
    let digestData = Data(args[2].utf8)
    guard let sig = try? key.signature(for: digestData) else {
        jprint(["ok": false, "error": "sign failed"])
        exit(0)
    }
    jprint([
        "ok": true,
        "sig": sig.rawRepresentation.base64EncodedString(),
        "pubkey": key.publicKey.rawRepresentation.base64EncodedString(),
    ])

case "--pubkey":
    // The enrolled public key, so the Python side can pin it once and
    // verify every later signature against that one enrolment rather
    // than against whatever key happens to answer today (R11/R22).
    guard let key = loadOrCreateKey() else {
        jprint(["ok": false, "error": "secure enclave key unavailable"])
        exit(0)
    }
    jprint(["ok": true, "pubkey": key.publicKey.rawRepresentation.base64EncodedString()])

case "--verify-sig":
    // args: --verify-sig <digest> <signature-base64> <pubkey-base64>
    // Verification is CryptoKit's own P256 ECDSA check. Nothing is
    // re-implemented in Python: the estate has no crypto dependency and
    // a hand-rolled curve check is exactly the thing LAW 43 forbids.
    guard args.count >= 5 else { jprint(["ok": false, "error": "usage"]); exit(1) }
    let digestData = Data(args[2].utf8)
    guard let sigData = Data(base64Encoded: args[3]),
          let pubData = Data(base64Encoded: args[4]) else {
        jprint(["ok": false, "error": "bad base64"])
        exit(0)
    }
    guard let pub = try? P256.Signing.PublicKey(rawRepresentation: pubData),
          let sig = try? P256.Signing.ECDSASignature(rawRepresentation: sigData) else {
        jprint(["ok": false, "error": "bad key or signature encoding"])
        exit(0)
    }
    jprint(["ok": pub.isValidSignature(sig, for: digestData)])

default:
    jprint(["error": "unknown command"])
}
