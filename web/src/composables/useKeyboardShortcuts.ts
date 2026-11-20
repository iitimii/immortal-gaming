import { computed, getCurrentScope, onScopeDispose, readonly, ref, shallowRef } from 'vue'

/**
 * Central keyboard shortcut registry.
 *
 * - Shortcuts are declared as data (`KeyboardShortcut`) and registered with `registerShortcuts()`
 *   or `useKeyboardShortcuts().register()`; the help overlay renders straight from the registry.
 * - A single window `keydown` listener (installed once by the app shell via
 *   `installKeyboardShortcuts()`) dispatches to the first matching, enabled shortcut.
 * - Events are ignored while typing, when a browser modifier (Ctrl/Meta/Alt) is held, when
 *   another handler already called `preventDefault()`, and (for `scope: 'game'`) outside the
 *   game scene.
 */

/** `game` shortcuts only fire while the game scene is active; `global` ones fire everywhere. */
export type ShortcutScope = 'game' | 'global'

export interface ShortcutContext {
  /** A third-party (Naive UI) modal or drawer was open when the key went down; it owns Escape. */
  modalOpen: boolean
}

export interface KeyboardShortcut {
  id: string
  /** `KeyboardEvent.key` values that trigger the shortcut; single letters match case-insensitively. */
  keys: string[]
  /** Keycaps shown in the help overlay (defaults to `keys`); `shortcuts.keys.<name>` is used when defined. */
  displayKeys?: string[]
  labelKey: string
  groupKey: string
  /** Return `false` to mark the event as not handled and let later shortcuts try it. */
  handler: (event: KeyboardEvent, context: ShortcutContext) => void | boolean
  enabled?: (context: ShortcutContext) => boolean
  /** Defaults to `game`. */
  scope?: ShortcutScope
  /** Fire even when focus is inside an input, textarea, select or contenteditable element. */
  allowInInputs?: boolean
  /** Fire on auto-repeated keydown events (key held down). */
  allowRepeat?: boolean
  /** Defaults to true; hidden shortcuts still dispatch but are not listed in the help overlay. */
  showInHelp?: boolean
}

export interface ShortcutHelpGroup {
  groupKey: string
  shortcuts: KeyboardShortcut[]
}

export interface KeyboardShortcutListenerOptions {
  /** Whether game-scoped shortcuts may fire (game scene active and controls not blocked). */
  isGameActive: () => boolean
}

const registry = shallowRef<KeyboardShortcut[]>([])
const helpVisible = ref(false)

const MODAL_SELECTOR = '.n-modal-container .n-modal, .n-drawer-container .n-drawer'
const CONTENT_EDITABLE_SELECTOR = '[contenteditable]:not([contenteditable="false"])'
const ACTIVATABLE_CONTROL_SELECTOR = [
  'button',
  'a[href]',
  'summary',
  'input',
  '[role="button"]',
  '[role="checkbox"]',
  '[role="switch"]',
  '[role="radio"]',
  '[role="tab"]',
  '[role="option"]',
  '[role="menuitem"]',
].join(', ')

function normalizeKey(key: string): string {
  if (key === 'Esc') return 'Escape'
  if (key === 'Spacebar') return ' '
  return key.length === 1 ? key.toLowerCase() : key
}

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  return target.isContentEditable === true || target.closest(CONTENT_EDITABLE_SELECTOR) !== null
}

/** Ctrl/Meta/Alt combinations belong to the browser or OS; Shift is allowed (e.g. `?`, `+`). */
export function hasBrowserModifier(event: KeyboardEvent): boolean {
  return event.ctrlKey || event.metaKey || event.altKey
}

function isActivationKeyOnControl(key: string, target: EventTarget | null): boolean {
  if (key !== ' ' && key !== 'Enter') return false
  return target instanceof Element && target.closest(ACTIVATABLE_CONTROL_SELECTOR) !== null
}

export function isThirdPartyModalOpen(): boolean {
  return typeof document !== 'undefined' && document.querySelector(MODAL_SELECTOR) !== null
}

export function registerShortcuts(shortcuts: KeyboardShortcut[]): () => void {
  const ids = new Set(shortcuts.map(shortcut => shortcut.id))
  registry.value = [...registry.value.filter(shortcut => !ids.has(shortcut.id)), ...shortcuts]

  return () => {
    registry.value = registry.value.filter(shortcut => !shortcuts.includes(shortcut))
  }
}

export function getRegisteredShortcuts(): readonly KeyboardShortcut[] {
  return registry.value
}

export function openShortcutHelp() {
  helpVisible.value = true
}

export function closeShortcutHelp() {
  helpVisible.value = false
}

export function toggleShortcutHelp() {
  helpVisible.value = !helpVisible.value
}

// Naive UI modals close themselves on Escape from a document listener, which runs (and unmounts
// the modal) before our window listener. A capture-phase probe records whether a modal was open
// when the key went down so the Escape shortcut does not also act on the layer underneath.
let probedEvent: Event | null = null
let probedModalOpen = false

function probeKeydown(event: KeyboardEvent) {
  probedEvent = event
  probedModalOpen = isThirdPartyModalOpen()
}

/** Dispatch a keydown event to the registry. Returns true when a shortcut handled it. */
export function dispatchShortcut(event: KeyboardEvent, options: KeyboardShortcutListenerOptions): boolean {
  if (event.defaultPrevented || event.isComposing) return false
  if (hasBrowserModifier(event)) return false

  const key = normalizeKey(event.key)
  const typing = isTypingTarget(event.target)
  const activationOnControl = isActivationKeyOnControl(key, event.target)
  const context: ShortcutContext = {
    modalOpen: probedEvent === event ? probedModalOpen : isThirdPartyModalOpen(),
  }

  for (const shortcut of registry.value) {
    if (!shortcut.keys.some(candidate => normalizeKey(candidate) === key)) continue
    if ((shortcut.scope ?? 'game') === 'game' && !options.isGameActive()) continue
    if (typing && !shortcut.allowInInputs) continue
    if (activationOnControl) continue
    if (event.repeat && !shortcut.allowRepeat) continue
    if (shortcut.enabled && !shortcut.enabled(context)) continue
    if (shortcut.handler(event, context) === false) continue

    event.preventDefault()
    return true
  }

  return false
}

const helpCloseShortcut: KeyboardShortcut = {
  id: 'shortcuts.close-help',
  keys: ['Escape', '?'],
  labelKey: 'shortcuts.actions.close_help',
  groupKey: 'shortcuts.groups.general',
  scope: 'global',
  allowInInputs: true,
  showInHelp: false,
  enabled: () => helpVisible.value,
  handler: () => closeShortcutHelp(),
}

/**
 * Install the single window listener. Call once from the app shell; the listener is removed when
 * the calling scope is disposed (or when the returned cleanup is called).
 */
export function installKeyboardShortcuts(options: KeyboardShortcutListenerOptions): () => void {
  const unregisterHelpClose = registerShortcuts([helpCloseShortcut])
  const onKeydown = (event: KeyboardEvent) => {
    dispatchShortcut(event, options)
  }

  window.addEventListener('keydown', probeKeydown, true)
  window.addEventListener('keydown', onKeydown)

  let disposed = false
  const cleanup = () => {
    if (disposed) return
    disposed = true
    window.removeEventListener('keydown', probeKeydown, true)
    window.removeEventListener('keydown', onKeydown)
    unregisterHelpClose()
  }

  if (getCurrentScope()) {
    onScopeDispose(cleanup)
  }

  return cleanup
}

export function useKeyboardShortcuts() {
  const helpGroups = computed<ShortcutHelpGroup[]>(() => {
    const groups = new Map<string, KeyboardShortcut[]>()
    for (const shortcut of registry.value) {
      if (shortcut.showInHelp === false) continue
      const group = groups.get(shortcut.groupKey)
      if (group) {
        group.push(shortcut)
      } else {
        groups.set(shortcut.groupKey, [shortcut])
      }
    }
    return Array.from(groups, ([groupKey, shortcuts]) => ({ groupKey, shortcuts }))
  })

  /** Register shortcuts for the lifetime of the calling scope (component or effect scope). */
  function register(shortcuts: KeyboardShortcut[]): () => void {
    const unregister = registerShortcuts(shortcuts)
    if (getCurrentScope()) {
      onScopeDispose(unregister)
    }
    return unregister
  }

  return {
    shortcuts: computed(() => registry.value),
    helpGroups,
    helpVisible: readonly(helpVisible),
    register,
    openHelp: openShortcutHelp,
    closeHelp: closeShortcutHelp,
    toggleHelp: toggleShortcutHelp,
  }
}
