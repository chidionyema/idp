"""sovereign.presence -- the presence model (W3, master spec 2.1, 2.2, 2.5, 2.6).

fsm.py      Ghost / Haptic / Spatial / Converse; Converse is unreachable
            from a system event by construction (R1-R4).
receipt.py  the one-line receipt (R5).
chat.py     the chat gate: founder reply, catastrophe, digest, nothing else (R13).
digest.py   the signed daily digest, at most six lines (R13).
haptic.py   tap / double tap / buzz through the alert inbox (spec 2.1).
spatial.py  the estate graph the cockpit draws (spec 2.1).
status.py   the counts Siri speaks (R14).
state.py    the state file the SwiftBar menu bar dot reads (R2/R3).
router.py   which surface each event reaches.
cli.py      `sb digest`, `sb status`, `sb presence`.
"""
