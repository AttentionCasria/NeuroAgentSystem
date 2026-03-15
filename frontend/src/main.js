import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedstate from 'pinia-plugin-persistedstate'

import App from './App.vue'
import router from './router'

// 全局注册图标组件
import UserSVG from './components/svg/UserSVG.vue'
import PasswordSVG from './components/svg/PasswordSVG.vue'
import SendSVG from './components/svg/SendSVG.vue'

import 'normalize.css'

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPersistedstate)

app.use(pinia)
app.use(router)

// 初始化主题
import { useThemeStore } from './stores/theme'
const themeStore = useThemeStore()
themeStore.applyTheme()

app.component('UserSVG', UserSVG)
app.component('PasswordSVG', PasswordSVG)
app.component('SendSVG', SendSVG)

app.mount('#app')
