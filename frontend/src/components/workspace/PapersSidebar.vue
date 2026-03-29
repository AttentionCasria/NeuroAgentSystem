<script setup>
import { computed } from 'vue'

defineOptions({ name: 'PapersSidebar' })

const props = defineProps({
  papers: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

// 证据等级 → pill 样式类名
const EVIDENCE_HIGH = new Set(['Practice Guideline', 'Guideline', 'Meta-Analysis', 'Systematic Review'])
const EVIDENCE_MID = new Set(['Randomized Controlled Trial', 'Clinical Trial'])

function pillClass(type) {
  if (EVIDENCE_HIGH.has(type)) return 'pill pill--high'
  if (EVIDENCE_MID.has(type)) return 'pill pill--mid'
  return 'pill pill--low'
}

// 只展示有意义的文章类型标签（过滤掉噪音类型如 "Journal Article"）
const DISPLAY_TYPES = new Set([
  'Practice Guideline', 'Guideline', 'Meta-Analysis', 'Systematic Review',
  'Randomized Controlled Trial', 'Clinical Trial', 'Review', 'Case Reports',
])

function displayTypes(pubTypes) {
  const filtered = (pubTypes || []).filter((t) => DISPLAY_TYPES.has(t))
  return filtered.length ? filtered : []
}

const isEmpty = computed(() => !props.loading && props.papers.length === 0)
</script>

<template>
  <div class="papers-sidebar">
    <div class="papers-header">
      <h3 class="papers-title">相关文献</h3>
      <p class="papers-subtitle">PubMed 最新循证证据</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="papers-state papers-state--loading">
      <span class="spinner" />
      <span>正在检索 PubMed...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="isEmpty" class="papers-state papers-state--empty">
      完成一次问诊后将自动推送相关文献
    </div>

    <!-- 论文卡片列表 -->
    <ul v-else class="paper-list">
      <li v-for="paper in papers" :key="paper.pmid" class="paper-card">
        <!-- 期刊名（权威性第一眼） -->
        <div class="paper-journal">{{ paper.journal }}</div>

        <!-- 标题（可点击，新标签打开 PubMed 链接） -->
        <a
          :href="paper.url"
          target="_blank"
          rel="noopener noreferrer"
          class="paper-title"
        >{{ paper.title }}</a>

        <!-- 作者 + 日期 -->
        <div class="paper-meta">
          {{ [paper.authors, paper.pub_date].filter(Boolean).join(' · ') }}
        </div>

        <!-- 证据等级标签 -->
        <div v-if="displayTypes(paper.pub_type).length" class="paper-types">
          <span
            v-for="type in displayTypes(paper.pub_type)"
            :key="type"
            :class="pillClass(type)"
          >{{ type }}</span>
        </div>

        <!-- 摘要（默认折叠，点击展开） -->
        <details v-if="paper.abstract" class="paper-abstract">
          <summary>摘要</summary>
          <p class="paper-abstract-text">{{ paper.abstract }}</p>
        </details>
      </li>
    </ul>

    <!-- 底部免责声明 + 数据来源 -->
    <div v-if="!loading" class="papers-footer">
      <p class="papers-disclaimer">文献仅供参考，请结合临床判断</p>
      <p class="papers-source">数据来源: PubMed, U.S. National Library of Medicine</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.papers-sidebar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
  margin-top: 12px;
}

.papers-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.papers-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-strong);
  margin: 0;
}

.papers-subtitle {
  font-size: 11px;
  color: var(--color-text-weak);
  margin: 0;
}

/* ── 状态占位 ── */
.papers-state {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-weak);
  padding: 8px 0;
}

.papers-state--empty {
  font-style: italic;
}

/* 旋转加载圈 */
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 论文列表 ── */
.paper-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.paper-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: var(--color-bg-base);
  border: 1px solid var(--color-border-item);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast);

  &:hover {
    border-color: var(--color-border);
  }
}

.paper-journal {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-primary-dark);
}

.paper-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-strong);
  line-height: 1.4;
  text-decoration: none;

  &:hover {
    color: var(--color-primary);
    text-decoration: underline;
  }
}

.paper-meta {
  font-size: 11px;
  color: var(--color-text-weak);
  line-height: 1.3;
}

/* ── 证据等级 pill ── */
.paper-types {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.pill {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
  font-size: 10px;
  font-weight: 600;
  line-height: 1.6;
}

/* 红色：指南 / Meta-Analysis / Systematic Review */
.pill--high {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

/* 黄色：RCT / Clinical Trial */
.pill--mid {
  background: rgba(180, 83, 9, 0.1);
  color: var(--color-orange);
}

/* 灰色：普通综述 / Case Reports / 其他 */
.pill--low {
  background: var(--color-badge-status-bg);
  color: var(--color-badge-status-color);
}

/* ── 摘要折叠区 ── */
.paper-abstract {
  margin-top: 2px;

  summary {
    font-size: 11px;
    color: var(--color-text-medium);
    cursor: pointer;
    user-select: none;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 4px;

    &::before {
      content: '▶';
      font-size: 8px;
      transition: transform var(--transition-fast);
    }

    &:hover {
      color: var(--color-primary);
    }
  }

  &[open] summary::before {
    transform: rotate(90deg);
  }
}

.paper-abstract-text {
  font-size: 11px;
  color: var(--color-text-medium);
  line-height: 1.5;
  margin: 6px 0 0;
}

/* ── 底部信息 ── */
.papers-footer {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 6px;
  border-top: 1px solid var(--color-border-light);
}

.papers-disclaimer {
  font-size: 10px;
  color: var(--color-text-weak);
  margin: 0;
}

.papers-source {
  font-size: 10px;
  color: var(--color-text-weak);
  margin: 0;
  font-style: italic;
}
</style>
