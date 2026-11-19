/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';

export type ActiveWorkspace =
  | 'flagship'
  | 'dof-governance'
  | 'prose-engine'
  | 'inspector'
  | 'compiler'
  | 'foundations'
  | 'strategy';

interface TopBarProps {
  activeWorkspace: ActiveWorkspace;
  onSelectWorkspace: (workspace: ActiveWorkspace) => void;
  corpusCount: number;
}

const PUBLIC_NAV_ITEMS = [
  { id: 'the-premise', label: 'The Premise' },
  { id: 'interactive-architecture', label: 'Architecture' },
  { id: 'the-stack', label: 'The Four Layers' },
  { id: 'explanation-record', label: 'The Record' },
  { id: 'open-weights', label: 'Honest Limits' },
] as const;

export const TopBar: React.FC<TopBarProps> = ({
  activeWorkspace,
  onSelectWorkspace,
  corpusCount,
}) => {
  const isPublicSite = activeWorkspace === 'flagship';
  const [activeSection, setActiveSection] = useState<string>('');
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  useEffect(() => {
    if (!isPublicSite) return;

    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight =
        document.documentElement.scrollHeight - window.innerHeight;
      const pct = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0;
      setScrollProgress(pct);

      const offsets = PUBLIC_NAV_ITEMS.map((item) => {
        const el = document.getElementById(item.id);
        if (!el) return { id: item.id, top: Infinity };
        const rect = el.getBoundingClientRect();
        return { id: item.id, top: rect.top };
      });

      const current = offsets
        .filter((o) => o.top <= 180)
        .sort((a, b) => b.top - a.top)[0];

      setActiveSection(current ? current.id : '');
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isPublicSite]);

  const scrollToPublicSection = (sectionId: string) => {
    setMobileMenuOpen(false);
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  if (isPublicSite) {
    return (
      <header className="sticky top-0 z-30 bg-[#FBF9F5]/95 backdrop-blur-sm border-b border-[#E2DDD5]">
        <div className="max-w-5xl mx-auto px-6 sm:px-10 h-16 flex items-center justify-between gap-8">
          {/* Zone 1: Single text element wordmark */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setMobileMenuOpen(false);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="font-serif-editorial text-xl font-medium tracking-tight text-[#141413] whitespace-nowrap shrink-0"
          >
            Meridian Intelligence
          </a>

          {/* Zone 2: 5 concise single-line navigation links */}
          <nav
            aria-label="Primary Navigation"
            className="hidden md:flex items-center gap-7 text-[13px] font-medium text-[#57534E]"
          >
            {PUBLIC_NAV_ITEMS.map((item) => {
              const isActive = activeSection === item.id;
              return (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    scrollToPublicSection(item.id);
                  }}
                  className={`py-1 transition-colors whitespace-nowrap shrink-0 border-b ${
                    isActive
                      ? 'text-[#141413] border-[#141413]'
                      : 'border-transparent hover:text-[#141413] hover:border-[#A8A29E]'
                  }`}
                >
                  {item.label}
                </a>
              );
            })}
          </nav>

          {/* Zone 3: 1 Primary Action + Mobile Menu Trigger */}
          <div className="flex items-center gap-3 shrink-0">
            <a
              href="#inquire"
              onClick={(e) => {
                e.preventDefault();
                scrollToPublicSection('inquire');
              }}
              className="px-4 py-2 text-[13px] font-medium text-[#FBF9F5] bg-[#141413] hover:bg-[#1E3A5F] transition-colors whitespace-nowrap shrink-0"
            >
              Inquire
            </a>

            <button
              type="button"
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden px-3 py-2 text-xs font-mono text-[#141413] border border-[#D6D0C4] hover:border-[#141413] transition-colors cursor-pointer"
            >
              {mobileMenuOpen ? 'Close' : 'Menu'}
            </button>
          </div>
        </div>

        {/* Reading Depth Progress Hairline */}
        <div
          aria-hidden="true"
          className="h-[1.5px] bg-transparent w-full overflow-hidden"
        >
          <div
            className="h-full bg-[#1E3A5F] transition-transform duration-150 ease-out origin-left"
            style={{ transform: `scaleX(${scrollProgress / 100})` }}
          />
        </div>

        {/* Responsive Mobile Drawer */}
        {mobileMenuOpen && (
          <nav
            aria-label="Mobile Navigation"
            className="md:hidden border-t border-[#E2DDD5] bg-[#FBF9F5] px-6 py-4 space-y-1"
          >
            {PUBLIC_NAV_ITEMS.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  scrollToPublicSection(item.id);
                }}
                className="block py-2.5 text-sm font-medium text-[#1C1917] hover:text-[#1E3A5F] border-b border-[#EFECE6] last:border-b-0"
              >
                {item.label}
              </a>
            ))}
          </nav>
        )}
      </header>
    );
  }

  // INTERNAL WORKBENCH HEADER (Only visible when navigating to internal tools)
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-3.5 border-b border-slate-800 bg-[#090D16] text-slate-100 sticky top-0 z-30">
      <button
        type="button"
        onClick={() => onSelectWorkspace('inspector')}
        className="font-serif-editorial text-lg font-medium tracking-tight text-slate-100 whitespace-nowrap shrink-0 cursor-pointer"
      >
        Meridian Workbench
      </button>

      <nav
        aria-label="Internal Workbench Navigation"
        className="flex items-center gap-6 text-xs font-mono text-slate-400 overflow-x-auto"
      >
        <button
          type="button"
          onClick={() => onSelectWorkspace('inspector')}
          className={`py-1.5 transition-colors whitespace-nowrap shrink-0 border-b-2 cursor-pointer ${
            activeWorkspace === 'inspector'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'border-transparent hover:text-slate-100'
          }`}
        >
          Record Inspector ({corpusCount})
        </button>
        <button
          type="button"
          onClick={() => onSelectWorkspace('compiler')}
          className={`py-1.5 transition-colors whitespace-nowrap shrink-0 border-b-2 cursor-pointer ${
            activeWorkspace === 'compiler'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'border-transparent hover:text-slate-100'
          }`}
        >
          Record Compiler
        </button>
        <button
          type="button"
          onClick={() => onSelectWorkspace('prose-engine')}
          className={`py-1.5 transition-colors whitespace-nowrap shrink-0 border-b-2 cursor-pointer ${
            activeWorkspace === 'prose-engine'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'border-transparent hover:text-slate-100'
          }`}
        >
          Prose Gate
        </button>
        <button
          type="button"
          onClick={() => onSelectWorkspace('foundations')}
          className={`py-1.5 transition-colors whitespace-nowrap shrink-0 border-b-2 cursor-pointer ${
            activeWorkspace === 'foundations' || activeWorkspace === 'strategy'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'border-transparent hover:text-slate-100'
          }`}
        >
          Theorems &amp; EU Matrix
        </button>
        <button
          type="button"
          onClick={() => onSelectWorkspace('dof-governance')}
          className={`py-1.5 transition-colors whitespace-nowrap shrink-0 border-b-2 cursor-pointer ${
            activeWorkspace === 'dof-governance'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'border-transparent hover:text-slate-100'
          }`}
        >
          Genesis &amp; IDP (DoF-v1)
        </button>
      </nav>

      <div className="flex items-center shrink-0">
        <button
          type="button"
          onClick={() => onSelectWorkspace('flagship')}
          className="px-4 py-2 text-xs font-medium text-slate-100 bg-slate-800/90 border border-slate-700 hover:border-slate-500 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
        >
          ← Meridian Public Site
        </button>
      </div>
    </header>
  );
};

