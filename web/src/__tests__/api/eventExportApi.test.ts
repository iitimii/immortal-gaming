import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, httpClient, parseContentDispositionFilename } from '@/api/http'
import { buildEventExportPath, eventApi } from '@/api/modules/event'

describe('buildEventExportPath', () => {
  it('always sends the format and omits unset filters', () => {
    expect(buildEventExportPath({ format: 'markdown' })).toBe(
      '/api/v1/query/events/export?format=markdown',
    )
  })

  it('encodes avatar, major-only and year range filters', () => {
    const path = buildEventExportPath({
      format: 'json',
      avatar_id: 'a 1',
      major_only: true,
      from_year: 0,
      to_year: 112,
    })
    const [base, qs] = path.split('?')
    const query = new URLSearchParams(qs)

    expect(base).toBe('/api/v1/query/events/export')
    expect(query.get('format')).toBe('json')
    expect(query.get('avatar_id')).toBe('a 1')
    expect(query.get('major_only')).toBe('true')
    expect(query.get('from_year')).toBe('0')
    expect(query.get('to_year')).toBe('112')
  })

  it('does not send major_only when false', () => {
    expect(buildEventExportPath({ format: 'json', major_only: false })).not.toContain('major_only')
  })
})

describe('parseContentDispositionFilename', () => {
  it('reads quoted, bare and RFC 5987 filenames', () => {
    expect(parseContentDispositionFilename('attachment; filename="chronicle-year-100-to-112.md"'))
      .toBe('chronicle-year-100-to-112.md')
    expect(parseContentDispositionFilename('attachment; filename=chronicle.json')).toBe('chronicle.json')
    expect(parseContentDispositionFilename("attachment; filename*=UTF-8''my%20chronicle.md"))
      .toBe('my chronicle.md')
  })

  it('returns null when no filename is present', () => {
    expect(parseContentDispositionFilename(null)).toBeNull()
    expect(parseContentDispositionFilename('attachment')).toBeNull()
  })
})

describe('eventApi.downloadEventExport', () => {
  beforeEach(() => {
    vi.useRealTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fetches the export through the API base and returns blob + filename', async () => {
    const blob = new Blob(['# Chronicle'], { type: 'text/markdown' })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'Content-Disposition': 'attachment; filename="chronicle-year-100.md"' }),
      blob: vi.fn().mockResolvedValue(blob),
    })
    global.fetch = fetchMock as unknown as typeof fetch

    const file = await eventApi.downloadEventExport({ format: 'markdown', major_only: true })

    const expectedBase = import.meta.env.VITE_API_TARGET || ''
    expect(fetchMock).toHaveBeenCalledWith(
      `${expectedBase}/api/v1/query/events/export?format=markdown&major_only=true`,
      expect.objectContaining({ method: 'GET' }),
    )
    expect(file).toEqual({ blob, filename: 'chronicle-year-100.md' })
  })

  it('surfaces the standard public error message', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: vi.fn().mockResolvedValue({
        detail: { code: 'INVALID_EXPORT_FORMAT', message: 'format must be one of: markdown, json' },
      }),
    }) as unknown as typeof fetch

    const error = await httpClient.download('/api/v1/query/events/export?format=pdf').catch(e => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(400)
    expect(error.message).toBe('format must be one of: markdown, json')
  })
})
