import * as React from 'react';
import {
  Button, Card, CardTitle, CardBody, CardMeta, Eyebrow, Display, Heading, Lede, Price, StatePill, Field, Input, Checkbox,
  SiteNav, SiteFooter, SiteShell, LedgerFeed, Dialog, DialogTrigger, DialogContent, DialogClose, Tabs, TabsList, TabsTrigger, TabsContent, VoiceButton,
  Landing, Catalogue, Detail, Checkout, Account, Docs, ErrorPage, Empty,
} from '../src/index';
import { STATES } from '../dist/tokens';

// SAMPLE DATA. Every string below is labelled sample and none is a claim about the estate.
const nav = <SiteNav brand="Sample Co" links={[{ label: 'Catalogue', href: '#', current: true }, { label: 'How we check', href: '#' }, { label: 'Free sample', href: '#' }]} action={<Button asChild variant="ghost"><a href="#">Account</a></Button>} />;
const footer = <SiteFooter legal="Sample Ltd · sample address · sample@example.com">Sample footer links</SiteFooter>;
const shelf = Array.from({ length: 6 }, (_, i) => ({ title: `Sample pack ${i + 1}`, text: 'Sample one-line blurb about who buys it and why, cut at a word boundary.', meta: ['29 sources', '£29.99'], href: `#pack-${i}` }));

const sections = ['Tokens', 'Type', 'Buttons', 'States', 'Cards', 'Forms', 'Nav', 'Feed', 'Overlay', 'Voice', 'T · Landing', 'T · Catalogue', 'T · Detail', 'T · Checkout', 'T · Account', 'T · Docs', 'T · Error', 'T · Empty'] as const;
type Section = (typeof sections)[number];

export function App() {
  const [theme, setTheme] = React.useState<'light' | 'dark'>(() => (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  const [section, setSection] = React.useState<Section>(() => (decodeURIComponent(location.hash.slice(1)) as Section) || 'Tokens');
  React.useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  React.useEffect(() => { if (decodeURIComponent(location.hash.slice(1)) !== section) location.hash = section; }, [section]);
  React.useEffect(() => {
    const onHash = () => { const s = decodeURIComponent(location.hash.slice(1)) as Section; if (sections.includes(s)) setSection(s); };
    addEventListener('hashchange', onHash); return () => removeEventListener('hashchange', onHash);
  }, []);
  const isTemplate = section.startsWith('T ·');
  return (
    <div className="min-h-dvh bg-canvas text-text desktop:grid desktop:grid-cols-[14rem_1fr]">
      <aside className="border-b desktop:border-b-0 desktop:border-r border-border p-4 flex flex-col gap-4 desktop:sticky desktop:top-0 desktop:h-dvh desktop:overflow-auto">
        <div className="flex items-center justify-between gap-2">
          <span className="font-display font-bold">Estate UI Kit</span>
          <button type="button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="min-h-(--size-tap-min) px-3 rounded-md border border-border-strong text-sm">{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </div>
        <nav aria-label="Sections" className="flex flex-wrap desktop:flex-col gap-1">
          {sections.map((s) => <button key={s} type="button" onClick={() => setSection(s)} aria-current={s === section ? 'page' : undefined} className={`text-left min-h-(--size-tap-min) px-3 rounded-md text-sm ${s === section ? 'bg-surface-3 text-text font-medium' : 'text-text-2 hover:text-text'}`}>{s}</button>)}
        </nav>
        <p className="font-mono text-xs text-text-2 mt-auto">crew#694 CP2 · tokens.json is the source · every string here is sample data</p>
      </aside>
      {isTemplate ? (
        <div className="min-w-0"><TemplateView section={section} /></div>
      ) : (
        <div className="p-4 desktop:p-8 flex flex-col gap-12 max-w-(--size-content) min-w-0"><ComponentView section={section} /></div>
      )}
    </div>
  );
}

function Block({ title, children, note }: { title: string; children: React.ReactNode; note?: string }) {
  return (
    <section className="flex flex-col gap-4">
      <div><Heading className="text-lg">{title}</Heading>{note && <p className="text-sm text-text-2 mt-1">{note}</p>}</div>
      <div className="flex flex-wrap items-start gap-4">{children}</div>
    </section>
  );
}

function ComponentView({ section }: { section: Section }) {
  switch (section) {
    case 'Tokens':
      return (
        <>
          <Block title="Colour" note="Every value is a CSS variable from tokens.json; guards/purity.mjs refuses a literal anywhere else.">
            {['canvas', 'surface-1', 'surface-2', 'surface-3', 'border-subtle', 'border', 'border-strong', 'text', 'text-2', 'text-muted', 'accent', 'accent-pressed', 'accent-soft', 'on-accent'].map((n) => (
              <div key={n} className="flex flex-col gap-1 w-24"><div className="h-12 rounded-md border border-border" style={{ background: `var(--color-${n})` }} /><span className="font-mono text-xs text-text-2">{n}</span></div>
            ))}
          </Block>
          <Block title="Space" note="4px base, eight steps.">{['1', '2', '3', '4', '6', '8', '12', '16'].map((s) => <div key={s} className="flex flex-col items-center gap-1"><div className="bg-accent" style={{ width: `var(--space-${s})`, height: `var(--space-${s})` }} /><span className="font-mono text-xs text-text-2">{s}</span></div>)}</Block>
          <Block title="Radius">{['sm', 'md', 'pill'].map((r) => <div key={r} className="flex flex-col items-center gap-1"><div className="size-12 bg-surface-3 border border-border-strong" style={{ borderRadius: `var(--radius-${r})` }} /><span className="font-mono text-xs text-text-2">{r}</span></div>)}</Block>
        </>
      );
    case 'Type':
      return (
        <Block title="Six steps" note="A size outside these is refused. xs is meta only, and only in text-2.">
          <div className="flex flex-col gap-3 w-full">
            <Display>2xl · Display, the one headline on a page</Display>
            <Heading>xl · Heading</Heading>
            <p className="text-lg">lg · Lede and card titles</p>
            <p className="text-md">md · Body, 17px, 1.55</p>
            <p className="text-sm text-text-2">sm · Meta, hints, labels, in text-2 (5.4:1)</p>
            <Eyebrow>xs · Eyebrow, mono, uppercase</Eyebrow>
            <p className="font-mono text-md">mono · anything checkable: prices, ids, counts</p>
            <p className="font-serif text-md">serif · long-form reading, optional</p>
          </div>
        </Block>
      );
    case 'Buttons':
      return (
        <>
          <Block title="Variants" note="Every button is at least 44px tall. An arrow never wraps from its label.">
            <Button>Primary</Button><Button variant="accent">Accent</Button><Button variant="secondary">Secondary</Button><Button variant="ghost">Ghost</Button><Button variant="link">Link</Button>
          </Block>
          <Block title="Sizes and states"><Button size="lg">Large <span aria-hidden>→</span></Button><Button disabled>Disabled</Button><Button asChild><a href="#" className="label-arrow">As a link →</a></Button></Block>
        </>
      );
    case 'States':
      return (
        <Block title="Six states" note="A dot, a word and a tint. Blind is hollow and never green.">
          {STATES.map((s) => <StatePill key={s} state={s} />)}
        </Block>
      );
    case 'Cards':
      return (
        <Block title="Card" note="One border token. The whole card is the link when it links.">
          <Card className="w-72"><CardTitle>Sample card title</CardTitle><CardBody>Sample body copy of a sensible length that wraps at a word boundary.</CardBody><CardMeta><span>29 sources</span><span>£29.99</span></CardMeta></Card>
          <Card interactive className="w-72 relative"><CardTitle><a href="#" className="after:absolute after:inset-0">Interactive card</a></CardTitle><CardBody>Hover shows the strong border.</CardBody><div className="mt-auto"><Price amount="£29.99" note="one-time" /></div></Card>
        </Block>
      );
    case 'Forms':
      return (
        <Block title="Fields" note="Label, control, hint or error, ids wired. The checkbox row is the tap target.">
          <div className="flex flex-col gap-6 w-full max-w-md">
            <Field id="g-email" label="Email" hint="We only use this for the receipt."><Input type="email" placeholder="you@example.com" /></Field>
            <Field id="g-bad" label="Card name" error="Enter the name on the card."><Input defaultValue="" /></Field>
            <Checkbox id="g-consent" label="One email, only if a pack ships. No marketing." />
            <Checkbox id="g-consent-2" label="Checked state" defaultChecked />
          </div>
        </Block>
      );
    case 'Nav':
      return <Block title="Site nav and footer" note="Brand, at most four links, one action."><div className="w-full border border-border rounded-md overflow-hidden">{nav}<div className="p-8 text-sm text-text-2">page</div>{footer}</div></Block>;
    case 'Feed':
      return (
        <>
          <Block title="Ledger feed" note="Read-only rows of what happened."><div className="w-full max-w-xl"><LedgerFeed rows={[{ at: '14:02', text: 'sample: merge queue landed a change', state: 'good' }, { at: '13:47', text: 'sample: research read 31 sources, 4 claims survived', state: 'good' }, { at: '13:12', text: 'sample: guard refused a push', state: 'needs' }]} /></div></Block>
          <Block title="Quiet" note="Empty is a state with a time, never a fake row."><div className="w-full max-w-xl"><LedgerFeed rows={[]} quietSince="09:14" /></div></Block>
        </>
      );
    case 'Overlay':
      return (
        <>
          <Block title="Dialog"><Dialog><DialogTrigger asChild><Button variant="secondary">Open dialog</Button></DialogTrigger><DialogContent title="Sample dialog" description="A short sentence about what this asks."><div className="flex gap-2 justify-end"><DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose><DialogClose asChild><Button>Confirm</Button></DialogClose></div></DialogContent></Dialog></Block>
          <Block title="Tabs"><Tabs defaultValue="a" className="w-full"><TabsList><TabsTrigger value="a">First</TabsTrigger><TabsTrigger value="b">Second</TabsTrigger></TabsList><TabsContent value="a" className="pt-4 text-sm text-text-2">First panel.</TabsContent><TabsContent value="b" className="pt-4 text-sm text-text-2">Second panel.</TabsContent></Tabs></Block>
        </>
      );
    case 'Voice':
      return <Block title="Press to talk" note="Web Speech where the browser has it; a hollow blind state where it does not. Whisper/Kokoro plug in through the engine prop."><VoiceButton /></Block>;
    default:
      return null;
  }
}

function TemplateView({ section }: { section: Section }) {
  const body = (
    <>
      <p>Sample paragraph one. This is placeholder prose to show measure, rhythm and link colour, <a href="#">with a link</a>.</p>
      <p>Sample paragraph two, long enough to wrap at the 68ch measure on a desktop and to run several lines on a phone.</p>
    </>
  );
  const inner = (() => {
    switch (section) {
      case 'T · Landing':
        return <Landing eyebrow="Sample" headline="Business ideas that survived the checks. With the sources." lede="1,444 researched. 77 for sale. Every claim linked to public data. (sample copy)" proof={['29 sources', 'buyer named', 'price tested']} cta={{ label: 'See the 77', href: '#' }} secondary={{ label: 'Free sample, no email', href: '#' }} voice feed={{ rows: [{ at: '14:02', text: 'sample event', state: 'good' }], title: 'Today' }} shelf={{ title: 'Newest packs', items: shelf }} />;
      case 'T · Catalogue':
        return <Catalogue title="Catalogue" count={77} facets={[{ name: 'Sector', options: [{ label: 'All', href: '#', active: true, count: 77 }, { label: 'Food', href: '#', count: 12 }, { label: 'Health', href: '#', count: 9 }] }]} sort={[{ label: 'Newest', href: '#', active: true }, { label: 'Price', href: '#' }]} items={shelf.map((s) => ({ ...s, price: '£29.99', meta: ['29 sources', 'pays back in 8 months'] }))} more={{ label: 'Next 12', href: '#' }} />;
      case 'T · Detail':
        return <Detail eyebrow="Sample · Food" title="Cold chain audit software for poultry processors" lede="Sample lede: who buys it, what they pay today, and why now." price={{ amount: '£29.99', note: 'one-time' }} checks={[{ label: 'Pain', state: 'good' }, { label: 'Buyer', state: 'good' }, { label: 'Price', state: 'good' }, { label: 'Reach', state: 'needs' }, { label: 'Legal', state: 'good' }, { label: 'Timing', state: 'blind' }]} facts={['14-day money back', 'One payment, guest checkout', 'Operated by Sample Ltd, London']} cta={{ label: 'Buy this pack', href: '#' }} sample={{ label: 'Read a free sample first', href: '#' }} body={body} sources={[{ label: 'sample.gov/report-2026', href: '#' }, { label: 'sample.org/data', href: '#' }]} />;
      case 'T · Checkout':
        return <Checkout item={{ title: 'Sample pack', price: '£29.99' }} payment={<div className="text-sm text-text-2 py-8 text-center">payment element goes here</div>} facts={['14-day money back', 'One payment', 'Download in 30 seconds']} consent={{ id: 'c1', label: 'One email, only if a pack ships.' }} submit={{ label: 'Pay £29.99', onSubmit: (e) => e.preventDefault() }} />;
      case 'T · Account':
        return <Account name="Sample Person" email="sample@example.com" orders={[{ id: 'ord_1', title: 'Sample pack', date: '2026-09-01', href: '#' }]} signOut={{ label: 'Sign out', href: '#' }} />;
      case 'T · Docs':
        return <Docs section="Guides" title="Sample doc page" nav={[{ title: 'Start', links: [{ label: 'Install', href: '#', current: true }, { label: 'Tokens', href: '#' }] }, { title: 'Guards', links: [{ label: 'Purity', href: '#' }, { label: 'Contrast', href: '#' }] }]} toc={[{ label: 'First', href: '#' }, { label: 'Second', href: '#' }]} body={body} updated="2026-10-01" />;
      case 'T · Error':
        return <ErrorPage code="404" title="That page is not here" text="The link may be old. The catalogue and the free sample are one tap away." requestId="req_sample" />;
      case 'T · Empty':
        return <Empty title="No packs match" text="Try fewer filters, or read the free sample while you decide." action={{ label: 'Clear filters', href: '#' }} />;
      default:
        return null;
    }
  })();
  return <SiteShell nav={nav} footer={footer}>{inner}</SiteShell>;
}
