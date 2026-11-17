import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

type ModuleCase = {
  key: string
  fields: string[]
  actions: string[]
  actionTargets: string[]
  shape: string
}

const modules: ModuleCase[] = [
  {
    "key": "targetsite",
    "fields": [
      "站点编号",
      "站点名称",
      "入口URL",
      "请求方法",
      "请求头模板",
      "字符编码",
      "重试上限",
      "抓取间隔"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "selector",
    "fields": [
      "规则编号",
      "归属站点",
      "列表选择器",
      "详情选择器",
      "字段选择器",
      "分页参数",
      "等待条件",
      "字符编码"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "crawler",
    "fields": [
      "任务编号",
      "任务名称",
      "关联站点",
      "关联规则",
      "并发线程",
      "调度周期",
      "超时秒数",
      "下发批次"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "job-timeline"
  },
  {
    "key": "proxy",
    "fields": [
      "节点编号",
      "IP地址",
      "端口号",
      "协议类型",
      "匿程度",
      "响应延迟",
      "存活检测",
      "所属区域"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "antiblock",
    "fields": [
      "策略编号",
      "策略名称",
      "触发条件",
      "延迟范围",
      "UA伪装",
      "Referer生成",
      "Cookie策略",
      "熔断阈值"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "schedule",
    "fields": [
      "计划编号",
      "关联任务",
      "Cron表达式",
      "执行窗口",
      "重试策略",
      "失败通知",
      "最大并发",
      "是否启用"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "job-timeline"
  },
  {
    "key": "extractor",
    "fields": [
      "模板编号",
      "模板名称",
      "输入URL",
      "字段映射",
      "清洗规则",
      "输出格式",
      "版本号",
      "生效批次"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "dag-graph"
  },
  {
    "key": "validate",
    "fields": [
      "规则编号",
      "校验字段",
      "期望格式",
      "空值阈值",
      "重复判定",
      "异常策略",
      "阻断级别",
      "校验批次"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "retry",
    "fields": [
      "策略编号",
      "适用任务",
      "最大重试",
      "退避类型",
      "退避系数",
      "幂等标识",
      "状态记录",
      "最后更新"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "storage",
    "fields": [
      "配置编号",
      "存储类型",
      "连接信息",
      "分区策略",
      "压缩格式",
      "保存天数",
      "备份副本",
      "清理策略"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "dedup",
    "fields": [
      "策略编号",
      "业务键列",
      "去重算法",
      "对比窗口",
      "相似阈值",
      "保留顺序",
      "增量模式",
      "生效批次"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "quality",
    "fields": [
      "指标编号",
      "指标名称",
      "统计口径",
      "阈值下界",
      "阈值上界",
      "统计周期",
      "样本数量",
      "达标率"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "monitor",
    "fields": [
      "大盘编号",
      "关联任务",
      "采集速率",
      "成功率",
      "平均延迟",
      "内存占用",
      "错误次数",
      "观测时段"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "analysis-dashboard"
  },
  {
    "key": "alert",
    "fields": [
      "规则编号",
      "监控对象",
      "告警条件",
      "通知渠道",
      "通知模板",
      "重复间隔",
      "生效时段",
      "值班人员"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "apigate",
    "fields": [
      "配置编号",
      "端点路径",
      "请求方法",
      "鉴权方式",
      "速率限制",
      "响应缓存",
      "调用配额",
      "版本控制"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "archive",
    "fields": [
      "策略编号",
      "数据来源",
      "归档周期",
      "归档格式",
      "保留年限",
      "压缩级别",
      "索引规则",
      "清理策略"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "template",
    "fields": [
      "模板编号",
      "模板名称",
      "适用站点",
      "站点类型",
      "提取逻辑",
      "内置规则",
      "使用次数",
      "作者来源"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "crud-table"
  },
  {
    "key": "flowline",
    "fields": [
      "流程编号",
      "流程名称",
      "步骤序列",
      "输入站点",
      "输出目标",
      "失败处理",
      "触发条件",
      "版本号"
    ],
    "actions": [
      "提交校验",
      "启用配置",
      "停用配置"
    ],
    "actionTargets": [
      "待校验",
      "已启用",
      "已停用"
    ],
    "shape": "dag-graph"
  }
]
const repoKind = 'fullstack'
const crudModules = modules.filter(m => m.shape === 'crud-table')
const dagModules = modules.filter(m => m.shape === 'dag-graph')
const timelineModules = modules.filter(m => m.shape === 'job-timeline')
const analysisModules = modules.filter(m => m.shape === 'analysis-dashboard')

function parseCsv(text: string): string[][] {
  const records: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  const input = text.replace(/^\uFEFF/, '')
  for (let index = 0; index < input.length; index++) {
    const char = input[index]
    if (quoted) {
      if (char === '"' && input[index + 1] === '"') { cell += '"'; index++ }
      else if (char === '"') { quoted = false }
      else { cell += char }
    } else if (char === '"' && cell === '') { quoted = true }
    else if (char === ',') { row.push(cell); cell = '' }
    else if (char === '\n') {
      row.push(cell.replace(/\r$/, ''))
      if (row.some(v => v !== '')) records.push(row)
      row = []; cell = ''
    } else { cell += char }
  }
  row.push(cell.replace(/\r$/, ''))
  if (row.some(v => v !== '')) records.push(row)
  return records
}

test('CRUD模块：筛选、导出、登记、动作、指标全链路', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (crudModules.length === 0) { test.skip(); return }

  for (const mod of crudModules) {
    await page.goto(`/${mod.key}`)
    const bodyRows = page.locator('tbody tr[data-testid^="row-"]')
    await expect(bodyRows).toHaveCount(3)
    const firstValue = await bodyRows.nth(0).locator('td').nth(0).innerText()

    await page.getByTestId(`filter-${mod.fields[0]}`).fill(firstValue)
    await page.getByTestId('query').click()
    await expect(bodyRows).toHaveCount(1)
    await page.getByTestId('reset').click()
    await expect(bodyRows).toHaveCount(3)

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    const createdValues = mod.fields.map((f, i) => `验收-${mod.key}-${i+1}`)
    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.entries()) {
      await page.getByTestId(`create-${field}`).fill(createdValues[i])
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
    await expect(bodyRows).toHaveCount(4)

    const createdRow = page.locator('tbody tr').filter({ hasText: createdValues[0] })
    for (const [i, action] of mod.actions.entries()) {
      await createdRow.getByRole('button', { name: action, exact: true }).click()
      await expect(createdRow).toHaveAttribute('data-status', mod.actionTargets[i])
    }
  }

  expect(browserErrors).toEqual([])
})

test('DAG拓扑模块：节点渲染、详情、动作、导出', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (dagModules.length === 0) { test.skip(); return }

  for (const mod of dagModules) {
    await page.goto(`/${mod.key}`)
    await expect(page.locator('svg.dag-svg')).toBeVisible()
    await page.locator('g.dag-node').first().waitFor({ timeout: 10000 })
    const nodes = page.locator('g.dag-node')
    const count = await nodes.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await nodes.first().click()
    await expect(page.getByTestId('dag-detail')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('时间线模块：甘特条渲染、日期筛选、日志查看、登记', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (timelineModules.length === 0) { test.skip(); return }

  for (const mod of timelineModules) {
    await page.goto(`/${mod.key}`)
    await page.locator('.timeline-bar').first().waitFor({ timeout: 10000 })
    const bars = page.locator('.timeline-bar')
    const count = await bars.count()
    expect(count).toBeGreaterThanOrEqual(3)

    await bars.first().click()
    await expect(page.getByTestId('timeline-log')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`${mod.key}.csv`)

    await page.getByTestId('open-create').click()
    await expect(page.getByTestId('create-modal')).toBeVisible()
    for (const [i, field] of mod.fields.slice(0,3).entries()) {
      await page.locator('.create-field input').nth(i).fill(`E2E-${mod.key}-${i}`)
    }
    await page.getByTestId('submit-create').click()
    await expect(page.getByTestId('create-modal')).toHaveCount(0)
  }

  expect(browserErrors).toEqual([])
})

test('分析看板模块：KPI卡片、运行分析、图表渲染', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })
  if (analysisModules.length === 0) { test.skip(); return }

  for (const mod of analysisModules) {
    await page.goto(`/${mod.key}`)
    await page.getByTestId('kpi-card').first().waitFor({ timeout: 10000 })
    const kpiCards = page.getByTestId('kpi-card')
    const kpiCount = await kpiCards.count()
    expect(kpiCount).toBeGreaterThanOrEqual(2)
    await expect(kpiCards.first().locator('strong')).toBeVisible()

    await page.getByTestId('run-analysis').click()
    await expect(page.locator('.analysis-bar').first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.data-table tbody tr').first()).toBeVisible({ timeout: 5000 })
  }

  expect(browserErrors).toEqual([])
})

test('质量趋势数据报告：周期切换、样本依据、规则版本与台账核对', async ({ page }) => {
  test.setTimeout(300_000)
  const browserErrors: string[] = []
  page.on('pageerror', e => browserErrors.push(e.message))
  page.on('response', r => { if (r.url().includes('/api/') && r.status()>=400) browserErrors.push(`${r.status()} ${r.url()}`) })

  await page.goto('/quality')
  await expect(page.getByTestId('trend-table')).toBeVisible()
  const rows = page.getByTestId('trend-row')
  await expect(rows.first()).toBeVisible()
  // 同一统计周期只呈现一份报告
  const periodsSeen = await rows.locator('td:first-child').allInnerTexts()
  expect(new Set(periodsSeen).size).toBe(periodsSeen.length)
  // 每个统计周期都带规则版本
  for (const text of await rows.locator('td:nth-child(3)').allInnerTexts()) {
    expect(text.trim().length).toBeGreaterThan(0)
  }

  // 切换周期：样本数量、迟到样本和样本快照一起变化
  const switcher = page.getByTestId('period-switch')
  const options = await switcher.locator('option').allInnerTexts()
  expect(options.length).toBeGreaterThanOrEqual(2)
  const firstPeriod = (await switcher.inputValue())
  const firstSamples = Number(await page.getByTestId('detail-samples').innerText())
  const firstLate = Number(await page.getByTestId('detail-late').innerText())
  await switcher.selectOption(options.find(o => o !== firstPeriod)!)
  await expect(page.getByTestId('detail-period')).not.toHaveText(firstPeriod)
  const secondSamples = Number(await page.getByTestId('detail-samples').innerText())
  expect(secondSamples).toBeGreaterThan(0)
  // 样本快照行数与样本数量一致，指标数据集和快照同批可见
  await expect(page.getByTestId('sample-table').locator('tbody tr')).toHaveCount(secondSamples)
  await expect(page.getByTestId('dataset-table').locator('tbody tr').first()).toBeVisible()
  await expect(page.getByTestId('trend-record-table').locator('tbody tr').first()).toBeVisible()
  await expect(page.getByTestId('anomaly-table')).toBeVisible()
  expect(firstSamples).toBeGreaterThan(0)
  expect(firstLate).toBeGreaterThanOrEqual(0)

  // 规则版本可见
  await expect(page.getByTestId('detail-rule')).toContainText('RULE-')

  // 采集校验侧能读到同步过来的校验趋势记录
  await page.goto('/validate')
  await expect(page.getByTestId('trend-ledger').locator('tbody tr').first()).toBeVisible()
  await expect(page.getByTestId('anomaly-ledger')).toBeVisible()

  expect(browserErrors).toEqual([])
})

test('质量趋势接口：迟到样本只重算所属周期、重复送交只写一份、落库失败整批回退', async ({ request }) => {
  test.setTimeout(120_000)
  const list = await (await request.get('/api/quality/trends')).json()
  expect(list.items.length).toBeGreaterThanOrEqual(2)
  const periods = list.items.map((item: any) => item.统计周期)
  const target = periods[0]
  const other = periods[1]
  const beforeOther = list.items.find((item: any) => item.统计周期 === other)
  const beforeTarget = list.items.find((item: any) => item.统计周期 === target)

  // 重复送交同一统计周期（同一规则、同一批样本）只保留一份
  const repeat = await request.post('/api/quality/trends', { data: { values: { 统计周期: target, 规则版本: beforeTarget.规则版本 } } })
  expect((await repeat.json()).ok).toBe(true)
  const afterRepeat = await (await request.get(`/api/quality/trends?period=${target}`)).json()
  expect(afterRepeat.total).toBe(1)
  expect(afterRepeat.items[0].版本号).toBe(beforeTarget.版本号)

  // 另一规则的口径冲突：最终仍只展示一份带规则版本的报告
  const conflict = await (await request.post('/api/quality/trends', { data: { values: { 统计周期: target, 规则版本: 'RULE-B@1' } } })).json()
  expect(conflict.ok).toBe(true)
  const afterConflict = await (await request.get(`/api/quality/trends?period=${target}`)).json()
  expect(afterConflict.total).toBe(1)
  expect(afterConflict.items[0].规则版本).toContain('RULE-')

  // 迟到样本只改所属统计周期
  const late = await (await request.post(`/api/quality/trends/${target}/late-samples`, {
    data: { values: { 样本编号: `E2E-LATE-${Date.now()}`, 指标编号: 'QUAL-0001', 样本值: 0.1 } },
  })).json()
  expect(late.ok).toBe(true)
  expect(late.entry.report.版本号).toBeGreaterThan(beforeTarget.版本号)
  const afterLate = await (await request.get('/api/quality/trends')).json()
  expect(afterLate.items.find((item: any) => item.统计周期 === other).版本号).toBe(beforeOther.版本号)

  // 落库失败：指标数字与样本依据一起回退，不留半份数据
  const beforeFail = await (await request.get(`/api/quality/trends/${target}`)).json()
  const failed = await (await request.post('/api/quality/trends', {
    data: { values: { 统计周期: target, 样本: [{ 样本编号: `E2E-FAIL-${Date.now()}`, 指标编号: 'QUAL-0001', 样本值: 0.2 }], 模拟落库失败: '1' } },
  })).json()
  expect(failed.ok).toBe(false)
  const afterFail = await (await request.get(`/api/quality/trends/${target}`)).json()
  expect(afterFail.report.版本号).toBe(beforeFail.report.版本号)
  expect(afterFail.samples.length).toBe(beforeFail.samples.length)

  // 半份落库（指标数据集已写、样本快照失败）也必须整批回退
  const partial = await (await request.post('/api/quality/trends', {
    data: { values: { 统计周期: target, 样本: [{ 样本编号: `E2E-PARTIAL-${Date.now()}`, 指标编号: 'QUAL-0001', 样本值: 0.3 }], 模拟部分落库失败: '1' } },
  })).json()
  expect(partial.ok).toBe(false)
  const afterPartial = await (await request.get(`/api/quality/trends/${target}`)).json()
  expect(afterPartial.report.版本号).toBe(beforeFail.report.版本号)
  expect(afterPartial.samples.length).toBe(beforeFail.samples.length)
  expect(afterPartial.datasets.length).toBe(beforeFail.datasets.length)

  // 趋势中的异常数与达标率回到同一统计窗口
  expect(afterFail.report.异常数 + afterFail.report.达标样本数).toBe(afterFail.report.样本数量)
  expect(afterFail.trendRecords.length).toBe(afterFail.report.指标数量)
})


test('概览汇总', async ({ page }) => {
  test.setTimeout(300_000)
  const totalNew = modules.length * 3
  await page.goto('/')
  const actual = Number(await page.locator('.stat-value').nth(1).innerText())
  expect(actual).toBeGreaterThanOrEqual(totalNew)
})
