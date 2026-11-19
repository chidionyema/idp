import { FamilyKinProfile } from '../types/otto';

export const DEFAULT_FAMILY_PROFILES: FamilyKinProfile[] = [
  {
    id: 'kin-parent-01',
    name: 'Mom (Elder Parent)',
    relationship: 'Mother',
    preferredTone: 'warm-gentle',
    fontSize: 'large',
    prayerSchedule: [
      { time: '07:30 AM', name: 'Morning Walk & Serene Chimes', audioAvailable: true },
      { time: '12:30 PM', name: 'Midday Quiet Reading', audioAvailable: true },
      { time: '05:30 PM', name: 'Evening Garden Reminder', audioAvailable: true },
      { time: '08:30 PM', name: 'Night Wind-down Audio', audioAvailable: true }
    ],
    medications: [
      { time: '08:00 AM', name: 'Morning Blood Pressure Care', dosage: '1 tablet with breakfast', taken: true },
      { time: '01:00 PM', name: 'Hydrating Eye Drops', dosage: '1 drop per eye', taken: true },
      { time: '08:00 PM', name: 'Evening Joint & Vitamin Wellness', dosage: '1 capsule with warm tea', taken: false }
    ],
    scamShieldStatus: {
      active: true,
      blockedAttempts: 4,
      lastChecked: '2 mins ago'
    },
    emergencyContact: 'Founder Direct Private Line (+1 650-***-0199)'
  },
  {
    id: 'kin-partner-02',
    name: 'Spouse / Partner',
    relationship: 'Spouse',
    preferredTone: 'warm-gentle',
    fontSize: 'standard',
    prayerSchedule: [
      { time: '08:00 AM', name: 'Daily Calendar Sync', audioAvailable: false },
      { time: '06:00 PM', name: 'Dinner & Estate Logistics', audioAvailable: false }
    ],
    medications: [],
    scamShieldStatus: {
      active: true,
      blockedAttempts: 1,
      lastChecked: '10 mins ago'
    },
    emergencyContact: 'Founder Direct Private Line (+1 650-***-0199)'
  },
  {
    id: 'kin-custom-03',
    name: 'Custom Family Member',
    relationship: 'Family Kin',
    preferredTone: 'warm-gentle',
    fontSize: 'standard',
    prayerSchedule: [
      { time: '09:00 AM', name: 'Morning Check-In', audioAvailable: false },
      { time: '06:00 PM', name: 'Evening Update', audioAvailable: false }
    ],
    medications: [
      { time: '09:00 AM', name: 'Daily Vitamins', dosage: '1 tablet', taken: false }
    ],
    scamShieldStatus: {
      active: true,
      blockedAttempts: 0,
      lastChecked: 'Just now'
    },
    emergencyContact: 'Founder Mobile'
  }
];

export const INITIAL_KIN_PROFILE: FamilyKinProfile = DEFAULT_FAMILY_PROFILES[0];
export const ELDER_NUN_PROFILE: FamilyKinProfile = {
  id: 'kin-sister-beatrice',
  name: 'Sister Beatrice (Elder Nun)',
  relationship: 'Aunt / Elder Nun',
  preferredTone: 'warm-gentle',
  fontSize: 'extra-large',
  prayerSchedule: [
    { time: '06:00 AM', name: 'Matins & Lauds (Dawn Chants)', audioAvailable: true },
    { time: '12:00 PM', name: 'Angelus & Sext (Midday Psalm)', audioAvailable: true },
    { time: '03:00 PM', name: 'None & Divine Mercy (Garden Chimes)', audioAvailable: true },
    { time: '06:00 PM', name: 'Vespers (Evening Gregorian Choir)', audioAvailable: true },
    { time: '08:30 PM', name: 'Compline (Night Blessing)', audioAvailable: true }
  ],
  medications: [
    { time: '08:00 AM', name: 'Timolol Eye Drops (Glaucoma)', dosage: '1 drop per eye', taken: true },
    { time: '08:30 AM', name: 'Blood Pressure Tablet', dosage: '1 tablet with warm tea', taken: true },
    { time: '01:00 PM', name: 'Joint Mobility & Calcium', dosage: '1 capsule with lunch', taken: false },
    { time: '07:30 PM', name: 'Evening Heart Support Care', dosage: '1 tablet after Vespers', taken: false }
  ],
  scamShieldStatus: {
    active: true,
    blockedAttempts: 7,
    lastChecked: 'Just now'
  },
  emergencyContact: 'Founder Direct Private Line (+1 650-***-0199)'
};

export const FAMILY_LETTERS = [
  {
    id: 'letter-01',
    from: 'Founder',
    date: 'Yesterday at 5:15 PM',
    subject: 'Thinking of you · Evening update',
    body: 'Hope you had a wonderful afternoon. I had Otto set up the gentle chime alerts on your phone so you never have to worry about missing anything. Otto is handling all the spam calls and tech chores quietly. Sending lots of love.',
    audioVoiced: true
  },
  {
    id: 'letter-02',
    from: 'Family Circle',
    date: 'Wednesday at 10:00 AM',
    subject: 'Weekend Gathering Plans',
    body: 'Looking forward to our family lunch this Sunday. Otto confirmed the table reservation and sent the directions.',
    audioVoiced: true
  }
];

export const SCAM_SHIELD_INCIDENTS = [
  {
    id: 'scam-01',
    timestamp: 'Today 11:24 AM',
    threatType: 'Impersonation Robocall ("IRS Urgent Notice")',
    channel: 'Landline VoIP Gateway',
    actionTaken: 'Silently intercepted and blocked. No ring or stress to family member. Logged to Founder Outbox.',
    safetyStatus: '100% PROTECTED'
  },
  {
    id: 'scam-02',
    timestamp: 'Yesterday 3:42 PM',
    threatType: 'Phishing SMS ("Unclaimed Package Click Here")',
    channel: 'Family WhatsApp / SMS',
    actionTaken: 'Screened before display. Sender quarantined. 0 taps required by family member.',
    safetyStatus: '100% PROTECTED'
  }
];
