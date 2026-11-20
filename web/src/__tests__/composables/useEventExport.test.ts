import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

const mocks = vi.hoisted(() => ({
  downloadEventExport: vi.fn(),
  saveBlobAsFile: vi.fn(),
  messageError: vi.fn(),
  avatarList: [
    { id: 'a1', name: 'Alice', is_dead: false },
    { id: 'a2', name: 'Bob', is_dead: true },
  ],
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/api/modules/event', () => ({
  eventApi: { downloadEventExport: mocks.downloadEventExport },
}))

vi.mock('@/stores/avatar', () => ({
  useAvatarStore: () => ({ avatarList: mocks.avatarList }),
}))

vi.mock('@/utils/fileDownload', () => ({
  saveBlobAsFile: mocks.saveBlobAsFile,
}))

vi.mock('@/utils/discreteApi', () => ({
  message: { error: mocks.messageError },
}))

import { useEventExport } from '@/composables/useEventExport'

async function flush() {
  for (let i = 0; i < 5; i += 1) await Promise.resolve()
  await nextTick()
}

describe('useEventExport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('offers all/major scopes only when the panel is unfiltered', () => {
    const exporter = useEventExport(ref(''))
    expect(exporter.scopeOptions.value.map(option => option.value)).toEqual(['all', 'major'])
    expect(exporter.exportScope.value).toBe('all')
    expect(exporter.buildExportParams()).toEqual({ format: 'markdown' })
  })

  it('defaults to the filtered avatar scope and names the avatar', () => {
    const exporter = useEventExport(ref('a1'))
    expect(exporter.scopeOptions.value.map(option => option.value)).toEqual(['all', 'avatar', 'major'])
    expect(exporter.scopeOptions.value[1].label).toBe(
      'game.event_panel.export_scope_avatar:{"avatar":"Alice"}',
    )
    expect(exporter.exportScope.value).toBe('avatar')
    expect(exporter.buildExportParams()).toEqual({ format: 'markdown', avatar_id: 'a1' })
  })

  it('drops the avatar scope when the panel filter is cleared', async () => {
    const avatarId = ref('a2')
    const exporter = useEventExport(avatarId)
    expect(exporter.exportScope.value).toBe('avatar')

    avatarId.value = ''
    await nextTick()
    expect(exporter.exportScope.value).toBe('all')
    expect(exporter.scopeOptions.value.map(option => option.value)).toEqual(['all', 'major'])
  })

  it('builds major-only JSON params', () => {
    const exporter = useEventExport(ref('a1'))
    exporter.exportFormat.value = 'json'
    exporter.exportScope.value = 'major'
    expect(exporter.buildExportParams()).toEqual({ format: 'json', major_only: true })
  })

  it('downloads with the server filename and closes the menu', async () => {
    const blob = new Blob(['{}'])
    mocks.downloadEventExport.mockResolvedValue({ blob, filename: 'chronicle-alice-year-100.json' })
    const exporter = useEventExport(ref('a1'))
    exporter.exportFormat.value = 'json'
    exporter.showMenu.value = true

    const pending = exporter.runExport()
    expect(exporter.exporting.value).toBe(true)
    await pending
    await flush()

    expect(mocks.downloadEventExport).toHaveBeenCalledWith({ format: 'json', avatar_id: 'a1' })
    expect(mocks.saveBlobAsFile).toHaveBeenCalledWith(blob, 'chronicle-alice-year-100.json')
    expect(exporter.showMenu.value).toBe(false)
    expect(exporter.exporting.value).toBe(false)
  })

  it('falls back to a default filename when the header is missing', async () => {
    const blob = new Blob(['# Chronicle'])
    mocks.downloadEventExport.mockResolvedValue({ blob, filename: null })
    const exporter = useEventExport(ref(''))

    await exporter.runExport()
    expect(mocks.saveBlobAsFile).toHaveBeenCalledWith(blob, 'chronicle.md')
  })

  it('reports failures and keeps the menu open', async () => {
    mocks.downloadEventExport.mockRejectedValue(new Error('World not initialized'))
    const exporter = useEventExport(ref(''))
    exporter.showMenu.value = true

    await exporter.runExport()

    expect(mocks.saveBlobAsFile).not.toHaveBeenCalled()
    expect(mocks.messageError).toHaveBeenCalledWith(
      'game.event_panel.export_failed:{"error":"World not initialized"}',
    )
    expect(exporter.showMenu.value).toBe(true)
    expect(exporter.exporting.value).toBe(false)
  })

  it('ignores repeated clicks while an export is running', async () => {
    let resolve: (value: unknown) => void = () => {}
    mocks.downloadEventExport.mockReturnValue(new Promise(r => { resolve = r }))
    const exporter = useEventExport(ref(''))

    const first = exporter.runExport()
    await exporter.runExport()
    expect(mocks.downloadEventExport).toHaveBeenCalledTimes(1)

    resolve({ blob: new Blob([]), filename: 'chronicle.md' })
    await first
  })
})
