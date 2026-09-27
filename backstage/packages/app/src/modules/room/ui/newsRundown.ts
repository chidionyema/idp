import type { ShotType } from './cinecam';
import { SEVERITY_COLOR } from '../../home/intentCue';

export type Channel = 'news' | 'agents' | 'deploys' | 'cluster' | 'metrics' | 'products';
export type Severity = 'info' | 'warn' | 'danger';
export type StoryState = 'reported' | 'confirmed' | 'corrected';

export interface Story {
  id: string;
  supersedes?: string;
  channel: Channel;
  source: string;
  severity: Severity;
  state: StoryState;
  headline: string;
  anchor: string;
  entity: string;
  link?: string;
  evidence: string[];
  score: number;
  count: number;
  breaking: boolean;
  first_at: string;
  at: string;
}

export interface StoryFrame {
  type: 'story';
  on: Channel;
  story: Story;
}

const CHANNELS_SET: Channel[] = ['news', 'agents', 'deploys', 'cluster', 'metrics', 'products'];
const SEVERITIES: Severity[] = ['info', 'warn', 'danger'];
const STATES: StoryState[] = ['reported', 'confirmed', 'corrected'];

export interface ChannelDef {
  n: number;
  key: string;
  label: string;
}

export const CHANNELS: ChannelDef[] = [
  { n: 0, key: 'news', label: 'NEWS' },
  { n: 1, key: 'agents', label: 'AGENTS' },
  { n: 2, key: 'deploys', label: 'DEPLOYS & CI' },
  { n: 3, key: 'cluster', label: 'CLUSTER' },
  { n: 4, key: 'metrics', label: 'METRICS & SPEND' },
  { n: 5, key: 'products', label: 'PRODUCTS' },
  { n: 6, key: 'movie', label: 'MOVIE' },
];

export function channelForKey(key: string): number | null {
  const def = CHANNELS.find(c => c.key === key);
  return def ? def.n : null;
}

function isStringArray(x: unknown): x is string[] {
  return Array.isArray(x) && x.every(item => typeof item === 'string');
}

function parseStory(x: unknown): Story | null {
  if (typeof x !== 'object' || x === null) {
    return null;
  }
  const s = x as Record<string, unknown>;
  if (typeof s.id !== 'string' || s.id.length === 0) {
    return null;
  }
  if (s.supersedes !== undefined && typeof s.supersedes !== 'string') {
    return null;
  }
  if (typeof s.channel !== 'string' || !CHANNELS_SET.includes(s.channel as Channel)) {
    return null;
  }
  if (typeof s.source !== 'string') {
    return null;
  }
  if (typeof s.severity !== 'string' || !SEVERITIES.includes(s.severity as Severity)) {
    return null;
  }
  if (typeof s.state !== 'string' || !STATES.includes(s.state as StoryState)) {
    return null;
  }
  if (typeof s.headline !== 'string') {
    return null;
  }
  if (typeof s.anchor !== 'string') {
    return null;
  }
  if (typeof s.entity !== 'string') {
    return null;
  }
  if (s.link !== undefined && typeof s.link !== 'string') {
    return null;
  }
  if (!isStringArray(s.evidence)) {
    return null;
  }
  if (typeof s.score !== 'number') {
    return null;
  }
  if (typeof s.count !== 'number') {
    return null;
  }
  if (typeof s.breaking !== 'boolean') {
    return null;
  }
  if (typeof s.first_at !== 'string') {
    return null;
  }
  if (typeof s.at !== 'string') {
    return null;
  }

  const story: Story = {
    id: s.id,
    channel: s.channel as Channel,
    source: s.source,
    severity: s.severity as Severity,
    state: s.state as StoryState,
    headline: s.headline,
    anchor: s.anchor,
    entity: s.entity,
    evidence: s.evidence,
    score: s.score,
    count: s.count,
    breaking: s.breaking,
    first_at: s.first_at,
    at: s.at,
  };
  if (s.supersedes !== undefined) {
    story.supersedes = s.supersedes as string;
  }
  if (s.link !== undefined) {
    story.link = s.link as string;
  }
  return story;
}

export function parseStoryFrame(x: unknown): StoryFrame | null {
  if (typeof x !== 'object' || x === null) {
    return null;
  }
  const f = x as Record<string, unknown>;
  if (f.type !== 'story') {
    return null;
  }
  if (typeof f.on !== 'string' || !CHANNELS_SET.includes(f.on as Channel)) {
    return null;
  }
  const story = parseStory(f.story);
  if (story === null) {
    return null;
  }
  return { type: 'story', on: f.on as Channel, story };
}

export type Rundown = Record<Channel, Story[]>;

export function emptyRundown(): Rundown {
  return {
    news: [],
    agents: [],
    deploys: [],
    cluster: [],
    metrics: [],
    products: [],
  };
}

const MAX_PER_CHANNEL = 50;

/** Breaking first, then score desc, then most recent. */
export function rank(a: Story, b: Story): number {
  if (a.breaking !== b.breaking) {
    return a.breaking ? -1 : 1;
  }
  if (a.score !== b.score) {
    return b.score - a.score;
  }
  const aAt = Date.parse(a.at);
  const bAt = Date.parse(b.at);
  return bAt - aAt;
}

function sortChannel(stories: Story[]): Story[] {
  return [...stories].sort(rank);
}

function removeFromChannel(stories: Story[], id: string): Story[] {
  return stories.filter(s => s.id !== id);
}

export function ingest(rundown: Rundown, frame: StoryFrame, _nowMs: number): Rundown {
  const next: Rundown = {
    news: [...rundown.news],
    agents: [...rundown.agents],
    deploys: [...rundown.deploys],
    cluster: [...rundown.cluster],
    metrics: [...rundown.metrics],
    products: [...rundown.products],
  };

  const { on, story } = frame;
  const channelStories = removeFromChannel(next[on], story.id);
  channelStories.push(story);
  let sorted = sortChannel(channelStories);
  if (sorted.length > MAX_PER_CHANNEL) {
    sorted = sorted.slice(0, MAX_PER_CHANNEL);
  }
  next[on] = sorted;

  if (story.supersedes !== undefined) {
    for (const key of CHANNELS_SET) {
      next[key] = removeFromChannel(next[key], story.supersedes);
    }
  }

  return next;
}

export function shouldInterrupt(story: Story, nowMs: number, seen: ReadonlySet<string>): boolean {
  if (!story.breaking) {
    return false;
  }
  if (seen.has(story.id)) {
    return false;
  }
  const atMs = Date.parse(story.at);
  if (Number.isNaN(atMs)) {
    return false;
  }
  return Math.abs(nowMs - atMs) <= 120_000;
}

export interface Visual {
  ring: 'pulse' | 'burn' | 'fire';
  color: string;
  burst: number;
  shot: ShotType | null;
}

export function visualFor(story: Story): Visual {
  if (story.severity === 'danger' || story.breaking) {
    return { ring: 'fire', color: SEVERITY_COLOR.danger, burst: 8, shot: 'MACRO_DOV' };
  }
  if (story.channel === 'deploys' && story.state === 'confirmed') {
    return { ring: 'pulse', color: '#00ffaa', burst: 3, shot: 'ORBIT_FOCUS' };
  }
  if (story.state === 'corrected') {
    return { ring: 'pulse', color: '#00ffaa', burst: 0, shot: null };
  }
  if (story.severity === 'warn') {
    return { ring: 'pulse', color: SEVERITY_COLOR.warn, burst: 0, shot: null };
  }
  return { ring: 'pulse', color: SEVERITY_COLOR.info, burst: 0, shot: null };
}

export function ago(atIso: string, nowMs: number): string {
  const atMs = Date.parse(atIso);
  if (Number.isNaN(atMs)) {
    return 'now';
  }
  const deltaMs = nowMs - atMs;
  if (deltaMs < 60_000) {
    return 'now';
  }
  if (deltaMs < 3_600_000) {
    return `${Math.floor(deltaMs / 60_000)}m`;
  }
  return `${Math.floor(deltaMs / 3_600_000)}h`;
}
