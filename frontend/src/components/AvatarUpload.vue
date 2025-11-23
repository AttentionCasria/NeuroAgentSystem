<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import request from '@/utils/request'

// props: showTip 控制是否显示红色提示, initialAvatar 传入初始头像地址
const props = defineProps({
  showTip: {
    type: Boolean,
    default: false
  },
  initialAvatar: {
    type: String,
    default: '' // 如果没传，就为空字符串
  }
})

// emit: 上传完成后触发 uploaded 事件，传递图片地址
const emit = defineEmits(['uploaded'])

const avatarUrl = ref(props.initialAvatar) // 初始化时直接赋值一次
const fileInput = ref(null)


const triggerUpload = () => {
  fileInput.value.click()
}

const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 校验图片格式
  const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
  if (!validTypes.includes(file.type)) {
    alert('请选择 jpg / png / webp 格式的图片')
    return
  }

  // 构造 FormData
  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await request.post('/user/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res.code === 1) {
      avatarUrl.value = res.data // 阿里云 OSS 返回的图片地址
      emit('uploaded', avatarUrl.value) // 上传完成触发事件
    } else {
      alert('上传失败')
    }
  } catch (err) {
    console.error(err)
    alert('上传出错')
  } finally {
    e.target.value = '' // 重置 input，确保能重复选择同一文件
  }
}
</script>


<template>
  <div class="avatar-upload">
    <!-- 有头像就显示头像 -->
    <div v-if="avatarUrl" class="avatar-preview" @click="triggerUpload">
      <img :src="avatarUrl" alt="avatar" />
      <div class="avatar-overlay">更换头像</div>
    </div>
    <div v-else class="upload-btn" @click="triggerUpload">上传头像</div>

    <!-- 红色提示 -->
    <div v-if="props.showTip && !avatarUrl" class="tip-text">请选择图片！</div>

    <input
      type="file"
      ref="fileInput"
      class="file-input"
      accept="image/*"
      @change="handleFileChange" />
  </div>
</template>

<style scoped lang="scss">
.avatar-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #fff;

  .upload-btn {
    padding: 12px 20px;
    background-color: #07bf9b;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background-color: #05a583;
    }
  }

  .file-input {
    display: none;
  }

  .tip-text {
    margin-top: 8px;
    color: red;
    font-size: 14px;
  }

  .avatar-preview {
    position: relative;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    overflow: hidden;
    cursor: pointer;
    border: 2px solid #07bf9b;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .avatar-overlay {
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 30%;
      background: rgba(0, 0, 0, 0.6);
      color: #07bf9b;
      font-size: 12px;
      display: flex;
      justify-content: center;
      align-items: center;
      opacity: 0;
      transition: opacity 0.2s;
    }

    &:hover .avatar-overlay {
      opacity: 1;
    }
  }
}
</style>
