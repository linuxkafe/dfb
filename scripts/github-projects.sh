#!/bin/bash
# GitHub Projects automation for AES + local kanban sync
# This script connects GitHub Projects (issues, labels, board) to the local
# aes/kanban.md and aes/tickets/ files.

set -euo pipefail

# Configuration
PROJECT_NAME="${AES_GITHUB_PROJECT_NAME:-AES Project}"
# shellcheck disable=SC2034 # used in create_project
PROJECT_TEMPLATE="${AES_GITHUB_PROJECT_TEMPLATE:-kanban}"
AES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KANBAN_FILE="$AES_ROOT/aes/kanban.md"
TICKET_MAP="$AES_ROOT/aes/ticket-map.json"
TICKETS_DIR="$AES_ROOT/aes/tickets"

GH_AVAILABLE=false
if command -v gh &> /dev/null && gh auth status 2>&1 | grep -q 'Logged in'; then
    GH_AVAILABLE=true
fi

# ── Helper: check gh project scope ──────────────────────────────────────────────

check_gh_project_scope() {
    if ! $GH_AVAILABLE; then
        return 0  # Already checked upstream
    fi
    local auth_status
    auth_status=$(gh auth status 2>&1 || true)
    if ! echo "$auth_status" | grep -q "project"; then
        echo "❌ GitHub token missing 'project' scope — required for GitHub Projects v2 API" >&2
        echo "   Run: gh auth refresh -s project" >&2
        return 1
    fi
    return 0
}

# ── Helper: gh command wrapper with error handling ───────────────────────────────

gh_cmd() {
    local out
    out=$(gh "$@" 2>&1) || {
        echo "❌ gh $* failed:" >&2
        echo "$out" >&2
        return 1
    }
    echo "$out"
}

# Get repository information if GitHub is available
REMOTE_URL=""
REPO_OWNER=""
REPO_NAME=""
if $GH_AVAILABLE && git rev-parse --git-dir &> /dev/null; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [ -n "$REMOTE_URL" ]; then
        REPO_OWNER=$(echo "$REMOTE_URL" | sed -E 's|.*[/:]([^/]+)/[^/]+\.git.*|\1|' 2>/dev/null || echo "")
        REPO_NAME=$(echo "$REMOTE_URL" | sed -E 's|.*[/:]([^/]+)/([^/]+)(\.git)?$|\2|' 2>/dev/null || echo "")
    fi
fi

# ── Helper: move a board card to a named status column ────────────────────────

move_card_to() {
    local project_number="$1"
    local item_id="$2"
    local target_status="$3"

    local status_field_id
    status_field_id=$(gh project field-list "$project_number" \
        --owner "$REPO_OWNER" \
        --json name,id \
        -q '.[] | select(.name == "Status") | .id' 2>/dev/null || echo "")
    [ -z "$status_field_id" ] && return 0

    local option_id
    option_id=$(gh project field-list "$project_number" \
        --owner "$REPO_OWNER" \
        --json name,options \
        -q ".[] | select(.name == \"Status\") | .options[] | select(.name == \"$target_status\") | .id" \
        2>/dev/null || echo "")
    [ -z "$option_id" ] && return 0

    gh project item-edit "$project_number" \
        --owner "$REPO_OWNER" \
        --id "$item_id" \
        --field-id "$status_field_id" \
        --single-select-option-id "$option_id" 2>/dev/null || true
}

# ── Helper: get project number by name ────────────────────────────────────────

get_project_number() {
    gh_cmd project list --owner "$REPO_OWNER" \
        --format json \
        -q ".[] | select(.title == \"$PROJECT_NAME\") | .number"
}

# ── Helper: get item ID for an issue in a project ─────────────────────────────

get_item_id() {
    local project_number="$1"
    local issue_number="$2"
    gh_cmd project item-list "$project_number" \
        --owner "$REPO_OWNER" \
        --format json \
        -q ".[] | select(.content.number == $issue_number) | .id"
}

# ── Function: create a GitHub Project ─────────────────────────────────────────

create_project() {
    check_gh_project_scope || return 1
    echo "Creating GitHub Project: $PROJECT_NAME"

    PROJECT_NUMBER=$(get_project_number)
    if [ -n "$PROJECT_NUMBER" ]; then
        echo "Project already exists with number: $PROJECT_NUMBER"
    else
        # FIX: removed invalid --format json flag (gh project create uses --json directly)
        PROJECT_NUMBER=$(gh_cmd project create \
            --owner "$REPO_OWNER" \
            --title "$PROJECT_NAME" \
            --json number \
            -q '.number')
        echo "Created project #$PROJECT_NUMBER"
    fi

    echo "Project URL: https://github.com/orgs/$REPO_OWNER/projects/$PROJECT_NUMBER"
    echo "or: https://github.com/users/$REPO_OWNER/projects/$PROJECT_NUMBER"
    echo ""
    echo "Next: run '$0 setup-labels' to create AES labels in this repository."
}

# ── Function: create AES labels in the repository ─────────────────────────────
# Run once per repository after creating the project board.
# Uses --force so it's safe to run multiple times (updates existing labels).

setup_labels() {
    echo "Creating AES labels in $REPO_OWNER/$REPO_NAME..."

    # Format: "name:color:description"
    local label_defs=(
        "aes:backlog:#0075ca:Available for claiming by an agent or developer"
        "aes:in-progress:#e4e669:Currently being worked on — do not claim"
        "aes:plan:#d93f0b:In Plan phase (hostile analysis + spec)"
        "aes:build:#0e8a16:In Build phase (implementation)"
        "aes:verify:#1d76db:In Verify phase (quality gates)"
        "aes:review:#5319e7:In Review phase (5-lens code review)"
        "aes:done:#2cbe4e:All phases complete"
        "aes:blocked:#b60205:Blocked — see issue comments for reason"
    )

    for label_def in "${label_defs[@]}"; do
        local name color desc
        name=$(echo "$label_def" | cut -d: -f1)
        color=$(echo "$label_def" | cut -d: -f2)
        desc=$(echo "$label_def" | cut -d: -f3-)
        gh label create "$name" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --color "${color#\#}" \
            --description "$desc" \
            --force 2>/dev/null && echo "  ✓ $name" || echo "  ✗ $name (failed — check gh auth)"
    done

    echo ""
    echo "Labels ready. Add 'aes:backlog' to issues you want agents to pick up."
}

# ── Function: link an issue to the project ────────────────────────────────────

link_issue_to_project() {
    local issue_number="$1"
    local project_number="$2"

    echo "Linking issue #$issue_number to project #$project_number"
    gh project item-add "$project_number" \
        --owner "$REPO_OWNER" \
        --url "https://github.com/$REPO_OWNER/$REPO_NAME/issues/$issue_number"
}

# ── Function: claim a ticket ──────────────────────────────────────────────────
# Assigns an issue to the current user, updates labels, moves the board card,
# and creates a local branch — ready to start the AES Plan phase.
#
# Usage:
#   ./github-projects.sh claim <issue-number>
#   ./github-projects.sh claim   # auto-picks lowest-numbered unassigned backlog issue
#
# Race condition note: the check-then-assign is not atomic (GitHub API limitation).
# The re-verify step below detects most races in practice. For high-concurrency
# environments, use a dedicated arbitration mechanism (e.g. a GitHub Action lock).

claim_ticket() {
    local issue_number=""
    local ticket_id=""

    # Parse args: first positional arg is issue number, --ticket sets TXXX
    for arg in "$@"; do
        case "$arg" in
            --ticket=*) ticket_id="${arg#--ticket=}" ;;
            *)          issue_number="$arg" ;;
        esac
    done

    # Auto-pick issue if not specified
    if [ -z "$issue_number" ] && $GH_AVAILABLE; then
        echo "No issue number given — searching for next available ticket..."
        issue_number=$(gh issue list \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --state open \
            --label "aes:backlog" \
            --json number,assignees \
            -q '[.[] | select(.assignees | length == 0)] | sort_by(.number) | .[0].number' \
            2>/dev/null || echo "")
        if [ -z "$issue_number" ] || [ "$issue_number" = "null" ]; then
            echo "No unassigned backlog tickets found."
            echo "Either all tickets are claimed or no issues have the 'aes:backlog' label."
            [ -n "$ticket_id" ] && echo "Updating local kanban anyway for $ticket_id..."
            [ -z "$ticket_id" ] && exit 0
        fi
    fi

    # If no issue number but we have a ticket_id, generate a placeholder
    if [ -z "$issue_number" ] && [ -n "$ticket_id" ]; then
        issue_number="local-${ticket_id}"
    fi

    local issue_title=""
    local current_user=""

    if $GH_AVAILABLE && [ -n "$REPO_OWNER" ]; then
        # Pre-check: is the issue already assigned?
        if [ -n "$issue_number" ] && [[ "$issue_number" =~ ^[0-9]+$ ]]; then
            local current_assignee
            current_assignee=$(gh issue view "$issue_number" \
                --repo "$REPO_OWNER/$REPO_NAME" \
                --json assignees \
                -q '.assignees[0].login' 2>/dev/null || echo "")
            if [ -n "$current_assignee" ] && [ "$current_assignee" != "null" ]; then
                echo "Error: Issue #$issue_number is already claimed by @$current_assignee"
                exit 1
            fi

            # Get current GitHub user
            current_user=$(gh api user -q '.login' 2>/dev/null || echo "")

            # Get issue title
            issue_title=$(gh issue view "$issue_number" \
                --repo "$REPO_OWNER/$REPO_NAME" \
                --json title \
                -q '.title' 2>/dev/null || echo "untitled")
        fi
    else
        echo "GitHub CLI not available — local-only claim"
        issue_title=$(python3 -c "
import os, re
tickets_dir = '$TICKETS_DIR'
for fname in os.listdir(tickets_dir):
    if fname.startswith('$ticket_id'):
        with open(os.path.join(tickets_dir, fname)) as f:
            for line in f:
                m = re.match(r'^title:\s*(.+)', line)
                if m: print(m.group(1).strip())
" 2>/dev/null || echo "untitled")
    fi

    # ── GitHub operations ──────────────────────────────────────────────────
    if $GH_AVAILABLE && [[ "$issue_number" =~ ^[0-9]+$ ]]; then
        local slug
        slug=$(echo "$issue_title" | tr '[:upper:]' '[:lower:]' | \
            sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//g' | cut -c1-40)
        local branch_name="aes/${issue_number}-${slug}"

        echo "Claiming issue #$issue_number: $issue_title"

        # 1. Assign to current user
        gh issue edit "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --add-assignee "$current_user" 2>/dev/null || true

        # 2. Re-verify assignment
        sleep 1
        local final_assignee
        final_assignee=$(gh issue view "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --json assignees \
            -q '.assignees[0].login' 2>/dev/null || echo "")
        if [ -n "$final_assignee" ] && [ "$final_assignee" != "$current_user" ]; then
            echo "Race condition — issue #$issue_number claimed by @$final_assignee"
            exit 1
        fi

        # 3. Update labels
        gh issue edit "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --add-label "aes:in-progress" \
            --remove-label "aes:backlog" 2>/dev/null || true

        # 4. Move card on board
        local project_number
        project_number=$(get_project_number)
        if [ -n "$project_number" ]; then
            local item_id
            item_id=$(get_item_id "$project_number" "$issue_number")
            if [ -z "$item_id" ]; then
                link_issue_to_project "$issue_number" "$project_number"
                item_id=$(get_item_id "$project_number" "$issue_number")
            fi
            [ -n "$item_id" ] && move_card_to "$project_number" "$item_id" "In Progress"
        fi

        # 5. Create/switch branch
        if git show-ref --quiet "refs/heads/$branch_name" 2>/dev/null; then
            echo "Branch exists: $branch_name"
            git checkout "$branch_name" 2>/dev/null || true
        else
            git checkout -b "$branch_name" 2>/dev/null || true
        fi

        # 6. Post comment
        local body
        body="<!-- AES-CLAIM -->"$'\n'
        body+="🤖 **Claimed by @${current_user}"$'\n'
        body+=$'\n'
        body+="- Branch: \`${branch_name}\`"$'\n'
        body+="- Phase: Plan"$'\n'
        body+="- Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"$'\n'
        body+=$'\n'
        body+="Following AES protocol: Plan → Build → Verify → Review → Learn"
        gh issue comment "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --body "$body" 2>/dev/null || true

        echo "  GitHub: issue #$issue_number claimed"
    fi

    # ── Local kanban updates ───────────────────────────────────────────────
    if [ -n "$ticket_id" ]; then
        update_kanban_current_ticket "$ticket_id"
        update_ticket_status "$ticket_id" "in-progress"
    fi

    # Update ticket map
    if [ -n "$issue_number" ] && [ -n "$ticket_id" ]; then
        ticket_map_set "$issue_number" "$ticket_id" "$issue_title" "$current_user"
    fi

    echo ""
    echo "✅ Claimed: issue #${issue_number:-local} → ${ticket_id:-untracked}"
    echo "   Next: run 'make aes-plan' to start the Plan phase"
}

# ── Function: release a ticket (unclaim) ──────────────────────────────────────
# Used when an agent or human needs to abandon a ticket without completing it.

release_ticket() {
    local issue_number=""
    local ticket_id=""

    for arg in "$@"; do
        case "$arg" in
            --ticket=*) ticket_id="${arg#--ticket=}" ;;
            *)          issue_number="$arg" ;;
        esac
    done

    local current_user=""
    if $GH_AVAILABLE; then
        current_user=$(gh api user -q '.login' 2>/dev/null || echo "")
    fi

    if [ -n "$issue_number" ] && $GH_AVAILABLE; then
        echo "Releasing issue #$issue_number"

        gh issue edit "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --remove-assignee "$current_user" \
            --add-label "aes:backlog" \
            --remove-label "aes:in-progress" 2>/dev/null || \
        gh issue edit "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --remove-assignee "$current_user" 2>/dev/null || true

        local project_number
        project_number=$(get_project_number)
        if [ -n "$project_number" ]; then
            local item_id
            item_id=$(get_item_id "$project_number" "$issue_number")
            [ -n "$item_id" ] && move_card_to "$project_number" "$item_id" "Backlog"
        fi

        gh issue comment "$issue_number" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --body "<!-- AES-RELEASE -->
🔓 **Released by @${current_user}**

Ticket returned to Backlog. Available for another agent or developer to pick up." \
            2>/dev/null || true

        echo "  GitHub: issue #$issue_number released to Backlog"
    fi

    # Update local ticket
    if [ -n "$ticket_id" ]; then
        update_ticket_status "$ticket_id" "pending"
    fi

    # Remove from ticket map
    if [ -n "$issue_number" ]; then
        ticket_map_remove "$issue_number"
    fi

    # Clear current_ticket if it matches
    if [ -n "$ticket_id" ]; then
        local current_ticket
        current_ticket=$(grep '^current_ticket:' "$KANBAN_FILE" 2>/dev/null | sed 's/.*: //')
        if [ "$current_ticket" = "$ticket_id" ]; then
            update_kanban_current_ticket "none"
        fi
    fi

    echo ""
    echo "✅ Released: ${ticket_id:-untracked}"
}

# ── Function: update issue status based on labels ─────────────────────────────

update_issue_status() {
    local issue_number="$1"
    local project_number="$2"

    local labels
    labels=$(gh issue view "$issue_number" \
        --repo "$REPO_OWNER/$REPO_NAME" \
        --json labels \
        -q '.labels[].name' | tr '\n' ',' | sed 's/,$//')

    local item_id
    item_id=$(get_item_id "$project_number" "$issue_number")
    [ -z "$item_id" ] && return 0

    # Map AES labels to board columns (first match wins)
    local target_status=""
    case "$labels" in
        *"aes:backlog"*)     target_status="Backlog" ;;
        *"aes:plan"*)        target_status="Plan" ;;
        *"aes:build"*)       target_status="In Progress" ;;
        *"aes:verify"*)      target_status="In Review" ;;
        *"aes:review"*)      target_status="In Review" ;;
        *"aes:in-progress"*) target_status="In Progress" ;;
        *"aes:done"*)        target_status="Done" ;;
        # Legacy label support
        *"ready"*)           target_status="Backlog" ;;
        *"in-progress"*|*"development"*) target_status="In Progress" ;;
        *"review"*)          target_status="In Review" ;;
        *"done"*|*"completed"*) target_status="Done" ;;
    esac

    if [ -n "$target_status" ]; then
        move_card_to "$project_number" "$item_id" "$target_status"
        echo "  Issue #$issue_number → $target_status"
    fi
}

# ── Ticket map management ──────────────────────────────────────────────────────
# aes/ticket-map.json maps GitHub issue numbers to local ticket IDs:
# { "42": { "ticket": "T011", "title": "...", "claimed_by": "..." } }

ensure_ticket_map() {
    if [ ! -f "$TICKET_MAP" ]; then
        mkdir -p "$AES_ROOT/aes"
        echo "{}" > "$TICKET_MAP"
    fi
}

ticket_map_get() {
    local issue_number="$1"
    ensure_ticket_map
    python3 -c "
import json
with open('$TICKET_MAP') as f:
    m = json.load(f)
entry = m.get('$issue_number', {})
print(entry.get('ticket', ''))
" 2>/dev/null || echo ""
}

ticket_map_set() {
    local issue_number="$1"
    local ticket_id="$2"
    local title="$3"
    local claimed_by="${4:-}"
    ensure_ticket_map
    python3 -c "
import json
with open('$TICKET_MAP') as f:
    m = json.load(f)
m['$issue_number'] = {'ticket': '$ticket_id', 'title': '$title', 'claimed_by': '$claimed_by'}
with open('$TICKET_MAP', 'w') as f:
    json.dump(m, f, indent=2)
" 2>/dev/null
    echo "  Ticket map: issue #$issue_number → $ticket_id"
}

ticket_map_remove() {
    local issue_number="$1"
    ensure_ticket_map
    python3 -c "
import json
with open('$TICKET_MAP') as f:
    m = json.load(f)
m.pop('$issue_number', None)
with open('$TICKET_MAP', 'w') as f:
    json.dump(m, f, indent=2)
" 2>/dev/null
    echo "  Ticket map: removed issue #$issue_number"
}

# ── Local kanban update functions ──────────────────────────────────────────────
# These update aes/kanban.md frontmatter and aes/tickets/TXXX-name.md status.

update_kanban_current_ticket() {
    local ticket_id="${1:-none}"
    if [ ! -f "$KANBAN_FILE" ]; then
        echo "  Local kanban: $KANBAN_FILE not found — skipping"
        return 0
    fi
    if grep -q '^current_ticket:' "$KANBAN_FILE" 2>/dev/null; then
        sed -i "s/^current_ticket:.*/current_ticket: $ticket_id/" "$KANBAN_FILE"
    else
        echo "  Local kanban: no current_ticket field found — skipping"
        return 0
    fi
    echo "  Local kanban: current_ticket → $ticket_id"
}

update_ticket_status() {
    local ticket_id="$1"
    local new_status="$2"
    if [ -z "$ticket_id" ]; then
        return 0
    fi
    local ticket_file
    ticket_file=$(find "$TICKETS_DIR" -name "${ticket_id}*.md" -type f 2>/dev/null | head -1)
    if [ -z "$ticket_file" ] || [ ! -f "$ticket_file" ]; then
        echo "  Local ticket: $ticket_id not found — skipping"
        return 0
    fi
    if grep -q '^status:' "$ticket_file" 2>/dev/null; then
        sed -i "s/^status:.*/status: $new_status/" "$ticket_file"
        echo "  Local ticket: $ticket_id → status: $new_status"
    fi
}

# ── Sync from GitHub to local ──────────────────────────────────────────────────
# Reads GitHub issue labels and updates local ticket status + kanban.

sync_from_github() {
    if ! $GH_AVAILABLE; then
        echo "GitHub CLI not available — cannot sync from GitHub"
        return 1
    fi
    if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
        echo "No GitHub remote configured — cannot sync"
        return 1
    fi

    echo "Syncing GitHub issues → local kanban..."
    ensure_ticket_map

    gh issue list --repo "$REPO_OWNER/$REPO_NAME" \
        --state open \
        --json number,title,labels,assignees \
        -q '.[] | {number, title, labels: [.labels[].name], assignee: (.assignees[0].login // "")}' 2>/dev/null | \
    python3 -c "
import sys, json

LABEL_MAP = {
    'aes:plan': 'plan',
    'aes:build': 'build',
    'aes:verify': 'verify',
    'aes:review': 'review',
    'aes:done': 'done',
    'aes:in-progress': 'in-progress',
    'aes:backlog': 'pending',
}

status_by_ticket = {}
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    num = data['number']
    labels = data.get('labels', [])
    assignee = data.get('assignee', '')
    local_status = 'pending'
    for L, S in LABEL_MAP.items():
        if L in labels:
            local_status = S
            break
    status_by_ticket[str(num)] = {'status': local_status, 'assignee': assignee}

print(json.dumps(status_by_ticket))
" > /tmp/aes-gh-sync.json 2>/dev/null || true

    local updated=0
    while IFS="|" read -r issue_num ticket_id; do
        [ -z "$ticket_id" ] && continue
        local gh_data
        gh_data=$(python3 -c "
import json
with open('/tmp/aes-gh-sync.json') as f:
    data = json.load(f)
entry = data.get('$issue_num', {})
print(entry.get('status', 'pending'))
print(entry.get('assignee', ''))
" 2>/dev/null)
        local status_from_gh
        status_from_gh=$(echo "$gh_data" | sed -n '1p')
        if [ -n "$status_from_gh" ] && [ "$status_from_gh" != "pending" ]; then
            update_ticket_status "$ticket_id" "$status_from_gh"
            updated=$((updated + 1))
        fi
    done < <(python3 -c "
import json
with open('$TICKET_MAP') as f:
    m = json.load(f)
for issue, entry in m.items():
    print(f\"{issue}|{entry.get('ticket', '')}\")
" 2>/dev/null)

    rm -f /tmp/aes-gh-sync.json
    echo "  Updated $updated local tickets from GitHub"
}

# ── Push from local to GitHub ─────────────────────────────────────────────────
# Reads local ticket status and pushes to GitHub issue labels.

sync_to_github() {
    if ! $GH_AVAILABLE; then
        echo "GitHub CLI not available — cannot push to GitHub"
        return 1
    fi
    if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
        echo "No GitHub remote configured — cannot push"
        return 1
    fi

    echo "Syncing local kanban → GitHub issues..."
    ensure_ticket_map

    local count=0
    while IFS="|" read -r issue_num ticket_id status; do
        [ -z "$ticket_id" ] && continue
        local target_label=""
        case "$status" in
            pending|backlog) target_label="aes:backlog" ;;
            in-progress)     target_label="aes:in-progress" ;;
            plan)            target_label="aes:plan" ;;
            build)           target_label="aes:build" ;;
            verify)          target_label="aes:verify" ;;
            review)          target_label="aes:review" ;;
            done)            target_label="aes:done" ;;
            blocked)         target_label="aes:blocked" ;;
        esac
        if [ -n "$target_label" ]; then
            gh issue edit "$issue_num" \
                --repo "$REPO_OWNER/$REPO_NAME" \
                --add-label "$target_label" 2>/dev/null || true
            count=$((count + 1))
        fi
    done < <(python3 -c "
import json, os, re
tickets_dir = '$TICKETS_DIR'
with open('$TICKET_MAP') as f:
    m = json.load(f)
for issue, entry in m.items():
    tid = entry.get('ticket', '')
    if not tid:
        continue
    status = 'pending'
    for fname in os.listdir(tickets_dir):
        if fname.startswith(tid):
            with open(os.path.join(tickets_dir, fname)) as tf:
                content = tf.read()
                mo = re.search(r'^status: (.+)', content, re.MULTILINE)
                if mo:
                    status = mo.group(1).strip()
            break
    print(f'{issue}|{tid}|{status}')
" 2>/dev/null)

    echo "  Synced $count tickets to GitHub"
}

# ── Main ───────────────────────────────────────────────────────────────────────

case "${1:-}" in
    create)
        check_gh_project_scope || exit 1
        create_project
        ;;
    setup-labels)
        setup_labels
        ;;
    claim)
        # Supports: claim [issue-number] [--ticket=TXXX]
        shift
        claim_ticket "$@"
        ;;
    release)
        # Supports: release [issue-number] [--ticket=TXXX]
        shift
        release_ticket "$@"
        ;;
    link)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 link <issue-number>"
            exit 1
        fi
        check_gh_project_scope || exit 1
        PROJECT_NUMBER=$(get_project_number)
        if [ -z "$PROJECT_NUMBER" ]; then
            create_project
            PROJECT_NUMBER=$(get_project_number)
        fi
        link_issue_to_project "$2" "$PROJECT_NUMBER"
        ;;
    update)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 update <issue-number>"
            exit 1
        fi
        check_gh_project_scope || exit 1
        PROJECT_NUMBER=$(get_project_number)
        if [ -z "$PROJECT_NUMBER" ]; then
            echo "Error: Project '$PROJECT_NAME' not found. Run '$0 create' first."
            exit 1
        fi
        update_issue_status "$2" "$PROJECT_NUMBER"
        ;;
    sync)
        check_gh_project_scope || exit 1
        echo "Syncing all open issues with GitHub Project..."
        PROJECT_NUMBER=$(get_project_number)
        if [ -z "$PROJECT_NUMBER" ]; then
            create_project
            PROJECT_NUMBER=$(get_project_number)
        fi
        ISSUES=$(gh issue list \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --state open \
            --json number \
            -q '.[].number')
        for issue_num in $ISSUES; do
            item_id=$(get_item_id "$PROJECT_NUMBER" "$issue_num")
            if [ -z "$item_id" ]; then
                link_issue_to_project "$issue_num" "$PROJECT_NUMBER"
            fi
            update_issue_status "$issue_num" "$PROJECT_NUMBER"
        done
        echo "Sync complete."
        ;;
    sync-from-github)
        sync_from_github
        ;;
    sync-to-github)
        sync_to_github
        ;;
    map)
        ensure_ticket_map
        python3 -m json.tool "$TICKET_MAP" 2>/dev/null || echo "{}"
        ;;
    *)
        echo "GitHub Projects automation for AES"
        echo ""
        echo "Usage:"
        echo "  $0 create                  Create GitHub Project board"
        echo "  $0 setup-labels            Create all aes:* labels in the repository (run once)"
        echo "  $0 claim [issue-number]       Claim a ticket (assign + branch + move card)"
        echo "                             Omit issue-number to auto-pick next from Backlog"
        echo "  $0 claim --ticket=TXXX        Claim a local ticket (no GitHub, sets status)"
        echo "  $0 release <issue-number>     Release a ticket back to Backlog"
        echo "  $0 release --ticket=TXXX      Release a local ticket (no GitHub)"
        echo "  $0 link <issue-number>        Add an issue to the project board"
        echo "  $0 update <issue-number>      Sync issue status to board based on labels"
        echo "  $0 sync                       Sync all open issues to board"
        echo "  $0 sync-from-github           Pull GitHub labels → local ticket status"
        echo "  $0 sync-to-github             Push local ticket status → GitHub labels"
        echo "  $0 map                        Show ticket map (GitHub issue ↔ ticket ID)"
        echo ""
        echo "Options:"
        echo "  Claim/release accept --ticket=TXXX for local kanban integration"
        echo "  Example: $0 claim 42 --ticket=T012"
        echo ""
        echo "Quick start:"
        echo "  $0 create          # create the board"
        echo "  $0 setup-labels    # create aes:* labels in the repo"
        echo "  $0 claim           # pick up the next available ticket"
        echo ""
        echo "AES labels (managed by this script):"
        echo "  aes:backlog     Available for claiming"
        echo "  aes:in-progress Being worked on (set by claim, cleared by release/done)"
        echo "  aes:plan        In Plan phase"
        echo "  aes:build       In Build phase"
        echo "  aes:verify      In Verify phase"
        echo "  aes:review      In Review phase"
        echo "  aes:done        Complete"
        echo "  aes:blocked     Blocked (see issue comments)"
        echo ""
        echo "Environment variables:"
        echo "  AES_GITHUB_PROJECT_NAME     Board name (default: AES Project)"
        echo "  AES_GITHUB_PROJECT_TEMPLATE Template: kanban or scrum (default: kanban)"
        echo ""
        echo "Examples:"
        echo "  $0 create"
        echo "  $0 setup-labels"
        echo "  $0 claim                  # auto-pick next available ticket"
        echo "  $0 claim 42               # claim specific issue #42"
        echo "  $0 claim 42 --ticket=T012 # claim + sync local kanban"
        echo "  $0 release 42             # give back issue #42"
        echo "  $0 release 42 --ticket=T012"
        echo "  $0 release --ticket=T012  # release local ticket only"
        echo "  $0 sync-from-github       # pull GitHub labels → local"
        echo "  $0 sync-to-github         # push local status → GitHub"
        exit 1
        ;;
esac
