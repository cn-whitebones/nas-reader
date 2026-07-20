<template>
  <router-view />
</template>

<script setup lang="ts"></script>

<style>
* { box-sizing: border-box; }
html, body, #app { margin: 0; }
/* 高度优先用 JS 持续校正的 --app-height(visualViewport 真实高度),
   多级回退:老浏览器 100vh → 支持则 100dvh → JS 就绪后 --app-height。 */
html { height: 100vh; height: 100dvh; background: var(--app-bg, #f5f7fa); }
#app { height: 100vh; height: 100dvh; height: var(--app-height, 100dvh); }
body {
  height: 100vh;
  height: 100dvh;
  height: var(--app-height, 100dvh);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  overflow-x: hidden;
  background: var(--app-bg, #f5f7fa);
}
</style>
