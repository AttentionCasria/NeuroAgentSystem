<script setup>
defineOptions({
  name: 'LoginIndex',
})
import LeftIntro from '@/components/LeftIntro.vue'
import RightForm from '@/components/form/RightForm.vue'
</script>

<template>
  <div class="login-page">
    <div class="login-left">
      <LeftIntro></LeftIntro>
    </div>
    <div class="login-right">
      <RightForm></RightForm>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  display: flex;
  width: 100%;
  height: 100vh;
  background: var(--color-bg-base);
}

.login-left {
  flex: 6;
  min-width: 0;
  background: var(--color-bg-light);
  color: var(--color-text-strong);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 2rem;
  border-right: 1px solid var(--color-border);
}

.login-right {
  flex: 4;
  min-width: 0;
  background: var(--color-bg-base);
  color: var(--color-text-strong);
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 960px) {
  .login-page {
    flex-direction: column;
  }

  .login-left {
    flex: none;
    min-height: 280px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }

  .login-right {
    flex: 1;
    padding: 2rem 1rem;
  }
}
</style>
