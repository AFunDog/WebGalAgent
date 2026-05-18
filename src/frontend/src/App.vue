<template>
  <div class="app-layout">
    <!-- 顶部信息条：展示产品名与当前应用定位 -->
    <header class="topbar">
      <h1>WebGalAgent</h1>
      <span style="color:var(--text-muted);font-size:13px">多智能体协作工作流</span>
    </header>

    <!-- 左侧导航：承载一级页面切换 -->
    <AppSidebar />

    <!-- 主内容区：由路由视图承载具体业务页面 -->
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './components/AppSidebar.vue'

// App.vue 只负责应用级布局，不维护页面级业务状态。
</script>
