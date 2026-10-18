import { createApp } from 'vue'
import 'bootstrap/dist/css/bootstrap.min.css'
import '@fontsource-variable/fraunces'
import '@fontsource-variable/inter'
import '@fontsource-variable/fredoka'
import '@fontsource-variable/nunito'
import '@fontsource/silkscreen/400.css'
import './styles.css'
import './retro.css'
import App from './App.vue'
import { router } from './router.js'

createApp(App).use(router).mount('#app')
