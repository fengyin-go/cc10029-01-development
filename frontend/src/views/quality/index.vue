<template>
  <section class="page" data-module="quality">
    <header class="page-head">
      <div>
        <h2>质量报告</h2>
        <p class="page-desc">定义采集质量统计的指标口径和阈值，从已落库采集样本生成可复现的质量趋势数据报告。</p>
      </div>
    </header>

    <!-- 结果看板：指标全部来自最新可见趋势批次 -->
    <div class="analysis-summary">
      <article v-for="m in summaryMetrics" :key="m.label" class="analysis-card" data-testid="kpi-card">
        <span style="font-size:12px;color:var(--muted)">{{ m.label }}</span>
        <strong style="font-size:22px;display:block">{{ m.value }}</strong>
        <span v-if="typeof m.trend === 'number' && m.trend !== 0" :class="m.trend > 0 ? 'trend-up' : 'trend-down'" style="font-size:12px">
          {{ m.trend > 0 ? '↑' : '↓' }}{{ Math.abs(m.trend) }}%
        </span>
      </article>
    </div>

    <!-- 质量趋势数据报告列表：同一统计周期只呈现一份带规则版本的报告 -->
    <section class="trend-panel">
      <div class="trend-panel-head">
        <h3>质量趋势数据报告</h3>
        <label class="trend-switch">
          <span>统计周期</span>
          <select v-model="selectedPeriod" data-testid="period-switch" @change="loadDetail">
            <option v-for="p in periods" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
      </div>
      <table class="data-table" data-testid="trend-table">
        <thead>
          <tr>
            <th>统计周期</th><th>版本号</th><th>规则版本</th><th>样本数量</th>
            <th>异常数</th><th>达标率</th><th>迟到样本</th><th>校验结论</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in trendReports"
            :key="row.统计周期"
            data-testid="trend-row"
            :class="{ 'trend-row-active': row.统计周期 === selectedPeriod }"
            @click="selectPeriod(row.统计周期)"
          >
            <td>{{ row.统计周期 }}</td>
            <td>{{ row.版本号 }}</td>
            <td>{{ row.规则版本 }}</td>
            <td>{{ row.样本数量 }}</td>
            <td>{{ row.异常数 }}</td>
            <td>{{ formatRate(row.达标率) }}</td>
            <td>{{ row.迟到样本数 }}</td>
            <td>{{ row.校验结论 }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!trendReports.length" class="empty-state">暂无质量趋势数据报告</p>
    </section>

    <!-- 当前统计周期的完整依据：指标数据集与样本快照同属一个发布批次 -->
    <section v-if="detail" class="trend-detail" data-testid="trend-detail">
      <div class="trend-chips">
        <span>统计周期 <strong data-testid="detail-period">{{ detail.report.统计周期 }}</strong></span>
        <span>版本 <strong>v{{ detail.report.版本号 }}</strong></span>
        <span>规则版本 <strong data-testid="detail-rule">{{ detail.report.规则版本 }}</strong></span>
        <span>样本数量 <strong data-testid="detail-samples">{{ detail.report.样本数量 }}</strong></span>
        <span>迟到样本 <strong data-testid="detail-late">{{ detail.report.迟到样本数 }}</strong></span>
        <span>达标率 <strong data-testid="detail-rate">{{ formatRate(detail.report.达标率) }}</strong></span>
      </div>
      <h4>指标数据集</h4>
      <table class="data-table" data-testid="dataset-table">
        <thead><tr><th>指标编号</th><th>指标名称</th><th>样本数量</th><th>达标样本数</th><th>异常数</th><th>达标率</th><th>规则版本</th></tr></thead>
        <tbody>
          <tr v-for="row in detail.datasets" :key="row.id">
            <td>{{ row.指标编号 }}</td><td>{{ row.指标名称 }}</td><td>{{ row.样本数量 }}</td>
            <td>{{ row.达标样本数 }}</td><td>{{ row.异常数 }}</td><td>{{ formatRate(row.达标率) }}</td><td>{{ row.规则版本 }}</td>
          </tr>
        </tbody>
      </table>
      <h4>样本快照 <span class="muted-note">（发布批次 #{{ detail.report.发布批次 }}，与指标数据集同批可见）</span></h4>
      <table class="data-table" data-testid="sample-table">
        <thead><tr><th>样本编号</th><th>采集批次</th><th>指标编号</th><th>样本值</th><th>落库时间</th><th>迟到</th><th>是否达标</th></tr></thead>
        <tbody>
          <tr v-for="row in detail.samples" :key="row.id" :class="{ 'late-sample': row.迟到 }">
            <td>{{ row.样本编号 }}</td><td>{{ row.采集批次 }}</td><td>{{ row.指标编号 }}</td>
            <td>{{ row.样本值 }}</td><td>{{ row.落库时间 }}</td><td>{{ row.迟到 ? '是' : '否' }}</td>
            <td>{{ row.是否达标 ? '达标' : '未达标' }}</td>
          </tr>
        </tbody>
      </table>
      <h4>校验趋势记录台账 <span class="muted-note">（同步到采集校验）</span></h4>
      <table class="data-table" data-testid="trend-record-table">
        <thead><tr><th>统计周期</th><th>指标编号</th><th>样本数量</th><th>异常数</th><th>达标率</th><th>规则版本</th><th>校验结论</th></tr></thead>
        <tbody>
          <tr v-for="row in detail.trendRecords" :key="row.id">
            <td>{{ row.统计周期 }}</td><td>{{ row.指标编号 }}</td><td>{{ row.样本数量 }}</td>
            <td>{{ row.异常数 }}</td><td>{{ formatRate(row.达标率) }}</td><td>{{ row.规则版本 }}</td><td>{{ row.校验结论 }}</td>
          </tr>
        </tbody>
      </table>
      <h4>采集校验异常处置台账 <span class="muted-note">（趋势中的异常结论回写）</span></h4>
      <table class="data-table" data-testid="anomaly-table">
        <thead><tr><th>指标编号</th><th>异常数</th><th>样本数量</th><th>达标率</th><th>异常结论</th><th>处置状态</th></tr></thead>
        <tbody>
          <tr v-for="row in detail.anomalyRecords" :key="row.id">
            <td>{{ row.指标编号 }}</td><td>{{ row.异常数 }}</td><td>{{ row.样本数量 }}</td>
            <td>{{ formatRate(row.达标率) }}</td><td>{{ row.异常结论 }}</td><td>{{ row.处置状态 }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 运行分析：按统计周期回放趋势结果，用于核对达标率 -->
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
import { request } from '@/api/client'

const ENDPOINT = '/api/quality'
const TREND_ENDPOINT = '/api/quality/trends'

type TrendReport = {
  统计周期: string
  版本号: number
  发布批次: number
  规则版本: string
  样本数量: number
  异常数: number
  达标率: number
  迟到样本数: number
  校验结论: string
}

type TrendDetail = {
  report: TrendReport
  datasets: any[]
  samples: any[]
  lateSamples: any[]
  trendRecords: any[]
  anomalyRecords: any[]
}

const summaryMetrics = ref<{ label: string; value: number | string; trend: number }[]>([])
const trendReports = ref<TrendReport[]>([])
const periods = ref<string[]>([])
const selectedPeriod = ref('')
const detail = ref<TrendDetail | null>(null)
const results = ref<any[]>([])
const chartData = ref<{ label: string; value: number }[]>([])
const loading = ref(false)
const params = ref<Record<string, string>>({})
const paramFields = ["统计周期", "指标编号", "指标名称", "统计口径"]
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

function selectPeriod(period: string) {
  selectedPeriod.value = period
  loadDetail()
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
      { label: '统计周期', value: '—', trend: 0 },
      { label: '样本数量', value: 0, trend: 0 },
      { label: '异常数', value: 0, trend: 0 },
      { label: '达标率', value: '—', trend: 0 },
    ]
  }
}

async function fetchReports() {
  try {
    const res = await request(`${TREND_ENDPOINT}`)
    const data = await res.json()
    trendReports.value = data.items || []
    if (!selectedPeriod.value || !trendReports.value.some(r => r.统计周期 === selectedPeriod.value)) {
      selectedPeriod.value = trendReports.value[0]?.统计周期 || ''
    }
  } catch {
    trendReports.value = []
  }
}

async function fetchPeriods() {
  try {
    const res = await request(`${TREND_ENDPOINT}/periods`)
    const data = await res.json()
    periods.value = data.items || []
  } catch {
    periods.value = []
  }
}

async function loadDetail() {
  if (!selectedPeriod.value) {
    detail.value = null
    return
  }
  try {
    const res = await request(`${TREND_ENDPOINT}/${encodeURIComponent(selectedPeriod.value)}`)
    detail.value = await res.json()
  } catch {
    detail.value = null
  }
}

async function loadAll() {
  await Promise.all([fetchSummary(), fetchReports(), fetchPeriods()])
  await loadDetail()
}

async function runAnalysis() {
  loading.value = true
  try {
    const res = await request(`${ENDPOINT}/run`, {
      method: 'POST',
      body: JSON.stringify({ values: params.value }),
    })
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

onMounted(loadAll)
</script>
