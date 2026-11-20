import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

vi.mock('@/api/modules/world', () => ({
  worldApi: { fetchDeceasedList: vi.fn(async () => []) },
}))

import WatchlistPanel from '@/components/game/panels/WatchlistPanel.vue'
import { useWatchlistStore } from '@/stores/watchlist'
import { useAvatarStore } from '@/stores/avatar'
import { useUiStore } from '@/stores/ui'
import { createTestI18n } from '../../../utils/i18n'

const i18n = createTestI18n({
  game: {
    watchlist: {
      title: 'Watchlist',
      empty: 'Nobody watched',
      unwatch: 'Unwatch {name}',
      deceased: 'Deceased',
      expand: 'Show',
      collapse: 'Hide',
    },
  },
})

function mountPanel() {
  return mount(WatchlistPanel, {
    global: {
      plugins: [i18n],
      directives: { sound: () => {} },
    },
  })
}

describe('WatchlistPanel', () => {
  beforeEach(() => {
    const avatars = useAvatarStore()
    avatars.updateAvatars([
      { id: 'a1', name: 'Alice', x: 0, y: 0, cultivation_display: 'Core Formation Early' },
      { id: 'a2', name: 'Bob', x: 0, y: 0, cultivation_display: 'Qi Refinement Late', is_dead: true },
    ])
  })

  it('shows an empty hint when nobody is watched', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('[data-testid="watchlist-count"]').text()).toBe('0')
    expect(wrapper.text()).toContain('Nobody watched')
    expect(wrapper.findAll('[data-testid="watchlist-row"]')).toHaveLength(0)
  })

  it('lists watched avatars with name, realm and a deceased mark', async () => {
    const store = useWatchlistStore()
    store.toggle('a1')
    store.toggle('a2')
    store.toggle('ghost', { name: 'Old Master', realm: 'Nascent Soul', deceased: true })
    const wrapper = mountPanel()
    await nextTick()

    const rows = wrapper.findAll('[data-testid="watchlist-row"]')
    expect(rows).toHaveLength(3)
    expect(rows[0].text()).toContain('Alice')
    expect(rows[0].text()).toContain('Core Formation Early')
    expect(rows[0].find('[data-testid="watchlist-deceased"]').exists()).toBe(false)
    expect(rows[1].text()).toContain('Bob')
    expect(rows[1].find('[data-testid="watchlist-deceased"]').exists()).toBe(true)
    expect(rows[2].text()).toContain('Old Master')
    expect(rows[2].text()).toContain('Nascent Soul')
    expect(rows[2].find('[data-testid="watchlist-deceased"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="watchlist-count"]').text()).toBe('3')
  })

  it('selects the avatar when a row is clicked', async () => {
    const store = useWatchlistStore()
    const ui = useUiStore()
    const select = vi.spyOn(ui, 'select').mockResolvedValue(undefined)
    store.toggle('a1')
    const wrapper = mountPanel()
    await nextTick()

    await wrapper.find('[data-testid="watchlist-focus"]').trigger('click')
    expect(select).toHaveBeenCalledWith('avatar', 'a1')
  })

  it('highlights the currently selected avatar', async () => {
    const store = useWatchlistStore()
    const ui = useUiStore()
    store.toggle('a1')
    ui.selectedTarget = { type: 'avatar', id: 'a1' }
    const wrapper = mountPanel()
    await nextTick()

    expect(wrapper.find('[data-testid="watchlist-row"]').classes()).toContain('is-selected')
  })

  it('unwatches from the row button', async () => {
    const store = useWatchlistStore()
    store.toggle('a1')
    store.toggle('a2')
    const wrapper = mountPanel()
    await nextTick()

    const unwatch = wrapper.findAll('[data-testid="watchlist-unwatch"]')[0]
    expect(unwatch.attributes('aria-label')).toBe('Unwatch Alice')
    await unwatch.trigger('click')

    expect(store.watchedIds).toEqual(['a2'])
    expect(wrapper.findAll('[data-testid="watchlist-row"]')).toHaveLength(1)
  })

  it('collapses and expands the list', async () => {
    const store = useWatchlistStore()
    store.toggle('a1')
    const wrapper = mountPanel()
    await nextTick()

    const toggle = wrapper.find('[data-testid="watchlist-toggle"]')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(wrapper.findAll('[data-testid="watchlist-row"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="watchlist-count"]').text()).toBe('1')

    await toggle.trigger('click')
    expect(wrapper.findAll('[data-testid="watchlist-row"]')).toHaveLength(1)
  })
})
