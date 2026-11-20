import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'

import { loadWorldInfoRows, parseWorldInfoCsv, translateWorldInfoRows } from '@/utils/worldInfo'
import enUSGame from '@/locales/en-US/game.json'

describe('worldInfo utils', () => {
  it('parses world_info.csv rows after the two header lines', () => {
    const rows = parseWorldInfoCsv([
      'title,title_id,name_id,desc_id,desc',
      'Title,Title ID,Name ID,Description ID,Description',
      'Introduction,WORLD_INFO_INTRO_TITLE,WORLD_INFO_INTRO_NAME,WORLD_INFO_INTRO_DESC,A cultivation world where many cultivators compete.',
      'Realm,WORLD_INFO_REALM_TITLE,WORLD_INFO_REALM_NAME,WORLD_INFO_REALM_DESC,Cultivation realms from weak to strong.',
    ].join('\n'))

    expect(rows).toEqual([
      {
        title: 'Introduction',
        titleId: 'WORLD_INFO_INTRO_TITLE',
        nameId: 'WORLD_INFO_INTRO_NAME',
        descId: 'WORLD_INFO_INTRO_DESC',
        fallbackDesc: 'A cultivation world where many cultivators compete.',
      },
      {
        title: 'Realm',
        titleId: 'WORLD_INFO_REALM_TITLE',
        nameId: 'WORLD_INFO_REALM_NAME',
        descId: 'WORLD_INFO_REALM_DESC',
        fallbackDesc: 'Cultivation realms from weak to strong.',
      },
    ])
  })

  it('translates rows with i18n keys and falls back to csv text when missing', () => {
    const rows = [
      {
        title: 'Introduction',
        titleId: 'WORLD_INFO_INTRO_TITLE',
        nameId: 'WORLD_INFO_INTRO_NAME',
        descId: 'WORLD_INFO_INTRO_DESC',
        fallbackDesc: 'A cultivation world where many cultivators compete.',
      },
      {
        title: 'Realm',
        titleId: 'WORLD_INFO_REALM_TITLE',
        nameId: 'WORLD_INFO_REALM_NAME',
        descId: 'WORLD_INFO_REALM_DESC',
        fallbackDesc: 'Cultivation realms from weak to strong.',
      },
    ]

    const translated = translateWorldInfoRows(rows, (key) => {
      const dictionary: Record<string, string> = {
        'game.world_info.entries.WORLD_INFO_INTRO_TITLE': 'Introduction',
        'game.world_info.entries.WORLD_INFO_INTRO_NAME': 'Introduction',
        'game.world_info.entries.WORLD_INFO_INTRO_DESC': 'This is a cultivation world where many cultivators compete.',
      }
      return dictionary[key] ?? key
    })

    expect(translated).toEqual([
      {
        id: 'WORLD_INFO_INTRO_TITLE',
        title: 'Introduction',
        name: 'Introduction',
        desc: 'This is a cultivation world where many cultivators compete.',
      },
      {
        id: 'WORLD_INFO_REALM_TITLE',
        title: 'Realm',
        name: 'Realm',
        desc: 'Cultivation realms from weak to strong.',
      },
    ])
  })

  it('provides en-US world info entry translations for every csv row', () => {
    const rows = parseWorldInfoCsv([
      'title,title_id,name_id,desc_id,desc',
      'Title,Title ID,Name ID,Description ID,Description',
      'Introduction,WORLD_INFO_INTRO_TITLE,WORLD_INFO_INTRO_NAME,WORLD_INFO_INTRO_DESC,A cultivation world where many cultivators compete.',
      'Office,WORLD_INFO_OFFICIAL_TITLE,WORLD_INFO_OFFICIAL_NAME,WORLD_INFO_OFFICIAL_DESC,CSV fallback: cultivators may serve the court.',
    ].join('\n'))

    const entries: Record<string, string> = enUSGame.world_info?.entries ?? {}
    for (const row of [...rows, ...loadWorldInfoRows()]) {
      expect(entries[row.titleId]).toBeTruthy()
      expect(entries[row.nameId]).toBeTruthy()
      expect(entries[row.descId]).toBeTruthy()
    }
  })

  it('uses the game namespace when resolving world info translations', () => {
    const rows = [
      {
        title: 'Office',
        titleId: 'WORLD_INFO_OFFICIAL_TITLE',
        nameId: 'WORLD_INFO_OFFICIAL_NAME',
        descId: 'WORLD_INFO_OFFICIAL_DESC',
        fallbackDesc: 'CSV fallback: cultivators may serve the court.',
      },
    ]

    const translated = translateWorldInfoRows(rows, (key) => {
      if (key === 'game.world_info.entries.WORLD_INFO_OFFICIAL_TITLE') return 'Official Rank'
      if (key === 'game.world_info.entries.WORLD_INFO_OFFICIAL_NAME') return 'Official Rank'
      if (key === 'game.world_info.entries.WORLD_INFO_OFFICIAL_DESC') return 'Cultivators may govern for the imperial court.'
      return key
    })

    expect(translated[0]).toEqual({
      id: 'WORLD_INFO_OFFICIAL_TITLE',
      title: 'Official Rank',
      name: 'Official Rank',
      desc: 'Cultivators may govern for the imperial court.',
    })
  })

  it('resolves world info translations from the real game locale namespace', () => {
    const i18n = createI18n({
      legacy: false,
      locale: 'en-US',
      messages: {
        'en-US': {
          game: enUSGame,
        },
      },
    })

    const rows = [
      {
        title: 'Office',
        titleId: 'WORLD_INFO_OFFICIAL_TITLE',
        nameId: 'WORLD_INFO_OFFICIAL_NAME',
        descId: 'WORLD_INFO_OFFICIAL_DESC',
        fallbackDesc: 'CSV fallback: cultivators may serve the court.',
      },
    ]

    const translated = translateWorldInfoRows(rows, i18n.global.t)

    expect(translated[0]?.title).toBe('Official Rank')
    expect(translated[0]?.name).toBe('Official Rank')
    expect(translated[0]?.desc).toContain('imperial court')
    expect(translated[0]?.desc).not.toContain('CSV fallback')
  })
})
