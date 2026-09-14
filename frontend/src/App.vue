<script setup>
</script>

<template>
  <div id="app">
    <header class="masthead">
      <div class="title">🌙 一夜狼人</div>
      <div class="tagline">ONE NIGHT WEREWOLF</div>
    </header>

    <nav class="nav">
      <router-link class="nav-link" to="/">主页</router-link>
      <router-link class="nav-link" to="/createroom">创建房间</router-link>
      <router-link class="nav-link" to="/joinroom">加入房间</router-link>
    </nav>

    <router-view />
  </div>
</template>