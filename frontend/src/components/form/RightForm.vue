<script setup>
import { ref } from 'vue'
import LoginForm from './LoginForm.vue'
import RegisterForm from './RegisterForm.vue'

const isLogin = ref(true)
</script>

<template>
  <div class="content">
    <transition name="fade" mode="out-in">
      <div :key="isLogin ? 'login' : 'register'" class="form-wrapper">
        <LoginForm v-if="isLogin" />
        <RegisterForm v-else />
        <div class="switch-text" @click="isLogin = !isLogin">
          <span v-if="isLogin">新用户？去注册</span>
          <span v-else>已有帐号？去登录</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped lang="scss">
.fade-enter-from {
  opacity: 0;
  transform: perspective(600px) rotateY(-90deg);
}

.fade-leave-to {
  opacity: 0;
  transform: perspective(600px) rotateY(90deg);
}

.fade-enter-active,
.fade-leave-active {
  transition: all 0.2s ease-out;
}

.content {
  width: 70%;
}

.switch-text {
  margin-top: 1rem;
  text-align: center;
  color: var(--color-primary);
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}
</style>
