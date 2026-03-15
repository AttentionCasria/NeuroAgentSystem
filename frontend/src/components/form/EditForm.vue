<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AvatarUpload from '../AvatarUpload.vue'
import { useUserStore } from '@/stores/user'
import { logoutAPI, updateInfoAPI } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()

const EditFormData = ref({
  prePassword: '',
  newPassword: ''
})
const image = ref('')
const errorMessage = ref('')

async function handleUpdateInfo() {
  errorMessage.value = ''

  if (!EditFormData.value.prePassword) {
    errorMessage.value = '旧密码不能为空'
    return
  }
  if (EditFormData.value.prePassword.length < 6) {
    errorMessage.value = '旧密码至少为6个字符'
    return
  }
  if (!EditFormData.value.newPassword) {
    errorMessage.value = '新密码不能为空'
    return
  }
  if (EditFormData.value.newPassword.length < 6) {
    errorMessage.value = '新密码至少为6个字符'
    return
  }

  const updateForm = {
    prePassword: EditFormData.value.prePassword,
    newPassword: EditFormData.value.newPassword,
    image: image.value || userStore.image // 如果没有新上传头像，就用原来的
  }

  try {
    await updateInfoAPI(updateForm)
    alert('修改成功，请重新登录')
    userStore.reset()
    router.replace('/login')
  } catch (error) {
    // 说明密码错误
    console.log(error)
    errorMessage.value = '旧密码错误，修改失败'
  }
}

function handleAvatarUploadSuccess(url) {
  image.value = url
}

async function handleLogout() {
  await logoutAPI()
  userStore.reset()
  router.replace('/login')
}
</script>

<template>
  <div class="custom-form">
    <div class="form-header">
      <p class="greeting">Hi, {{ userStore.name }}</p>
    </div>

    <div class="input-group">
      <div class="input-wrapper">
        <span class="icon">
          <PasswordSVG size="20" color="var(--color-text-medium)"></PasswordSVG>
        </span>
        <input v-model="EditFormData.prePassword" type="password" placeholder="请输入旧密码" />
      </div>
    </div>

    <div class="input-group">
      <div class="input-wrapper">
        <span class="icon">
          <PasswordSVG size="20" color="var(--color-text-medium)"></PasswordSVG>
        </span>
        <input v-model="EditFormData.newPassword" type="password" placeholder="请输入新密码" />
      </div>
    </div>

    <div class="avatar-upload-container">
      <AvatarUpload :initialAvatar="userStore.image" :initialName="userStore.name"
        @uploaded="url => handleAvatarUploadSuccess(url)" />
    </div>

    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    <button class="primary-action submit-btn" @click="handleUpdateInfo">确认修改</button>
    <button class="danger-action logout-btn" @click="handleLogout">退出登录</button>
  </div>
</template>

<style scoped lang="scss">
.custom-form {
  width: 100%;
}

.form-header {
  margin-bottom: 1.5rem;
}

.greeting {
  font-size: 16px;
  color: var(--color-text-strong);
  margin: 0;
  font-weight: bold;
}

.input-group {
  margin-bottom: 1.25rem;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;

  .icon {
    position: absolute;
    left: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }

  input {
    width: 100%;
    height: 48px;
    padding: 0 16px 0 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-input);
    color: var(--color-text-strong);
    font-size: 15px;
    transition: all var(--transition-fast);
    box-sizing: border-box;

    &::placeholder {
      color: var(--color-text-weak);
    }

    &:focus {
      outline: none;
      border-color: var(--color-primary);
      box-shadow: 0 0 0 3px rgba(17, 150, 127, 0.15);
    }
  }
}

.avatar-upload-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 1.25rem;
}

.error-message {
  color: #ef4444;
  font-size: 13px;
  margin-bottom: 1rem;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-bottom: 0.75rem;
}

.danger-action {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-red, #ef4444);
  color: white;
  cursor: pointer;
  transition: opacity var(--transition-normal);

  &:hover {
    opacity: 0.88;
  }
}
</style>
