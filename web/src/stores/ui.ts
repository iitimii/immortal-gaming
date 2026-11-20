import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import { avatarApi } from '../api';
import { mapDetailDTOToDomain } from '../api/mappers/detailMapper';
import type { AvatarDetail, POIDetail, RegionDetail, SectDetail } from '../types/core';

export type SelectionType = 'avatar' | 'region' | 'sect' | 'poi';

export interface Selection {
  type: SelectionType;
  id: string;
}

export type SystemMenuTab =
  | 'save'
  | 'load'
  | 'characters'
  | 'llm'
  | 'start'
  | 'settings'
  | 'about'
  | 'other';

export type SystemMenuContext = 'splash' | 'game';

export const useUiStore = defineStore('ui', () => {
  // --- Selection & Panels ---
  
  const selectedTarget = ref<Selection | null>(null);
  const systemMenuVisible = ref(false);
  const systemMenuDefaultTab = ref<SystemMenuTab>('load');
  const systemMenuClosable = ref(true);
  const systemMenuContext = ref<SystemMenuContext>('game');
  const llmConfigError = ref('');
  
  // Detail data (may be empty or still loading)
  // Use shallowRef to avoid deep reactivity overhead (large nested objects such as AvatarDetail)
  const detailData = shallowRef<AvatarDetail | RegionDetail | SectDetail | POIDetail | null>(null);
  const isLoadingDetail = ref(false);
  const detailError = ref<string | null>(null);

  // Request counter to handle race conditions.
  let detailRequestId = 0;

  // --- Actions ---

  async function select(type: SelectionType, id: string) {
    if (selectedTarget.value?.type === type && selectedTarget.value?.id === id) {
      return; // Already selected
    }
    
    selectedTarget.value = { type, id };
    detailData.value = null; // Reset current data
    
    await refreshDetail();
  }

  function clearSelection() {
    selectedTarget.value = null;
    detailData.value = null;
    detailError.value = null;
  }

  function clearHoverCache() {
    // Clear the detail cache so the next selection reloads.
    detailData.value = null;
  }

  function openSystemMenu(
    tab: SystemMenuTab = 'load',
    closable = true,
    context: SystemMenuContext = 'game',
  ) {
    systemMenuDefaultTab.value = tab;
    systemMenuClosable.value = closable;
    systemMenuContext.value = context;
    systemMenuVisible.value = true;
  }

  function closeSystemMenu() {
    if (systemMenuClosable.value) {
      systemMenuVisible.value = false;
      systemMenuContext.value = 'game';
    }
  }

  function setSystemMenuClosable(closable: boolean) {
    systemMenuClosable.value = closable;
  }

  function setLlmConfigError(error: string) {
    llmConfigError.value = error;
  }

  function clearLlmConfigError() {
    llmConfigError.value = '';
  }

  async function refreshDetail() {
    if (!selectedTarget.value) return;

    // Bump the counter per request; only accept the latest response.
    const currentRequestId = ++detailRequestId;
    const target = { ...selectedTarget.value };
    isLoadingDetail.value = true;
    detailError.value = null;

    // Accept the response only if requestId matches and the target is unchanged.
    const shouldAcceptResponse = () =>
      currentRequestId === detailRequestId &&
      selectedTarget.value?.type === target.type &&
      selectedTarget.value?.id === target.id;

    try {
      const data = await avatarApi.fetchDetailInfo(target);

      if (shouldAcceptResponse()) {
        detailData.value = mapDetailDTOToDomain(data, target.type);
      }
    } catch (e) {
      if (shouldAcceptResponse()) {
        detailError.value = e instanceof Error ? e.message : 'Failed to load detail';
      }
    } finally {
      if (shouldAcceptResponse()) {
        isLoadingDetail.value = false;
      }
    }
  }

  return {
    selectedTarget,
    systemMenuVisible,
    systemMenuDefaultTab,
    systemMenuClosable,
    systemMenuContext,
    llmConfigError,
    detailData,
    isLoadingDetail,
    detailError,

    select,
    clearSelection,
    clearHoverCache,
    openSystemMenu,
    closeSystemMenu,
    setSystemMenuClosable,
    setLlmConfigError,
    clearLlmConfigError,
    refreshDetail
  };
});

