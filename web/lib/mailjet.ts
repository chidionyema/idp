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
      From: { Email: target.senderEmail, Name: "Merdian Intelligence" },
      To: [{ Email: target.recipientEmail }],
      ReplyTo: { Email: value.email, Name: value.name },
      Subject: "New Merdian Intelligence enquiry",
      TextPart: [
        "New project enquiry via Merdian Intelligence",
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

/** Mailjet may reply HTTP 200 with a per-message failure. */
export function mailjetAccepted(body: unknown): boolean {
  if (!body || typeof body !== "object" || !("Messages" in body)) return false;
  const messages = body.Messages;
  return Array.isArray(messages) && messages.length === 1 &&
    messages[0] !== null && typeof messages[0] === "object" &&
    messages[0].Status === "success";
}
