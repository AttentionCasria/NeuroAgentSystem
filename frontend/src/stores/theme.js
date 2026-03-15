import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore(
  'theme',
  () => {
    const dark = ref(false)

    function applyTheme() {
      document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light')
    }

    function toggle() {
      dark.value = !dark.value
    }

    watch(dark, applyTheme, { immediate: true })

    return { dark, toggle, applyTheme }
  },
  {
    persist: {
      key: 'Synapse_MD_THEME',
      storage: localStorage,
    },
  },
)
