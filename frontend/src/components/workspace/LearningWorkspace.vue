<script setup>
defineOptions({ name: 'LearningWorkspace' })

defineProps({
  materials: {
    type: Array,
    default: () => [],
  },
  learningTotal: {
    type: Number,
    default: 0,
  },
  materialsLoading: {
    type: Boolean,
    default: false,
  },
  selectedMaterialId: {
    type: [Number, null],
    default: null,
  },
  materialDetail: {
    type: Object,
    default: null,
  },
  materialDetailLoading: {
    type: Boolean,
    default: false,
  },
  materialPageCount: {
    type: Number,
    default: 1,
  },
})

const query = defineModel('query', { required: true })

const emit = defineEmits(['search', 'select-material', 'page-change', 'open-material-link'])

function shortText(value, fallback = '暂无内容') {
  const text = String(value || '').trim()
  return text || fallback
}
</script>

<template>
  <section class="learning-workspace">
    <div class="material-list-card">
      <div class="section-head">
        <div>
          <h3>学习资料列表</h3>
          <p>按分类筛选医生学习资料，并查看详情。</p>
        </div>
      </div>

      <form class="toolbar" @submit.prevent="emit('search')">
        <input v-model="query.category" type="text" placeholder="例如：心血管疾病" />
        <button type="submit" class="secondary-action">查询资料</button>
      </form>

      <div v-if="materialsLoading" class="empty-card">正在加载学习资料...</div>

      <div v-else-if="materials.length" class="material-list">
        <article v-for="material in materials" :key="material.id" class="material-item"
          :class="{ active: material.id === selectedMaterialId }" @click="emit('select-material', material.id)">
          <div class="material-head">
            <h4>{{ material.title }}</h4>
            <span class="type-badge">{{ material.type || '资料' }}</span>
          </div>
          <p>{{ shortText(material.url, '点击查看详情') }}</p>
        </article>
      </div>

      <div v-else class="empty-card">暂无学习资料，请调整分类关键词后重试。</div>

      <div class="pager">
        <button type="button" class="secondary-action" :disabled="query.page <= 1"
          @click="emit('page-change', -1)">上一页</button>
        <span>第 {{ query.page }} / {{ materialPageCount }} 页，共 {{ learningTotal }} 条</span>
        <button type="button" class="secondary-action" :disabled="query.page >= materialPageCount"
          @click="emit('page-change', 1)">
          下一页
        </button>
      </div>
    </div>

    <div class="material-detail-card">
      <div class="section-head">
        <div>
          <h3>资料详情</h3>
          <p>支持查看正文或打开外部资源链接。</p>
        </div>
      </div>

      <div v-if="materialDetailLoading" class="empty-card">正在加载资料详情...</div>

      <div v-else-if="materialDetail" class="detail-card accent">
        <div class="detail-title-row">
          <div>
            <p class="summary-label">资料标题</p>
            <h4>{{ materialDetail.title }}</h4>
          </div>
          <button v-if="materialDetail.url" type="button" class="secondary-action"
            @click="emit('open-material-link', materialDetail.url)">
            打开原文
          </button>
        </div>

        <div class="material-content">
          <p>{{ shortText(materialDetail.content, '该资料未返回正文，可通过原文链接查看。') }}</p>
        </div>
      </div>

      <div v-else class="empty-card">从左侧选择一份资料后，这里会显示详情。</div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.learning-workspace {
  display: grid;
  grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* ───────────────── Panels ───────────────── */
.material-list-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-light);
  overflow: hidden;
}

.material-detail-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--color-bg-base);
  overflow-y: auto;
}

/* ───────────────── Material head ───────────────── */
.material-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}

/* ───────────────── Material list ───────────────── */
.material-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.material-item {
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border-item);
  cursor: pointer;
  transition: background var(--transition-fast);
  flex-shrink: 0;

  &:hover {
    background: var(--color-patient-select-hover);
  }

  &.active {
    background: var(--color-patient-select-active);
    border-left: 3px solid var(--color-active-border);
    padding-left: 11px;
  }

  h4 {
    margin: 0 0 3px;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-text-strong);
  }

  p {
    margin: 0;
    font-size: 13px;
    color: var(--color-text-medium);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.type-badge {
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 700;
  background: var(--color-badge-accent-bg);
  color: var(--color-orange);
  white-space: nowrap;
}

/* ───────────────── Material detail ───────────────── */
.detail-card.accent {
  background: var(--color-detail-accent-bg);
  border-top: 3px solid var(--color-primary);
  border-left: none;
}

.detail-title-row h4 {
  font-size: 16px;
}

.material-content {
  padding: 12px 14px;
  border-left: 2px solid var(--color-border);
  background: var(--color-bg-light);

  p {
    margin: 0;
    color: var(--color-text-medium);
    font-size: 14px;
    line-height: 1.6;
  }
}

@media (max-width: 1080px) {
  .learning-workspace {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }

  .material-list-card {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    max-height: 340px;
    overflow: hidden;
  }
}

@media (max-width: 640px) {

  .section-head,
  .toolbar,
  .pager,
  .material-head,
  .detail-title-row {
    flex-wrap: wrap;
  }
}
</style>