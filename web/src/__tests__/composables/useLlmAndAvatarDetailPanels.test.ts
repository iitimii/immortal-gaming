import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { llmApi, avatarApi } from '@/api'
import { useLlmConfigPanel } from '@/composables/useLlmConfigPanel'
import {
  buildAvatarRelationMetaLines,
  parseAvatarEffectLine,
  useAvatarDetailPanel,
} from '@/composables/useAvatarDetailPanel'
import type { AvatarDetail } from '@/types/core'

const messageMock = {
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}
const dialogMock = {
  error: vi.fn(),
  warning: vi.fn(),
}

vi.mock('naive-ui', () => ({
  useMessage: () => messageMock,
  useDialog: () => dialogMock,
}))

vi.mock('@/api', () => ({
  llmApi: {
    fetchConfig: vi.fn(),
    testConnection: vi.fn(),
    saveConfig: vi.fn(),
  },
  avatarApi: {
    setLongTermObjective: vi.fn(),
    clearLongTermObjective: vi.fn(),
  },
}))

const i18n = createI18n({
  legacy: false,
  locale: 'en-US',
  messages: {
    'en-US': {
      common: {
        confirm: 'Confirm',
        cancel: 'Cancel',
      },
      ui: {
        other: 'Other',
        create_avatar: {
          gender_labels: {
            male: 'Male',
            female: 'Female',
          },
        },
      },
      llm: {
        fetch_failed: 'Failed to load',
        base_url_required: 'Base URL required',
        test_success: 'Test succeeded',
        save_success: 'Saved',
        test_save_failed_title: 'Failed',
        preset_applied: 'Applied {name} ({extra})',
        preset_extra_local: 'local',
        preset_extra_key: 'API key required',
        preset_extra_keep_saved_key: 'keeping saved key',
        preset_extra_keep_draft_key: 'keeping current key',
        clear_key: {
          title: 'Clear key?',
          content: 'Confirm clearing the key?',
          confirm: 'Clear',
          success: 'Cleared',
          failed: 'Clear failed',
        },
        placeholders: {
          api_key: 'Enter key',
          api_key_saved: 'Enter a new key to replace',
        },
        modes: {
          default: 'Default',
          default_desc: 'Default mode description',
          normal: 'Normal',
          normal_desc: 'Normal mode description',
          fast: 'Fast',
          fast_desc: 'Fast mode description',
        },
        formats: {
          openai: 'OpenAI',
          openai_desc: 'OpenAI format',
          anthropic: 'Anthropic',
          anthropic_desc: 'Anthropic format',
        },
        presets: {
          qwen: 'Qwen',
          gemini: 'Gemini',
          openai: 'OpenAI',
          anthropic: 'Anthropic',
          kimi: 'Kimi',
          deepseek: 'DeepSeek',
          groq: 'Groq',
          minimax: 'MiniMax',
          longcat: 'LongCat',
          siliconflow: 'SiliconFlow',
          openrouter: 'OpenRouter',
          ollama: 'Ollama',
        },
      },
      game: {
        ranking: {
          heaven: 'Heaven List',
        },
        info_panel: {
          avatar: {
            weapon_meta: 'Proficiency {value}',
            stats: {
              rogue: 'Rogue Cultivator',
            },
            sections: {
              goldfinger: 'Goldfinger',
            },
            adjust: {
              categories: {
                technique: 'Technique',
                weapon: 'Weapon',
                auxiliary: 'Auxiliary',
              },
            },
            modals: {
              clear_confirm: 'Confirm clear?',
              set_failed: 'Failed to set',
            },
          },
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

const avatarData = (): AvatarDetail => ({
  id: 'a1',
  name: 'Li Qing',
  realm: 'QI_REFINEMENT',
  pic_id: 1,
  level: 1,
  age: 20,
  lifespan: 100,
  origin: 'Mountain Village',
  hp: { cur: 10, max: 10 },
  gender: 'Male',
  alignment: 'GOOD',
  root: 'Metal',
  luck: 0,
  magic_stone: 0,
  appearance: 'Fair',
  base_battle_strength: 10,
  emotion: { emoji: ':)', name: 'Calm' },
  is_dead: false,
  current_effects: '[Technique] Attack+1; Speed+2\nUnlabeled effect',
  personas: [],
  materials: [],
  relations: [],
  ranking: { type: 'heaven', rank: 2 },
})

describe('useLlmConfigPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(llmApi.fetchConfig).mockResolvedValue({
      base_url: 'https://example.com',
      model_name: 'normal',
      fast_model_name: 'fast',
      mode: 'default',
      max_concurrent_requests: 8,
      has_api_key: true,
      api_format: 'openai',
    })
    vi.mocked(llmApi.testConnection).mockResolvedValue(true)
    vi.mocked(llmApi.saveConfig).mockResolvedValue({
      status: 'ok',
      message: 'saved',
      config: {
        base_url: 'https://example.com',
        model_name: 'normal',
        fast_model_name: 'fast',
        mode: 'default',
        max_concurrent_requests: 8,
        has_api_key: true,
        api_format: 'openai',
      },
    })
  })

  it('loads config, keeps API key while applying preset, then tests and saves', async () => {
    const onSaved = vi.fn()
    const panel = mountComposable(() => useLlmConfigPanel(onSaved))
    await settle()

    expect(panel.hasSavedApiKey.value).toBe(true)
    expect(panel.showSavedApiKeyMask.value).toBe(true)
    expect(panel.config.value.model_name).toBe('normal')

    panel.config.value.api_key = 'draft-secret'
    const ollama = panel.presets.value.find(preset => preset.isLocal)
    expect(ollama).toBeTruthy()
    panel.applyPreset(ollama!)
    expect(panel.config.value.api_key).toBe('draft-secret')

    await panel.handleTestAndSave()
    expect(llmApi.testConnection).toHaveBeenCalledWith(expect.objectContaining({
      api_key: 'draft-secret',
      base_url: ollama!.base_url,
    }))
    expect(llmApi.saveConfig).toHaveBeenCalledWith(expect.objectContaining({
      api_key: 'draft-secret',
      base_url: ollama!.base_url,
    }))
    expect(panel.config.value.api_key).toBe('')
    expect(panel.hasSavedApiKey.value).toBe(true)
    expect(onSaved).toHaveBeenCalled()
  })

  it('clears saved API key when saving a local preset without a draft key', async () => {
    vi.mocked(llmApi.saveConfig).mockResolvedValue({
      status: 'ok',
      message: 'saved',
      config: {
        base_url: 'http://localhost:11434/v1',
        model_name: 'qwen3.5:9b',
        fast_model_name: 'qwen3:8b',
        mode: 'default',
        max_concurrent_requests: 8,
        has_api_key: false,
        api_format: 'openai',
      },
    })
    const panel = mountComposable(() => useLlmConfigPanel(vi.fn()))
    await settle()

    const ollama = panel.presets.value.find(preset => preset.isLocal)
    expect(ollama).toBeTruthy()
    panel.applyPreset(ollama!)

    await panel.handleTestAndSave()

    expect(llmApi.testConnection).toHaveBeenCalledWith(expect.objectContaining({
      api_key: '',
      clear_api_key: true,
      base_url: ollama!.base_url,
    }))
    expect(llmApi.saveConfig).toHaveBeenCalledWith(expect.objectContaining({
      clear_api_key: true,
      base_url: ollama!.base_url,
    }))
    expect(panel.hasSavedApiKey.value).toBe(false)
  })

  it('clears saved API key when endpoint scope changes without a draft key', async () => {
    const panel = mountComposable(() => useLlmConfigPanel(vi.fn()))
    await settle()

    panel.config.value.base_url = 'https://api.other.example/v1'
    panel.config.value.model_name = 'other-model'
    panel.config.value.fast_model_name = 'other-fast'

    await panel.handleTestAndSave()

    expect(llmApi.testConnection).toHaveBeenCalledWith(expect.objectContaining({
      api_key: '',
      clear_api_key: true,
      base_url: 'https://api.other.example/v1',
    }))
  })

  it('keeps current recommended preset model names from regressing to old aliases', async () => {
    const panel = mountComposable(() => useLlmConfigPanel(vi.fn()))
    await settle()

    const presets = Object.fromEntries(panel.presets.value.map(preset => [preset.name, preset]))

    expect(presets.OpenAI.model_name).toBe('gpt-5.6-terra')
    expect(presets.Qwen.fast_model_name).toBe('qwen3.5-flash')
    expect(presets.DeepSeek.model_name).toBe('deepseek-v4-pro')
    expect(presets.Groq.fast_model_name).toBe('openai/gpt-oss-20b')
    expect(presets.Ollama.model_name).toBe('qwen3.5:9b')
    expect(panel.presets.value.map(preset => preset.model_name)).not.toContain('gpt-4o')
    expect(panel.presets.value.map(preset => preset.model_name)).not.toContain('deepseek-chat')
  })

  it('clears saved API key only after confirmation', async () => {
    const panel = mountComposable(() => useLlmConfigPanel(vi.fn()))
    await settle()

    panel.clearSavedApiKey()
    expect(dialogMock.warning).toHaveBeenCalled()
    const warningOptions = dialogMock.warning.mock.calls[0][0]
    await warningOptions.onPositiveClick()

    expect(llmApi.saveConfig).toHaveBeenCalledWith(expect.objectContaining({
      api_key: '',
      clear_api_key: true,
    }))
  })

  it('warns before saving without base url', async () => {
    const panel = mountComposable(() => useLlmConfigPanel(vi.fn()))
    await settle()

    panel.config.value.base_url = ''
    await panel.handleTestAndSave()

    expect(messageMock.warning).toHaveBeenCalledWith('Base URL required')
    expect(llmApi.testConnection).not.toHaveBeenCalled()
  })
})

describe('useAvatarDetailPanel helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(avatarApi.setLongTermObjective).mockResolvedValue({})
    vi.mocked(avatarApi.clearLongTermObjective).mockResolvedValue({})
  })

  it('parses effect lines with source and fallback source', () => {
    expect(parseAvatarEffectLine('[Technique] Attack+1; Speed+2', i18n.global.t)).toEqual({
      source: 'Technique',
      segments: ['Attack+1', 'Speed+2'],
    })
    expect(parseAvatarEffectLine('Unlabeled effect', i18n.global.t)).toEqual({
      source: 'Other',
      segments: ['Unlabeled effect'],
    })
  })

  it('builds relation meta lines without stranger attitude', () => {
    expect(buildAvatarRelationMetaLines({
      target_id: 'a2',
      name: 'Qing Lan',
      relation: 'Dao Partner / Friendly',
      relation_type: 'lover',
      numeric_relation: 'friend',
      friendliness: 12,
      realm: 'QI_REFINEMENT',
      sect: 'Azure Cloud Sect',
    })).toEqual(['Dao Partner', 'Friendly (12)'])

    expect(buildAvatarRelationMetaLines({
      target_id: 'a3',
      name: 'A Stranger',
      relation: 'Stranger',
      relation_type: '',
      numeric_relation: 'stranger',
      friendliness: 0,
      realm: 'QI_REFINEMENT',
      sect: '',
    })).toEqual([])
  })

  it('groups relations, formats rank, and updates objectives', async () => {
    const refreshDetail = vi.fn()
    const select = vi.fn()
    const panel = mountComposable(() => useAvatarDetailPanel(
      avatarData,
      i18n.global.t,
      { refreshDetail, select } as any,
      () => true,
      vi.fn(),
    ))

    expect(panel.formattedRanking.value).toBe('Heaven Rank 2')
    expect(panel.parsedCurrentEffects.value).toHaveLength(2)
    expect(panel.groupedRelations.value.parents).toHaveLength(2)

    panel.objectiveContent.value = 'Seclusion breakthrough'
    await panel.handleSetObjective()
    expect(avatarApi.setLongTermObjective).toHaveBeenCalledWith('a1', 'Seclusion breakthrough')
    expect(refreshDetail).toHaveBeenCalled()

    await panel.handleClearObjective()
    expect(avatarApi.clearLongTermObjective).toHaveBeenCalledWith('a1')
  })
})
