# DESIGN.md

# PHIRE
## Frontend Design Constitution

> **This file is the single source of truth for frontend design.**
>
> Every AI coding agent and every developer working on the frontend MUST read this file before creating or modifying UI.
>
> Do not invent a second visual language.
>
> Do not fall back to component-library defaults.
>
> Do not interpret "premium", "modern", or "beautiful" as permission to improvise.
>
> **If a design decision is not defined here, choose the option that best preserves the principles in this document.**

---

# 00. DESIGN NORTH STAR

The product should feel like it was designed by a small, exceptionally good product-design team — one that has spent time in a hospital waiting room, not one that has spent time on Dribbble.

It should feel:

- premium
- calm
- intelligent
- human
- trustworthy
- purposeful
- editorial
- tactile
- clinically credible
- quietly distinctive

It should **not** feel:

- futuristic for the sake of being futuristic
- like an AI demo
- like a SaaS landing-page template
- like a dashboard template
- like a shadcn showcase
- like a Dribbble concept that nobody could actually use
- like a hospital portal from 2009
- like a startup pitch deck converted into HTML
- like a diagnosis is being handed down

### The governing principle

**The interface is a tool for a person reasoning about their own health.**

PHIRE's users are not clinicians reading a chart. They are:

- someone trying to understand what their last few months of labs, symptoms, and notes actually mean
- someone tracking fitness and nutrition and wanting recommendations grounded in their own data
- someone anxious about a result who needs calm, evidence-backed context — not alarm, and not false reassurance

Their attention is valuable, and their trust is fragile.

Do not spend either on decoration. Every screen should make it obvious that PHIRE is careful, not clever.

---

# 01. THE DESIGN LANGUAGE

## Private Ledger

The name is literal, not decorative: **private**, because PHI never leaves the
machine — there is no cloud dashboard to design for, only a personal space;
**ledger**, because the product's core mechanic is an attributed record —
every generated claim is an entry that cites its source, the way a ledger
line cites its receipt. The visual language should make both of those true
at a glance, before a user reads a word of copy.

The visual language combines:

**editorial typography**
+
**precise product UI**
+
**warm physical materials**
+
**restrained data visualization**
+
**subtle tactile motion**

The result should feel closer to a well-designed personal health record — the kind a thoughtful clinician would keep for themselves — than to a wellness-app dashboard or a hospital EHR.

### Three qualities must coexist

### 1. Human

Use warmth, plain language, and thoughtful copy. A person reading about their own body should never feel like they're reading a lab printout.

### 2. Precise

Use grids, alignment, typography, hierarchy, consistent spacing, and predictable interactions. Precision is how the interface earns trust — sloppy layout reads as sloppy reasoning.

### 3. Alive

The interface should respond to the user's actions with subtle motion and state changes, without ever feeling urgent or alarmed.

None of these qualities should overpower the others. In particular: **human warmth must never soften into false certainty, and precision must never harden into cold clinical detachment.**

---

# 02. ANTI-AI-SLOP PRINCIPLE

## AI must not be allowed to choose the aesthetic by default.

The following patterns are common enough to be recognizable as AI-generated when combined:

- purple/blue gradient backgrounds
- dark backgrounds with neon accents
- emerald-on-black "AI" interfaces
- giant centered hero sections
- pill-shaped eyebrow labels
- oversized gradient headings
- three identical feature cards
- bento grids used without information-architecture justification
- glassmorphism
- floating translucent cards
- radial gradient blobs
- dot-grid backgrounds
- decorative noise
- excessive blur
- excessive glow
- giant rounded cards
- every element inside a card
- colored left borders on cards
- excessive pills
- excessive badges
- emoji as interface decoration
- sparkle icons representing generic AI
- animated arrows pointing toward CTAs
- generic dashboard metric cards
- fake testimonials
- fake user avatars
- fake company logos
- fake activity feeds
- fake data
- generic "AI-powered" marketing copy
- "It's not X. It's Y." copy
- "Unlock", "Empower", "Transform", "Seamlessly", "Revolutionize"
- Inter/Roboto/Geist as an automatic choice
- excessive scroll-triggered fade-up animations
- random parallax
- animated background particles
- terminal windows used as decoration
- 3D objects without product meaning
- "premium" achieved through more shadows
- "modern" achieved through more rounded corners
- red/yellow/green traffic-light coloring applied to health data without clinical basis
- confidence expressed only as a percentage with no explanation

These are **warning signs, not isolated sins**.

A rounded card can be excellent.

A gradient can be excellent.

A glass surface can be excellent.

Animation can be excellent.

The question is:

> **Why is it here?**

If the answer is merely:

> "It looks modern."

remove it.

---

# 03. PURPOSE GATE

Every non-trivial visual technique must have a reason.

Before introducing a visual treatment, determine which of these it serves:

1. hierarchy
2. grouping
3. navigation
4. comprehension
5. feedback
6. emphasis
7. interaction
8. orientation
9. trust
10. emotional context
11. accessibility

If it serves none of them, do not introduce it.

### Example

Bad:

> Add a gradient to make the timeline feel premium.

Good:

> Use a very subtle tonal shift to visually separate a claim's stated conclusion from the evidence supporting it.

The second has a design reason.

---

# 04. VISUAL PERSONALITY

The product should have a recognizable visual fingerprint.

It should not depend on:

- gradients
- shadows
- glass
- giant typography
- animation
- trendy components

to establish personality.

Personality comes primarily from:

- typography
- proportion
- color restraint
- editorial composition
- information hierarchy
- how evidence and confidence are shown
- micro-interactions
- content language
- carefully chosen details

---

# 05. COLOR SYSTEM

## Base

The interface uses a warm neutral foundation — paper and ink, like a
personal study rather than a clinic waiting room — and deliberately avoids
both clinical pure-white and the blue/teal "healthtech" default.

```css
:root {
  --canvas: #F5F1E8;
  --surface: #FBF9F3;
  --surface-raised: #FFFFFF;
  --surface-subtle: #ECE7DA;

  --ink: #1C1A15;
  --ink-secondary: #55503F;
  --ink-muted: #7A755F;
  --ink-faint: #9C9782;

  --line: #DDD6C4;
  --line-strong: #C2BAA2;

  /* Ledger accent — primary actions, selection, interactive emphasis */
  --accent: #8C3F2B;
  --accent-hover: #732F1F;
  --accent-soft: #EFDCD2;

  /* Evidence accent — reserved exclusively for citations, source
     attribution, and confidence framing. See §05 "Evidence color". */
  --evidence: #96742A;
  --evidence-hover: #7C5E1E;
  --evidence-soft: #F1E6C8;

  --positive: #33684D;
  --positive-soft: #E1EBE3;

  --warning: #96631F;
  --warning-soft: #F0E4CC;

  --danger: #9C4437;
  --danger-soft: #F1DED9;

  --info: #3F5F72;
  --info-soft: #DEE7EA;
}
```

## Color philosophy

The interface is predominantly:

- warm neutral
- ink
- paper
- oxide

Color should feel **material**, not synthetic, and never like a diagnostic instrument.

### Accent color

Oxide is the primary accent.

Use it for:

- primary actions
- selected states
- important links
- key interactive emphasis
- meaningful highlights

Do not paint entire sections in accent color.

Do not turn every icon into the accent color.

Do not use the accent merely because there is empty space.

### Evidence color (unique to this product)

`--evidence` is a second accent that exists for exactly one job: marking
where something on screen traces back to a source record. A citation mark
next to a generated claim, the "from your visit on [date]" reference, a
confidence explanation, an evidence drawer's active tab — all render in
this ochre, never in oxide.

This is the one place the palette departs from "one accent, used sparingly"
— deliberately, because attribution is PHIRE's core trust mechanism (§35),
not a secondary UI detail. Over repeated use, a person should be able to
learn "ochre means this is backed by something in my record" without
reading a label.

Do not use `--evidence` for anything that isn't a citation or attribution
signal — diluting it to a general second accent color destroys the thing
it's for.

### Health-semantic color (critical rule)

`--positive`, `--warning`, `--danger` may be used for genuine state (a value trending favorably, a flagged inconsistency between two claims, a system error) — never as a stand-in for a clinical judgment PHIRE is not qualified to make.

Do not color-code a lab value, symptom, or trend red/green/yellow as if it were a verdict. PHIRE surfaces evidence and context; it does not triage. If a value needs visual distinction, prefer neutral emphasis (weight, position, a short label) over stoplight color, unless the claim is genuinely about system state (data freshness, sync status, extraction confidence) rather than about the user's health.

---

# 06. COLOR PROHIBITIONS

Do not use as default visual identity:

- purple gradients
- blue-purple gradients
- neon green
- neon cyan
- neon pink
- rainbow gradients
- fluorescent backgrounds
- black + purple
- black + electric blue
- black + emerald glow
- pastel rainbow dashboards
- the generic "digital health" teal-and-white palette

A domain-specific problem may require a different semantic color.

If it does, preserve the underlying neutral foundation, and preserve the rule in §05 that semantic color is never used to imply a diagnosis, and that `--evidence` is never repurposed as a general-use accent.

---

# 07. TYPOGRAPHY

Typography is a primary part of the product identity.

## Primary typeface

**IBM Plex Sans**

Use it for:

- navigation
- buttons
- forms
- tables
- body copy
- labels
- metrics
- interface text

It has enough character to avoid generic system typography while remaining extremely functional.

## Editorial typeface

**Newsreader**

Use sparingly for:

- major contextual headings
- narrative summaries (e.g. a plain-language synopsis of a trend across visits)
- human-centered moments
- important empty states
- occasional editorial emphasis

Do not use Newsreader everywhere, and never for a claim's supporting evidence or a numeric value — those stay in the functional or mono type.

The contrast between IBM Plex Sans and Newsreader should feel intentional.

## Data / technical typeface

**IBM Plex Mono**

Use only where it improves comprehension:

- record IDs
- timestamps
- lab values and units
- source citations / evidence references
- compact numerical metadata

Do not use monospace merely to make the interface look "developer-ish".

## Dense-table typeface

**IBM Plex Sans Condensed**

PHIRE's density comes from real clinical/personal data — lab panels,
medication lists, multi-visit comparison tables (§21, §53) — not from
shrinking the primary typeface. Use the Condensed cut, at the same weight
and size steps as Plex Sans, specifically for wide tabular data where the
regular cut would force horizontal scrolling or awkward truncation.

Do not use it for prose, labels, or anything read as a sentence — it is a
table-density tool, not a stylistic variant of the interface font.

---

# 08. TYPE SCALE

Use a restrained scale.

```text
Display       56 / 64
Hero          48 / 56
Page title    36 / 44
Section       24 / 32
Subsection    18 / 26
Body          15 / 24
Small         13 / 20
Micro         11 / 16
```

Typography must scale responsively.

Do not use enormous headings simply because there is available space.

Do not use all-caps as a substitute for hierarchy.

Use weight, size, spacing, and position to establish hierarchy.

---

# 09. TYPOGRAPHIC CHARACTER

Avoid:

```text
EVERYTHING IN UPPERCASE
```

Avoid:

```text
tiny eyebrow
BIG GRADIENT HEADING
```

Avoid highlighting random words in another color merely for visual interest.

Avoid decorative quotation marks.

Avoid unnecessary italics.

Avoid excessive font-weight variation.

### Preferred hierarchy

```text
Title
Supporting explanation

Section
Supporting context

Content
Metadata
```

Hierarchy should emerge naturally.

---

# 10. SPACING SYSTEM

Base unit:

```text
4px
```

Preferred values:

```text
4
8
12
16
20
24
32
40
48
64
80
96
128
```

Do not introduce arbitrary spacing values without an optical reason.

### Density

The interface should feel **comfortable, not sparse**.

Do not create enormous empty regions to imitate luxury websites.

Do not compress a timeline or evidence list merely to fit more content — a health record is read carefully, not skimmed like a feed.

Density should follow the task.

---

# 11. GRID

Use a consistent grid.

Desktop:

- 12-column conceptual grid
- generous outer margins
- strong alignment
- deliberate column relationships

Tablet:

- 8-column conceptual grid

Mobile:

- 4-column conceptual grid

The exact CSS implementation may differ.

The visual principle must remain:

> **Everything should appear to belong to the same coordinate system.**

Misalignment should be intentional, not accidental.

---

# 12. LAYOUT PHILOSOPHY

Prefer **hierarchical composition** over repetitive component grids.

Do not default to:

```text
┌────────┐ ┌────────┐ ┌────────┐
│ CARD   │ │ CARD   │ │ CARD   │
└────────┘ └────────┘ └────────┘
```

Instead ask:

> What is the most important thing on this screen?

Then give it the strongest spatial position.

A screen should have:

- primary information
- secondary information
- supporting information

not twelve equally important boxes, and not six metric tiles competing for the same attention a lab result deserves.

---

# 13. APPLICATION SHELL

The application shell should be quiet.

Desktop structure:

```text
┌────────────────┬──────────────────────────────────┐
│                │                                  │
│                │          PAGE CONTENT             │
│   NAVIGATION   │                                  │
│                │                                  │
│                │                                  │
└────────────────┴──────────────────────────────────┘
```

Navigation must support the product.

It must not become the visual centerpiece.

### Sidebar

Use:

- clear labels
- restrained active state
- subtle separators
- deliberate grouping

Avoid:

- glowing active items
- excessive icons
- decorative section headers
- pill-shaped navigation items everywhere

---

# 14. PAGE HEADER

Application pages should generally establish context immediately.

Preferred:

```text
Page title
Short contextual explanation

[Primary action]   [Secondary action]
```

Do not automatically add:

```text
[SMALL PILL]

A MASSIVE MARKETING HEADLINE

"Revolutionize your health journey..."
```

PHIRE is an application people return to, not a landing page trying to convert them.

---

# 15. CARDS

Cards are optional containers.

They are not the fundamental building block of the entire UI.

Use a card when content needs:

- grouping
- separation
- independent interaction
- elevation
- movable/sortable behavior

Do not use a card simply because the content exists. A single claim with its evidence is often better as a structured block within a flowing record than as an isolated card.

### Default card

```css
background: var(--surface-raised);
border: 1px solid var(--line);
border-radius: 10px;
box-shadow: none;
```

### Radius system

```text
2px   → technical / compact controls
6px   → small controls
10px  → cards / panels
14px  → large interactive surfaces
```

Do not use 24px, 32px, or 40px radii as a default.

Do not make every element pill-shaped.

---

# 16. DEPTH

Use borders before shadows.

The default interface should feel mostly flat with subtle physical separation.

### Shadow usage

Shadows are reserved for:

- floating menus
- dialogs
- popovers
- elevated temporary surfaces
- drag interactions

Avoid shadows on every card.

Avoid giant diffuse shadows.

Avoid:

```text
0 20px 60px rgba(...)
```

as a universal "premium" effect.

---

# 17. SURFACES

Surfaces should feel related.

Use tonal differences rather than dramatic effects.

Preferred:

```text
Canvas
  ↓
Surface
  ↓
Raised surface
  ↓
Temporary elevation
```

Do not create ten visually different surface treatments.

Do not make every panel look like frosted glass.

---

# 18. GLASSMORPHISM

Glass is not part of the default visual language.

It may only be used where translucency communicates actual spatial layering.

Examples:

- floating navigation over an image
- temporary overlay
- media controls

If used:

- keep blur restrained
- preserve contrast
- preserve readability
- do not combine with glowing borders
- do not combine with neon gradients

---

# 19. BUTTONS

Buttons must establish hierarchy.

### Primary

One dominant action within a context.

### Secondary

Supporting action.

### Tertiary

Low-emphasis action.

### Destructive

Explicitly destructive (e.g. deleting a record, revoking local data).

Button styling must communicate this hierarchy.

Do not make every button visually loud.

Do not make every button pill-shaped.

### Interaction

Buttons should respond through:

- subtle color transition
- small tonal shift
- pressed state
- focus state

Do not animate buttons with unnecessary movement.

---

# 20. FORMS

Forms must optimize completion — and in PHIRE, most forms are a person entering personal health information, so they must also optimize for feeling safe to fill in.

Every field should have:

- visible label
- appropriate input type
- useful default where safe
- clear validation
- understandable error message
- keyboard accessibility

Do not hide important instructions in tooltips.

Do not use placeholder text as the only label.

Do not create multi-step forms unless the complexity genuinely requires them.

Group fields by the user's mental model (e.g. "medications" and "symptoms" as separate groups, not one undifferentiated list).

Where a field touches sensitive health data, state briefly and plainly that it stays local — do not bury that behind a settings page.

---

# 21. TABLES

PHIRE will often need dense information: lab panels, medication lists, claim/evidence pairs, longitudinal metrics.

Tables are preferred when users need to:

- compare records across visits
- sort
- filter
- scan
- identify exceptions (an out-of-range value, a contradicted claim)
- perform bulk operations

Do not replace a useful table with cards merely because cards look modern.

### Table design

Use:

- strong column alignment
- restrained borders
- readable row height
- meaningful status treatment
- hover feedback
- clear selected state

Avoid excessive zebra striping.

Avoid colored rows.

Avoid turning every cell into a badge.

---

# 22. DATA VISUALIZATION

Charts exist to answer questions.

Every visualization must communicate something meaningful — in PHIRE, usually something about change over time, since longitudinal trend is the whole point of the health record.

Before adding a chart, ask:

> What decision or understanding does this chart help someone reach?

If there is no answer, remove it.

### Preferred forms

```text
Change over time (vitals, labs, weight, fitness) → line
Comparison across categories                     → bar
Composition (macro breakdown, symptom categories) → stacked bar
Exact values                                      → table
Progress toward a goal                            → bar / progress
Sequence of events (visits, claims, interventions) → timeline
```

Avoid decorative charts.

Avoid charts merely because the dashboard feels empty.

Avoid donut charts unless the proportion itself matters.

Every chart plotting a health metric must make the data's source and time range legible — a trend line with no dates and no provenance is not trustworthy in this product.

---

# 23. METRICS

Metrics should tell a story.

Do not create a row of six cards containing:

```text
TOTAL
VISITS
CLAIMS
ACTIVE
STREAK
SCORE
```

unless those metrics genuinely represent what the user came to understand.

Prefer:

```text
Primary outcome
Current value
Change
Context
```

For example:

```text
Resting heart rate

62 bpm

↓ 4 from last month, consistent with increased cardio activity
```

The metric should answer:

> So what?

not just report a number stripped of meaning.

---

# 24. MAPS

Maps are not part of PHIRE's core workflow and should not be introduced by default.

If a future feature genuinely requires geography (e.g. locating in-network providers), a map is allowed only when it provides:

- clear legend
- meaningful markers
- useful interaction
- accessible alternatives
- contextual data

A map should never become a screenshot with pins sprinkled on it, and never a substitute for a list a user could actually act on.

---

# 25. ICONOGRAPHY

Use one coherent icon family.

Icons should clarify meaning.

They should not decorate every line of content, and they should never imply clinical severity (no ambulance icons, no heart-attack pictograms) beyond what the underlying data actually supports.

### Important rule

Do not automatically use Lucide simply because it is installed.

The icon set must visually fit the product.

If Lucide is used, customize its:

- stroke width
- size
- alignment
- color

consistently.

Do not combine multiple icon families casually.

---

# 26. EMOJI

Emoji are not interface decoration.

Do not use emoji:

- beside every heading
- inside buttons
- as fake illustrations
- as navigation icons
- as status indicators
- as a substitute for clinical nuance ("🎉 great numbers!")

Emoji may appear in genuine user-generated content (e.g. a note a user writes themselves).

---

# 27. IMAGERY

Imagery must contribute meaning.

Preferred:

- real anatomy/data diagrams where they aid comprehension
- authentic charts and timelines
- typography-led composition
- documentary-style photography if used at all (never staged "patient" photos)

Avoid:

- generic smiling stock photos of "healthy people"
- fake testimonials
- AI-generated people pretending to be patients or clinicians
- random abstract illustrations
- generic 3D blobs
- stethoscope/DNA-helix/heartbeat-line clichés used as decoration

If real imagery is unavailable, use typography, diagrams, or data instead of fake authenticity.

---

# 28. MOTION LANGUAGE

Motion should make the product feel physical and calm.

The motion language is:

**quick, quiet, precise.**

Never:

**bouncy, floaty, theatrical**, and never anything that could read as an alert or alarm when the underlying content is routine.

### Timing

```text
Instant feedback       100–140ms
Micro interaction      140–180ms
Standard transition    180–240ms
Panel / drawer         240–320ms
Large transition       320–450ms
```

Do not make ordinary UI interactions take 600ms.

---

# 29. MOTION PRINCIPLES

Animate:

- state changes
- navigation
- expansion
- selection
- confirmation
- meaningful data transitions
- spatial movement

Do not animate:

- everything entering the viewport
- decorative blobs
- backgrounds
- random icons
- entire pages without reason
- every card on initial load
- a flagged or out-of-range value with pulsing/attention-grabbing motion — surface it clearly through layout and language instead, never through motion designed to alarm

### Forbidden default

Do not generate:

```text
opacity: 0
transform: translateY(20px)

then stagger every element
```

as the automatic page-entry animation.

This is one of the strongest AI-generated UI fingerprints.

---

# 30. MICRO-INTERACTIONS

The product should respond to the user's actions.

Examples:

- button presses subtly compress
- selected rows become visually distinct
- navigation changes state immediately
- filters update predictably
- saved data produces confirmation
- destructive actions require deliberate confirmation
- drawers preserve the user's context
- expanded content (e.g. a claim's evidence) transitions without disorientation

The rule:

> **User action → understandable response.**

Do not animate merely because animation is available.

---

# 31. LOADING STATES

Never show a blank screen when content is loading — especially not while a local LLM is generating a response, which can take longer than a typical API call.

Use:

- skeletons for predictable structures
- progress indicators when actual progress exists
- optimistic updates where safe
- contextual loading messages for expensive operations (e.g. "Reviewing your recent labs and visit notes…" rather than a bare spinner)

Skeletons should resemble the final content structure.

Do not use skeletons as decorative shimmer animations.

---

# 32. EMPTY STATES

Every meaningful empty state must explain:

1. what is empty
2. why it is empty
3. what the user can do next

Example:

```text
No records yet

Upload a visit summary, lab report, or note and PHIRE
will start building your timeline.

[ Upload a record ]
```

Do not use:

```text
Nothing here yet ✨
```

unless the product context genuinely warrants that voice — it generally doesn't here.

---

# 33. ERROR STATES

Errors should be specific and actionable.

Bad:

```text
Something went wrong.
```

Better:

```text
We couldn't process this record.

The file may be corrupted or in an unsupported format. Try
re-uploading it, or add the details manually.

[ Retry ]
```

Never hide meaningful failures behind vague language.

Never blame the user.

For anything touching extracted or inferred health data, an error must be honest about *what* failed — parsing, extraction, verification — not just that something went wrong, since the user needs to know whether to trust what's already on screen.

---

# 34. SUCCESS STATES

Success should be immediate and proportional.

Use:

- inline confirmation
- toast
- state transition
- updated record

Do not create a giant celebratory animation for every successful operation.

Uploading a lab report or logging a meal does not need fireworks.

---

# 35. AI INTERACTION

AI is not PHIRE's visual identity — evidence-attributed reasoning is the product, and the interface must make that reasoning legible, not decorate it.

Do not create:

- floating AI orbs
- glowing chat bubbles
- sparkle buttons everywhere
- generic "Ask AI" interfaces detached from the user's actual record
- AI avatars or personas
- typing-dots or "thinking" animation used as spectacle rather than honest status

Prefer:

```text
User question / task
    ↓
Retrieved evidence (from the user's own records)
    ↓
Generated answer or claim
    ↓
Attribution (which record, which visit, which value)
    ↓
User judgment
    ↓
Action (save, dismiss, ask a follow-up)
```

The human remains in control.

Every AI-generated claim shown to the user must communicate:

- what was generated or concluded
- what evidence it's grounded in, and where that evidence came from
- confidence, expressed honestly (e.g. "based on 2 of your last 3 visits" beats a bare "87%")
- what the user can do next (verify, dismiss, ask why)

Never imply certainty the system does not have. Never present an inference as a fact from the record. Never let a claim appear on screen without a visible path back to its source, rendered in `--evidence` (§05) so attribution is recognizable at a glance — this is the one non-negotiable rule in this document, because it is the product's core trust mechanism, not a UI nicety.

Always keep visible, in whatever restrained form fits the screen, that PHIRE is a decision-support tool — not a diagnosis, not a substitute for a clinician, not for emergencies. This does not need to be a scary banner; it needs to be honestly present.

---

# 36. COPY

Interface copy must sound like a product used by someone thinking carefully about their own health, not a wellness-app growth team.

Avoid AI marketing language:

- empower
- transform
- revolutionize
- unlock
- elevate
- seamless
- cutting-edge
- next-generation
- intelligent solutions
- harness
- reimagine
- optimize your health journey

Avoid:

> It's not X. It's Y.

Avoid fake philosophical copy.

Avoid alarmist copy and avoid falsely reassuring copy — both are dishonest about what the system actually knows.

Prefer concrete, calibrated language.

Bad:

> Unlock powerful insights into your health journey.

Good:

> Your resting heart rate has trended down over the last 3 months.

---

# 37. NAVIGATION LANGUAGE

Navigation labels should describe the user's destination in plain terms.

Prefer:

```text
Timeline
Records
Claims & Evidence
Insights
Fitness & Nutrition
Reports
Settings
```

Avoid:

```text
Insights Hub
Impact Intelligence
Command Center
Mission Control
AI Workspace
Health OS
```

unless those are genuinely meaningful, load-bearing concepts in the product — none currently are.

---

# 38. RESPONSIVE DESIGN

Mobile is not a compressed desktop.

Design each breakpoint around the user's task.

### Desktop

Optimize for:

- parallel information (timeline + evidence panel)
- tables
- contextual panels
- navigation

### Tablet

Optimize for:

- reflow
- reduced density
- collapsible secondary information

### Mobile

Optimize for:

- one primary task (e.g. logging a meal, checking today's summary)
- progressive disclosure
- readable content
- thumb-friendly controls

Do not simply stack every desktop card vertically.

---

# 39. ACCESSIBILITY

Accessibility is part of the visual system, and it is not optional in a health product — some users interacting with their own health data will have disabilities that make this doubly true.

Required:

- semantic HTML
- keyboard navigation
- visible focus states
- accessible labels
- appropriate contrast
- appropriate touch targets
- screen-reader names
- reduced-motion support
- validation that does not rely solely on color
- health status conveyed by more than color alone (see §05)

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

Never make animation necessary for understanding.

---

# 40. RESPONSIVE TYPOGRAPHY

Typography must remain readable.

Do not shrink body text excessively on mobile.

Do not force large headings to remain on one line.

Prefer natural wrapping.

Avoid horizontal scrolling unless the content genuinely requires it, such as a complex lab panel or claims table.

---

# 41. DESIGN TOKENS

All visual decisions must flow through tokens.

Do not scatter raw values throughout components.

Centralize:

- colors
- typography
- spacing
- radius
- shadows
- motion
- breakpoints

If a value is used repeatedly, it belongs in the design system.

---

# 42. COMPONENT SYSTEM

Recommended structure:

```text
components/
├── ui/
│   ├── Button
│   ├── Input
│   ├── Select
│   ├── Dialog
│   ├── Popover
│   └── ...
│
├── layout/
│   ├── AppShell
│   ├── Sidebar
│   ├── Header
│   └── PageHeader
│
├── data/
│   ├── DataTable
│   ├── Metric
│   ├── Chart
│   ├── Timeline
│   └── FilterBar
│
├── feedback/
│   ├── LoadingState
│   ├── EmptyState
│   ├── ErrorState
│   └── Toast
│
└── domain/
    ├── ClaimCard          (a generated claim + its evidence + attribution)
    ├── EvidenceReference  (a citation back to a source record)
    ├── RecordTimeline
    └── ...
```

Do not create abstractions simply for the sake of abstraction.

Do not create duplicate versions of the same component.

---

# 43. COMPONENT LIBRARIES

Component libraries may be used.

They are implementation infrastructure, not design direction.

If using shadcn/ui:

- customize tokens
- customize typography
- customize radius
- customize states
- customize spacing
- customize shadows
- customize component composition

Never ship default shadcn styling as the finished product.

The library provides primitives.

**The product owns the visual identity.**

---

# 44. BENTO GRIDS

Bento layouts are not prohibited.

They are prohibited as a reflex.

Use a bento composition only when different information types genuinely require different spatial weights (e.g. a dominant primary trend beside smaller supporting metrics).

Do not make:

```text
large card
small card
small card
large card
```

merely because it looks trendy.

---

# 45. GRADIENTS

Gradients are not part of the default visual language.

A gradient may be introduced only when it has a clear purpose:

- image treatment
- atmospheric transition
- data visualization
- spatial layering
- semantic emphasis

Never use gradients merely to make a flat section "premium".

No default purple gradient.

No default blue-purple gradient.

No neon gradient.

---

# 46. BACKGROUNDS

Backgrounds should generally be quiet.

Do not use:

- dot grids
- radial orbs
- floating blobs
- random geometric decorations
- animated particles
- noise textures
- DNA-helix or heartbeat-line motifs used decoratively

unless they have a clear relationship to the product's content.

The default background is:

**warm, quiet, textured through typography and layout rather than decoration.**

---

# 47. DECORATIVE ELEMENTS

Every decorative element must pass this test:

> If removed, does the user lose meaning, orientation, hierarchy, or emotional context?

If no:

**remove it.**

---

# 48. DOMAIN MODEL

Unlike a hackathon problem statement received on day one, PHIRE's domain is known. Derive every screen from these five questions, answered concretely:

### Users

The person whose health data this is — tracking their own timeline, fitness, and nutrition, and reasoning about it with AI support grounded in their own records. (Not, at this stage, a clinician-facing product.)

### Entities

Patient/timeline record, source document (lab report, visit note, upload), extracted claim, supporting evidence, metric (vitals, labs, fitness, nutrition), trend, recommendation, chat/query session.

### Actions

Upload or connect a record, browse the timeline, ask a question about their health history, review a generated claim and its evidence, log fitness/nutrition data, review a recommendation, verify or dismiss a claim.

### Decisions

What questions to bring to a doctor, whether a trend is worth acting on, whether to trust or challenge an AI-generated claim, what fitness/nutrition change to try next.

### Outcomes

Better-informed conversations with real clinicians, earlier awareness of meaningful trends, sustained fitness/nutrition habits — never a diagnosis, never an emergency decision.

The frontend should emerge from these five answers, not from what looks good in a component gallery.

---

# 49. FEATURE-TO-UI TRANSLATION

When a new feature or screen is proposed:

```text
FEATURE
   ↓
WHICH USER TASK (from §48)
   ↓
CORE WORKFLOW
   ↓
ENTITIES INVOLVED
   ↓
ACTIONS
   ↓
DECISIONS SUPPORTED
   ↓
OUTCOMES
   ↓
UI
```

Never start with:

> "What dashboard should we build?"

Start with:

> "What does the user need to understand or decide, and what evidence does that require showing?"

---

# 50. SCREEN PRIORITY

Every new screen must have a primary job.

Before creating a page, define:

```text
User:
<who>

Goal:
<what they need>

Primary action:
<what they do>

Primary information:
<what they need to understand, and what evidence backs it>

Success:
<what changes after the task>
```

If this cannot be answered, the screen is not ready to design.

---

# 51. DASHBOARD RULE

A dashboard must answer:

1. What is happening with my health/fitness/nutrition right now?
2. What changed recently?
3. What's worth my attention or a conversation with a clinician?
4. What should I look at or log next?

If a dashboard cannot answer these questions, it is probably a collection of widgets rather than a useful summary — and in a health product, a widget collection with no clear "so what" is actively unhelpful, not just weak design.

---

# 52. INFORMATION HIERARCHY

Every screen must have:

```text
PRIMARY
SECONDARY
TERTIARY
```

Never make every component equally visually important.

Visual hierarchy comes from:

- position
- scale
- contrast
- whitespace
- typography
- density

not from adding more colors, and never from stoplight-coding a health value to fake urgency (§05).

---

# 53. DATA DENSITY

Timeline, records, and evidence screens may be dense.

Premium does not mean empty.

A useful screen may contain:

- tables
- filters
- timelines
- metadata
- charts
- evidence citations
- actions

The goal is **clarity at density**.

Do not remove useful clinical/personal context merely to make screenshots prettier.

---

# 54. REALISM

Never fabricate product credibility.

Do not create:

- fake testimonials
- fake clinical endorsements
- fake partner/certification logos
- fake impact numbers
- fake user activity
- fake patients or health records
- fake quotes

If demo data is necessary, clearly treat it as demo data internally, and never present a synthetic claim as if it came from a real evidence pipeline.

The product should demonstrate capability, not manufacture legitimacy — this matters more here than in most products, because false legitimacy in a health tool is a safety problem, not just a credibility one.

---

# 55. INTERACTION STATES

Every interactive component should consider:

```text
default
hover
focus
active
selected
disabled
loading
success
error
```

Not every component requires every state visually, but the interaction model must be complete.

---

# 56. FOCUS STATES

Focus must be visible.

Do not remove browser focus indicators without replacing them with a stronger accessible treatment.

Keyboard users must be able to understand where they are.

---

# 57. TOUCH

Touch targets must be comfortable.

Do not create tiny controls merely because the desktop design has enough space.

Avoid dense icon-only controls on mobile unless their meaning is universally clear and accessible.

---

# 58. ICON + TEXT

When an action is important, prefer:

```text
[ icon ] Action
```

over unexplained icon-only controls.

Icon-only controls require:

- recognizable icon
- accessible label
- tooltip where useful

Do not make users decipher a collection of mystery symbols, especially not for actions that touch their own health data.

---

# 59. TOOLTIP RULE

Tooltips explain unfamiliar controls or terms (e.g. a lab abbreviation).

They must not contain information necessary to understand the page, and they must never be the only place evidence or attribution for an AI claim is shown — that belongs in the interface itself (§35).

Important information belongs in the interface itself.

---

# 60. MODALS

Use modals sparingly.

Prefer:

- inline editing
- drawers
- dedicated pages

when the task is complex.

A modal is appropriate for:

- confirmation
- short focused action
- temporary contextual task

Do not put entire workflows inside tiny dialogs.

---

# 61. DRAWERS

Drawers are useful when the user needs contextual detail without losing their current location — this is the primary pattern for viewing a claim's evidence.

Examples:

```text
Timeline
   ↓
Claim detail drawer (evidence, source record, confidence)
```

The drawer should preserve context.

Do not turn the drawer into a full application hidden inside a panel.

---

# 62. NOTIFICATIONS

Notifications must be:

- relevant
- actionable
- dismissible where appropriate
- understandable
- calibrated — never alarmist about health data the system is not qualified to triage

Do not create notification spam.

Do not use toast notifications for information the user needs to act on later — a new claim worth reviewing belongs in the timeline, not a toast that disappears.

---

# 63. PREMIUM QUALITY

Premium does not mean:

```text
more gradients
more blur
more shadows
more animation
more rounded corners
more whitespace
more 3D
more effects
```

Premium means:

```text
better typography
better proportions
better hierarchy
better content
better states
better responsiveness
better accessibility
better interaction
better consistency
better restraint
better-attributed claims
```

---

# 64. THE HUMAN TOUCH

The product should contain at least a few details that feel authored rather than algorithmically assembled.

Examples:

- a carefully written empty state for someone with no records yet
- a plain-language narrative summary alongside a chart, not just the chart
- thoughtful, calibrated data labels (§36)
- a considered transition into a claim's evidence
- unusually good information hierarchy on the timeline
- deliberate, honest handling of uncertainty rather than hiding it

Do not manufacture "quirkiness".

Specificity beats novelty, and in a health product, honesty beats both.

---

# 65. AGENT OPERATING RULES

AI coding agents MUST follow this sequence before frontend work:

### Step 1

Read `DESIGN.md`.

### Step 2

Inspect the existing component system.

### Step 3

Inspect existing tokens.

### Step 4

Identify the user's task and screen purpose (§48–§50).

### Step 5

Reuse existing patterns.

### Step 6

Implement the smallest coherent design solution.

### Step 7

Check every relevant state.

### Step 8

Check responsive behavior.

### Step 9

Check accessibility.

### Step 10

For any screen showing an AI-generated claim, recommendation, or trend, verify evidence/attribution is visible per §35.

### Step 11

Perform the Anti-Slop Review below.

---

# 66. AGENT PROHIBITIONS

Agents MUST NOT introduce:

- a new font
- a new color
- a new radius
- a new shadow style
- a new icon family
- a new component library
- a new animation language
- a gradient
- glassmorphism
- decorative background effects
- decorative 3D
- generic AI visual motifs
- a health claim with no visible path back to its source evidence

without an explicit product/design reason.

Agents MUST NOT rewrite working UI merely to make it look different.

Agents MUST NOT replace existing design decisions with their own preferences.

Cross-folder changes that affect another owner's contract (per the root `CLAUDE.md`) are a heads-up moment, not a silent change — this applies to the `frontend/`/`backend/`/`ml/` boundary as much as to design decisions.

---

# 67. ONE-OFF PATTERN RULE

Before introducing a new visual pattern:

> **Does this pattern need to exist more than once?**

If yes:

Create a reusable primitive or extend an existing one.

If no:

Keep it local unless it represents a meaningful domain concept.

This prevents visual fragmentation.

---

# 68. DESIGN CHANGE RULE

If an agent believes the design system itself needs to change:

It must identify:

```text
Current rule:
<existing rule>

Problem:
<why it fails>

Proposed change:
<new rule>

Impact:
<what changes>
```

Do not silently alter the design system.

---

# 69. ANTI-SLOP REVIEW

Before delivering any frontend work, perform this review.

## A. Visual

- [ ] Does the interface look intentionally designed?
- [ ] Does it resemble a generic AI dashboard?
- [ ] Are cards being overused?
- [ ] Are rounded corners being used without purpose?
- [ ] Are shadows being used merely for polish?
- [ ] Is there unnecessary visual decoration?
- [ ] Is the hierarchy obvious?

## B. Color

- [ ] Is the warm neutral foundation preserved?
- [ ] Is oxide used intentionally?
- [ ] Are semantic colors meaningful, and never used to imply a diagnosis (§05)?
- [ ] Is `--evidence` used only for citations/attribution, never as a general second accent (§05)?
- [ ] Is there any unnecessary gradient?
- [ ] Is there any neon color?
- [ ] Is color being used to compensate for weak hierarchy?

## C. Typography

- [ ] Is IBM Plex Sans used consistently?
- [ ] Is Newsreader used only where it adds meaning?
- [ ] Is typography doing the work of hierarchy?
- [ ] Is there unnecessary uppercase text?
- [ ] Are random words highlighted for decoration?

## D. Components

- [ ] Are existing components reused?
- [ ] Are new components actually necessary?
- [ ] Are component states complete?
- [ ] Does the interface look like untouched shadcn?
- [ ] Are cards used only where appropriate?

## E. Motion

- [ ] Does animation communicate something?
- [ ] Are transitions appropriately fast?
- [ ] Is anything moving merely for spectacle?
- [ ] Has the generic staggered fade-up pattern been avoided?
- [ ] Does reduced-motion work?

## F. Content

- [ ] Is the language concrete?
- [ ] Is there any AI marketing language?
- [ ] Is there fake credibility?
- [ ] Are labels understandable?
- [ ] Does the content reflect the user's actual task?
- [ ] Is copy free of both alarmism and false reassurance?

## G. Product

- [ ] Is the primary user goal obvious?
- [ ] Is the primary action obvious?
- [ ] Are loading states handled?
- [ ] Are empty states handled?
- [ ] Are errors actionable?
- [ ] Is success communicated?
- [ ] Is responsive behavior intentional?

## H. Trust & Safety

- [ ] Does every AI-generated claim show its evidence and source?
- [ ] Is confidence expressed honestly, not just as a bare percentage?
- [ ] Is it clear PHIRE is decision support, not diagnosis?
- [ ] Would a person reading this about their own health feel informed, not alarmed or falsely reassured?

## I. Humanity

Ask:

> **Could a designer explain why every major visual decision exists?**

If not, redesign it.

---

# 70. THE SCREENSHOT TEST

Before finalizing a major screen:

Hide the browser chrome.

Look at the interface as a screenshot.

Ask:

> Does this look like a real product?

Then ask:

> Could I identify the product's visual identity if the logo were removed?

Then ask:

> Could someone reasonably accuse this of being generated from a generic AI prompt?

Then ask:

> If this screen shows a health claim, is it obvious where that claim came from?

If the answer to the third question is yes, or the fourth is no:

**do not ship it.**

---

# 71. THE FIVE-SECOND TEST

A first-time user should understand within approximately five seconds:

1. where they are
2. what this screen is about
3. what matters most
4. what they can do next

If the user must decode the visual design first, the design has failed.

---

# 72. THE REMOVAL TEST

For every decorative element:

Remove it temporarily.

If the interface becomes:

- clearer
- faster
- calmer

without losing meaning:

**keep it removed.**

If removing it causes:

- hierarchy loss
- orientation loss
- context loss
- emotional loss
- loss of evidence/attribution

then it may belong.

---

# 73. THE "WHY" TEST

Every major design choice should survive this sentence:

> "We did this because..."

Examples:

> We use warm canvas because it creates a calmer reading environment for someone reviewing their own health data.

> We use oxide for primary actions because it creates a restrained, distinctive interaction color.

> We use Newsreader for narrative summaries because those moments are interpretive rather than clinical.

> We use tables for lab panels because users need to scan and compare values across visits.

> We never color-code a symptom red/yellow/green because that would imply a clinical judgment the system isn't making.

> We show a citation on every generated claim because attribution is how the user decides whether to trust it.

> We give citations their own accent color, distinct from primary actions, because attribution needs to be recognizable at a glance, not just present in the markup.

If the sentence cannot be completed honestly:

**remove the decision.**

---

# 74. FINAL QUALITY BAR

The final frontend should feel:

### At first glance

Distinctive.

### After five seconds

Understandable.

### After five minutes

Efficient.

### After repeated use

Comfortable.

### Under stress (a concerning result, an ambiguous trend)

Reliable, calm, and honest about what it does and doesn't know.

That is the standard.

---

# 75. FINAL RULE

## DO NOT DESIGN FOR THE SCREENSHOT.

Design for the person reading about their own health.

The screenshot should look good because the product is trustworthy.

Not the other way around.

---

# DESIGN MANTRA

```text
Purpose before decoration.

Hierarchy before aesthetics.

Typography before effects.

Evidence before claims.

Content before components.

Interaction before animation.

Clarity before novelty.

Specificity before trends.

Restraint before spectacle.

Honesty before confidence.

Human needs before AI defaults.
```

**If the interface feels impressive but the reason for the impression is unclear, it is not finished. If a claim feels trustworthy but its evidence is unclear, it is not finished either.**
