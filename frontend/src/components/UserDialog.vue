<script setup>
import EditForm from './form/EditForm.vue'
defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}
</script>

<template>
  <!-- 过渡动画 -->
  <transition name="fade">
    <div v-if="visible" class="overlay">
      <transition name="zoom">
        <div class="dialog" v-if="visible">
          <!-- 头部 -->
          <div class="dialog-header">
            <h2>设置</h2>
            <button class="close-btn" @click="close">&times;</button>
          </div>


          <!-- 编辑信息 -->
          <div>
            <EditForm></EditForm>
          </div>

        </div>
      </transition>
    </div>
  </transition>
</template>


<style lang="scss" scoped>
/* 遮罩层 */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

/* 弹出框 */
.dialog {
  background: #000000;
  border-radius: 10px;
  width: 320px;
  max-width: 90%;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h2 {
      font-size: 18px;
      margin: 0;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: #666;

      &:hover {
        color: #fff;
      }
    }

  }

  .dialog-content {
    margin: 15px 0;
    font-size: 14px;
    color: #333;
  }

}


/* 遮罩层淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 弹窗缩放淡入淡出 */
.zoom-enter-active,
.zoom-leave-active {
  transition: all 0.25s ease;
}

.zoom-enter-from,
.zoom-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
