# The founder is enterprise client zero

Founder ruling, 2026-09-03, and it is across the board — every surface, every vendor,
every credential, not any one product.

Every capability the founder touches is graded as if a paying enterprise client received
it. He is not a special operator with special chores; he is the first customer, and the
road he is given is the road a customer gets.

## What that means in practice

- **No terminal.** A step that asks him to run a command, set a repository secret, or edit
  a file by hand is a defect, whatever it saves the builder. The fix is redesigning the
  step, never wording the ask more politely.
- **The console is the intake.** A credential he already holds is pasted into the
  product's own signed-in console, stored encrypted by the platform, never sent through
  chat, never re-minted because a fresh one would be easier to script.
- **No fresh credential when one exists.** Asking him to create a new key while he holds a
  working one is the same defect in a second coat.
- **A capability built for him is built as the customer capability.** If the founder needs
  it, a buyer's operator will need it; it ships on the product surface with its
  documentation, not as founder lore.
- **Repetition is the incident.** If he has to say any of this twice, the process that
  made him repeat it is the thing to fix.

## Instances on record

- Model router credential intake: [picking and adding models](../../how-to/onboarding/litellm.md)
  — key brought through the router console's credentials tab, nothing else.
- Sign-in everywhere: one estate login at the gateway
  ([auth belongs to the gateway](../../policy/auth-is-infrastructure.md)); no surface
  ships its own password.

When a new step for the founder is unavoidable, it is one action, named in plain words,
on a page or a phone — and it is recorded here as an instance with the redesign that
retires it.
