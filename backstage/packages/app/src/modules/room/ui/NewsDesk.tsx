import React, { useEffect, useMemo, useState } from 'react';
import { SEVERITY_COLOR } from '../../home/intentCue';
import { CHANNELS, ago, rank } from './newsRundown';
import type { Rundown, Story } from './newsRundown';

const ROTATE_MS = 8000;
const SLIDE_MS = 450;
const MARQUEE_PX_PER_S = 70;

const STYLE_BLOCK = `
@keyframes newsdesk-live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}
@keyframes newsdesk-lower-third-in {
  from { transform: translateX(-40px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes newsdesk-marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
@keyframes newsdesk-glare {
  0% { transform: translateX(-120%) skewX(-20deg); }
  100% { transform: translateX(220%) skewX(-20deg); }
}
@keyframes newsdesk-vignette-pulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 0.75; }
}
`;

const glassPlate: React.CSSProperties = {
  background: 'rgba(10, 12, 20, 0.72)',
  backdropFilter: 'blur(6px)',
  border: '1px solid rgba(255,255,255,0.12)',
  boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
};

interface NewsBugProps {
  channelDef: { n: number; label: string };
  story: Story | null;
}

function NewsBug({ channelDef, story }: NewsBugProps): JSX.Element {
  const isLive = story?.state === 'confirmed';
  const tag = story?.state === 'corrected' ? 'CORRECTED' : 'REPORTED';
  return (
    <div
      data-testid="news-bug"
      style={{
        position: 'absolute',
        top: 64,
        left: 24,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 14px',
        borderRadius: 8,
        pointerEvents: 'none',
        ...glassPlate,
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 4,
          background: '#111',
          border: '2px solid #fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: 14,
          color: '#fff',
        }}
      >
        {channelDef.n}
      </div>
      <div style={{ fontWeight: 700, fontSize: 13, letterSpacing: 1, color: '#fff' }}>
        {channelDef.label}
      </div>
      {isLive ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '2px 8px',
            borderRadius: 999,
            background: 'rgba(255,0,60,0.18)',
            border: '1px solid rgba(255,0,60,0.6)',
          }}
        >
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: '#ff0033',
              animation: 'newsdesk-live-pulse 1.1s ease-in-out infinite',
            }}
          />
          <span style={{ fontSize: 11, fontWeight: 700, color: '#ff5577', letterSpacing: 1 }}>
            LIVE
          </span>
        </div>
      ) : story ? (
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.5)',
            letterSpacing: 1,
          }}
        >
          {tag}
        </span>
      ) : null}
    </div>
  );
}

interface LowerThirdProps {
  channelDef: { label: string };
  story: Story | null;
  nowMs: number;
  progress: number;
}

function LowerThird({ channelDef, story, nowMs, progress }: LowerThirdProps): JSX.Element {
  const [displayStory, setDisplayStory] = useState(story);
  const [animKey, setAnimKey] = useState(0);

  useEffect(() => {
    if (story?.id !== displayStory?.id) {
      setDisplayStory(story);
      setAnimKey(k => k + 1);
    }
  }, [story, displayStory]);

  if (!story) {
    return (
      <div
        data-testid="news-lower-third"
        style={{
          position: 'absolute',
          bottom: 42,
          left: 24,
          padding: '12px 20px',
          borderRadius: 6,
          pointerEvents: 'none',
          color: 'rgba(255,255,255,0.5)',
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: 1,
          ...glassPlate,
        }}
      >
        NO STORIES · {channelDef.label}
      </div>
    );
  }

  const color = SEVERITY_COLOR[story.severity];
  const metaCount = story.count > 1 ? ` · ×${story.count}` : '';

  return (
    <div
      key={animKey}
      data-testid="news-lower-third"
      style={{
        position: 'absolute',
        bottom: 42,
        left: 24,
        maxWidth: 640,
        display: 'flex',
        borderRadius: 6,
        overflow: 'hidden',
        pointerEvents: 'none',
        animation: `newsdesk-lower-third-in ${SLIDE_MS}ms cubic-bezier(0.16, 1, 0.3, 1)`,
        ...glassPlate,
      }}
    >
      <div style={{ width: 6, alignSelf: 'stretch', background: color }} />
      <div style={{ padding: '12px 18px', flex: 1 }}>
        <div
          style={{
            fontSize: 26,
            fontWeight: 800,
            textTransform: 'uppercase',
            color: '#fff',
            textShadow: `0 0 12px ${color}88`,
            lineHeight: 1.15,
          }}
        >
          {story.headline}
        </div>
        <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.85)', marginTop: 4 }}>
          {story.anchor}
        </div>
        <div
          style={{
            fontSize: 12,
            color: 'rgba(255,255,255,0.55)',
            marginTop: 6,
            letterSpacing: 0.5,
          }}
        >
          {story.source.toUpperCase()} · {ago(story.at, nowMs)}
          {metaCount}
        </div>
        <div
          style={{
            marginTop: 8,
            height: 2,
            background: 'rgba(255,255,255,0.12)',
            borderRadius: 1,
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.max(0, Math.min(1, progress)) * 100}%`,
              background: color,
              borderRadius: 1,
            }}
          />
        </div>
      </div>
    </div>
  );
}

interface CrawlProps {
  channelDef: { label: string };
  stories: Story[];
}

function Crawl({ channelDef, stories }: CrawlProps): JSX.Element {
  if (stories.length === 0) {
    return (
      <div
        data-testid="news-crawl"
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 34,
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(6, 8, 14, 0.88)',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            padding: '0 16px',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            background: '#c00020',
            color: '#fff',
            fontWeight: 800,
            fontSize: 13,
            letterSpacing: 1,
          }}
        >
          ESTATE NEWS
        </div>
        <div
          style={{
            marginLeft: 16,
            fontSize: 13,
            color: 'rgba(255,255,255,0.45)',
            letterSpacing: 0.5,
          }}
        >
          quiet on this channel
        </div>
      </div>
    );
  }

  const items = stories.map((s, i) => (
    <span key={`${s.id}-${i}`} style={{ display: 'inline-flex', alignItems: 'center' }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: SEVERITY_COLOR[s.severity],
          display: 'inline-block',
          marginRight: 10,
        }}
      />
      <span style={{ marginRight: 40 }}>{s.headline}</span>
    </span>
  ));

  const widthPx = Math.max(2000, stories.length * 400);
  const durationS = widthPx / MARQUEE_PX_PER_S;

  return (
    <div
      data-testid="news-crawl"
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 34,
        display: 'flex',
        alignItems: 'center',
        background: 'rgba(6, 8, 14, 0.88)',
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          padding: '0 16px',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          background: '#c00020',
          color: '#fff',
          fontWeight: 800,
          fontSize: 13,
          letterSpacing: 1,
          zIndex: 1,
          flexShrink: 0,
        }}
      >
        {channelDef.label}
      </div>
      <div style={{ overflow: 'hidden', flex: 1, whiteSpace: 'nowrap' }}>
        <div
          style={{
            display: 'inline-flex',
            whiteSpace: 'nowrap',
            fontSize: 13,
            color: 'rgba(255,255,255,0.9)',
            animation: `newsdesk-marquee ${durationS}s linear infinite`,
          }}
        >
          <span style={{ display: 'inline-flex', paddingLeft: 24 }}>{items}</span>
          <span style={{ display: 'inline-flex', paddingLeft: 24 }} aria-hidden="true">
            {items}
          </span>
        </div>
      </div>
    </div>
  );
}

interface BreakingBandProps {
  story: Story;
}

function BreakingBand({ story }: BreakingBandProps): JSX.Element {
  return (
    <div
      data-testid="news-breaking"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'fixed',
          inset: 0,
          boxShadow: 'inset 0 0 140px rgba(255,0,40,0.55)',
          animation: 'newsdesk-vignette-pulse 1.6s ease-in-out infinite',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(180deg, #c00018, #7a0010)',
          padding: '18px 32px',
          borderBottom: '3px solid #fff',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            width: '30%',
            background:
              'linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent)',
            animation: 'newsdesk-glare 1.6s ease-in-out infinite',
          }}
        />
        <div
          style={{
            fontSize: 44,
            fontWeight: 900,
            fontStretch: 'condensed',
            letterSpacing: 2,
            color: '#fff',
            textTransform: 'uppercase',
            lineHeight: 1,
          }}
        >
          BREAKING NEWS
        </div>
        <div
          style={{
            marginTop: 8,
            fontSize: 20,
            fontWeight: 700,
            color: '#fff',
            textTransform: 'uppercase',
          }}
        >
          {story.headline}
        </div>
      </div>
    </div>
  );
}

interface ChannelStripProps {
  active: number;
  onChannel: (n: number) => void;
}

function ChannelStrip({ active, onChannel }: ChannelStripProps): JSX.Element {
  return (
    <div
      data-testid="news-channels"
      style={{
        position: 'absolute',
        bottom: 42,
        right: 24,
        display: 'flex',
        gap: 6,
        pointerEvents: 'auto',
      }}
    >
      {CHANNELS.map(c => {
        const isActive = c.n === active;
        return (
          <button
            key={c.n}
            type="button"
            data-testid={`news-chip-${c.n}`}
            onClick={() => onChannel(c.n)}
            style={{
              cursor: 'pointer',
              border: isActive ? '1px solid rgba(255,255,255,0.8)' : '1px solid rgba(255,255,255,0.15)',
              borderRadius: 4,
              padding: '4px 8px',
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 0.5,
              color: isActive ? '#fff' : 'rgba(255,255,255,0.5)',
              background: isActive ? 'rgba(255,255,255,0.15)' : 'rgba(10,12,20,0.6)',
            }}
          >
            {c.n} {c.label}
          </button>
        );
      })}
    </div>
  );
}

export interface NewsDeskProps {
  rundown: Rundown;
  channel: number;
  onChannel: (n: number) => void;
  breaking: Story | null;
  nowMs: number;
}

export default function NewsDesk({
  rundown,
  channel,
  onChannel,
  breaking,
  nowMs,
}: NewsDeskProps): JSX.Element {
  const channelDef = CHANNELS.find(c => c.n === channel) ?? CHANNELS[0];
  const isMovie = channelDef.key === 'movie';

  const channelStories = useMemo(() => {
    if (isMovie) {
      return [];
    }
    const key = channelDef.key as keyof Rundown;
    return [...(rundown[key] ?? [])].sort(rank).slice(0, 5);
  }, [rundown, channelDef, isMovie]);

  const [rotationIndex, setRotationIndex] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    setRotationIndex(0);
    setElapsedMs(0);
  }, [channel]);

  useEffect(() => {
    if (channelStories.length <= 1) {
      return undefined;
    }
    const interval = setInterval(() => {
      setElapsedMs(prev => {
        const next = prev + 200;
        if (next >= ROTATE_MS) {
          setRotationIndex(i => (i + 1) % channelStories.length);
          return 0;
        }
        return next;
      });
    }, 200);
    return () => clearInterval(interval);
  }, [channelStories.length]);

  const onScreenStory =
    channelStories.length > 0 ? channelStories[rotationIndex % channelStories.length] : null;
  const progress = channelStories.length > 1 ? elapsedMs / ROTATE_MS : 0;

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <style>{STYLE_BLOCK}</style>
      <NewsBug channelDef={channelDef} story={onScreenStory} />
      {!isMovie && (
        <LowerThird
          channelDef={channelDef}
          story={onScreenStory}
          nowMs={nowMs}
          progress={progress}
        />
      )}
      {!isMovie && <Crawl channelDef={channelDef} stories={channelStories} />}
      {breaking && <BreakingBand story={breaking} />}
      <ChannelStrip active={channel} onChannel={onChannel} />
    </div>
  );
}
