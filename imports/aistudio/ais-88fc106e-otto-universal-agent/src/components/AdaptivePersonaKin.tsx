import React, { useState } from 'react';
import { 
  Heart, 
  Volume2, 
  ShieldCheck, 
  Check, 
  Clock, 
  BookOpen, 
  Sun, 
  Send, 
  Mic, 
  PhoneCall, 
  Sparkles,
  Lock,
  UserCheck,
  ChevronRight,
  Eye,
  CheckCircle2,
  MessageCircle,
  QrCode,
  Share2
} from 'lucide-react';
import { 
  DEFAULT_FAMILY_PROFILES, 
  INITIAL_KIN_PROFILE, 
  FAMILY_LETTERS, 
  SCAM_SHIELD_INCIDENTS 
} from '../data/familyRecords';
import { FamilyKinProfile } from '../types/otto';

export const AdaptivePersonaKin: React.FC = () => {
  const [profiles, setProfiles] = useState<FamilyKinProfile[]>(DEFAULT_FAMILY_PROFILES);
  const [profile, setProfile] = useState<FamilyKinProfile>(INITIAL_KIN_PROFILE);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editName, setEditName] = useState<string>(INITIAL_KIN_PROFILE.name);
  const [editRelationship, setEditRelationship] = useState<string>(INITIAL_KIN_PROFILE.relationship);
  const [activeTab, setActiveTab] = useState<'prayers' | 'health' | 'letters' | 'scam-shield' | 'whatsapp'>('whatsapp');
  const [isPlayingAudio, setIsPlayingAudio] = useState<string | null>(null);
  const [customQuery, setCustomQuery] = useState('');
  const [ottoReply, setOttoReply] = useState<string | null>(
    `Peace be with you, ${INITIAL_KIN_PROFILE.name}. I am quietly looking after your day, daily schedule, and keeping spam away.`
  );

  const handleSelectProfile = (p: FamilyKinProfile) => {
    setProfile(p);
    setEditName(p.name);
    setEditRelationship(p.relationship);
    setOttoReply(`Hello ${p.name}. I am quietly looking after your schedule, daily health routines, and keeping spam calls away.`);
  };

  const handleSaveProfile = () => {
    const updated = { ...profile, name: editName, relationship: editRelationship };
    setProfile(updated);
    setProfiles(profiles.map(p => p.id === updated.id ? updated : p));
    setIsEditing(false);
    setOttoReply(`Profile updated for ${updated.name}. All care routines and air-gapped protection are synchronized.`);
  };

  const toggleMedication = (index: number) => {
    if (!profile.medications) return;
    const updated = [...profile.medications];
    updated[index].taken = !updated[index].taken;
    setProfile({ ...profile, medications: updated });
  };

  const handlePlayPrayerAudio = (name: string) => {
    if (isPlayingAudio === name) {
      setIsPlayingAudio(null);
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      return;
    }

    setIsPlayingAudio(name);
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const textToSpeak = `Beginning ${name} for ${profile.name}. May peace and light fill your day.`;
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.rate = 0.9;
      utterance.pitch = 0.95;
      utterance.onend = () => setIsPlayingAudio(null);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleSendFamilyMessage = (text?: string) => {
    const q = text || customQuery;
    if (!q.trim()) return;

    setOttoReply('Listening with care...');
    setTimeout(() => {
      setOttoReply(
        `Right away, ${profile.name}. I have taken care of that gently for you. Your family sends their love and I've ensured everything is running smoothly.`
      );
      setCustomQuery('');

      if (typeof window !== 'undefined' && window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(
          `Right away, ${profile.name}. I have taken care of that gently for you.`
        );
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
      }
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Dynamic Family Member Directory Selector */}
      <div className="rounded-2xl border border-stone-800 bg-stone-900/80 p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 text-xs font-serif">
        <div className="flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-rose-300" />
          <span className="font-bold text-stone-200">Select or Configure Family Member:</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {profiles.map(p => (
            <button
              key={p.id}
              onClick={() => handleSelectProfile(p)}
              className={`px-3 py-1.5 rounded-xl transition-all font-medium ${
                profile.id === p.id
                  ? 'bg-rose-600 text-white shadow font-semibold'
                  : 'bg-stone-950 text-stone-400 border border-stone-800 hover:text-stone-200'
              }`}
            >
              {p.name}
            </button>
          ))}

          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-3 py-1.5 rounded-xl bg-stone-800 hover:bg-stone-700 text-stone-200 border border-stone-700 font-medium transition-all"
          >
            {isEditing ? 'Cancel Edit' : '✏️ Rename / Edit'}
          </button>
        </div>
      </div>

      {/* Inline Profile Editor Form */}
      {isEditing && (
        <div className="p-4 rounded-2xl bg-stone-900 border border-rose-500/30 space-y-3 animate-fadeIn">
          <div className="font-serif font-bold text-sm text-stone-100 flex items-center gap-2">
            <span>Edit Family Profile Information</span>
            <span className="text-xs text-stone-400 font-normal">(Customize name, relationship, and care preferences)</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-serif">
            <div>
              <label className="text-stone-400 block mb-1">Family Member Name:</label>
              <input
                type="text"
                value={editName}
                onChange={e => setEditName(e.target.value)}
                placeholder="e.g. Mom, Dad, Grandma Sarah, Wife, Son"
                className="w-full bg-stone-950 text-stone-100 px-3 py-2 rounded-xl border border-stone-800 focus:outline-none focus:border-rose-400"
              />
            </div>
            <div>
              <label className="text-stone-400 block mb-1">Relationship Role:</label>
              <input
                type="text"
                value={editRelationship}
                onChange={e => setEditRelationship(e.target.value)}
                placeholder="e.g. Mother, Father, Spouse, Child"
                className="w-full bg-stone-950 text-stone-100 px-3 py-2 rounded-xl border border-stone-800 focus:outline-none focus:border-rose-400"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 rounded-lg bg-stone-800 text-stone-300 text-xs font-serif"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveProfile}
              className="px-4 py-1.5 rounded-lg bg-rose-600 text-white text-xs font-serif font-semibold shadow hover:bg-rose-500"
            >
              Save Profile Changes
            </button>
          </div>
        </div>
      )}

      {/* Serene Non-Tech Banner */}
      <div className="rounded-2xl border border-rose-300/20 bg-gradient-to-b from-stone-900 via-stone-950 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-serif mb-2">
              <Heart className="w-3.5 h-3.5 fill-current" />
              <span>COMPASSIONATE KIN MODE · FAMILY CIRCLE</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-serif font-bold text-stone-100 tracking-tight">
              Gentle Family Assistant: {profile.name}
            </h2>
            <p className="text-sm text-stone-300 max-w-2xl mt-1 leading-relaxed">
              Adapted specifically for non-technical family members ({profile.relationship}). <span className="text-emerald-400 font-semibold">Zero terminal jargon</span>, warm serene typography, daily routines, and an automated silent shield against scams and robocalls.
            </p>
          </div>

          {/* Privacy & Air-Gap Badge */}
          <div className="flex items-center gap-3 bg-stone-900/90 p-3 rounded-xl border border-stone-800 text-xs">
            <Lock className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <div className="font-semibold text-stone-200">Cryptographic Air-Gap Active</div>
              <div className="text-[11px] text-stone-400">Personal care isolated from estate cloud keys</div>
            </div>
          </div>
        </div>

        {/* Serene Navigation Tabs */}
        <div className="mt-6 flex flex-wrap gap-2">
          {[
            { id: 'whatsapp', label: `WhatsApp Companion (${profile.name})`, icon: MessageCircle },
            { id: 'prayers', label: 'Daily Care & Routines', icon: Sun },
            { id: 'health', label: 'Medications & Daily Care', icon: Heart },
            { id: 'letters', label: 'Family Letters & Audio', icon: BookOpen },
            { id: 'scam-shield', label: 'Scam & Robocall Shield', icon: ShieldCheck }
          ].map(tab => {
            const Icon = tab.icon;
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 rounded-xl font-serif text-xs font-semibold flex items-center gap-2 transition-all ${
                  isSelected
                    ? 'bg-rose-500/20 text-rose-200 border border-rose-400/40 shadow-md'
                    : 'bg-stone-900/60 text-stone-400 border border-stone-800 hover:text-stone-200 hover:bg-stone-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isSelected ? 'text-rose-300' : 'text-stone-500'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Gentle Otto Speaking Card */}
      <div className="p-5 rounded-2xl bg-stone-900/70 border border-stone-800/80 shadow-xl flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-300 shrink-0 mt-0.5">
          <Sparkles className="w-6 h-6" />
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-serif font-bold text-stone-200 text-sm">Otto (Your Family Companion)</span>
            <span className="text-xs text-emerald-400 font-serif flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse" />
              Quietly looking after you
            </span>
          </div>
          <p className="text-stone-200 text-sm font-serif leading-relaxed italic">
            "{ottoReply}"
          </p>
        </div>
      </div>

      {/* TAB 0: WHATSAPP COMPANION & FOUNDER DELEGATION */}
      {activeTab === 'whatsapp' && (
        <div className="space-y-6">
          {/* Founder Delegation Explainer Header */}
          <div className="rounded-2xl border border-stone-800 bg-stone-950 p-6 shadow-xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-stone-800 pb-4">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-bold mb-1">
                  <MessageCircle className="w-3.5 h-3.5" />
                  <span>WHATSAPP INTEGRATION &amp; 10-SECOND FAMILY ONBOARDING</span>
                </div>
                <h3 className="font-serif font-bold text-xl text-stone-100">
                  How a Founder Gives Otto to a Family Member
                </h3>
                <p className="text-xs text-stone-300 font-serif max-w-2xl mt-1 leading-relaxed">
                  Family members do <strong className="text-stone-100">not</strong> need to install new apps, create accounts, or remember passwords. Otto integrates natively with <strong className="text-emerald-400">WhatsApp</strong>, Apple iMessage, and phone calls.
                </p>
              </div>

              {/* Instant WhatsApp Action Link */}
              <div className="flex items-center gap-2">
                <a
                  href="#whatsapp-chat"
                  className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg transition-all"
                >
                  <Share2 className="w-4 h-4" />
                  <span>1-Tap Invite Link (wa.me)</span>
                </a>
              </div>
            </div>

            {/* 3 Step Zero-Friction Delegation Pipeline */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-stone-900/60 border border-stone-800 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold text-sm">
                  1
                </div>
                <h4 className="font-serif font-bold text-sm text-stone-100">Air-Gapped Kin Token</h4>
                <p className="text-xs text-stone-400 font-serif leading-relaxed">
                  Founder clicks one button to generate a scoped Kin token. It strictly sandboxes Otto to pastoral care, medication checks, and scam shielding—permanently revoking terminal, git, and AWS/GCP keys.
                </p>
                <div className="text-[10px] font-mono text-emerald-400 bg-stone-950 p-2 rounded border border-stone-800">
                  scope: ["prayers", "health", "scam_shield"]
                </div>
              </div>

              <div className="p-4 rounded-xl bg-stone-900/60 border border-stone-800 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center font-bold text-sm">
                  2
                </div>
                <h4 className="font-serif font-bold text-sm text-stone-100">1-Tap Distribution</h4>
                <p className="text-xs text-stone-400 font-serif leading-relaxed">
                  Share via WhatsApp contact card, send a <code className="text-stone-200">wa.me</code> link, or tap an NFC card by Sister Beatrice's bedside. WhatsApp opens instantly with a warm greeting already queued.
                </p>
                <div className="text-[10px] font-mono text-cyan-300 bg-stone-950 p-2 rounded border border-stone-800 truncate">
                  wa.me/+1800555OTTO?auth=kin_beatrice_v1
                </div>
              </div>

              <div className="p-4 rounded-xl bg-stone-900/60 border border-stone-800 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-rose-500/20 text-rose-300 flex items-center justify-center font-bold text-sm">
                  3
                </div>
                <h4 className="font-serif font-bold text-sm text-stone-100">Zero-Typing Experience</h4>
                <p className="text-xs text-stone-400 font-serif leading-relaxed">
                  Sister Beatrice simply holds the microphone button to talk. Otto responds with soothing voice notes and single-tap button options (<code className="text-stone-200">Mark Taken ✓</code>).
                </p>
                <div className="text-[10px] font-mono text-rose-300 bg-stone-950 p-2 rounded border border-stone-800">
                  Audio In → Voice Note Out (&lt;800ms)
                </div>
              </div>
            </div>
          </div>

          {/* Interactive WhatsApp Mobile Simulator */}
          <div id="whatsapp-chat" className="rounded-2xl border border-stone-800 bg-stone-950 p-4 sm:p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-stone-800 pb-3">
              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-bold">Interactive Simulator</span>
                <h3 className="font-serif font-bold text-lg text-stone-100">Sister Beatrice's Live WhatsApp with Otto</h3>
              </div>
              <span className="text-xs font-serif text-stone-400 hidden sm:inline">Try sending voice notes or tapping interactive cards below</span>
            </div>

            {/* Mobile Device Frame */}
            <div className="max-w-md mx-auto rounded-3xl border-4 border-stone-700 bg-[#0b141a] overflow-hidden shadow-2xl flex flex-col h-[620px]">
              {/* WhatsApp Header */}
              <div className="bg-[#202c33] px-4 py-3 flex items-center justify-between border-b border-stone-800 shrink-0">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-rose-700 to-amber-600 flex items-center justify-center text-white font-serif font-bold text-lg">
                      O
                    </div>
                    <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#202c33]" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-stone-100 flex items-center gap-1.5">
                      <span>Otto Companion</span>
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div className="text-[11px] text-emerald-400 font-mono">online · family companion</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-stone-300">
                  <button 
                    onClick={() => handleSendFamilyMessage("Sister Beatrice initiates quick check-in call with Otto")}
                    title="Start phone call" 
                    className="p-1.5 hover:bg-stone-700 rounded-full transition-colors"
                  >
                    <PhoneCall className="w-4 h-4" />
                  </button>
                  <span title="End-to-End Encrypted & Cryptographically Scoped">
                    <Lock className="w-3.5 h-3.5 text-stone-400" />
                  </span>
                </div>
              </div>

              {/* Chat Messages Body */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] text-xs">
                {/* Encryption Notice */}
                <div className="text-center my-1">
                  <span className="bg-[#182229] text-[#8696a0] text-[10px] px-3 py-1 rounded-lg inline-flex items-center gap-1 border border-stone-800">
                    <Lock className="w-3 h-3" /> Messages are end-to-end encrypted &amp; privacy isolated.
                  </span>
                </div>

                {/* Date Header */}
                <div className="text-center my-1">
                  <span className="bg-[#182229] text-[#8696a0] text-[10px] px-2 py-0.5 rounded font-mono">TODAY</span>
                </div>

                {/* Otto Message: Morning Greeting + Audio */}
                <div className="flex justify-start">
                  <div className="bg-[#202c33] text-stone-100 rounded-2xl rounded-tl-none p-3 max-w-[85%] space-y-2 shadow">
                    <div className="flex items-center justify-between gap-4 text-[10px] text-rose-300 font-serif font-bold">
                      <span>Morning Matins &amp; Lauds</span>
                      <span className="text-stone-400">07:00 AM</span>
                    </div>
                    <p className="font-serif leading-relaxed text-[13px] text-stone-200">
                      Peace be with you, Sister Beatrice. The morning chapel chimes have concluded. Here is the Benedictine Psalm chant for today's meditation:
                    </p>
                    
                    {/* Audio Player Pill */}
                    <div className="bg-[#111b21] p-2.5 rounded-xl flex items-center gap-3 border border-stone-800">
                      <button
                        onClick={() => handlePlayPrayerAudio("Psalm 91 - Abiding in the Shadow of the Almighty")}
                        className="w-8 h-8 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shrink-0 transition-transform active:scale-95"
                      >
                        <Volume2 className="w-4 h-4" />
                      </button>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-1 h-4">
                          {[40, 70, 90, 60, 100, 45, 80, 65, 30, 90, 75, 40, 85].map((h, idx) => (
                            <span 
                              key={idx} 
                              className={`w-1 rounded-full transition-all duration-300 ${isPlayingAudio ? 'bg-emerald-400 animate-pulse' : 'bg-stone-500'}`}
                              style={{ height: `${h}%` }}
                            />
                          ))}
                        </div>
                        <div className="flex justify-between text-[10px] text-stone-400 font-mono">
                          <span>Psalm 91 Chant</span>
                          <span>1:42</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Otto Interactive Medication Card */}
                <div className="flex justify-start">
                  <div className="bg-[#202c33] text-stone-100 rounded-2xl rounded-tl-none p-3 max-w-[85%] space-y-2.5 shadow">
                    <div className="flex items-center justify-between text-[10px] text-emerald-400 font-mono font-bold">
                      <span className="flex items-center gap-1">
                        <Heart className="w-3 h-3 fill-current" />
                        MEDICATION REMINDER
                      </span>
                      <span className="text-stone-400">08:00 AM</span>
                    </div>
                    <div className="font-serif text-[13px] text-stone-100">
                      Time for your morning <strong>Timolol Eye Drops (1 drop each eye)</strong> and heart pill with warm water.
                    </div>

                    {/* WhatsApp Action Buttons */}
                    <div className="space-y-1.5 pt-1">
                      <button
                        onClick={() => toggleMedication(0)}
                        className={`w-full py-2 px-3 rounded-lg text-xs font-serif font-bold flex items-center justify-center gap-2 transition-all ${
                          profile.medications?.[0]?.taken
                            ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                            : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow'
                        }`}
                      >
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                        <span>{profile.medications?.[0]?.taken ? 'Taken & Recorded for Doctor ✓' : 'Tap to Confirm: Eye Drops Taken'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Sister Beatrice Voice Note (User Bubble) */}
                <div className="flex justify-end">
                  <div className="bg-[#005c4b] text-stone-100 rounded-2xl rounded-tr-none p-3 max-w-[85%] space-y-1.5 shadow">
                    <div className="flex items-center justify-between gap-4 text-[10px] text-emerald-200 font-serif">
                      <span>Sister Beatrice (Voice Note)</span>
                      <span className="text-stone-300">11:15 AM</span>
                    </div>
                    <div className="bg-[#025143] p-2 rounded-xl flex items-center gap-3">
                      <button 
                        onClick={() => {
                          if (typeof window !== 'undefined' && window.speechSynthesis) {
                            window.speechSynthesis.cancel();
                            const u = new SpeechSynthesisUtterance("Thank you Otto, dear. I have taken my drops. Could you let my nephew know my garden tomatoes are ripening?");
                            u.rate = 0.85;
                            u.pitch = 1.05;
                            window.speechSynthesis.speak(u);
                          }
                        }}
                        className="w-7 h-7 rounded-full bg-stone-100 text-[#005c4b] flex items-center justify-center shrink-0"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                      </button>
                      <div className="flex-1 text-[11px] font-serif text-emerald-100 italic">
                        "Thank you Otto dear. I took the drops. Can you tell my nephew my tomatoes are ripe?"
                      </div>
                    </div>
                    <div className="flex justify-end text-[10px] text-emerald-200 gap-1 items-center">
                      <span>11:16 AM</span>
                      <CheckCircle2 className="w-3 h-3 text-cyan-300" />
                    </div>
                  </div>
                </div>

                {/* Forwarded Scam Shield Example */}
                <div className="flex justify-start">
                  <div className="bg-[#202c33] text-stone-100 rounded-2xl rounded-tl-none p-3 max-w-[88%] space-y-2 shadow border-l-4 border-rose-500">
                    <div className="text-[10px] text-rose-400 font-mono font-bold flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      SILENT SCAM SHIELD INTERCEPT
                    </div>
                    <div className="bg-stone-900/90 p-2 rounded text-[11px] text-stone-300 font-mono border border-stone-800">
                      Forwarded SMS from +1 (800) 555-0199: <em>"URGENT: Social Security suspended. Wire $2,500 now or face immediate arrest."</em>
                    </div>
                    <p className="font-serif text-[12px] text-stone-200 leading-relaxed">
                      Sister Beatrice, please do not worry at all. This is a known robocall scam. <strong className="text-emerald-400">I have safely blocked and reported this number.</strong> Your phone will never ring from them again. You are completely safe.
                    </p>
                    <div className="text-[10px] text-stone-400 text-right">11:17 AM</div>
                  </div>
                </div>
              </div>

              {/* WhatsApp Quick Reply Suggestions */}
              <div className="bg-[#202c33] px-3 py-1.5 flex gap-1.5 overflow-x-auto border-t border-stone-800 text-[11px] font-serif shrink-0">
                <button
                  onClick={() => handleSendFamilyMessage("Did I take my afternoon vitamins?")}
                  className="px-2.5 py-1 rounded-full bg-stone-800 text-stone-300 whitespace-nowrap hover:bg-stone-700 transition-colors"
                >
                  "Did I take my afternoon vitamins?"
                </button>
                <button
                  onClick={() => handleSendFamilyMessage("Play afternoon garden chimes")}
                  className="px-2.5 py-1 rounded-full bg-stone-800 text-stone-300 whitespace-nowrap hover:bg-stone-700 transition-colors"
                >
                  "Play afternoon chimes"
                </button>
                <button
                  onClick={() => handleSendFamilyMessage("Call my nephew")}
                  className="px-2.5 py-1 rounded-full bg-stone-800 text-stone-300 whitespace-nowrap hover:bg-stone-700 transition-colors"
                >
                  "Call nephew"
                </button>
              </div>

              {/* WhatsApp Input Footer */}
              <div className="bg-[#202c33] px-3 py-2 flex items-center gap-2 shrink-0">
                <input
                  type="text"
                  value={customQuery}
                  onChange={e => setCustomQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSendFamilyMessage()}
                  placeholder="Type or tap mic to speak..."
                  className="flex-1 bg-[#2a3942] text-stone-100 text-xs font-serif rounded-full px-4 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <button
                  onClick={() => handleSendFamilyMessage()}
                  className="w-9 h-9 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shrink-0 shadow transition-all active:scale-95"
                  title="Send message or voice note"
                >
                  {customQuery.trim() ? <Send className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 1: PRAYER & HYMN SCHEDULE */}
      {activeTab === 'prayers' && (
        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-stone-800 pb-3">
            <div>
              <h3 className="font-serif font-bold text-lg text-stone-100">Liturgy of the Hours &amp; Rosary</h3>
              <p className="text-xs text-stone-400 font-serif">Daily prayer times synchronized with the Convent of St. Clare chapel bells.</p>
            </div>
            <span className="text-xs font-serif text-stone-400">Tap to play gentle audio chanting</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {profile.prayerSchedule?.map((prayer, i) => (
              <div
                key={i}
                className="p-4 rounded-xl bg-stone-900/60 border border-stone-800/80 flex items-center justify-between transition-all hover:border-stone-700"
              >
                <div className="space-y-1">
                  <div className="text-xs font-mono text-rose-300 font-bold flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{prayer.time}</span>
                  </div>
                  <div className="font-serif text-sm font-semibold text-stone-100">{prayer.name}</div>
                </div>

                <button
                  onClick={() => handlePlayPrayerAudio(prayer.name)}
                  className={`px-3 py-2 rounded-lg font-serif text-xs font-medium flex items-center gap-1.5 transition-all ${
                    isPlayingAudio === prayer.name
                      ? 'bg-rose-600 text-white animate-pulse'
                      : 'bg-stone-800 hover:bg-stone-700 text-stone-200'
                  }`}
                >
                  <Volume2 className="w-4 h-4" />
                  <span>{isPlayingAudio === prayer.name ? 'Chanting...' : 'Listen'}</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: MEDICATIONS & DAILY CARE */}
      {activeTab === 'health' && (
        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-stone-800 pb-3">
            <div>
              <h3 className="font-serif font-bold text-lg text-stone-100">Daily Health &amp; Medications</h3>
              <p className="text-xs text-stone-400 font-serif">Simple reminder cards. Tap the checkmark when you have taken yours.</p>
            </div>
            <span className="text-xs font-serif text-emerald-400">Carefully tracked for doctor visits</span>
          </div>

          <div className="space-y-3">
            {profile.medications?.map((med, i) => (
              <div
                key={i}
                onClick={() => toggleMedication(i)}
                className={`p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                  med.taken
                    ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-300'
                    : 'bg-stone-900/60 border-stone-800 text-stone-200 hover:border-stone-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
                    med.taken ? 'bg-emerald-500 text-stone-950' : 'border border-stone-600 text-transparent'
                  }`}>
                    <Check className="w-4 h-4 stroke-[3]" />
                  </div>
                  <div>
                    <div className="font-serif font-bold text-sm text-stone-100">{med.name}</div>
                    <div className="text-xs text-stone-400 font-serif">{med.dosage} · Scheduled for {med.time}</div>
                  </div>
                </div>

                <span className="text-xs font-serif font-medium px-3 py-1 rounded-full bg-stone-950 border border-stone-800">
                  {med.taken ? 'Completed Today ✓' : 'Tap to Mark Taken'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: FAMILY LETTERS */}
      {activeTab === 'letters' && (
        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-stone-800 pb-3">
            <div>
              <h3 className="font-serif font-bold text-lg text-stone-100">Letters from Family</h3>
              <p className="text-xs text-stone-400 font-serif">Read in large print or listen to Otto voice them aloud.</p>
            </div>
          </div>

          <div className="space-y-4">
            {FAMILY_LETTERS.map(letter => (
              <div key={letter.id} className="p-5 rounded-xl bg-stone-900/60 border border-stone-800 space-y-3">
                <div className="flex items-center justify-between text-xs font-serif text-stone-400">
                  <span className="font-bold text-stone-200 text-sm">{letter.from}</span>
                  <span>{letter.date}</span>
                </div>
                <div className="font-serif font-semibold text-stone-100 text-base">{letter.subject}</div>
                <p className="font-serif text-sm text-stone-300 leading-relaxed bg-stone-950/60 p-4 rounded-xl border border-stone-800/60">
                  {letter.body}
                </p>
                <button
                  onClick={() => {
                    if (typeof window !== 'undefined' && window.speechSynthesis) {
                      window.speechSynthesis.cancel();
                      const u = new SpeechSynthesisUtterance(letter.body);
                      u.rate = 0.9;
                      window.speechSynthesis.speak(u);
                    }
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-stone-800 hover:bg-stone-700 text-stone-200 text-xs font-serif flex items-center gap-1.5 transition-colors"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  <span>Read Aloud</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: SCAM & ROBOCALL SHIELD */}
      {activeTab === 'scam-shield' && (
        <div className="rounded-2xl border border-stone-800 bg-stone-950 p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-stone-800 pb-3">
            <div>
              <h3 className="font-serif font-bold text-lg text-stone-100">Automated Scam &amp; Robocall Shield</h3>
              <p className="text-xs text-stone-400 font-serif">
                Otto filters all incoming calls and text messages before they can ring or bother Sister Beatrice.
              </p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800 flex items-center gap-1 font-bold">
              <ShieldCheck className="w-3.5 h-3.5" />
              SHIELD 100% ACTIVE
            </span>
          </div>

          <div className="space-y-3">
            {SCAM_SHIELD_INCIDENTS.map(scam => (
              <div key={scam.id} className="p-4 rounded-xl bg-stone-900/60 border border-stone-800 space-y-2 text-xs font-serif">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-300 text-sm">{scam.threatType}</span>
                  <span className="text-stone-400 font-mono text-[10px]">{scam.timestamp}</span>
                </div>
                <div className="text-stone-300 leading-relaxed">{scam.actionTaken}</div>
                <div className="flex items-center justify-between pt-1 border-t border-stone-800/60 text-[11px] text-stone-500 font-mono">
                  <span>Channel: {scam.channel}</span>
                  <span className="text-emerald-400 font-bold">{scam.safetyStatus}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Simple Kin Voice/Input Box */}
      <div className="p-4 rounded-2xl bg-stone-900/90 border border-stone-800 flex items-center gap-3">
        <input
          type="text"
          value={customQuery}
          onChange={e => setCustomQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSendFamilyMessage()}
          placeholder="Speak or type a gentle message to Otto (e.g. 'Play midday chime', 'Call my nephew')..."
          className="flex-1 bg-stone-950 text-stone-100 text-sm font-serif rounded-xl px-4 py-3 border border-stone-800 focus:outline-none focus:border-rose-400"
        />

        <button
          onClick={() => handleSendFamilyMessage()}
          className="p-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-serif font-semibold text-xs shadow-md transition-all flex items-center gap-1.5"
        >
          <Send className="w-4 h-4" />
          <span>Ask Otto</span>
        </button>
      </div>
    </div>
  );
};
