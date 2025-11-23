import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
export const useUserStore = defineStore(
  'user',
  () => {
    const name = ref('')
    const token = ref('')
    const image = ref('')

    const hasToken = computed(() => token.value && token.value.trim() !== '')

    function reset() {
      name.value = ''
      token.value = ''
      image.value = ''
    }

    return {
      name,
      token,
      image,
      hasToken,
      reset,
    }
  },
  {
    persist: {
      key: 'Synapse_MD_USER',
      storage: localStorage,
    },
  },
)
