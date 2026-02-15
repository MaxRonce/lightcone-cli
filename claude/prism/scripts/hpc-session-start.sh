#!/bin/bash
# SessionStart hook: Show HPC target context at session start
# Only activates if .claude/hpc.yaml exists in the project

# Read JSON input from stdin
input=$(cat)

# Get the current working directory
cwd=$(echo "$input" | jq -r '.cwd // empty')

if [ -z "$cwd" ]; then
    exit 0
fi

cd "$cwd" 2>/dev/null || exit 0

# Check for HPC config
hpc_config=".claude/hpc.yaml"
if [ ! -f "$hpc_config" ]; then
    exit 0
fi

# --- Read config values ---
yaml_value() {
    local key="$1"
    grep -E "^\s*${key}:" "$hpc_config" 2>/dev/null | head -1 | sed 's/.*: *//' | tr -d '"' | tr -d "'"
}

target_name=$(yaml_value "display_name")
target_name=${target_name:-$(yaml_value "name")}
account=$(yaml_value "account")
username=$(yaml_value "username")
max_nodes=$(yaml_value "max_nodes")
max_walltime=$(yaml_value "max_walltime_minutes")
max_concurrent=$(yaml_value "max_concurrent_jobs")
max_node_hours=$(yaml_value "max_node_hours_per_session")
default_qos=$(yaml_value "default_qos")
default_constraint=$(yaml_value "default_constraint")

# Check current session usage
session_usage=0
session_file=".claude/.hpc-session-usage"
if [ -f "$session_file" ]; then
    session_usage=$(cat "$session_file" 2>/dev/null || echo 0)
fi

# Build summary
summary="HPC Target: ${target_name}
- Account: ${account:-not set}
- Username: ${username:-not set}
- Default QOS: ${default_qos:-regular}
- Default constraint: ${default_constraint:-cpu}

Resource limits (enforced by guard hook):
- Max nodes/job: ${max_nodes:-4}
- Max walltime: ${max_walltime:-120} min
- Max concurrent jobs: ${max_concurrent:-3}
- Session node-hours: ${session_usage}/${max_node_hours:-16} used

SLURM commands (sbatch, srun, salloc, scancel) require approval.
The guard hook enforces resource limits on every job submission."

# Output as JSON
escaped_summary=$(echo "$summary" | jq -Rs .)
echo "{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": $escaped_summary}}"

exit 0
