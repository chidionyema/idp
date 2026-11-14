import type { SecretReader, ValidationResult } from "./contact";

export interface MailjetTarget {
  apiKey: string;
  secretKey: string;
  senderEmail: string;
  recipientEmail: string;
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Never expose these values through the public readiness endpoint. */
export function mailjetTarget(
  env: Record<string, string | undefined>,
  readSecret?: SecretReader,
): MailjetTarget | null {
  const value = (name: string) => (env[name] ?? readSecret?.(name))?.trim() ?? "";
  const apiKey = value("MAILJET_API_KEY");
  const secretKey = value("MAILJET_SECRET_KEY");
  const senderEmail = value("MERDIAN_ENQUIRIES_FROM");
  const recipientEmail = value("MERDIAN_ENQUIRIES_TO");
  if (!apiKey || !secretKey || !EMAIL.test(senderEmail) || !EMAIL.test(recipientEmail)) return null;
  return { apiKey, secretKey, senderEmail, recipientEmail };
}

export function mailjetPayload(
  target: MailjetTarget,
  value: NonNullable<ValidationResult["value"]>,
  receivedAt: string,
) {
  return {
    Messages: [{
      From: { Email: target.senderEmail, Name: "Meridian Intelligence" },
      To: [{ Email: target.recipientEmail }],
      ReplyTo: { Email: value.email, Name: value.name },
      Subject: "New Meridian Intelligence enquiry",
      TextPart: [
        "New project enquiry via Meridian Intelligence",
        `Received: ${receivedAt}`,
        `Name: ${value.name}`,
        `Email: ${value.email}`,
        ...(value.company ? [`Company: ${value.company}`] : []),
        "",
        value.message,
      ].join("\n"),
      TrackOpens: "disabled",
      TrackClicks: "disabled",
    }],
  };
}

/** An HTTP 200 is not acceptance unless Mailjet identifies the intended recipient. */
export function mailjetAccepted(body: unknown, expectedRecipient: string): boolean {
  if (!body || typeof body !== "object" || !("Messages" in body)) return false;
  const messages = body.Messages;
  if (!Array.isArray(messages) || messages.length !== 1) return false;
  const message = messages[0];
  if (!message || typeof message !== "object" || message.Status !== "success") return false;
  const recipients = message.To;
  if (!Array.isArray(recipients) || recipients.length !== 1) return false;
  const recipient = recipients[0];
  if (!recipient || typeof recipient !== "object" ||
      typeof recipient.Email !== "string" ||
      recipient.Email.toLowerCase() !== expectedRecipient.toLowerCase()) return false;
  const uuid = recipient.MessageUUID;
  const id = recipient.MessageID;
  return (typeof uuid === "string" && uuid.trim().length > 0) ||
    (typeof id === "number" && Number.isSafeInteger(id) && id > 0) ||
    (typeof id === "string" && /^[1-9][0-9]*$/.test(id));
}
