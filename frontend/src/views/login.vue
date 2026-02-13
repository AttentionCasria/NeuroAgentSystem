<script setup>
defineOptions({
  name: 'LoginIndex',
})
import LeftIntro from '@/components/LeftIntro.vue'
import RightForm from '@/components/RightForm.vue'
</script>

<template>
  <div class="container">
    <div class="left-intro">
      <LeftIntro></LeftIntro>
    </div>
    <div class="right-form">
      <RightForm></RightForm>
    </div>
  </div>
</template>

<style scoped lang="scss">
.container {
  display: flex;
  width: 100%;
  height: 100vh;

  .left-intro {
    flex: 6;
    min-width: 0;
    background-color: #f0f7ff;
    color: #1e293b;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    padding: 2rem;
  }

  .right-form {
    flex: 4;
    min-width: 0;
    background-color: #ffffff;
    color: #333;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
