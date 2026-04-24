# WeChatDigestWindows UI Handoff

This document is the implementation-side companion to the Figma redesign brief.

## Product Shape

The desktop app is now organized as a sidebar app shell instead of a tab-first utility:

- `工作台 / Workbench`
- `数据源 / Data Source`
- `历史输出 / Reports`
- `运行日志 / Logs`
- `设置 / Settings`

The default landing page is `工作台`, which keeps the main task visible in one screen:

1. choose group or DM
2. choose single day or date range
3. run summary
4. inspect report and task log

## Visual System

### Tone

- light theme first
- neutral surfaces with one blue accent
- dense but readable desktop layout
- low-radius cards and controls
- restrained borders instead of decorative gradients

### Core Tokens

- App background: `#f5f7fb`
- Sidebar background: `#eef2f8`
- Card background: `#ffffff`
- Primary accent: `#2f6fed`
- Text primary: `#162033`
- Text secondary: `#617086`
- Border: `#d7e0ec`
- Radius: `8px`
- Form/control padding: `7px` to `10px`

### State Colors

- neutral badge: `#e9eef6`
- info badge: `#e4efff`
- success badge: `#dff5e9`
- warning badge: `#fff1cf`
- danger badge: `#fde5e8`

## Component Mapping

These are the intended design-to-code mappings for PySide6.

| Figma component | PySide6 implementation |
| --- | --- |
| Sidebar navigation | `QListWidget` |
| Header status badge | `QLabel` with `badgeKind` property |
| Section card | `QFrame` with `Card` object name |
| Hero / onboarding card | `QFrame` with `HeroCard` object name |
| Inline privacy notice | `QFrame` with `InlineNotice` object name |
| Session row | `QListWidgetItem` with readable name + muted metadata |
| Segmented controls | checkable-looking `QPushButton` rows |
| Report / log tabs | `QTabWidget` |
| Page content switch | `QStackedWidget` |

## Layout Constraints

- Sidebar width: about `236px`
- Main desktop width target: `1360px` to `1480px`
- Workbench uses a three-zone splitter:
  - sessions: about `300px`
  - job config: about `420px`
  - result area: about `560px`
- Setup uses stacked cards in a scroll area rather than one long form block.
- Reports page uses a left report list and right report preview split.

## Content Rules

- Chinese is the default visible language.
- English is secondary and mainly used when language is switched or when vendor naming is clearer in English.
- DM rows always show readable name first; raw identifier is only supporting metadata.
- Risky fields must include inline help below the input, not only in a large help paragraph.
- Privacy guidance should always be visible on the setup side, not hidden in docs alone.

## Figma Frame Checklist

If continuing the design work in Figma, create at least these frames:

1. App Shell Overview
2. Workbench - Ready
3. Workbench - Running
4. Workbench - Success
5. Workbench - Error
6. Data Source / Setup
7. Reports
8. Logs
9. Settings
10. Empty states and status badge samples

Use redacted or synthetic sample data only.
