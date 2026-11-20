import type { ComposerTranslation } from 'vue-i18n';

// Backend population values are expressed in units of 10,000 people.
const POPULATION_UNIT = 10000;

function normalizeLocale(locale: string | undefined): string {
  return locale || 'en-US';
}

function formatCompactNumber(value: number, locale: string, maximumFractionDigits: number): string {
  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    maximumFractionDigits,
  }).format(value);
}

export function formatPopulationValue(
  value: number | undefined,
  locale?: string,
): string {
  return formatCompactNumber((value ?? 0) * POPULATION_UNIT, normalizeLocale(locale), 2);
}

export function formatPopulationText(
  value: number | undefined,
  t: ComposerTranslation,
  locale?: string,
): string {
  return t('game.mortal_system.population_value', {
    value: formatPopulationValue(value, locale)
  });
}

export function formatPopulationGrowthText(
  value: number | undefined,
  t: ComposerTranslation,
  locale?: string,
): string {
  const normalized = value ?? 0;
  const prefix = normalized > 0 ? '+' : '';
  const formattedValue = formatCompactNumber(normalized * POPULATION_UNIT, normalizeLocale(locale), 1);

  return t('game.mortal_system.population_growth_value', {
    value: `${prefix}${formattedValue}`
  });
}

export function formatPopulationRatioText(
  current: number | undefined,
  capacity: number | undefined,
  t: ComposerTranslation,
  locale?: string,
): string {
  return t('game.mortal_system.population_ratio_value', {
    current: formatPopulationValue(current, locale),
    capacity: formatPopulationValue(capacity, locale)
  });
}
