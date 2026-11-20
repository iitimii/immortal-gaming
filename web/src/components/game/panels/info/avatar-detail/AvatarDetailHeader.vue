<script setup lang="ts">
import pencilLineIcon from '@/assets/icons/ui/lucide/pencil-line.svg'
import starIcon from '@/assets/icons/ui/lucide/star.svg'

defineProps<{
  name: string
  portraitUrl: string
  realmText: string
  canonicalRealmText: string
  sectText: string
  portraitTitle: string
  portraitAlt: string
  canonicalRealmLabel: string
  watched?: boolean
  watchLabel?: string
}>()

const emit = defineEmits<{
  (e: 'edit-portrait'): void
  (e: 'toggle-watch'): void
}>()
</script>

<template>
  <div class="avatar-header">
    <button
      class="portrait-button"
      type="button"
      :title="portraitTitle"
      :aria-label="portraitTitle"
      @click="emit('edit-portrait')"
    >
      <div class="portrait-shell">
        <img v-if="portraitUrl" class="portrait-image" :src="portraitUrl" :alt="portraitAlt" />
        <div v-else class="portrait-fallback">{{ name.slice(0, 1) }}</div>
        <div class="portrait-overlay">
          <span class="portrait-overlay-text">{{ portraitTitle }}</span>
          <span class="portrait-edit-badge">
            <span class="portrait-edit-icon" :style="{ '--icon-url': `url(${pencilLineIcon})` }" aria-hidden="true"></span>
          </span>
        </div>
      </div>
    </button>
    <div class="avatar-header-meta">
      <div class="avatar-name-row">
        <div class="avatar-name">{{ name }}</div>
        <button
          v-if="watchLabel"
          class="watch-toggle"
          :class="{ 'is-watched': watched }"
          type="button"
          data-testid="watch-toggle"
          :title="watchLabel"
          :aria-label="watchLabel"
          :aria-pressed="watched ? 'true' : 'false'"
          @click="emit('toggle-watch')"
        >
          <span class="watch-toggle-icon" :style="{ '--icon-url': `url(${starIcon})` }" aria-hidden="true"></span>
        </button>
      </div>
      <div class="avatar-realm">{{ realmText }}</div>
      <div v-if="canonicalRealmText" class="avatar-realm-canonical">
        {{ canonicalRealmLabel }}
      </div>
      <div class="avatar-sect">{{ sectText }}</div>
    </div>
  </div>
</template>

<style scoped>
.avatar-header {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.portrait-button {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.portrait-shell {
  position: relative;
  width: 96px;
  height: 96px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.1), transparent 58%),
    rgba(255, 255, 255, 0.04);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.portrait-button:hover .portrait-shell {
  border-color: rgba(23, 125, 220, 0.45);
  box-shadow: 0 0 0 1px rgba(23, 125, 220, 0.18);
  transform: translateY(-1px);
}

.portrait-image,
.portrait-fallback {
  width: 100%;
  height: 100%;
}

.portrait-image {
  object-fit: contain;
}

.portrait-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ddd;
  font-size: 32px;
  font-weight: 700;
}

.portrait-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 8px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.04), rgba(0, 0, 0, 0.34));
  opacity: 0;
  transition: opacity 0.18s ease;
}

.portrait-button:hover .portrait-overlay {
  opacity: 1;
}

.portrait-overlay-text {
  font-size: 11px;
  color: #f2f6fb;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.34);
}

.portrait-edit-badge {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(19, 24, 31, 0.86);
  color: #dce9f8;
}

.portrait-edit-icon {
  display: inline-block;
  width: 13px;
  height: 13px;
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.avatar-header-meta {
  min-width: 0;
}

.avatar-name-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.watch-toggle {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: #8a96a3;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}

.watch-toggle:hover {
  color: #dce9f8;
  border-color: rgba(255, 255, 255, 0.22);
}

.watch-toggle.is-watched {
  color: #f2c94c;
  border-color: rgba(242, 201, 76, 0.42);
  background: rgba(242, 201, 76, 0.12);
}

.watch-toggle-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  background-color: currentColor;
  -webkit-mask-image: var(--icon-url);
  mask-image: var(--icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.avatar-name {
  font-size: 22px;
  font-weight: 700;
  color: #eee;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.avatar-realm {
  color: #aaddff;
  font-size: 13px;
  margin-top: 6px;
}

.avatar-realm-canonical {
  color: #8aa4bd;
  font-size: 11px;
  margin-top: 2px;
}

.avatar-sect {
  color: #aaa;
  font-size: 12px;
  margin-top: 4px;
}
</style>
