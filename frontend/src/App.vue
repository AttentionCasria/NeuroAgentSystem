<script setup>

</script>

<template>
  <router-view></router-view>
</template>

<style lang="scss">
@use '@/styles/variables.scss';
@use '@/styles/common.scss';
@use '@/styles/transitions.scss';

* {
  font-family:
    ui-sans-serif,
    -apple-system,
    system-ui,
    Segoe UI,
    Helvetica,
    Apple Color Emoji,
    Arial,
    sans-serif,
    Segoe UI Emoji,
    Segoe UI Symbol;
}

html,
body {
  transition: background-color 0.3s ease, color 0.3s ease;
}
</style>
