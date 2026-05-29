# DESIGN.md — JobTracker

Design system inspired by Linear (linear.app).

## Design Philosophy

Ultra-minimal, precise, fast-feeling interface. Every pixel is intentional. No visual noise. Dark-first. Information-dense but never cluttered. Animations are subtle and purposeful — never decorative.

## Color System

### Dark Theme (Primary)

```
Background:       #0A0A0B (near-black)
Surface:          #111113 (cards, sidebar)
Surface Elevated: #18181B (hover states, active items)
Surface Hover:    #1F1F23
Border:           #222226
Border Subtle:    #1A1A1E

Text Primary:     #EDEDEF
Text Secondary:   #8B8B8F
Text Tertiary:    #555559
Text Disabled:    #3D3D40

Accent:           #5E6AD2 (Linear purple)
Accent Hover:     #6C75DB
Accent Muted:     rgba(94, 106, 210, 0.15)

Success:          #4DAF73
Warning:          #E2A347
Error:            #E5534B

Match High:       #4DAF73 (>70%)
Match Medium:     #E2A347 (40-70%)
Match Low:        #E5534B (<40%)
```

### Light Theme

```
Background:       #FFFFFF
Surface:          #F9F9FA
Surface Elevated: #FFFFFF
Surface Hover:    #F0F0F2
Border:           #E4E4E7
Border Subtle:    #EDEDEE

Text Primary:     #1B1B1F
Text Secondary:   #636366
Text Tertiary:    #8E8E93

Accent:           #5E6AD2
Accent Muted:     rgba(94, 106, 210, 0.1)
```

## Typography

```
Font Family: Inter, -apple-system, system-ui, sans-serif
Monospace:   "JetBrains Mono", "SF Mono", monospace

Page Title:    20px / font-weight: 600 / letter-spacing: -0.02em
Section Title: 14px / font-weight: 600 / letter-spacing: -0.01em
Body:          13px / font-weight: 400 / line-height: 1.5
Small/Caption: 12px / font-weight: 400
Badge/Label:   11px / font-weight: 500 / letter-spacing: 0.02em / uppercase
```

## Layout

- Sidebar: 240px, fixed, full height, no scrollbar chrome
- Content: max-width 960px, centered, generous padding (24px)
- Spacing scale: 4px base, 8px / 12px / 16px / 24px / 32px
- Border radius: 6px (cards), 4px (buttons, inputs), 999px (badges/pills)

## Components

### Sidebar

- Background: Surface (#111113)
- Border-right: 1px Border
- Logo/title: Text Primary, 16px, semibold
- Nav items: 13px, Text Secondary, rounded 6px, 8px horizontal padding, 6px vertical
- Nav active: Background Accent Muted, Text Accent
- Nav hover: Background Surface Hover
- Sections separated by 4px spacing

### Cards (Job Items)

- Background: transparent (no card border by default)
- Border-bottom: 1px Border Subtle
- Padding: 12px 0
- Hover: Background Surface Elevated, slight lift
- Selected/expanded: Border-left 2px Accent

### Status Badges

- Pill shape (border-radius: 999px)
- Size: 11px font, 4px vertical padding, 8px horizontal padding
- Background: color at 15% opacity
- Text: color at full opacity
- No border

Status colors:
- New: Accent (#5E6AD2)
- Will Apply: Warning (#E2A347)
- Applied: Success (#4DAF73)
- Interview: #A855F7
- Rejected: Error (#E5534B)
- Closed: Text Tertiary

### Buttons

- Height: 32px
- Padding: 0 12px
- Border-radius: 6px
- Font: 13px, font-weight 500
- Primary: Background Accent, Text White
- Secondary: Background Surface Elevated, Text Primary, Border Border
- Ghost: transparent, Text Secondary, hover shows Surface Hover background
- Danger: Background Error, Text White

### Inputs

- Height: 32px
- Background: Surface
- Border: 1px Border
- Border-radius: 6px
- Font: 13px
- Focus: Border Accent, subtle glow
- Placeholder: Text Tertiary

### Match Score

- Displayed as large number (24px, font-weight 600)
- Color-coded: High (>70%) green, Medium (40-70%) amber, Low (<40%) red
- No background, just colored text

### Dashboard Stats

- Cards: Background Surface, Border Border, border-radius 8px
- Padding: 20px
- Stat number: 24px, font-weight 600
- Stat label: 12px, Text Secondary, uppercase, letter-spacing 0.04em

## Animations

- All transitions: 150ms ease
- Sidebar nav: background-color transition only
- Cards: background-color on hover
- Expand/collapse: max-height transition, 200ms ease
- No bounce, no overshoot, no spring physics

## Dark/Light Toggle

- Small icon button in sidebar header (Sun/Moon)
- Toggles class on <html> element
- Persisted in localStorage
- Default: dark
