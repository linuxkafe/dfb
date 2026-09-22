# Design System — Deck Fly Brain

**Version:** 1.0.0
**Status:** Draft
**Last Updated:** 2026-09-22
**Schema:** `aes/design-v1`

---

## Tokens (YAML Frontmatter)

```yaml
schema: aes/design-v1
design_system: "dfb-design-system"

# Color Palette
colors:
  # Dark mode (primary for Deck)
  dark:
    background: "#0a0a0a"
    surface: "#171717"
    surface-elevated: "#1f1f1f"
    border: "#262626"
    border-strong: "#3f3f3f"
    text-primary: "#fafafa"
    text-secondary: "#a3a3a3"
    text-muted: "#737373"
    text-inverse: "#171717"
    accent: "#22c55e"
    accent-hover: "#16a34a"
    accent-muted: "#14532d"
    destructive: "#ef4444"
    destructive-hover: "#dc2626"
    destructive-muted: "#7f1d1d"
    warning: "#f59e0b"
    warning-hover: "#d97706"
    info: "#3b82f6"
    info-hover: "#2563eb"
    focus-ring: "#22c55e"
    overlay: "rgba(0, 0, 0, 0.6)"

  # Light mode (secondary)
  light:
    background: "#ffffff"
    surface: "#f5f5f5"
    surface-elevated: "#ffffff"
    border: "#e5e5e5"
    border-strong: "#d4d4d4"
    text-primary: "#171717"
    text-secondary: "#525252"
    text-muted: "#737373"
    text-inverse: "#ffffff"
    accent: "#22c55e"
    accent-hover: "#16a34a"
    accent-muted: "#dcfce7"
    destructive: "#ef4444"
    destructive-hover: "#dc2626"
    destructive-muted: "#fef2f2"
    warning: "#f59e0b"
    warning-hover: "#d97706"
    info: "#3b82f6"
    info-hover: "#2563eb"
    focus-ring: "#22c55e"
    overlay: "rgba(0, 0, 0, 0.4)"

# Typography
typography:
  font-family:
    sans: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    mono: "'SF Mono', 'Fira Code', 'JetBrains Mono', monospace"
  scale:
    display: { size: "32px", weight: 700, line-height: 1.1, letter-spacing: "-0.02em" }
    h1: { size: "24px", weight: 600, line-height: 1.2, letter-spacing: "-0.01em" }
    h2: { size: "20px", weight: 600, line-height: 1.3 }
    h3: { size: "18px", weight: 600, line-height: 1.4 }
    body-lg: { size: "16px", weight: 400, line-height: 1.5 }
    body: { size: "14px", weight: 400, line-height: 1.5 }
    body-sm: { size: "12px", weight: 400, line-height: 1.5 }
    caption: { size: "11px", weight: 400, line-height: 1.4, letter-spacing: "0.02em" }
    button: { size: "13px", weight: 500, line-height: 1.4 }
    mono: { size: "12px", weight: 400, line-height: 1.6 }

# Spacing System (4px base unit)
spacing:
  base: 4
  scale: [0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 128]
  component-padding: 12
  component-gap: 8
  page-padding: 24
  section-gap: 48

# Border Radius
radius:
  none: 0
  sm: 4
  md: 8
  lg: 12
  xl: 16
  full: 9999

# Shadows
shadows:
  none: "none"
  sm: "0 1px 2px rgba(0, 0, 0, 0.05)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
  inner: "inset 0 2px 4px rgba(0, 0, 0, 0.06)"
  focus: "0 0 0 3px var(--color-focus-ring)"

# Z-Index
z-index:
  base: 0
  dropdown: 100
  sticky: 200
  modal-backdrop: 300
  modal: 400
  popover: 500
  tooltip: 600
  toast: 700

# Breakpoints
breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1280px"
  2xl: "1536px"

# Transitions
transitions:
  fast: "150ms ease"
  normal: "200ms ease"
  slow: "300ms ease"

# Iconography
icons:
  library: "lucide"
  sizes:
    sm: 14
    md: 18
    lg: 24
    xl: 32
```

---

## Foundations

### Color System

#### Semantic Color Roles
| Role | Dark | Light | Usage |
|------|------|-------|-------|
| `background` | `#0a0a0a` | `#ffffff` | Page background |
| `surface` | `#171717` | `#f5f5f5` | Card/panel background |
| `surface-elevated` | `#1f1f1f` | `#ffffff` | Modal, dropdown, tooltip |
| `border` | `#262626` | `#e5e5e5` | Dividers, input borders |
| `border-strong` | `#3f3f3f` | `#d4d4d4` | Focused inputs, active tabs |
| `text-primary` | `#fafafa` | `#171717` | Headings, body text |
| `text-secondary` | `#a3a3a3` | `#525252` | Subheadings, labels |
| `text-muted` | `#737373` | `#737373` | Placeholders, disabled text |
| `accent` | `#22c55e` | `#22c55e` | Primary actions, links |
| `destructive` | `#ef4444` | `#ef4444` | Errors, dangerous actions |
| `warning` | `#f59e0b` | `#f59e0b` | Warnings, caution states |
| `info` | `#3b82f6` | `#3b82f6` | Informational states |

#### State Colors (Safety System)
| State | Color | Usage |
|-------|-------|-------|
| Safe | `#22c55e` | Telemetry OK, within envelope |
| Warning | `#f59e0b` | Near limits, degraded |
| Critical | `#ef4444` | Envelope violation, RTL triggered |
| Unknown | `#737373` | No telemetry, no link |

### Typography

#### Scale
| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `display` | 32px | 700 | 1.1 | Hero, splash |
| `h1` | 24px | 600 | 1.2 | Page title |
| `h2` | 20px | 600 | 1.3 | Section title |
| `h3` | 18px | 600 | 1.4 | Subsection |
| `body-lg` | 16px | 400 | 1.5 | Lead paragraph |
| `body` | 14px | 400 | 1.5 | Standard text |
| `body-sm` | 12px | 400 | 1.5 | Dense UI, tables |
| `caption` | 11px | 400 | 1.4 | Metadata, timestamps |
| `button` | 13px | 500 | 1.4 | Buttons, actions |
| `mono` | 12px | 400 | 1.6 | Code, telemetry values |

#### Font Stacks
```css
/* Sans-serif (UI text) */
font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

/* Monospace (telemetry, code) */
font-family: "SF Mono", "Fira Code", "JetBrains Mono", monospace;
```

### Spacing System
Base unit: **4px**

| Token | Value | Usage |
|-------|-------|-------|
| `space-0` | 0 | Reset |
| `space-1` | 4px | Tight gaps |
| `space-2` | 8px | Standard gaps |
| `space-3` | 12px | Component padding |
| `space-4` | 16px | Standard padding |
| `space-5` | 20px | Loose padding |
| `space-6` | 24px | Section padding |
| `space-7` | 28px | Large gaps |
| `space-8` | 32px | Section gaps |
| `space-10` | 40px | Page sections |
| `space-12` | 48px | Major sections |
| `space-16` | 64px | Page margins |
| `space-20` | 80px | Hero sections |
| `space-24` | 96px | Large layouts |

### Iconography
- **Library:** Lucide (`lucide-react` or `lucide-static`)
- **No emoji in source code** (AES FR-D1)
- **Sizes:** 14px (sm), 18px (md), 24px (lg), 32px (xl)
- **Stroke width:** 2px (consistent with Lucide default)

---

## Components

### Button
```yaml
variants:
  - primary: accent background, white text, accent-hover on hover
  - secondary: surface background, border, text-primary
  - destructive: destructive background, white text
  - ghost: transparent, text-secondary, surface on hover
  - link: text-accent, underline on hover
sizes:
  - sm: padding 6px 10px, text-sm
  - md: padding 8px 16px, button
  - lg: padding 12px 24px, button
states:
  - default, hover, active, disabled, loading
```

### Card
```yaml
structure:
  - surface background
  - border: 1px solid border
  - radius: lg
  - shadow: md (elevated)
  - padding: space-4 (16px)
variants:
  - default
  - bordered (stronger border)
  - elevated (xl shadow)
  - interactive (hover: border-strong, shadow-lg)
```

### Input
```yaml
states:
  - default: surface, border
  - hover: border-strong
  - focus: border-strong, focus-ring shadow
  - error: destructive border, destructive focus-ring
  - disabled: muted background, muted text
sizes:
  - sm: padding 6px 10px, text-sm
  - md: padding 8px 12px, body
  - lg: padding 10px 14px, body-lg
```

### Badge / Status Pill
```yaml
variants:
  - success: accent-muted background, accent text
  - warning: warning-muted background, warning text
  - critical: destructive-muted background, destructive text
  - info: info-muted background, info text
  - neutral: surface background, text-secondary
sizes:
  - sm: padding 2px 6px, caption
  - md: padding 4px 8px, body-sm
```

### Table
```yaml
structure:
  - header: text-muted, caption, uppercase, letter-spacing
  - row: body, border-bottom
  - hover: surface-elevated
  - striped: alternating surface/surface-elevated
alignment:
  - text: left
  - numeric: right (mono font)
  - status: center
```

### Navigation
```yaml
tabs:
  - indicator: accent, 2px bottom border
  - active: text-primary, weight 500
  - inactive: text-secondary
  - gap: space-2 (8px)

sidebar:
  - width: 240px (collapsed: 64px)
  - item: padding space-2 space-3, radius md
  - active: surface-elevated, accent left border
  - icon: size md, gap space-2
```

### Modal / Dialog
```yaml
structure:
  - backdrop: overlay, z-index modal-backdrop
  - container: surface, radius xl, shadow xl, max-w lg
  - header: h2, close button (ghost, top-right)
  - body: space-4 padding
  - footer: space-4 padding, flex-end, gap space-2
sizes:
  - sm: max-w 320px
  - md: max-w 480px
  - lg: max-w 640px
  - xl: max-w 800px
  - full: max-w 4xl
```

### Toast / Notification
```yaml
positions:
  - top-right (default)
  - top-left
  - bottom-right
  - bottom-left
variants:
  - success: accent
  - warning: warning
  - error: destructive
  - info: info
behavior:
  - auto-dismiss: 5000ms (success/info), persistent (warning/error)
  - swipe to dismiss
  - pause on hover
```

---

## Patterns

### Layout
```css
/* Page container */
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-background);
}

/* Content area */
.content {
  flex: 1;
  padding: var(--space-6); /* 24px */
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}

/* Section */
.section {
  margin-bottom: var(--space-12); /* 48px */
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--space-4);
}
```

### Responsive Grid
```css
.grid {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: 1fr;
}

@media (min-width: 640px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 1280px) { .grid { grid-template-columns: repeat(4, 1fr); } }
```

### Telemetry Display
```css
.telemetry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-3);
}

.telemetry-card {
  @extend .card;
}

.telemetry-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 600;
}

.telemetry-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.telemetry-status {
  @extend .badge;
  font-size: var(--text-xs);
}
```

### Forms
```css
.form-group {
  margin-bottom: var(--space-4);
}

.form-label {
  display: block;
  margin-bottom: var(--space-1);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--text-base);
  transition: border var(--transition-fast), box-shadow var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-focus);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

.form-error {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-destructive);
}
```

---

## Guidelines

### Accessibility (WCAG 2.1 AA)
- **Contrast:** All text meets 4.5:1 (normal), 3:1 (large)
- **Focus:** Visible focus ring on all interactive elements
- **Keyboard:** All interactive elements reachable and operable
- **Screen readers:** Semantic HTML, ARIA labels where needed
- **Motion:** Respect `prefers-reduced-motion`

### Dark Mode (Primary for Deck)
- Default theme is dark (Steam Deck context)
- Light mode supported via `[data-theme="light"]`
- System preference respected: `@media (prefers-color-scheme: dark)`

### Responsive Design
- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Touch targets: minimum 44×44px on touch devices

### Motion
- Transitions: 150ms (fast), 200ms (normal), 300ms (slow)
- Easing: `ease-out` for enter, `ease-in` for exit
- Reduced motion: disable non-essential animations

### Icon Usage
- Use Lucide icons exclusively
- No emoji in source code (AES FR-D1)
- Icon + text labels for clarity
- Consistent 2px stroke weight

---

## Do's and Don'ts

### Do's
- Use semantic HTML elements (`<button>`, `<nav>`, `<main>`, `<section>`)
- Use design tokens exclusively (no hardcoded values)
- Use Lucide icons for all iconography
- Maintain 4px spacing grid
- Use mono font for telemetry/numeric data
- Respect user's color scheme preference

### Don'ts
- Use emoji in source code (AES FR-D1)
- Use arbitrary colors not in token system
- Hardcode spacing values
- Use emoji as icons
- Mix font families outside token system
- Skip focus states
- Use em units for spacing (use px/rem tokens)

---

## Integration with UX Manifests

### Page Manifest Contract
Each page in `docs/UX/pages/*.yaml` must declare:
```yaml
schema: aes/ux-v1
design_system: "dfb-design-system"
page: <page-id>
# ... other fields
```

### Component References
Components in manifests must use design system tokens:
```yaml
components:
  - type: button
    variant: primary
    size: md
    # Uses: colors.accent, spacing, radius, typography.button
  - type: card
    variant: elevated
    # Uses: colors.surface-elevated, shadows.lg, radius.lg
```

### Validation
- `make ux-check` runs FC-9 (design system consistency)
- Validates: manifest components ↔ DESIGN.md tokens
- CI gate: fails on mismatch

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-09-22 | Initial full spec per AES FR-D5 |

---

*This design system is the single source of truth for all UI work. All components, pages, and patterns must derive from these tokens and patterns.*