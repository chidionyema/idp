claims = []
malformed: list[str] = []
for comment in comments:
    for line in str(comment.get("body") or "").splitlines():
        if not line.strip().startswith("CLAIM "):
            continue
        try:
            claims.append(parse_claim_line(line))
            malformed.clear()  # a well-formed claim supersedes the malformed ones before it
        except ClaimContractError as exc:
            malformed.append(str(exc))
            claims.clear()  # it is now the claim of record, and it does not parse
if malformed: