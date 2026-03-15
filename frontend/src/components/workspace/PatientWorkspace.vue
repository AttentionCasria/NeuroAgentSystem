<script setup>
defineOptions({ name: 'PatientWorkspace' })

const props = defineProps({
  patients: {
    type: Array,
    default: () => [],
  },
  patientTotal: {
    type: Number,
    default: 0,
  },
  patientsLoading: {
    type: Boolean,
    default: false,
  },
  selectedPatientId: {
    type: [Number, null],
    default: null,
  },
  patientDetail: {
    type: Object,
    default: null,
  },
  patientDetailLoading: {
    type: Boolean,
    default: false,
  },
  patientPageCount: {
    type: Number,
    default: 1,
  },
})

const query = defineModel('query', { required: true })
const analysisText = defineModel('analysisText', { default: '' })

const emit = defineEmits([
  'search',
  'select-patient',
  'open-create',
  'open-edit',
  'delete-patient',
  'analyze-patient',
  'page-change',
])

function shortText(value, fallback = '暂无内容') {
  const text = String(value || '').trim()
  return text || fallback
}

function formatDateTime(value) {
  if (!value) return '暂无时间'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <section class="patient-workspace">
    <div class="section-card patient-list-card">
      <div class="section-head wrap">
        <div>
          <h3>患者列表</h3>
          <p>支持分页筛选、新增、编辑和删除患者。</p>
        </div>
        <button type="button" class="primary-action" @click="emit('open-create')">新增患者</button>
      </div>

      <form class="toolbar" @submit.prevent="emit('search')">
        <input v-model="query.name" type="text" placeholder="按姓名筛选" />
        <input v-model="query.diseases" type="text" placeholder="按疾病史筛选" />
        <button type="submit" class="secondary-action">查询</button>
      </form>

      <div v-if="patientsLoading" class="empty-card">正在加载患者列表...</div>

      <div v-else-if="patients.length" class="patient-list">
        <article
          v-for="patient in patients"
          :key="patient.id"
          class="patient-item"
          :class="{ active: patient.id === selectedPatientId }"
          @click="emit('select-patient', patient.id)"
        >
          <div class="patient-item-head">
            <div>
              <h4>{{ patient.name }}</h4>
              <small>患者 #{{ patient.id }}</small>
            </div>
            <span class="risk-badge">{{ patient.aiOpinion?.riskLevel || '待评估' }}</span>
          </div>

          <p>{{ shortText(patient.history) }}</p>

          <div class="patient-item-actions">
            <button type="button" class="link-btn" @click.stop="emit('open-edit', patient)">编辑</button>
            <button type="button" class="link-btn danger-text" @click.stop="emit('delete-patient', patient.id)">删除</button>
          </div>
        </article>
      </div>

      <div v-else class="empty-card">还没有患者数据，先新增一位患者开始管理。</div>

      <div class="pager">
        <button type="button" class="secondary-action" :disabled="query.page <= 1" @click="emit('page-change', -1)">上一页</button>
        <span>第 {{ query.page }} / {{ patientPageCount }} 页，共 {{ patientTotal }} 条</span>
        <button
          type="button"
          class="secondary-action"
          :disabled="query.page >= patientPageCount"
          @click="emit('page-change', 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <div class="section-card patient-detail-card">
      <div class="section-head">
        <div>
          <h3>患者详情与AI意见</h3>
          <p>查看完整病史，并可追加健康数据进行风险分析。</p>
        </div>
      </div>

      <div v-if="patientDetailLoading" class="empty-card">正在加载患者详情...</div>

      <div v-else-if="patientDetail" class="detail-stack">
        <section class="detail-card">
          <div class="detail-title-row">
            <div>
              <p class="summary-label">患者信息</p>
              <h4>{{ patientDetail.name }}</h4>
            </div>
            <button type="button" class="secondary-action" @click="emit('open-edit', patientDetail)">编辑信息</button>
          </div>

          <div class="detail-grid">
            <article>
              <h5>既往病史</h5>
              <p>{{ shortText(patientDetail.history) }}</p>
            </article>
            <article>
              <h5>医生备注</h5>
              <p>{{ shortText(patientDetail.notes) }}</p>
            </article>
          </div>
        </section>

        <section class="detail-card accent">
          <div class="detail-title-row">
            <div>
              <p class="summary-label">AI分析意见</p>
              <h4>{{ patientDetail.aiOpinion?.riskLevel || '暂未生成' }}</h4>
            </div>
            <small>{{ formatDateTime(patientDetail.aiOpinion?.lastUpdatedAt) }}</small>
          </div>

          <div class="detail-grid single">
            <article>
              <h5>处理建议</h5>
              <p>{{ shortText(patientDetail.aiOpinion?.suggestion, '暂无建议') }}</p>
            </article>
            <article>
              <h5>分析详情</h5>
              <p>{{ shortText(patientDetail.aiOpinion?.analysisDetails, '暂无分析详情') }}</p>
            </article>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-title-row">
            <div>
              <p class="summary-label">手动触发AI分析</p>
              <h4>补充健康数据</h4>
            </div>
          </div>

          <textarea
            v-model="analysisText"
            class="analysis-input"
            rows="6"
            placeholder="例如：近三天血压持续偏高，夜间头痛加重，伴手脚麻木..."
          ></textarea>
          <button type="button" class="primary-action" @click="emit('analyze-patient')">执行风险分析</button>
        </section>
      </div>

      <div v-else class="empty-card">从左侧选择一位患者后，这里会展示完整病历和AI分析结果。</div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.patient-workspace {
  display: grid;
  grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
}

.section-card,
.detail-card,
.patient-item {
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
.patient-item-head,
.patient-item-actions,
.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-head.wrap,
.toolbar {
  flex-wrap: wrap;
}

.section-head h3,
.detail-title-row h4 {
  margin: 0;
}

.section-head p,
.patient-item p,
.detail-card p,
.detail-card small,
.empty-card {
  color: #5e7379;
}

.toolbar input,
.analysis-input {
  width: 100%;
  border: 1px solid rgba(191, 213, 207, 0.95);
  background: rgba(249, 252, 252, 0.96);
  border-radius: 14px;
  padding: 12px 14px;
  font: inherit;
  color: #17313a;
  box-sizing: border-box;
}

.toolbar input {
  flex: 1 1 180px;
}

.analysis-input {
  min-height: 132px;
  resize: vertical;
}

.primary-action,
.secondary-action,
.link-btn {
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}

.primary-action,
.secondary-action {
  padding: 11px 16px;
  border-radius: 14px;
  font-weight: 700;
}

.primary-action {
  background: linear-gradient(135deg, #11967f 0%, #0f7666 100%);
  color: #ffffff;
}

.secondary-action {
  background: rgba(230, 241, 238, 0.9);
  color: #17313a;
}

.link-btn {
  background: transparent;
  padding: 0;
  color: #0f7666;
}

.danger-text {
  color: #dc2626;
}

.patient-list-card,
.patient-detail-card,
.detail-stack,
.patient-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.patient-list {
  overflow-y: auto;
}

.patient-item,
.detail-card {
  border-radius: 18px;
}

.patient-item {
  padding: 15px 16px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.patient-item:hover,
.patient-item.active {
  transform: translateY(-1px);
  border-color: rgba(17, 150, 127, 0.28);
  background: rgba(240, 249, 247, 0.96);
}

.patient-item h4,
.detail-card h5 {
  margin: 0 0 8px;
}

.risk-badge {
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

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.detail-grid.single {
  grid-template-columns: 1fr;
}

.detail-grid article {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(217, 230, 226, 0.9);
}

.summary-label {
  margin: 0;
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
  .patient-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .section-head,
  .toolbar,
  .pager,
  .patient-item-head,
  .detail-title-row,
  .detail-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>