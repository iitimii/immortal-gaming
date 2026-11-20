export interface SelectOptionLike<TValue extends string | number = string | number> {
  label: string
  value: TValue
}

/**
 * Prepend an "All" option to a select option list.
 * If the i18n key is missing, use the explicit fallback so the raw key is never shown.
 */
export function prependAllOption<TValue extends string | number>(
  options: SelectOptionLike<TValue>[],
  allLabel: string,
  translationKey: string,
  fallbackLabel: string,
  allValue: string | number
): Array<SelectOptionLike<TValue | string | number>> {
  const finalLabel = !allLabel || allLabel === translationKey ? fallbackLabel : allLabel

  return [
    { label: finalLabel, value: allValue },
    ...options,
  ]
}
