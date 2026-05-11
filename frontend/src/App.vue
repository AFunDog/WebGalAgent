<template>
  <div class="app-layout">
    <header class="topbar">
      <h1>WebGalAgent</h1>
      <span style="color:var(--text-muted);font-size:13px">多智能体协作工作流</span>
    </header>
    <AppSidebar />
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './components/AppSidebar.vue'
</script>
