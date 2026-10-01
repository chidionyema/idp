import { SiteShell, SiteNav, SiteFooter, Landing } from '@estate/ui-kit';
import { site } from '../site.config';

// The landing template with this product's copy. The feed is wired to a real source or left
// out; it never carries a mock row.
export default function Home() {
  return (
    <SiteShell nav={<SiteNav brand={site.name} links={site.nav} />} footer={<SiteFooter legal={site.legal} />}>
      <Landing
        headline="What this product does, in one sentence."
        lede="One paragraph that says who it is for and what they get."
        proof={['fact one', 'fact two', 'fact three']}
        cta={{ label: 'Start here', href: '/catalogue' }}
        voice
      />
    </SiteShell>
  );
}
