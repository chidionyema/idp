#!/bin/bash
# Disk Sentinel / Elephant Finder v3: one-pass APFS Data-volume attribution.
# Read-only: no sudo, cache deletion, process killing, service edits, network or installs.
# Uses Apple-shipped Perl File::Find (macOS Ventura includes Perl 5.30).
set -u
export LC_ALL=C
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

case "${1:---deep}" in
  --deep) LIMIT=1200 ;;
  --quick) LIMIT=300 ;;
  -h|--help) echo 'Usage: /bin/bash disk_elephant_once_macos.sh [--deep|--quick]'; exit 0 ;;
  *) echo 'ERROR: choose --deep or --quick' >&2; exit 2 ;;
esac
if [ "$(uname -s)" != Darwin ]; then
  echo 'BLOCKED: macOS required; no changes made.' >&2
  exit 2
fi
ROOT=/System/Volumes/Data
[ -d "$ROOT" ] || { echo 'BLOCKED: APFS Data mount not found.' >&2; exit 2; }
[ -x /usr/bin/perl ] || { echo 'BLOCKED: Apple Perl runtime missing.' >&2; exit 2; }

printf 'DISK SENTINEL / ELEPHANT FINDER v3: SINGLE-PASS READ-ONLY AUDIT\n'
printf 'Captured: %s | Mode: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "${1:---deep}"
echo 'Writes NOTHING to the Data volume unless you redirect output to a report.'
echo 'Does not remove files, stop agents, alter swap or require sudo.'
echo 'Privacy: output includes filenames, paths and process names; redact before sharing.'
echo

echo '=== APFS CAPACITY (do not sum APFS volume sizes) ==='
df -h "$ROOT" || true
/usr/sbin/diskutil apfs list 2>/dev/null | /usr/bin/grep -E 'Capacity Ceiling|In Use By Volumes|Not Allocated|Volume Disk \(Role\)|Capacity Consumed:' || true
printf '\n=== ACTIVE MEMORY PRESSURE (5.9 GB VM volume should not be manually cleared) ===\n'
/usr/sbin/sysctl vm.swapusage 2>/dev/null || true
/bin/ls -lsh /System/Volumes/VM/swapfile* 2>/dev/null || true
printf '\n=== ACTIVE PROCESSES (read-only) ===\n'
/bin/ps -axo pid,ppid,%cpu,%mem,etime,comm 2>/dev/null | /usr/bin/sort -k3,3nr | /usr/bin/head -n 25 || true
printf '\n=== SINGLE-PASS APFS DATA FILE ATTRIBUTE WALK ===\n'
echo 'Each visited filesystem entry is inspected once; measurements update progressively.'
echo 'Paths missing due to macOS privacy restrictions remain unaccounted for.'
echo 'Per-file block totals can overstate UNIQUE APFS storage when clones share extents.'
echo 'To allow complete file traversal: System Settings > Privacy & Security > Full Disk Access > Terminal.'

# Lower CPU / I/O priority. No aggressive recursive du calls or multiple overlapping scans.
/usr/bin/nice -n 15 /usr/bin/perl - "$ROOT" "$HOME" "$LIMIT" <<'PERL'
use strict;
use warnings;
use File::Find ();
use Time::HiRes qw(time);

$|=1;
my ($root, $home, $budget) = @ARGV;
my @rst = stat($root);
die "Cannot stat Data volume root\n" unless @rst;
my $dev = $rst[0];
my $begin = time();
my $next_report = $begin + 20;
my (%bucket, %seen_hardlink, @large);
my ($visits, $files, $dirs, $unstat, $other_mounts, $hardlinks, $warnings) = (0,0,0,0,0,0,0);
my $timed_out = 0;
my $all_alloc = 0;
my $logical_total = 0;
my $size_floor = 512*1024*1024; # record large files at least 512 MiB physically allocated

local $SIG{ALRM} = sub { die '__ELEPHANT_TIME_BUDGET__\n'; };
local $SIG{__WARN__} = sub {
  $warnings++;
  print STDERR "ACCESS/SCAN NOTICE: $_[0]" if $warnings <= 12;
};

my $abort = '__ELEPHANT_TIME_BUDGET__';
my $callback = sub {
  my $path = $File::Find::name;
  my @st = lstat($path);
  unless (@st) { $unstat++; return; }
  $visits++;
  # Stay on the Data volume. Do not traverse mounted network volumes or other APFS volumes.
  if ($st[0] != $dev) {
    $other_mounts++;
    $File::Find::prune = 1 if -d _;
    return;
  }
  my $is_dir = -d _;
  $is_dir ? $dirs++ : $files++;
  if (!$is_dir && $st[3] > 1) {
    my $ident = "$st[0]:$st[1]";
    if ($seen_hardlink{$ident}++) { $hardlinks++; return; }
  }
  # st_blocks is number of allocated 512-byte blocks on Unix/macOS.
  my $bytes = ($st[12] || 0) * 512;
  $all_alloc += $bytes;
  $logical_total += ($st[7] || 0) if !$is_dir;
  my $relative = substr($path, length($root));
  $relative =~ s{^/}{};
  my @parts = split m{/+}, $relative;
  # Depth 1..5 attributes top-level users, developer folders, and application owners.
  # A file itself can also form a bucket; it is therefore NOT safe to add bucket rows.
  my $cap = @parts < 5 ? scalar(@parts) : 5;
  my $key = '';
  for my $i (0 .. $cap-1) {
    $key .= '/' if $i;
    $key .= $parts[$i];
    $bucket{$key} += $bytes;
  }
  if (!$is_dir && $bytes >= $size_floor) {
    push @large, [$bytes, ($st[7] || 0), $path];
    if (@large > 90) {
      @large = sort { $b->[0] <=> $a->[0] } @large;
      $#large = 50;
    }
  }
  if (($visits % 4096) == 0) {
    my $now = time();
    if ($now >= $next_report) {
      printf STDERR "PROGRESS: %d entries, %.2f GiB per-file block sum, %.0fs elapsed\n",
        $visits, $all_alloc/1073741824, $now-$begin;
      $next_report = $now + 20;
    }
    die "$abort\n" if $now-$begin >= $budget;
  }
};

my $err='';
alarm($budget);
my $ok = eval { File::Find::find({ wanted => $callback, no_chdir => 1, follow => 0 }, $root); 1; };
alarm(0);
$err = $@ || 'unknown traversal error' unless $ok;
$timed_out = 1 if index($err, $abort) >= 0;
my $complete = $err eq '';
my $elapsed = time() - $begin;

printf "\nSCAN_STATE: %s\n", ($complete && !$warnings && !$unstat) ? 'COMPLETE' :
  ($timed_out ? 'TIME_BOUNDED_PARTIAL' : 'PARTIAL_OR_RESTRICTED');
printf "Entries visited: %d | regular/other files: %d | directories: %d | skipped mounts: %d | stat failures: %d | access notices: %d | hardlink duplicates avoided: %d\n",
  $visits,$files,$dirs,$other_mounts,$unstat,$warnings,$hardlinks;
printf "Elapsed: %.0f sec. Sum of file-level allocated blocks visited: %.2f GiB (NOT guaranteed unique APFS usage).\n",
  $elapsed, $all_alloc/1073741824;
if ($err && !$timed_out) { print "SCAN_ERROR: $err\n"; }
if (!$complete || $warnings || $unstat) {
  print "COVERAGE WARNING: counts below describe only visited accessible entries. Unknown areas may be larger.\n";
}

my @all = sort { $bucket{$b} <=> $bucket{$a} } keys %bucket;
print "\n=== TOP ATTRIBUTED PATHS (NESTED: DO NOT SUM) ===\n";
my $shown = 0;
for my $p (@all) {
  next if $p !~ m{/}; # do not waste space on 'Users' alone
  next if $bucket{$p} < 64*1024*1024;
  my $clean = $p;
  $clean =~ s/[\n\r\t]/_/g;
  printf "%8.2f GiB  %s/%s\n", $bucket{$p}/1073741824, $root, $clean;
  last if ++$shown >= 60;
}

print "\n=== TOP-LEVEL DATA VOLUME OWNERS ===\n";
for my $p (sort { $bucket{$b} <=> $bucket{$a} } grep { index($_,'/') == -1 } keys %bucket) {
  printf "%8.2f GiB  %s/%s\n", $bucket{$p}/1073741824, $root, $p;
}

print "\n=== TOP LARGE FILES (ALLOCATED BLOCKS, NOT NOMINAL SIZE) ===\n";
my @sorted = sort { $b->[0] <=> $a->[0] } @large;
my $n=0;
for my $r (@sorted) {
  my $clean = $r->[2]; $clean =~ s/[\n\r\t]/_/g;
  printf "allocated %6.2f GiB / logical %6.2f GiB  %s\n", $r->[0]/1073741824, $r->[1]/1073741824, $clean;
  last if ++$n >= 30;
}
print "\nROOT_CAUSE_STATUS: ", ($complete && !$warnings && !$unstat ? 'FULL_TREE_INSPECTED' : 'SOME_TREE_UNINSPECTED'), "\n";
print "No data deleted. Targeted cleanup requires workload ownership + quiescence + before/after free-space verification.\n";
PERL
STATUS=$?
printf '\n=== POST-AUDIT FREE SPACE ===\n'
df -h "$ROOT"
if [ "$STATUS" -ne 0 ]; then
  echo "SCAN_PROCESS_EXIT=$STATUS: results may be incomplete or blocked."
  exit "$STATUS"
fi
echo 'AUDIT EXITED: see SCAN_STATE and COVERAGE WARNING before interpreting results.'
