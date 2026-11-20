import { defineComponent, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { avatarApi } from '@/api'
import { useAvatarAdjustmentPanel, type AvatarAdjustmentPanelProps } from '@/composables/useAvatarAdjustmentPanel'
import { RACE_OPTIONS, useCreateAvatarPanel } from '@/composables/useCreateAvatarPanel'
import { useDeleteAvatarPanel } from '@/composables/useDeleteAvatarPanel'

const messageMock = {
  success: vi.fn(),
  error: vi.fn(),
}

const dialogMock = {
  warning: vi.fn(),
}

const { preloadAvatarTexturesMock } = vi.hoisted(() => ({
  preloadAvatarTexturesMock: vi.fn(),
}))

vi.mock('naive-ui', () => ({
  useMessage: () => messageMock,
  useDialog: () => dialogMock,
}))

vi.mock('@/components/game/composables/useTextures', () => ({
  useTextures: () => ({
    preloadAvatarTextures: preloadAvatarTexturesMock,
  }),
}))

const fetchStateMock = vi.fn()
const acceptMutationRevisionMock = vi.fn()
const avatarDirectoryRevisionMock = ref(0)
const updateAvatarsMock = vi.fn()
const removeAvatarMock = vi.fn()
const clearSelectionMock = vi.fn()
const uiStoreMock = {
  selectedTarget: null as null | { type: string; id: string },
  clearSelection: clearSelectionMock,
}
vi.mock('@/stores/world', () => ({
  useWorldStore: () => ({
    fetchState: fetchStateMock,
    acceptMutationRevision: acceptMutationRevisionMock,
    get avatarDirectoryRevision() {
      return avatarDirectoryRevisionMock.value
    },
  }),
}))
vi.mock('@/stores/ui', () => ({
  useUiStore: () => uiStoreMock,
}))
vi.mock('@/stores/avatar', () => ({
  useAvatarStore: () => ({
    updateAvatars: updateAvatarsMock,
    removeAvatar: removeAvatarMock,
  }),
}))
vi.mock('@/api', () => ({
  avatarApi: {
    fetchAvatarAdjustOptions: vi.fn(),
    updateAvatarAdjustment: vi.fn(),
    generateCustomContent: vi.fn(),
    createCustomContent: vi.fn(),
    fetchGameData: vi.fn(),
    fetchAvatarMeta: vi.fn(),
    fetchAvatarList: vi.fn(),
    createAvatar: vi.fn(),
    deleteAvatar: vi.fn(),
  },
}))

const i18n = createI18n({
  legacy: false,
  locale: 'en-US',
  messages: {
    'en-US': {
      common: {
        none: 'None',
        cancel: 'Cancel',
      },
      save_load: {
        delete: 'Delete',
      },
      realms: {
        QI_REFINEMENT: 'Qi Refinement',
        FOUNDATION_ESTABLISHMENT: 'Foundation Establishment',
        CORE_FORMATION: 'Core Formation',
        NASCENT_SOUL: 'Nascent Soul',
      },
      attributes: {
        FIRE: 'Fire',
      },
      technique_grades: {
        high: 'Upper Grade',
      },
      game: {
        info_panel: {
          popup: {
            types: {
              sword: 'Sword',
            },
          },
          avatar: {
            adjust: {
              title: 'Adjust {category}',
              current: 'Current',
              select: 'Select',
              search_placeholder: 'Search',
              load_failed: 'Failed to load',
              apply_success: 'Applied',
              apply_failed: 'Failed to apply',
              apply_personas: 'Apply Personas',
              categories: {
                technique: 'Technique',
                weapon: 'Weapon',
                auxiliary: 'Auxiliary',
                personas: 'Personas',
                goldfinger: 'Goldfinger',
              },
              custom: {
                title: 'Custom',
                unnamed: 'Unnamed',
                prompt_required: 'Please enter a prompt',
                generate_failed: 'Generation failed',
                create_failed: 'Save failed',
                create_success: 'Saved',
              },
            },
          },
        },
      },
      ui: {
        create_avatar: {
          fetch_failed: 'Failed to load',
          create_success: 'Created',
          create_failed: 'Creation failed {error}',
          relation_labels: {
            parent: 'Parent',
            child: 'Child',
            sibling: 'Sibling',
            master: 'Master',
            disciple: 'Disciple',
            lover: 'Dao Partner',
            friend: 'Friend',
            enemy: 'Enemy',
          },
        },
        delete_avatar: {
          fetch_failed: 'Failed to load',
          delete_success: 'Deleted',
          delete_failed: 'Delete failed',
          delete_confirm: 'Delete {name}?',
        },
      },
    },
  },
})

function mountComposable<T>(factory: () => T): T {
  let result!: T
  mount(defineComponent({
    setup() {
      result = factory()
      return () => null
    },
  }), {
    global: {
      plugins: [i18n],
    },
  })
  return result
}

async function settle() {
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()
}

const adjustCatalog = {
  techniques: [
    { id: '1', name: 'Fire Cloud Art', desc: 'Scorching', grade: 'high', attribute: 'FIRE' },
  ],
  weapons: [],
  auxiliaries: [],
  personas: [
    { id: '7', name: 'Steady', desc: 'Calm' },
    { id: '8', name: 'Sharp', desc: 'Decisive' },
  ],
  goldfingers: [],
}

describe('avatar panel composables', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    avatarDirectoryRevisionMock.value = 0
    uiStoreMock.selectedTarget = null
    updateAvatarsMock.mockReset()
    removeAvatarMock.mockReset()
    preloadAvatarTexturesMock.mockReset()
    preloadAvatarTexturesMock.mockResolvedValue(undefined)
    vi.mocked(avatarApi.fetchAvatarAdjustOptions).mockResolvedValue(adjustCatalog)
    vi.mocked(avatarApi.updateAvatarAdjustment).mockResolvedValue({ status: 'ok', message: 'ok' })
    vi.mocked(avatarApi.generateCustomContent).mockResolvedValue({
      status: 'ok',
      draft: {
        id: 'draft',
        category: 'technique',
        name: 'Self-made Technique',
        desc: 'Test',
        effects: {},
      },
    })
    vi.mocked(avatarApi.createCustomContent).mockResolvedValue({
      status: 'ok',
      item: { id: '9', name: 'Self-made Technique', desc: 'Test' },
    })
    vi.mocked(avatarApi.fetchGameData).mockResolvedValue({
      sects: [
        { id: 1, name: 'Azure Cloud Sect', alignment: 'GOOD', accepts_yao: true },
        { id: 2, name: 'Haoran Academy', alignment: 'GOOD', accepts_yao: false },
      ],
      races: [
        { id: 'human', label: 'Human', is_yao: false },
        { id: 'fox', label: 'Fox', is_yao: true },
      ],
      personas: [{ id: 2, name: 'Steady', desc: 'Calm', rarity: 'common' }],
      realms: ['QI_REFINEMENT', 'FOUNDATION_ESTABLISHMENT'],
      techniques: [{ id: 3, name: 'Fire Cloud Art', grade: 'high', attribute: 'FIRE', sect: null }],
      weapons: [{ id: 4, name: 'Azure Edge Sword', grade: 'high', type: 'sword' }],
      auxiliaries: [{ id: 5, name: 'Alchemy', grade: 'high' }],
      alignments: [{ value: 'GOOD', label: 'Righteous' }],
      avatar_creation: {
        age: {
          min: 16,
          max_by_realm: {
            QI_REFINEMENT: 100,
            FOUNDATION_ESTABLISHMENT: 109,
            CORE_FORMATION: 159,
            NASCENT_SOUL: 459,
          },
        },
      },
    })
    vi.mocked(avatarApi.fetchAvatarMeta).mockResolvedValue({
      human: { male: [1], female: [2] },
      fox: { male: [3], female: [4] },
    })
    vi.mocked(avatarApi.fetchAvatarList).mockResolvedValue([
      { id: 'a1', name: 'Li Qing', sect_name: 'Azure Cloud Sect', realm: 'QI_REFINEMENT', gender: 'male', age: 18 },
    ])
    vi.mocked(avatarApi.createAvatar).mockResolvedValue({
      status: 'ok',
      message: 'ok',
      avatar_id: 'new',
      avatar: {
        id: 'new',
        name: 'Li Qing',
        x: 1,
        y: 2,
        gender: 'male',
        race: 'human',
        pic_id: 1,
        realm: 'QI_REFINEMENT',
        is_dead: false,
      },
      world_revision: 42,
    })
    vi.mocked(avatarApi.deleteAvatar).mockResolvedValue({ status: 'ok', message: 'ok', removed_avatar_id: 'a1', world_revision: 43 })
    fetchStateMock.mockResolvedValue(undefined)
  })

  it('loads and applies a single avatar adjustment', async () => {
    const callbacks = { onClose: vi.fn(), onUpdated: vi.fn() }
    const props: AvatarAdjustmentPanelProps = { avatarId: 'a1', category: 'technique' }
    const panel = mountComposable(() => useAvatarAdjustmentPanel(props, callbacks))

    await settle()
    expect(panel.filteredOptions.value.map(option => option.name)).toEqual(['None', 'Fire Cloud Art'])

    await panel.handleSingleSelect(panel.filteredOptions.value[1])
    expect(avatarApi.updateAvatarAdjustment).toHaveBeenCalledWith({
      avatar_id: 'a1',
      category: 'technique',
      target_id: 1,
    })
    expect(callbacks.onUpdated).toHaveBeenCalled()
    expect(callbacks.onClose).toHaveBeenCalled()
  })

  it('syncs and applies persona selections', async () => {
    const props: AvatarAdjustmentPanelProps = {
      avatarId: 'a1',
      category: 'personas',
      currentPersonas: [{ id: '7', name: 'Steady' }],
    }
    const panel = mountComposable(() => useAvatarAdjustmentPanel(props, {
      onClose: vi.fn(),
      onUpdated: vi.fn(),
    }))

    await settle()
    panel.togglePersona(panel.filteredOptions.value[1])
    await panel.applyPersonas()

    expect(avatarApi.updateAvatarAdjustment).toHaveBeenCalledWith({
      avatar_id: 'a1',
      category: 'personas',
      persona_ids: [7, 8],
    })
  })

  it('generates and saves custom adjustment content', async () => {
    const callbacks = { onClose: vi.fn(), onUpdated: vi.fn() }
    const panel = mountComposable(() => useAvatarAdjustmentPanel(
      { avatarId: 'a1', category: 'technique' },
      callbacks,
    ))

    await settle()
    panel.customPrompt.value = 'Make a fire technique'
    await panel.generateCustomDraft()
    expect(panel.customDraft.value?.name).toBe('Self-made Technique')

    await panel.saveCustomDraft()
    expect(avatarApi.createCustomContent).toHaveBeenCalled()
    expect(avatarApi.updateAvatarAdjustment).toHaveBeenLastCalledWith({
      avatar_id: 'a1',
      category: 'technique',
      target_id: 9,
    })
  })

  it('loads create avatar metadata and submits with default alignment', async () => {
    const onCreated = vi.fn()
    const panel = mountComposable(() => useCreateAvatarPanel(onCreated))

    await settle()
    expect(panel.realmOptions.value[0]).toEqual({ label: 'Qi Refinement', value: 1 })
    expect(panel.createForm.value.level).toBe(1)
    expect(panel.createForm.value.appearance).toBe(5)

    panel.createForm.value.surname = 'Li'
    panel.createForm.value.given_name = 'Qing'
    await panel.handleCreateAvatar()

    expect(avatarApi.createAvatar).toHaveBeenCalledWith(expect.objectContaining({
      surname: 'Li',
      given_name: 'Qing',
      alignment: 'NEUTRAL',
    }))
    expect(updateAvatarsMock).toHaveBeenCalledWith([expect.objectContaining({
      id: 'new',
      name: 'Li Qing',
    })])
    expect(preloadAvatarTexturesMock).toHaveBeenCalledWith([expect.objectContaining({
      id: 'new',
      pic_id: 1,
    })])
    expect(fetchStateMock).not.toHaveBeenCalled()
    expect(acceptMutationRevisionMock).toHaveBeenCalledWith(42)
    expect(onCreated).toHaveBeenCalled()
  })

  it('uses realm-specific age limits and clamps age after lowering the realm', async () => {
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    expect(panel.ageLimits.value).toEqual({ min: 16, max: 100 })
    panel.createForm.value.level = 31
    await nextTick()
    expect(panel.ageLimits.value).toEqual({ min: 16, max: 109 })

    panel.createForm.value.age = 109
    panel.createForm.value.level = 1
    await nextTick()
    expect(panel.createForm.value.age).toBe(100)
  })

  it('filters sects that do not accept the selected yao race', async () => {
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    panel.createForm.value.sect_id = 2
    panel.createForm.value.race = 'fox'
    await nextTick()

    expect(panel.sectOptions.value).toEqual([{ label: 'Azure Cloud Sect', value: 1 }])
    expect(panel.createForm.value.sect_id).toBeUndefined()
  })

  it('does not expose hardcoded Chinese race labels in create avatar options', () => {
    const chinesePattern = /[\u4e00-\u9fff]/

    expect(RACE_OPTIONS.map(option => option.label).filter(label => chinesePattern.test(label))).toEqual([])
  })

  it('uses localized race options from game metadata', async () => {
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    expect(panel.raceOptions.value).toEqual([
      { label: 'Human', value: 'human' },
      { label: 'Fox', value: 'fox' },
    ])
  })

  it('resets selected portrait when gender changes', async () => {
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    panel.createForm.value.pic_id = 1
    panel.createForm.value.gender = 'female'
    await nextTick()

    expect(panel.createForm.value.pic_id).toBeUndefined()
  })

  it('resets selected portrait and switches library when race changes', async () => {
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    expect(panel.availableAvatars.value).toEqual([1])
    panel.createForm.value.pic_id = 1
    panel.createForm.value.race = 'fox'
    await nextTick()

    expect(panel.createForm.value.pic_id).toBeUndefined()
    expect(panel.availableAvatars.value).toEqual([3])
  })

  it('normalizes wrapped avatar metadata before switching race libraries', async () => {
    vi.mocked(avatarApi.fetchAvatarMeta).mockResolvedValueOnce({
      data: {
        human: { male: [1], female: [2] },
        fox: { male: [3, 4], female: [5] },
      },
    })
    const panel = mountComposable(() => useCreateAvatarPanel(vi.fn()))
    await settle()

    panel.createForm.value.race = 'fox'
    await nextTick()

    expect(panel.availableAvatars.value).toEqual([3, 4])
  })

  it('filters and deletes avatars after confirmation', async () => {
    const panel = mountComposable(() => useDeleteAvatarPanel(() => true))
    await settle()

    panel.avatarSearch.value = 'Li'
    expect(panel.filteredAvatars.value).toHaveLength(1)

    await panel.handleDeleteAvatar('a1', 'Li Qing')
    expect(avatarApi.deleteAvatar).toHaveBeenCalledWith('a1')
    expect(fetchStateMock).not.toHaveBeenCalled()
    expect(acceptMutationRevisionMock).toHaveBeenCalledWith(43)
    expect(panel.filteredAvatars.value).toHaveLength(0)
  })

  it('closes the confirmation dialog after a successful deletion', async () => {
    const destroy = vi.fn()
    dialogMock.warning.mockReturnValue({ destroy })
    const panel = mountComposable(() => useDeleteAvatarPanel())
    await settle()

    panel.handleDeleteAvatar('a1', 'Li Qing')
    const dialogOptions = dialogMock.warning.mock.calls[0][0]
    await dialogOptions.onPositiveClick()

    expect(destroy).toHaveBeenCalledOnce()
  })

  it('refreshes the deletion list after a remote character directory delta', async () => {
    const panel = mountComposable(() => useDeleteAvatarPanel(() => true))
    await settle()
    vi.mocked(avatarApi.fetchAvatarList).mockClear()

    avatarDirectoryRevisionMock.value += 1
    await settle()

    expect(avatarApi.fetchAvatarList).toHaveBeenCalled()
    expect(panel.filteredAvatars.value).toHaveLength(1)
  })

  it('ignores a stale list response after deleting an avatar', async () => {
    let resolveList!: (avatars: Array<{ id: string; name: string; sect_name: string; realm: string; gender: string; age: number }>) => void
    vi.mocked(avatarApi.fetchAvatarList).mockReturnValueOnce(new Promise(resolve => {
      resolveList = resolve
    }))
    const panel = mountComposable(() => useDeleteAvatarPanel(() => true))

    await panel.handleDeleteAvatar('a1', 'Li Qing')
    resolveList([{ id: 'a1', name: 'Li Qing', sect_name: 'Azure Cloud Sect', realm: 'QI_REFINEMENT', gender: 'male', age: 18 }])
    await settle()

    expect(panel.filteredAvatars.value).toHaveLength(0)
    expect(panel.isFetchingList.value).toBe(false)
  })

  it('does not delete when confirmation is cancelled', async () => {
    const panel = mountComposable(() => useDeleteAvatarPanel(() => false))
    await settle()

    await panel.handleDeleteAvatar('a1', 'Li Qing')
    expect(avatarApi.deleteAvatar).not.toHaveBeenCalled()
  })
})
