import { createApp } from 'vue'
import 'bootstrap/dist/css/bootstrap.min.css'
import '@fontsource-variable/fraunces'
import '@fontsource-variable/inter'
import './styles.css'
import App from './App.vue'
import { router } from './router.js'

createApp(App).use(router).mount('#app')
