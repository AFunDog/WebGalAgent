<template>
  <div class="app-shell">
    <div class="app-shell__glow app-shell__glow--left"></div>
    <div class="app-shell__glow app-shell__glow--right"></div>
    <div class="app-layout">
      <!-- 顶部信息条：展示产品名与当前应用定位 -->
      <header class="topbar">
        <div class="topbar-brand">
          <div class="topbar-mark">WG</div>
          <div>
            <h1>WebGalAgent</h1>
            <p>Dark workflow console for writing, routing, and recording</p>
          </div>
        </div>
        <div class="topbar-chip">Theme · #f7630c</div>
      </header>

      <!-- 左侧导航：承载一级页面切换 -->
      <AppSidebar />

      <!-- 主内容区：由路由视图承载具体业务页面 -->
      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './components/AppSidebar.vue'

// App.vue 只负责应用级布局，不维护页面级业务状态。
</script>
