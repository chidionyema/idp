# Where a scheduled job is allowed to live.
#
# The estate keeps reporting missed schedules and keeps repairing the individual
# job, which is the wrong repair, because the job is fine. A MacBook sleeps. A
# job scheduled for 03:30 on a machine whose lid is shut at 03:30 does not run,
# and no amount of fixing the script changes that.
#
# Measured 2026-08-24 against the live Healthchecks instance, 35 checks:
#
#   daily jobs (period >= 12h):     10 total,  7 had NEVER pinged   (70% dead)
#   sub-daily jobs (period < 12h):  25 total,  4 had NEVER pinged   (16% dead)
#
# Same wrapper, same machine, same scripts. The only variable is whether the
# schedule falls inside the hours a person has the laptop open. That is a
# placement defect, not 7 separate bugs.
#
# Input is reports/placement.json from bin/placement-audit:
#
#   {"jobs": [{"label": "...", "slug": "...", "schedule": "calendar|interval|keepalive",
#              "period_seconds": 86400, "hours": [3], "asleep_hours": [3],
#              "check": {"status": "...", "last_ping": null}}]}
#
# DENY vs WARN, as in licences.rego. A guard that refuses correct work is an
# outage (LAW 38), so deny is reserved for placements that provably cannot work
# on this hardware. Everything that is merely suspicious is a warn.

package main

import rego.v1

# --- hard failures ------------------------------------------------------------

# A schedule inside the hours the machine is asleep. Not a heuristic: pmset's
# own log shows this Mac entering Maintenance Sleep repeatedly through the night
# and staying there, and every job below has a check that has never pinged.
deny contains msg if {
	some job in input.jobs
	job.schedule == "calendar"
	count(job.asleep_hours) > 0
	msg := sprintf(
		"%v is scheduled in the %v o'clock hour and this machine is asleep then. It belongs on a host that stays awake.",
		[job.label, job.asleep_hours[0]],
	)
}

# A monitored job that has never once pinged is not late, it is not running.
# This is the strongest evidence there is and it needs no interpretation.
deny contains msg if {
	some job in input.jobs
	job.slug != null
	job.check != null
	job.check.last_ping == null
	msg := sprintf(
		"%v (check '%v') has never pinged. It is not late -- it has never run.",
		[job.label, job.slug],
	)
}

# The blinded case, and it is a hard failure on purpose.
#
# Measured 2026-08-24 03:30, on this policy's own second run: the Healthchecks
# container went unhealthy, bin/placement-audit degraded every job to
# "check": null, and the rule above stopped matching -- because in rego
# null.last_ping is undefined, not null, so the rule body simply fails. Eleven
# real failures vanished and the audit reported 11 instead of 22. A guard that
# gets QUIETER when its data source dies is worse than no guard: it reads as
# improvement.
#
# So a monitored job whose check could not be read is refused, not skipped. The
# honest state is "unknown", and unknown is not pass.
deny contains msg if {
	some job in input.jobs
	job.slug != null
	job.check == null
	msg := sprintf(
		"%v (check '%v') has no readable check record. Healthchecks was unreachable, so this job's state is UNKNOWN -- which is not the same as fine.",
		[job.label, job.slug],
	)
}

# The class that must survive losing the laptop, running only on the laptop.
# A backup whose only schedule is on the machine it is backing up protects
# nothing the moment that machine is the thing that failed.
deny contains msg if {
	some job in input.jobs
	survival_job(job.label)
	msg := sprintf(
		"%v is survival work (backup, restore drill or key escrow) and it runs only here. If this laptop is what fails, it was never running.",
		[job.label],
	)
}

# --- reported, not fatal ------------------------------------------------------

# Daily work on a machine that is not on for most of the day. It can work -- two
# of ten currently do -- but it is a coin toss, and it should be an explicit
# decision rather than an accident.
warn contains msg if {
	some job in input.jobs
	job.period_seconds != null
	job.period_seconds >= 43200
	count(job.asleep_hours) == 0
	msg := sprintf(
		"%v runs every %vh on a laptop. Measured 2026-08-24: 7 of 10 daily jobs here had never run. Confirm this one is meant to be a desk job.",
		[job.label, job.period_seconds / 3600],
	)
}

# A long-running process serving something another session or the founder reads.
# It works while the laptop is open and disappears when it is not, which is
# fine for a dev tool and wrong for anything anyone depends on.
warn contains msg if {
	some job in input.jobs
	job.schedule == "keepalive"
	msg := sprintf(
		"%v is a long-running service on a laptop. Anything depending on it is depending on the lid being open.",
		[job.label],
	)
}

# A scheduled job nobody is monitoring. It cannot report a missed schedule
# because nothing is watching for one, which is worse than a red check.
warn contains msg if {
	some job in input.jobs
	job.slug == null
	job.schedule != "keepalive"
	job.schedule != "manual"
	msg := sprintf(
		"%v is scheduled but not wrapped in hc-wrap.sh, so nothing notices when it stops. An instrument nobody reads is not an instrument.",
		[job.label],
	)
}

survival_job(label) if contains(label, "backup")

survival_job(label) if contains(label, "restic")

survival_job(label) if contains(label, "escrow")

survival_job(label) if contains(label, "restore-drill")

survival_job(label) if contains(label, "offsite")
