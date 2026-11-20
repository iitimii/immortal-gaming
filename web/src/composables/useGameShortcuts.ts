import type { Ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useAvatarStore } from '@/stores/avatar'
import { focusCameraOnTile } from '@/components/game/utils/cameraFocus'
import {
  useKeyboardShortcuts,
  type KeyboardShortcut,
  type ShortcutContext,
} from './useKeyboardShortcuts'

interface UseGameShortcutsOptions {
  showMenu: Ref<boolean>
  canCloseMenu: Ref<boolean>
  openGameMenu: () => void
  closeMenu: () => void
  toggleManualPause: () => void
  setSimulationSpeed: (speed: number) => void
  simulationSpeed: Ref<number>
  allowedSpeeds: Ref<number[]>
}

const GROUP_SIMULATION = 'shortcuts.groups.simulation'
const GROUP_MAP = 'shortcuts.groups.map'
const GROUP_GENERAL = 'shortcuts.groups.general'

/**
 * Registers the in-game shortcuts. All of them are game-scoped, so they only fire while the
 * game scene is active (see `installKeyboardShortcuts`). New shortcuts (e.g. stepping one month)
 * can be added as one more entry here or registered from any component via `useKeyboardShortcuts`.
 */
export function useGameShortcuts(options: UseGameShortcutsOptions) {
  const uiStore = useUiStore()
  const avatarStore = useAvatarStore()
  const { register, helpVisible, toggleHelp } = useKeyboardShortcuts()

  /** Gameplay keys are inert while the system menu, a modal or the help overlay covers the map. */
  function gameplayAvailable(context: ShortcutContext) {
    return !options.showMenu.value && !helpVisible.value && !context.modalOpen
  }

  function sortedSpeeds() {
    return [...options.allowedSpeeds.value].sort((a, b) => a - b)
  }

  function stepSpeed(direction: 1 | -1) {
    const speeds = sortedSpeeds()
    const current = options.simulationSpeed.value
    const next = direction > 0
      ? speeds.find(speed => speed > current)
      : speeds.reverse().find(speed => speed < current)
    if (next !== undefined) {
      options.setSimulationSpeed(next)
    }
  }

  function selectedAvatar() {
    const target = uiStore.selectedTarget
    if (target?.type !== 'avatar') return null
    return avatarStore.avatars.get(target.id) ?? null
  }

  function handleEscape(_event: KeyboardEvent, context: ShortcutContext) {
    // Naive UI modals close themselves on Escape; leave the layers underneath untouched.
    if (context.modalOpen) return
    if (options.showMenu.value) {
      if (options.canCloseMenu.value) options.closeMenu()
      return
    }
    if (uiStore.selectedTarget) {
      uiStore.clearSelection()
      return
    }
    options.openGameMenu()
  }

  const shortcuts: KeyboardShortcut[] = [
    {
      id: 'game.toggle-pause',
      keys: [' '],
      displayKeys: ['space'],
      labelKey: 'shortcuts.actions.toggle_pause',
      groupKey: GROUP_SIMULATION,
      enabled: gameplayAvailable,
      handler: () => options.toggleManualPause(),
    },
    {
      id: 'game.set-speed',
      keys: ['1', '2', '3', '4'],
      displayKeys: ['1', '2', '3', '4'],
      labelKey: 'shortcuts.actions.set_speed',
      groupKey: GROUP_SIMULATION,
      enabled: context => gameplayAvailable(context) && options.allowedSpeeds.value.length > 0,
      handler: (event) => {
        const speed = options.allowedSpeeds.value[Number(event.key) - 1]
        if (speed === undefined) return false
        options.setSimulationSpeed(speed)
      },
    },
    {
      id: 'game.speed-up',
      keys: ['+', '='],
      displayKeys: ['+'],
      labelKey: 'shortcuts.actions.speed_up',
      groupKey: GROUP_SIMULATION,
      allowRepeat: true,
      enabled: context => gameplayAvailable(context) && options.allowedSpeeds.value.length > 0,
      handler: () => stepSpeed(1),
    },
    {
      id: 'game.speed-down',
      keys: ['-'],
      displayKeys: ['-'],
      labelKey: 'shortcuts.actions.speed_down',
      groupKey: GROUP_SIMULATION,
      allowRepeat: true,
      enabled: context => gameplayAvailable(context) && options.allowedSpeeds.value.length > 0,
      handler: () => stepSpeed(-1),
    },
    {
      id: 'game.focus-selected-avatar',
      keys: ['f'],
      displayKeys: ['F'],
      labelKey: 'shortcuts.actions.focus_avatar',
      groupKey: GROUP_MAP,
      enabled: context => gameplayAvailable(context) && selectedAvatar() !== null,
      handler: () => {
        const avatar = selectedAvatar()
        if (!avatar || !focusCameraOnTile(avatar.x, avatar.y)) return false
      },
    },
    {
      id: 'game.escape',
      keys: ['Escape'],
      displayKeys: ['escape'],
      labelKey: 'shortcuts.actions.escape',
      groupKey: GROUP_GENERAL,
      allowInInputs: true,
      handler: handleEscape,
    },
    {
      id: 'game.toggle-help',
      keys: ['?'],
      displayKeys: ['?'],
      labelKey: 'shortcuts.actions.toggle_help',
      groupKey: GROUP_GENERAL,
      enabled: () => !options.showMenu.value,
      handler: () => toggleHelp(),
    },
  ]

  register(shortcuts)
}
