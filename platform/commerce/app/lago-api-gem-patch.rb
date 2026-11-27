# Moves gems in a vendor image's Gemfile.lock to patched versions, and refuses unless the result
# is a consistent lock (lago-api.Dockerfile, idp#8658).
#
#   ruby lago-api-gem-patch.rb LOCKFILE SPECDIR
#
# SPECDIR holds the target gems: fetched .gem files in the image build, .gemspec files in the
# tests. Every gem found there moves to that version in LOCKFILE, on every platform the lock
# records, and its dependency lines are rewritten from the gem's own spec, never typed by hand.
# Then every dependency line in the lock must be met by a locked version of the gem it names;
# one that is not is printed and the script exits 1 without writing. Unknown = refuse: a target
# the lock does not hold, or one older than the locked version, is refused too.
# On success the lock is rewritten in place and "name version" of each replaced version is
# printed, one per line, for the caller to uninstall.
require "rubygems"
require "rubygems/package"

SPEC_LINE = /\A {4}(\S+) \(([^)]+)\)\n?\z/.freeze
DEP_LINE = /\A {6}(\S+)(?: \(([^)]+)\))?\n?\z/.freeze

def load_targets(dir)
  specs = Dir[File.join(dir, "*.gem")].map { |p| Gem::Package.new(p).spec }
  specs += Dir[File.join(dir, "*.gemspec")].map { |p| Gem::Specification.load(p) }
  abort "gem-patch: no .gem or .gemspec in #{dir}" if specs.empty?
  specs.each_with_object({}) { |s, h| h[s.name] = s }
end

# "1.19.4-x86_64-linux-gnu" -> ["1.19.4", "-x86_64-linux-gnu"]
def split_version(text)
  m = text.match(/\A(\d[0-9A-Za-z.]*)(-.+)?\z/) or abort "gem-patch: unreadable version #{text}"
  [m[1], m[2].to_s]
end

def lock_requirement(dep)
  # Bundler writes requirements sorted descending: "~> 1.6, >= 1.7.2".
  dep.requirement.requirements.map { |op, v| "#{op} #{v}" }.sort.reverse.join(", ")
end

def rewrite(lines, targets)
  out = []
  replaced = []
  seen = {}
  skipping = false
  lines.each do |line|
    if (m = line.match(SPEC_LINE))
      skipping = false
      name = m[1]
      spec = targets[name]
      if spec
        old, platform = split_version(m[2])
        new = spec.version.to_s
        if Gem::Version.new(old) > spec.version
          abort "gem-patch: #{name} is locked at #{old}, newer than the target #{new}; refusing to downgrade"
        end
        seen[name] = true
        entry = "#{name} #{old}"
        replaced << entry unless old == new || replaced.include?(entry)
        out << "    #{name} (#{new}#{platform})\n"
        spec.runtime_dependencies.sort_by(&:name).each do |dep|
          req = lock_requirement(dep)
          out << (req == ">= 0" ? "      #{dep.name}\n" : "      #{dep.name} (#{req})\n")
        end
        skipping = true
        next
      end
    elsif skipping && line.match(DEP_LINE)
      next
    else
      skipping = false
    end
    out << line
  end
  missing = targets.keys - seen.keys
  abort "gem-patch: the lock holds no #{missing.sort.join(', ')}" unless missing.empty?
  [out, replaced]
end

# Every dependency line under a spec must be met by a version the lock holds for that gem.
def violations(lines)
  locked = Hash.new { |h, k| h[k] = [] }
  deps = []
  current = nil
  lines.each do |line|
    if (m = line.match(SPEC_LINE))
      current = "#{m[1]} (#{m[2]})"
      locked[m[1]] << Gem::Version.new(split_version(m[2])[0])
    elsif current && (m = line.match(DEP_LINE))
      deps << [current, m[1], m[2]]
    else
      current = nil
    end
  end
  deps.each_with_object([]) do |(owner, name, req), bad|
    next if req.nil?
    next unless locked.key?(name) # bundler itself and default gems are not locked as specs
    requirement = Gem::Requirement.new(*req.split(", "))
    next if locked[name].any? { |v| requirement.satisfied_by?(v) }
    bad << "#{owner} needs #{name} (#{req}); the lock holds #{locked[name].map(&:to_s).uniq.join(', ')}"
  end
end

lockfile, specdir = ARGV
abort "usage: ruby lago-api-gem-patch.rb LOCKFILE SPECDIR" unless lockfile && specdir
out, replaced = rewrite(File.readlines(lockfile), load_targets(specdir))
bad = violations(out)
unless bad.empty?
  warn "gem-patch: refused, the patched lock would be inconsistent:"
  bad.each { |b| warn "  #{b}" }
  exit 1
end
File.write(lockfile, out.join)
puts replaced
