<script setup>
defineOptions({ name: 'PatientFormDialog' })

defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'create',
  },
})

const form = defineModel('form', { required: true })

const emit = defineEmits(['close', 'submit'])
</script>

<template>
  <div v-if="visible" class="dialog-overlay" @click.self="emit('close')">
    <div class="dialog-card" @click.stop>
      <div class="dialog-head">
        <div>
          <p class="summary-label">患者信息</p>
          <h3>{{ mode === 'edit' ? '编辑患者' : '新增患者' }}</h3>
        </div>
        <button type="button" class="ghost-icon" @click="emit('close')">✕</button>
      </div>

      <div class="dialog-body form-stack">
        <label class="field-label">
          姓名
          <input v-model="form.name" type="text" placeholder="请输入患者姓名" />
        </label>
        <label class="field-label">
          病史
          <textarea v-model="form.history" rows="5" placeholder="请输入既往病史或慢性病信息"></textarea>
        </label>
        <label class="field-label">
          医生备注
          <textarea v-model="form.notes" rows="5" placeholder="请输入医嘱、随访或注意事项"></textarea>
        </label>
      </div>

      <div class="dialog-footer">
        <button type="button" class="secondary-action" @click="emit('close')">取消</button>
        <button type="button" class="primary-action" @click="emit('submit')">保存</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.ghost-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--color-secondary-bg);
}

.primary-action,
.secondary-action {
  padding: 11px 16px;
  border-radius: var(--radius-lg);
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 18px;
}

.field-label input,
.field-label textarea {
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  border-color: var(--color-border);
  background: var(--color-bg-input);
}

.field-label {
  gap: 8px;
}

@media (max-width: 640px) {

  .dialog-head,
  .dialog-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>