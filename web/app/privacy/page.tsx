import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "What Meridian Intelligence collects when you send an enquiry, why we hold it, how long we keep it, and how to get it back or have it deleted.",
  alternates: { canonical: "/privacy" },
  openGraph: {
    type: "website",
    title: "Privacy | Meridian Intelligence",
    description: "What we collect when you send an enquiry, and what we do with it.",
    url: "/privacy",
  },
};

export default function PrivacyPage() {
  return <div className="mi-interior">
    <section className="mi-page-hero" aria-labelledby="privacy-heading">
      <div className="mi-shell">
        <span className="mi-eyebrow">MERIDIAN / PRIVACY</span>
        <h1 id="privacy-heading">PRIVACY,<br/><em>PLAINLY.</em></h1>
        <div className="mi-page-hero-bottom">
          <p>This notice covers the enquiry form on this site. It is short because there is not much to say.</p>
          <Link href="/contact" className="mi-button mi-button-gold">Send an enquiry <span aria-hidden="true">↗</span></Link>
        </div>
      </div>
    </section>
    <section className="mi-section">
      <div className="mi-shell">
        <div className="mi-article-body">
          <h2>Who we are</h2>
          <p>Meridian Intelligence Limited runs this site. We are registered in England and Wales under number 16486712. Our registered office is 4th Floor, 14 Museum Place, Cardiff CF10 3BH. We are the data controller for anything you send us through the form.</p>

          <h2>What we collect</h2>
          <p>The form asks for your name, your email address and your message. The company field is optional. We also record the time the message arrived. That is the whole list.</p>
          <p>We do not ask for payment details. Please do not send passwords or customer records in a message. If you do, we will delete them.</p>

          <h2>Why we hold it</h2>
          <p>We use what you send to answer you. Our lawful basis is legitimate interests, because you contacted us about work. If the conversation turns into a project, the basis becomes the contract you sign with us.</p>

          <h2>How long we keep it</h2>
          <p>We keep an unanswered message for twelve months, then delete it. Records for work we have done follow our professional and legal duties instead.</p>

          <h2>Who else sees it</h2>
          <p>Our hosting provider serves the site. Our email provider delivers our reply. Both act on our instructions under a written contract, and neither may use your message for its own purposes. We do not sell what you send us. We do not pass it on for marketing.</p>

          <h2>Cookies and measurement</h2>
          <p>This site sets no cookies. It loads no analytics script and no advertising tag. Nothing about your visit is measured by us or by a third party.</p>

          <h2>Your rights</h2>
          <p>You can ask us for a copy of what we hold. You can ask us to correct it or delete it. You can object to us using it at all. Write to our registered office and we will answer within one month. If you are unhappy with how we handled it, you can complain to the Information Commissioner’s Office.</p>

          <h2>Changes</h2>
          <p>If this notice changes, the new version replaces this one. The date below is the version date.</p>
          <p>Last updated 11 November 2026.</p>
        </div>
      </div>
    </section>
  </div>;
}
