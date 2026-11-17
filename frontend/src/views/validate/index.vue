<template>
  <section class="page" data-module="validate">
    <header class="page-head">
      <div><h2>采集校验</h2><p class="page-desc">校验采集结果的行数、格式、空值和重复，对异常设定阻断或告警。</p></div>
    </header>
    <div class="analysis-summary">
      <article v-for="m in summaryMetrics" :key="m.label" class="analysis-card" data-testid="kpi-card">
        <span style="font-size:12px;color:var(--muted)">{{ m.label }}</span>
        <strong style="font-size:22px;display:block">{{ m.value }}</strong>
        <span v-if="typeof m.trend === 'number' && m.trend !== 0" :class="m.trend > 0 ? 'trend-up' : 'trend-down'" style="font-size:12px">{{ m.trend > 0 ? '↑' : '↓' }}{{ Math.abs(m.trend) }}%</span>
      </article>
    </div>

    <!-- 校验趋势记录台账：由质量趋势数据报告的校验结论同步而来 -->
    <section class="trend-panel">
      <div class="trend-panel-head"><h3>校验趋势记录台账</h3><span class="muted-note">质量趋势数据报告同步</span></div>
      <table class="data-table" data-testid="trend-ledger">
        <thead><tr><th>统计周期</th><th>版本号</th><th>指标编号</th><th>样本数量</th><th>异常数</th><th>达标率</th><th>规则版本</th><th>校验结论</th></tr></thead>
        <tbody>
          <tr v-for="row in trendRecords" :key="row.id">
            <td>{{ row.统计周期 }}</td><td>{{ row.版本号 }}</td><td>{{ row.指标编号 }}</td>
            <td>{{ row.样本数量 }}</td><td>{{ row.异常数 }}</td><td>{{ formatRate(row.达标率) }}</td>
            <td>{{ row.规则版本 }}</td><td>{{ row.校验结论 }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!trendRecords.length" class="empty-state">暂无同步的校验趋势记录</p>
    </section>

    <!-- 采集校验异常处置台账 -->
    <section class="trend-panel">
      <div class="trend-panel-head"><h3>采集校验异常处置台账</h3><span class="muted-note">质量趋势异常结论回写</span></div>
      <table class="data-table" data-testid="anomaly-ledger">
        <thead><tr><th>统计周期</th><th>指标编号</th><th>样本数量</th><th>异常数</th><th>达标率</th><th>异常结论</th><th>处置状态</th></tr></thead>
        <tbody>
          <tr v-for="row in anomalyRecords" :key="row.id">
            <td>{{ row.统计周期 }}</td><td>{{ row.指标编号 }}</td><td>{{ row.样本数量 }}</td>
            <td>{{ row.异常数 }}</td><td>{{ formatRate(row.达标率) }}</td>
            <td>{{ row.异常结论 }}</td><td>{{ row.处置状态 }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!anomalyRecords.length" class="empty-state">暂无待处置异常</p>
    </section>

    <form class="analysis-form" @submit.prevent="runAnalysis">
      <label v-for="field in paramFields" :key="field"><span>{{ field }}</span>
        <select v-if="field === '统计周期'" v-model="params[field]">
          <option value="">全部统计周期</option>
          <option v-for="p in periods" :key="p" :value="p">{{ p }}</option>
        </select>
        <input v-else v-model="params[field]" :placeholder="`请输入${field}`" />
      </label>
      <button class="btn primary" type="submit" data-testid="run-analysis">运行分析</button>
    </form>
    <div v-if="chartData.length" class="analysis-chart">
      <div v-for="(bar, i) in chartData" :key="i" class="analysis-bar" :style="{ height: barHeight(bar.value) + 'px' }"><span>{{ bar.label }}</span></div>
    </div>
    <table class="data-table" v-if="results.length">
      <thead><tr><th v-for="c in resultColumns" :key="c">{{ c }}</th></tr></thead>
      <tbody><tr v-for="row in results" :key="row.id"><td v-for="c in resultColumns" :key="c">{{ row[c] ?? '—' }}</td></tr></tbody>
    </table>
    <p v-if="!results.length && !loading" style="text-align:center;color:var(--muted)">请配置参数后运行分析</p>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchJson, request } from '@/api/client'

const ENDPOINT = '/api/validate'
const summaryMetrics = ref<{ label: string; value: number | string; trend: number }[]>([])
const trendRecords = ref<any[]>([])
const anomalyRecords = ref<any[]>([])
const periods = ref<string[]>([])
const results = ref<any[]>([])
const chartData = ref<{ label: string; value: number }[]>([])
const loading = ref(false)
const params = ref<Record<string, string>>({})
const paramFields = ["统计周期", "校验字段", "期望格式", "空值阈值"]
const resultColumns = ["统计周期", "版本号", "规则版本", "样本数量", "异常数", "达标率", "校验结论"]

function formatRate(value: unknown) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  return `${(numeric * 100).toFixed(1)}%`
}

function barHeight(v: number) {
  const max = Math.max(...chartData.value.map(d => d.value), 1)
  return Math.max(10, (v / max) * 140)
}

async function fetchSummary() {
  try {
    const res = await request(`${ENDPOINT}/summary`)
    const data = await res.json()
    summaryMetrics.value = (data.metrics || []).map((m: any) => ({
      ...m,
      value: typeof m.value === 'number' && m.label === '达标率' ? formatRate(m.value) : m.value,
    }))
  } catch {
    summaryMetrics.value = [
      { label: '统计周期数', value: 0, trend: 0 },
      { label: '校验样本数', value: 0, trend: 0 },
      { label: '异常样本数', value: 0, trend: 0 },
      { label: '达标率', value: '—', trend: 0 },
    ]
  }
}

async function fetchLedgers() {
  try {
    const [trend, anomaly, periodList] = await Promise.all([
      fetchJson<{ items: any[] }>(`${ENDPOINT}/trend-records`),
      fetchJson<{ items: any[] }>(`${ENDPOINT}/anomaly-records`),
      fetchJson<{ items: string[] }>('/api/quality/trends/periods'),
    ])
    trendRecords.value = trend.items || []
    anomalyRecords.value = anomaly.items || []
    periods.value = periodList.items || []
  } catch {
    trendRecords.value = []
    anomalyRecords.value = []
    periods.value = []
  }
}

async function runAnalysis() {
  loading.value = true
  try {
    const res = await request(`${ENDPOINT}/run`, { method: 'POST', body: JSON.stringify({ values: params.value }) })
    const data = await res.json()
    results.value = data.items || []
    chartData.value = results.value
      .map((row: any) => ({ label: String(row.统计周期), value: Number(row.达标率) || 0 }))
      .slice(0, 6)
  } catch {
    results.value = []
    chartData.value = []
  }
  loading.value = false
}

onMounted(async () => {
  await Promise.all([fetchSummary(), fetchLedgers()])
})
</script>
