import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import AvatarDetail from '@/components/game/panels/info/AvatarDetail.vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { systemApi } from '@/api'

const entityRowSpy = vi.fn()

vi.mock('@/api', () => ({
  avatarApi: {
    setLongTermObjective: vi.fn(),
    clearLongTermObjective: vi.fn(),
  },
  systemApi: {
    pauseGame: vi.fn(),
    pauseGameAndDrain: vi.fn(),
  },
}))

const compareModalSpy = vi.fn()

vi.mock('@/components/game/panels/info/avatar-detail/AvatarCompareModal.vue', () => ({
  __esModule: true,
  default: defineComponent({
    name: 'AvatarCompareModal',
    props: ['show', 'avatarId', 'avatarName'],
    emits: ['update:show'],
    setup(props) {
      compareModalSpy(props)
      return () => h('div', { class: 'compare-modal-stub' }, props.avatarName)
    },
  }),
}))

vi.mock('@/components/game/panels/info/components/EntityRow.vue', () => ({
  default: defineComponent({
    name: 'EntityRow',
    props: ['item', 'meta', 'compact', 'detailsBelow'],
    emits: ['click'],
    setup(props) {
      entityRowSpy(props)
      return () => h('div', { class: 'entity-row-stub' }, props.item?.name || '')
    },
  }),
}))

describe('AvatarDetail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    entityRowSpy.mockClear()
    vi.mocked(systemApi.pauseGame).mockResolvedValue(undefined)
    vi.mocked(systemApi.pauseGameAndDrain).mockResolvedValue(undefined)
  })

  const i18n = createI18n({
    legacy: false,
    locale: 'en-US',
    messages: {
      'en-US': {
        game: {
          info_panel: {
            avatar: {
              empty_short: '-',
              set_objective: 'Set Objective',
              clear_objective: 'Clear Objective',
              compare: {
                entry: 'Compare',
                entry_desc: 'Compare this cultivator',
              },
              long_term_objective: 'Long-term Objective',
              short_term_objective: 'Short-term Objective',
              backstory: 'Backstory',
              fate: 'Fate',
              portrait: {
                entry: 'Change Portrait',
                preview_alt: 'Portrait Preview',
              },
              dead_with_reason: 'Dead ({reason})',
              stats: {
                realm: 'Realm',
                age: 'Age',
                origin: 'Origin',
                hp: 'HP',
                gender: 'Gender',
                race: 'Race',
                unknown_race: 'Unknown',
                alignment: 'Alignment',
                sect: 'Sect',
                rogue: 'Rogue',
                official_rank: 'Official Rank',
                sect_contribution: 'Sect Contribution',
                root: 'Root',
                luck: 'Luck',
                magic_stone: 'Spirit Stone',
                appearance: 'Appearance',
                battle_strength: 'Battle Strength',
                emotion: 'Emotion',
                canonical_realm: 'Equivalent: {value}',
              },
              sections: {
                traits: 'Traits',
                techniques_equipment: 'Arts & Gear',
                goldfinger: 'Goldfinger',
                relations: 'Relations',
                current_effects: 'Current Effects',
              },
              adjust: {
                entry: 'Adjust',
                empty_item: 'No {label}',
                categories: {
                  personas: 'Traits',
                  technique: 'Technique',
                  weapon: 'Weapon',
                  auxiliary: 'Auxiliary',
                  goldfinger: 'Goldfinger',
                },
              },
              father_short: 'Father',
              mother_short: 'Mother',
              mortal_realm: 'Mortal',
            }
          }
        },
        common: {
          none: 'None'
        },
        ui: {
          create_avatar: {
            gender_labels: {
              male: 'Male',
              female: 'Female',
            },
          },
          other: 'Other',
        },
      }
    }
  })

  const mockAvatarData = {
    id: 'avatar_1',
    name: 'Test Avatar',
    realm: 'Foundation',
    pic_id: 7,
    level: 1,
    age: 20,
    lifespan: 100,
    origin: 'Test Origin',
    hp: { cur: 100, max: 100 },
    gender: 'Male',
    alignment: 'Good',
    root: 'Gold',
    luck: 0,
    magic_stone: 0,
    appearance: 'Plain',
    base_battle_strength: 10,
    emotion: { emoji: '😀', name: 'Happy' },
    is_dead: false,
    current_effects: '',
    personas: [],
    materials: [],
    goldfinger: undefined,
    traits: [],
    items: [],
    skills: [],
    events: [],
    relations: [],
  }

  it('should render successfully', () => {
    const wrapper = mount(AvatarDetail, {
      props: {
        data: mockAvatarData as any
      },
      global: {
        plugins: [
          createPinia(),
          i18n
        ],
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        }
      }
    })

    expect(wrapper.exists()).toBe(true)
    // Check if the actions bar exists since it's not dead
    expect(wrapper.find('.actions-bar').exists()).toBe(true)
    expect(wrapper.find('.avatar-header').exists()).toBe(true)
    expect(wrapper.find('.portrait-button').exists()).toBe(true)
  })

  it('should display dead banner if avatar is dead', () => {
    const deadAvatar = { ...mockAvatarData, is_dead: true, death_info: { reason: 'Old age' } }
    const wrapper = mount(AvatarDetail, {
      props: {
        data: deadAvatar as any
      },
      global: {
        plugins: [
          createPinia(),
          i18n
        ],
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        }
      }
    })

    expect(wrapper.find('.dead-banner').exists()).toBe(true)
    expect(wrapper.find('.actions-bar').exists()).toBe(false)
    expect(wrapper.find('.compare-btn').exists()).toBe(false)
  })

  it('opens the lazily loaded compare modal from the compare action', async () => {
    compareModalSpy.mockClear()
    const wrapper = mount(AvatarDetail, {
      props: {
        data: mockAvatarData as any
      },
      global: {
        plugins: [
          createPinia(),
          i18n
        ],
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        }
      }
    })

    expect(wrapper.find('.compare-modal-stub').exists()).toBe(false)
    const button = wrapper.find('.compare-btn')
    expect(button.text()).toBe('Compare')

    await button.trigger('click')
    for (let i = 0; i < 10; i += 1) {
      await Promise.resolve()
    }
    await nextTick()

    expect(wrapper.find('.compare-modal-stub').exists()).toBe(true)
    expect(compareModalSpy).toHaveBeenLastCalledWith(expect.objectContaining({
      show: true,
      avatarId: 'avatar_1',
      avatarName: 'Test Avatar',
    }))
  })

  it('renders identity and non-stranger attitude on separate lines', () => {
    const relationAvatar = {
      ...mockAvatarData,
      relations: [
        {
          target_id: 'avatar_2',
          name: 'Qing Lan',
          relation: 'Dao Companion / Friendly',
          relation_type: 'lovers',
          identity_relations: ['lovers'],
          numeric_relation: 'friend',
          friendliness: 12,
          realm: 'Core Formation Late',
          sect: 'Lingxiao Sword Sect',
        },
        {
          target_id: 'avatar_3',
          name: 'Dan Qisha',
          relation: 'Stranger',
          relation_type: '',
          identity_relations: [],
          numeric_relation: 'stranger',
          friendliness: 0,
          realm: 'Core Formation Late',
          sect: 'Core Formation Late',
        },
      ],
    }

    const wrapper = mount(AvatarDetail, {
      props: {
        data: relationAvatar as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          StatItem: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Dao Companion')
    expect(wrapper.text()).toMatch(/Friendly \(12\)/)
    expect(wrapper.text()).not.toContain('Attitude: Stranger')
    expect(wrapper.text()).not.toContain('Identity:')
    expect(wrapper.text()).not.toContain('Attitude:')
    expect(wrapper.text()).not.toContain('Dan Qisha')
  })

  it('renders long effect sources as separate rows with segmented content', () => {
    const effectAvatar = {
      ...mockAvatarData,
      current_effects: '[Orthodoxy [Nature]] Special Ability Respiration Refinement Success Rate +15.0%; Battle Strength +20\n[Heaven and Earth Phenomenon] Respiration Experience +20',
    }

    const wrapper = mount(AvatarDetail, {
      props: {
        data: effectAvatar as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    const rows = wrapper.findAll('.effect-row')
    expect(rows).toHaveLength(2)
    expect(rows[0].find('.effect-source').text()).toBe('Orthodoxy [Nature]')
    expect(rows[0].find('.effect-content').text()).toContain('Special Ability Respiration Refinement Success Rate +15.0%')
    expect(rows[0].find('.effect-content').text()).toContain('Battle Strength +20')
    expect(rows[1].find('.effect-source').text()).toBe('Heaven and Earth Phenomenon')
  })

  it('renders goldfinger entry when present', () => {
    const wrapper = mount(AvatarDetail, {
      props: {
        data: {
          ...mockAvatarData,
          goldfinger: {
            id: '1',
            name: 'Child of Fortune',
            desc: 'Favored by fate; fortune comes seeking',
            effect_desc: 'Luck +20',
          },
        } as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Goldfinger')
    expect(wrapper.findAll('.equipment-slot-block')).toHaveLength(4)
    expect(entityRowSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        item: expect.objectContaining({
          name: 'Child of Fortune',
          desc: 'Favored by fate; fortune comes seeking',
        }),
      }),
    )
  })

  it('renders race in stats grid and opens secondary detail', async () => {
    let secondaryItem: unknown = null
    const SecondaryPopupStub = defineComponent({
      name: 'SecondaryPopup',
      props: ['item'],
      setup(props) {
        return () => {
          secondaryItem = props.item
          return h('div', { class: 'secondary-popup-stub' }, props.item?.name || '')
        }
      },
    })

    const wrapper = mount(AvatarDetail, {
      props: {
        data: {
          ...mockAvatarData,
          race: {
            id: 'fox',
            name: 'Fox Folk',
            desc: 'Fox folk are clever and cunning',
            effect_desc: 'Material gathering +1',
          },
        } as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          RelationRow: true,
          TagList: true,
          SecondaryPopup: SecondaryPopupStub,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    expect(wrapper.text()).toContain('Race')
    expect(wrapper.text()).toContain('Fox Folk')

    const raceStat = wrapper.findAll('.stat-item').find(item => item.text().includes('Race'))
    expect(raceStat).toBeTruthy()
    await raceStat!.trigger('click')
    await nextTick()

    expect(secondaryItem).toMatchObject({
      id: 'fox',
      name: 'Fox Folk',
      effect_desc: 'Material gathering +1',
    })
    expect(wrapper.text()).toContain('Fox Folk')
  })

  it('prefers cultivation alias display and shows canonical equivalent', () => {
    const wrapper = mount(AvatarDetail, {
      props: {
        data: {
          ...mockAvatarData,
          realm: 'Foundation Establishment Middle Stage',
          cultivation: {
            profile_id: 'wu',
            profile_name: 'Martial Path',
            realm_id: 'FOUNDATION_ESTABLISHMENT',
            stage_id: 'MIDDLE_STAGE',
            level: 42,
            canonical_realm_name: 'Foundation Establishment',
            canonical_stage_name: 'Middle',
            canonical_full_name: 'Foundation Establishment Middle',
            display_realm_name: 'Sinew Tempering',
            display_stage_name: 'Intermediate',
            display_full_name: 'Sinew Tempering Intermediate',
          },
        } as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        stubs: {
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    expect(wrapper.find('.avatar-realm').text()).toBe('Sinew Tempering Intermediate')
    expect(wrapper.find('.avatar-realm-canonical').text()).toContain('Foundation Establishment Middle')
    expect(wrapper.text()).toContain('Sinew Tempering Intermediate')
  })

  it('does not fall back to hardcoded Chinese when race detail is missing', () => {
    const wrapper = mount(AvatarDetail, {
      props: {
        data: {
          ...mockAvatarData,
          race: undefined,
        } as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: true,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    const raceStat = wrapper.findAll('.stat-item').find(item => item.text().includes('Race'))

    expect(raceStat).toBeTruthy()
    expect(raceStat!.text()).not.toContain('Human')
  })

  it('passes goldfinger category and current item into adjust panel when clicking edit', async () => {
    let capturedProps: Record<string, unknown> | null = null
    const AvatarAdjustPanelStub = defineComponent({
      name: 'AvatarAdjustPanel',
      props: ['avatarId', 'category', 'currentItem', 'currentPersonas'],
      setup(props) {
        capturedProps = props as unknown as Record<string, unknown>
        return () => h('div', { class: 'adjust-panel-stub' })
      },
    })

    const wrapper = mount(AvatarDetail, {
      props: {
        data: {
          ...mockAvatarData,
          goldfinger: {
            id: '1',
            name: 'Child of Fortune',
            desc: 'Blessed by fate',
            effect_desc: 'Luck +20',
          },
        } as any,
      },
      global: {
        plugins: [
          createPinia(),
          i18n,
        ],
        directives: {
          sound: () => {},
        },
        stubs: {
          StatItem: true,
          RelationRow: true,
          TagList: true,
          SecondaryPopup: true,
          AvatarAdjustPanel: AvatarAdjustPanelStub,
          AvatarPortraitPanel: true,
          RoleplayPanel: true,
        },
      },
    })

    const adjustButtons = wrapper.findAll('button.adjust-btn.inline')
    expect(adjustButtons).toHaveLength(4)

    await adjustButtons[3].trigger('click')

    expect(systemApi.pauseGameAndDrain).toHaveBeenCalledTimes(1)
    expect(capturedProps).not.toBeNull()
    expect(capturedProps?.category).toBe('goldfinger')
    expect(capturedProps?.currentItem).toMatchObject({
      id: '1',
      name: 'Child of Fortune',
    })
  })
})
