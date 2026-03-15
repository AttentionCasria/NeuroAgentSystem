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
    <div class="section-card material-list-card">
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
        <article
          v-for="material in materials"
          :key="material.id"
          class="material-item"
          :class="{ active: material.id === selectedMaterialId }"
          @click="emit('select-material', material.id)"
        >
          <div class="material-head">
            <h4>{{ material.title }}</h4>
            <span class="type-badge">{{ material.type || '资料' }}</span>
          </div>
          <p>{{ shortText(material.url, '点击查看详情') }}</p>
        </article>
      </div>

      <div v-else class="empty-card">暂无学习资料，请调整分类关键词后重试。</div>

      <div class="pager">
        <button type="button" class="secondary-action" :disabled="query.page <= 1" @click="emit('page-change', -1)">上一页</button>
        <span>第 {{ query.page }} / {{ materialPageCount }} 页，共 {{ learningTotal }} 条</span>
        <button
          type="button"
          class="secondary-action"
          :disabled="query.page >= materialPageCount"
          @click="emit('page-change', 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <div class="section-card material-detail-card">
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
          <button v-if="materialDetail.url" type="button" class="secondary-action" @click="emit('open-material-link', materialDetail.url)">
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
  grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
}

.section-card,
.material-item,
.detail-card {
  border: 1px solid rgba(217, 230, 226, 0.95);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 45px rgba(15, 65, 79, 0.12);
}

.section-card {
  border-radius: 28px;
  padding: 20px;
}

.section-head,
.toolbar,
.pager,
.material-head,
.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-head h3,
.detail-title-row h4 {
  margin: 0;
}

.section-head p,
.material-item p,
.empty-card,
.material-content p {
  color: #5e7379;
}

.toolbar input {
  flex: 1 1 240px;
  width: 100%;
  border: 1px solid rgba(191, 213, 207, 0.95);
  background: rgba(249, 252, 252, 0.96);
  border-radius: 14px;
  padding: 12px 14px;
  font: inherit;
  color: #17313a;
  box-sizing: border-box;
}

.secondary-action {
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
  padding: 11px 16px;
  border-radius: 14px;
  font-weight: 700;
  background: rgba(230, 241, 238, 0.9);
  color: #17313a;
}

.material-list-card,
.material-detail-card,
.material-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.material-list {
  overflow-y: auto;
}

.material-item,
.detail-card {
  border-radius: 18px;
}

.material-item {
  padding: 15px 16px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.material-item:hover,
.material-item.active {
  transform: translateY(-1px);
  border-color: rgba(17, 150, 127, 0.28);
  background: rgba(240, 249, 247, 0.96);
}

.material-item h4 {
  margin: 0;
}

.type-badge {
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.detail-card {
  padding: 18px;
}

.detail-card.accent {
  background: linear-gradient(135deg, rgba(17, 150, 127, 0.1), rgba(255, 255, 255, 0.95));
}

.material-content {
  margin-top: 14px;
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(217, 230, 226, 0.9);
}

.material-content p,
.summary-label {
  margin: 0;
}

.summary-label {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2c7c6e;
}

.empty-card {
  padding: 24px;
  border-radius: 18px;
  background: rgba(248, 251, 251, 0.88);
  border: 1px dashed rgba(169, 195, 190, 0.9);
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .learning-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .section-head,
  .toolbar,
  .pager,
  .material-head,
  .detail-title-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>