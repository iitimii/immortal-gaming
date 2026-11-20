import type { Directive } from 'vue';
import { useAudio } from '../composables/useAudio';
import type { SoundType } from '../composables/useAudio';

type SoundElement = HTMLElement & {
  __cwsSoundHandler?: () => void;
};

function resolveSoundType(el: HTMLElement, fallback: unknown): SoundType {
  return (el.getAttribute('data-has-sound') || fallback || 'click') as SoundType;
}

export const vSound: Directive = {
  mounted(el: SoundElement, binding) {
    const { play } = useAudio();
    const type = (binding.arg || binding.value || 'click') as SoundType;
    
    // Mark this element as having its own sound so the global listener skips it
    el.setAttribute('data-has-sound', type);

    const handler = () => {
      // Do not stop propagation; that could break app logic
      play(resolveSoundType(el, type));
    };
    el.__cwsSoundHandler = handler;
    el.addEventListener('click', handler);
  },
  // Dynamic update
  updated(el: HTMLElement, binding) {
     const type = (binding.arg || binding.value || 'click') as SoundType;
     el.setAttribute('data-has-sound', type);
  },
  unmounted(el: SoundElement) {
    if (el.__cwsSoundHandler) {
      el.removeEventListener('click', el.__cwsSoundHandler);
      delete el.__cwsSoundHandler;
    }
    el.removeAttribute('data-has-sound');
  }
};
