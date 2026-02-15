#!/bin/bash
# PreToolUse hook: Guard HPC resource usage
# Reads .claude/hpc.yaml and enforces resource limits on SLURM commands.
# Blocks commands that exceed configured limits or match deny patterns.

set -euo pipefail

# Read JSON input from stdin
input=$(cat)

# Only run for Bash tool calls
tool_name=$(echo "$input" | jq -r '.tool_name // empty')
if [ "$tool_name" != "Bash" ]; then
    exit 0
fi

# Get the command being run
command=$(echo "$input" | jq -r '.tool_input.command // empty')
if [ -z "$command" ]; then
    exit 0
fi

# Get working directory
cwd=$(echo "$input" | jq -r '.cwd // empty')
if [ -z "$cwd" ]; then
    exit 0
fi

# Check for HPC config
hpc_config="$cwd/.claude/hpc.yaml"
if [ ! -f "$hpc_config" ]; then
    exit 0
fi

# --- Helper: read YAML values (simple grep-based, no Python dependency) ---
yaml_value() {
    local key="$1"
    grep -E "^\s*${key}:" "$hpc_config" 2>/dev/null | head -1 | sed 's/.*: *//' | tr -d '"' | tr -d "'"
}

# --- Check deny list ---
# Read deny patterns from permissions section
deny_patterns=$(awk '
    /^permissions:/{in_perms=1; next}
    in_perms && /^  deny:/{in_deny=1; next}
    in_deny && /^  [a-z]/{exit}
    in_deny && /^[a-z]/{exit}
    in_deny && /- /{
        sub(/^[ ]*- ["'\''"]?/, "")
        sub(/["'\''"]?$/, "")
        print
    }
' "$hpc_config" 2>/dev/null)

while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    if echo "$command" | grep -qF "$pattern"; then
        echo '{"decision": "block", "reason": "HPC guard: command matches deny pattern: '"$pattern"'"}'
        exit 0
    fi
done <<< "$deny_patterns"

# --- Only check SLURM commands beyond this point ---
# Extract the base command (first word)
base_cmd=$(echo "$command" | awk '{print $1}')

case "$base_cmd" in
    sbatch|srun|salloc) ;;
    *) exit 0 ;;  # Not a SLURM submission command, allow
esac

# --- Parse resource limits from config ---
max_nodes=$(yaml_value "max_nodes")
max_walltime=$(yaml_value "max_walltime_minutes")
max_node_hours=$(yaml_value "max_node_hours_per_session")

max_nodes=${max_nodes:-4}
max_walltime=${max_walltime:-120}
max_node_hours=${max_node_hours:-16}

# --- Parse nodes from command ---
requested_nodes=""
# Match --nodes=N or -N N
if echo "$command" | grep -qoE '\-\-nodes[= ]+[0-9]+'; then
    requested_nodes=$(echo "$command" | grep -oE '\-\-nodes[= ]+[0-9]+' | grep -oE '[0-9]+')
elif echo "$command" | grep -qoE '\-N[ ]+[0-9]+'; then
    requested_nodes=$(echo "$command" | grep -oE '\-N[ ]+[0-9]+' | grep -oE '[0-9]+')
fi

if [ -n "$requested_nodes" ] && [ "$requested_nodes" -gt "$max_nodes" ]; then
    echo '{"decision": "block", "reason": "HPC guard: requested '"$requested_nodes"' nodes exceeds limit of '"$max_nodes"'. Reduce --nodes or update .claude/hpc.yaml"}'
    exit 0
fi

# --- Parse walltime from command ---
requested_time=""
# Match --time=HH:MM:SS or --time=MM or -t HH:MM:SS or -t MM
if echo "$command" | grep -qoE '\-\-time[= ]+[0-9:]+'; then
    requested_time=$(echo "$command" | grep -oE '\-\-time[= ]+[0-9:]+' | sed 's/--time[= ]*//')
elif echo "$command" | grep -qoE '\-t[ ]+[0-9:]+'; then
    requested_time=$(echo "$command" | grep -oE '\-t[ ]+[0-9:]+' | sed 's/-t *//')
fi

if [ -n "$requested_time" ]; then
    # Convert time to minutes
    time_minutes=0
    if echo "$requested_time" | grep -qE '^[0-9]+:[0-9]+:[0-9]+$'; then
        # HH:MM:SS
        hours=$(echo "$requested_time" | cut -d: -f1)
        mins=$(echo "$requested_time" | cut -d: -f2)
        time_minutes=$(( hours * 60 + mins ))
    elif echo "$requested_time" | grep -qE '^[0-9]+:[0-9]+$'; then
        # MM:SS or HH:MM (SLURM treats as minutes:seconds if < 60, hours:minutes otherwise)
        first=$(echo "$requested_time" | cut -d: -f1)
        second=$(echo "$requested_time" | cut -d: -f2)
        # Treat as minutes:seconds for safety (SLURM default)
        time_minutes=$first
    elif echo "$requested_time" | grep -qE '^[0-9]+$'; then
        # Just minutes
        time_minutes=$requested_time
    fi

    if [ "$time_minutes" -gt "$max_walltime" ]; then
        echo '{"decision": "block", "reason": "HPC guard: requested walltime '"$requested_time"' ('"$time_minutes"' min) exceeds limit of '"$max_walltime"' minutes. Reduce --time or update .claude/hpc.yaml"}'
        exit 0
    fi
fi

# --- Track cumulative node-hours ---
session_file="$cwd/.claude/.hpc-session-usage"

# Calculate node-hours for this job
nodes=${requested_nodes:-1}
minutes=${time_minutes:-0}
if [ "$minutes" -gt 0 ]; then
    # node_hours = nodes * minutes / 60 (integer arithmetic, round up)
    job_node_hours=$(( (nodes * minutes + 59) / 60 ))

    # Read current usage
    current_usage=0
    if [ -f "$session_file" ]; then
        current_usage=$(cat "$session_file" 2>/dev/null || echo 0)
    fi

    new_total=$(( current_usage + job_node_hours ))

    if [ "$new_total" -gt "$max_node_hours" ]; then
        echo '{"decision": "block", "reason": "HPC guard: this job would use '"$job_node_hours"' node-hours, bringing session total to '"$new_total"' (limit: '"$max_node_hours"'). Reset .claude/.hpc-session-usage or update limits in .claude/hpc.yaml"}'
        exit 0
    fi

    # Update usage tracker
    mkdir -p "$(dirname "$session_file")"
    echo "$new_total" > "$session_file"
fi

# All checks passed
exit 0
