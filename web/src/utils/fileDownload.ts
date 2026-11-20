/**
 * Save a Blob to the user's machine through a temporary object URL.
 * Works in browsers and in the Electron desktop shell without extra deps.
 */
export function saveBlobAsFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  try {
    anchor.click()
  } finally {
    anchor.remove()
    // Revoke on the next tick so the browser has started reading the blob.
    globalThis.setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}
