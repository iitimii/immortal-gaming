# Frontend Sound Effect Guide

This document standardizes how sound effects are integrated into the frontend, to keep the user experience consistent and reduce development cost.

## 1. Global Auto-Sound

We use global event delegation, which means **most standard interactive elements get sound effects automatically without any extra code**.

### How it works
`main.ts` listens for window-level `click` events. The system recognizes the following elements and plays the default click sound (`click`):
- `<button>` elements
- `<a>` elements
- Elements with `role="button"`
- Elements with the `.n-button` (Naive UI), `.btn`, or `.clickable` class

### Notes for developers
- **Default behavior**: as long as you use the standard tags or classes above, sound works automatically.
- **Avoid duplicates**: don't add manual click listeners to ordinary buttons just to play a sound.

## 2. Manual Control

When the automatic mechanism isn't enough, use the following options.

### 2.1 Disable sound (`data-no-sound`)
If a button should not make a sound (e.g. it is a button used only for display, or a child element handles the sound), add the `data-no-sound` attribute.

```html
<!-- This button makes no sound when clicked -->
<button data-no-sound>Mute Button</button>
```

### 2.2 Specific sounds (`v-sound` directive)
To play a non-default sound (cancel, confirm, open a view), use the `v-sound` directive. The global listener detects the directive and steps aside, so this does **not** cause double sounds.

Supported sound types:
- `'click'` (default, ordinary click)
- `'cancel'` (close, cancel, delete, exit)
- `'select'` (confirm, save, important choices, start game)
- `'open'` (open a new view, follow a link, view details)

Examples:

```html
<!-- Play the cancel sound -->
<button v-sound:cancel @click="close">Close</button>

<!-- Play the confirm sound -->
<button v-sound:select @click="confirm">Confirm</button>

<!-- Play the open sound -->
<div class="card" v-sound="'open'" @click="openDetail">...</div>
```

**Note**: non-standard interactive elements (such as `div` or `span` list items) **must** use `v-sound` if they need sound, because the global listener ignores them by default (unless they have the `.clickable` class).

### 2.3 Programmatic playback (`useAudio`)
For cases that can't rely on DOM events (interaction inside a canvas, keyboard events, automatically triggered feedback), call `useAudio` directly.

```typescript
import { useAudio } from '@/composables/useAudio'

// Get it in setup
const { play } = useAudio()

function handleCanvasClick() {
  // Play manually
  play('select')
}
```

## 3. Best Practices

1.  **New views**: prefer `<button>` or `.btn`; you get sound for free.
2.  **List items**: for clickable list items (such as `EntityRow`), remember to add `v-sound` or the `.clickable` class.
3.  **Close/cancel buttons**: explicitly add `v-sound:cancel` for the right audio feedback.
4.  **Important actions**: explicitly add `v-sound:select` to reinforce the sense of confirmation.
5.  **Canvas interaction**: you must call `play()` manually.

## 4. Audio Assets

All sound effects are in `web/public/sfx/`. Currently `.ogg` is supported.

- `click.ogg`: generic click (short)
- `select.ogg`: confirm/select (crisp)
- `cancel.ogg`: cancel/close (low)
- `open.ogg`: expand/navigate (rising)
