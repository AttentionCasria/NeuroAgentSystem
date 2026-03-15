<script setup>
defineOptions({ name: 'WorkspaceTabs' })

defineProps({
  tabs: {
    type: Array,
    default: () => [],
  },
  activeTab: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['change'])
</script>

<template>
  <nav class="workspace-tabs" aria-label="工作台模块切换">
    <button v-for="tab in tabs" :key="tab.key" type="button" class="tab-btn" :class="{ active: tab.key === activeTab }"
      @click="emit('change', tab.key)">
      <span>{{ tab.label }}</span>
    </button>
  </nav>
</template>

<style scoped lang="scss">
.workspace-tabs {
  display: flex;
  overflow-x: auto;
  border: 1px solid rgba(191, 213, 207, 0.9);
  border-radius: 128px;
  width: fit-content;
  max-width: 100%;
}

.tab-btn {
  border: 1px solid transparent;
  border-radius: 128px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.88);
  color: #17313a;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;

  span {
    display: block;
    font-size: 16px;
    font-weight: 700;
  }

  small {
    display: block;
    margin-top: 6px;
    color: #5e7379;
  }

  &:hover {
    background: rgba(0, 0, 0, 0.04);
  }

  &.active {
    border-color: rgba(17, 150, 127, 0.35);
    border: 1px solid rgba(191, 213, 207, 0.9);
    background: linear-gradient(135deg, #11967f 0%, #0f7666 100%);
    color: white;
  }


}

@media (max-width: 640px) {
  .tab-btn {
    min-width: 160px;
  }
}
</style>
