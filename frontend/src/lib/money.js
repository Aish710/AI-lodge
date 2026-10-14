// Amounts in the interface are always printed in the SELECTED city's own currency. Components call this, never a hardcoded yen formatter.
import { store } from '../store.js'
import { formatLocalMoney } from './format.js'

export const cityCurrency = () => store.city?.currency_code ?? 'JPY'
export const money = (n) => formatLocalMoney(n, cityCurrency())
