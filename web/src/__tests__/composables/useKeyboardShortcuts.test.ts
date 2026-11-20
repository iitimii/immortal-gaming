import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import {
  closeShortcutHelp,
  getRegisteredShortcuts,
  installKeyboardShortcuts,
  openShortcutHelp,
  useKeyboardShortcuts,
  type KeyboardShortcut,
} from '@/composables/useKeyboardShortcuts'

function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = window) {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
  target.dispatchEvent(event)
  return event
}

function shortcut(overrides: Partial<KeyboardShortcut> = {}): KeyboardShortcut {
  return {
    id: 'test.shortcut',
    keys: ['k'],
    labelKey: 'test.label',
    groupKey: 'test.group',
    handler: vi.fn(),
    ...overrides,
  }
}

let wrapper: VueWrapper | null = null
const gameActive = { value: true }

function mountHost(shortcuts: KeyboardShortcut[]) {
  const Host = defineComponent({
    setup() {
      installKeyboardShortcuts({ isGameActive: () => gameActive.value })
      useKeyboardShortcuts().register(shortcuts)
      return () => h('div')
    },
  })
  wrapper = mount(Host, { attachTo: document.body })
  return wrapper
}

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  gameActive.value = true
  closeShortcutHelp()
  document.body.innerHTML = ''
})

describe('useKeyboardShortcuts registry', () => {
  it('dispatches a matching key to its handler and prevents the default action', () => {
    const handler = vi.fn()
    mountHost([shortcut({ handler })])

    const event = press('k')

    expect(handler).toHaveBeenCalledTimes(1)
    expect(event.defaultPrevented).toBe(true)
  })

  it('matches single letters case-insensitively and ignores unrelated keys', () => {
    const handler = vi.fn()
    mountHost([shortcut({ handler })])

    press('K', { shiftKey: true })
    press('j')

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('falls through to the next shortcut when a handler returns false', () => {
    const first = vi.fn(() => false)
    const second = vi.fn()
    mountHost([
      shortcut({ id: 'a', handler: first }),
      shortcut({ id: 'b', handler: second }),
    ])

    press('k')

    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(1)
  })

  it('skips disabled shortcuts', () => {
    const handler = vi.fn()
    mountHost([shortcut({ handler, enabled: () => false })])

    const event = press('k')

    expect(handler).not.toHaveBeenCalled()
    expect(event.defaultPrevented).toBe(false)
  })

  it.each([
    ['input', () => document.createElement('input')],
    ['textarea', () => document.createElement('textarea')],
    ['select', () => document.createElement('select')],
    ['contenteditable', () => {
      const el = document.createElement('div')
      el.setAttribute('contenteditable', 'true')
      return el
    }],
  ])('ignores keys typed into %s elements', (_name, createElement) => {
    const handler = vi.fn()
    mountHost([shortcut({ handler })])
    const el = createElement()
    document.body.appendChild(el)

    press('k', {}, el)

    expect(handler).not.toHaveBeenCalled()
  })

  it('still dispatches allowInInputs shortcuts while typing', () => {
    const handler = vi.fn()
    mountHost([shortcut({ keys: ['Escape'], handler, allowInInputs: true })])
    const input = document.createElement('input')
    document.body.appendChild(input)

    press('Escape', {}, input)

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it.each(['ctrlKey', 'metaKey', 'altKey'] as const)('ignores browser shortcuts with %s held', (modifier) => {
    const handler = vi.fn()
    mountHost([shortcut({ handler })])

    const event = press('k', { [modifier]: true })

    expect(handler).not.toHaveBeenCalled()
    expect(event.defaultPrevented).toBe(false)
  })

  it('ignores events already handled by a component', () => {
    const handler = vi.fn()
    mountHost([shortcut({ keys: ['1'], handler })])
    const list = document.createElement('div')
    list.addEventListener('keydown', event => event.preventDefault())
    document.body.appendChild(list)

    press('1', {}, list)

    expect(handler).not.toHaveBeenCalled()
  })

  it('does not hijack Space on a focused button', () => {
    const handler = vi.fn()
    mountHost([shortcut({ keys: [' '], handler })])
    const button = document.createElement('button')
    document.body.appendChild(button)

    press(' ', {}, button)
    press(' ')

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('ignores auto-repeat unless the shortcut allows it', () => {
    const once = vi.fn()
    const repeating = vi.fn()
    mountHost([
      shortcut({ id: 'once', keys: ['a'], handler: once }),
      shortcut({ id: 'repeat', keys: ['b'], handler: repeating, allowRepeat: true }),
    ])

    press('a', { repeat: true })
    press('b', { repeat: true })

    expect(once).not.toHaveBeenCalled()
    expect(repeating).toHaveBeenCalledTimes(1)
  })

  it('only fires game-scoped shortcuts while the game is active, global ones always', () => {
    const gameHandler = vi.fn()
    const globalHandler = vi.fn()
    mountHost([
      shortcut({ id: 'game', keys: ['g'], handler: gameHandler }),
      shortcut({ id: 'global', keys: ['h'], handler: globalHandler, scope: 'global' }),
    ])
    gameActive.value = false

    press('g')
    press('h')

    expect(gameHandler).not.toHaveBeenCalled()
    expect(globalHandler).toHaveBeenCalledTimes(1)

    gameActive.value = true
    press('g')
    expect(gameHandler).toHaveBeenCalledTimes(1)
  })

  it('reports whether a Naive UI modal was open when the key went down', () => {
    const handler = vi.fn()
    mountHost([shortcut({ keys: ['Escape'], handler })])
    const container = document.createElement('div')
    container.className = 'n-modal-container'
    const modal = document.createElement('div')
    modal.className = 'n-card n-modal'
    container.appendChild(modal)
    document.body.appendChild(container)
    // Simulate Naive closing (and unmounting) the modal before our bubble listener runs.
    document.addEventListener('keydown', () => container.remove(), { once: true })

    press('Escape', {}, modal)
    press('Escape')

    expect(handler).toHaveBeenNthCalledWith(1, expect.any(KeyboardEvent), { modalOpen: true })
    expect(handler).toHaveBeenNthCalledWith(2, expect.any(KeyboardEvent), { modalOpen: false })
  })

  it('unregisters shortcuts and removes the listener when the scope is disposed', () => {
    const handler = vi.fn()
    mountHost([shortcut({ handler })])
    expect(getRegisteredShortcuts().map(s => s.id)).toContain('test.shortcut')

    wrapper?.unmount()
    wrapper = null
    press('k')

    expect(handler).not.toHaveBeenCalled()
    expect(getRegisteredShortcuts()).toHaveLength(0)
  })

  it('replaces a shortcut registered again with the same id', () => {
    const first = vi.fn()
    const second = vi.fn()
    mountHost([shortcut({ handler: first })])
    const unregister = useKeyboardShortcuts().register([shortcut({ handler: second })])

    press('k')
    unregister()

    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
  })

  it('groups help entries by groupKey in registration order and omits hidden ones', () => {
    mountHost([
      shortcut({ id: 'a', groupKey: 'g1' }),
      shortcut({ id: 'b', groupKey: 'g2' }),
      shortcut({ id: 'c', groupKey: 'g1' }),
      shortcut({ id: 'd', groupKey: 'g2', showInHelp: false }),
    ])

    const groups = useKeyboardShortcuts().helpGroups.value

    expect(groups.map(group => group.groupKey)).toEqual(['g1', 'g2'])
    expect(groups[0].shortcuts.map(s => s.id)).toEqual(['a', 'c'])
    expect(groups[1].shortcuts.map(s => s.id)).toEqual(['b'])
  })

  it('closes the help overlay with Escape or ? in any scene', () => {
    const escape = vi.fn()
    mountHost([shortcut({ keys: ['Escape'], handler: escape, scope: 'global' })])
    const { helpVisible } = useKeyboardShortcuts()
    gameActive.value = false

    openShortcutHelp()
    press('Escape')
    expect(helpVisible.value).toBe(false)
    expect(escape).not.toHaveBeenCalled()

    openShortcutHelp()
    press('?', { shiftKey: true })
    expect(helpVisible.value).toBe(false)
  })
})
