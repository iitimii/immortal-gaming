import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveBlobAsFile } from '@/utils/fileDownload'

describe('saveBlobAsFile', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('clicks a temporary download link and revokes the object URL afterwards', () => {
    const createObjectURL = vi.fn(() => 'blob:chronicle')
    const revokeObjectURL = vi.fn()
    Object.assign(URL, { createObjectURL, revokeObjectURL })
    let clicked: HTMLAnchorElement | null = null
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicked = this
    })

    const blob = new Blob(['# Chronicle'])
    saveBlobAsFile(blob, 'chronicle-year-100.md')

    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(clicked).not.toBeNull()
    expect(clicked!.download).toBe('chronicle-year-100.md')
    expect(clicked!.href).toBe('blob:chronicle')
    expect(document.body.contains(clicked)).toBe(false)
    expect(revokeObjectURL).not.toHaveBeenCalled()

    vi.runAllTimers()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:chronicle')
  })
})
