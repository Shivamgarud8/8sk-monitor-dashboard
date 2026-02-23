<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>K8s Control Plane Monitor</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
  --bg:       #06090f;
  --surface:  #0c1422;
  --surface2: #101c2e;
  --border:   #182436;
  --accent:   #00e5ff;
  --accent2:  #7c5cfc;
  --accent3:  #ff4d7d;
  --warn:     #ffaa00;
  --success:  #00e676;
  --text:     #ccdaee;
  --muted:    #3d5570;
  --glow:     0 0 30px rgba(0,229,255,0.07);
}

*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}

body{
  background:var(--bg);
  color:var(--text);
  font-family:'JetBrains Mono',monospace;
  font-size:13px;
  min-height:100vh;
  overflow-x:hidden;
}

/* Grid background */
body::before{
  content:'';
  position:fixed;inset:0;z-index:0;
  background-image:
    linear-gradient(rgba(0,229,255,0.015) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,229,255,0.015) 1px,transparent 1px);
  background-size:48px 48px;
  pointer-events:none;
}

/* Glow blobs */
body::after{
  content:'';
  position:fixed;inset:0;z-index:0;
  background:
    radial-gradient(ellipse 600px 400px at 20% 20%, rgba(0,229,255,0.03), transparent),
    radial-gradient(ellipse 500px 400px at 80% 80%, rgba(124,92,252,0.04), transparent);
  pointer-events:none;
}

/* ── Header ─────────────────────────────────────────────────── */
header{
  position:sticky;top:0;z-index:200;
  background:rgba(6,9,15,0.9);
  backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
  height:54px;
  padding:0 28px;
  display:flex;align-items:center;justify-content:space-between;
}

.logo{
  font-family:'Syne',sans-serif;
  font-weight:800;font-size:16px;
  color:var(--accent);
  display:flex;align-items:center;gap:10px;
  letter-spacing:0.04em;
}
.logo-icon{
  width:30px;height:30px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  clip-path:polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%);
  display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:800;color:#000;font-family:'Syne',sans-serif;
}

.header-right{display:flex;align-items:center;gap:20px}

.mode-badge{
  padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;
  letter-spacing:0.1em;text-transform:uppercase;
}
.mode-live{background:rgba(0,230,118,0.12);color:var(--success);border:1px solid rgba(0,230,118,0.2)}
.mode-mock{background:rgba(255,170,0,0.12);color:var(--warn);border:1px solid rgba(255,170,0,0.2)}

.live-indicator{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--success)}
.live-dot{
  width:7px;height:7px;border-radius:50%;
  background:var(--success);
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{
  0%,100%{box-shadow:0 0 0 0 rgba(0,230,118,0.6)}
  50%{box-shadow:0 0 0 6px rgba(0,230,118,0)}
}
#refresh-time{font-size:11px;color:var(--muted)}

/* ── Layout ──────────────────────────────────────────────────── */
main{
  position:relative;z-index:1;
  max-width:1680px;margin:0 auto;
  padding:22px 28px 60px;
  display:flex;flex-direction:column;gap:28px;
}

/* ── Section label ───────────────────────────────────────────── */
.sec{
  font-family:'Syne',sans-serif;
  font-size:10px;font-weight:700;
  letter-spacing:0.22em;text-transform:uppercase;
  color:var(--muted);
  margin-bottom:14px;
  display:flex;align-items:center;gap:10px;
}
.sec span{font-size:14px}
.sec::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border),transparent)}

/* ── Action buttons ──────────────────────────────────────────── */
.actions{display:flex;gap:10px;flex-wrap:wrap}
.btn{
  padding:9px 20px;border-radius:8px;
  font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  letter-spacing:0.05em;text-transform:uppercase;
  cursor:pointer;border:1px solid;
  display:inline-flex;align-items:center;gap:7px;
  transition:all .15s;position:relative;overflow:hidden;
  background:transparent;
}
.btn::before{content:'';position:absolute;inset:0;background:currentColor;opacity:0;transition:opacity .15s}
.btn:hover::before{opacity:0.08}
.btn:active{transform:scale(0.97)}
.btn-hpa  {color:var(--warn);  border-color:rgba(255,170,0,0.4)}
.btn-node {color:var(--accent3);border-color:rgba(255,77,125,0.4)}
.btn-stop {color:var(--success);border-color:rgba(0,230,118,0.4)}
.btn-ref  {color:var(--accent); border-color:rgba(0,229,255,0.4)}

/* ── Overview cards ──────────────────────────────────────────── */
.ov-grid{
  display:grid;
  grid-template-columns:repeat(8,1fr);
  gap:12px;
}
@media(max-width:1400px){.ov-grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:700px) {.ov-grid{grid-template-columns:repeat(2,1fr)}}

.ov-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:10px;
  padding:18px 16px 14px;
  position:relative;overflow:hidden;
  box-shadow:var(--glow);
  transition:border-color .2s,transform .2s;
}
.ov-card:hover{border-color:rgba(0,229,255,0.3);transform:translateY(-2px)}
.ov-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  border-radius:2px 2px 0 0;
}
.ov-card.c-default::before{background:linear-gradient(90deg,var(--accent),var(--accent2))}
.ov-card.c-ok::before    {background:linear-gradient(90deg,var(--success),var(--accent))}
.ov-card.c-warn::before  {background:linear-gradient(90deg,var(--warn),var(--accent3))}
.ov-card.c-error::before {background:var(--accent3)}

.ov-label{font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.ov-val{
  font-family:'Syne',sans-serif;font-size:36px;font-weight:800;line-height:1;
}
.ov-card.c-default .ov-val{color:var(--accent)}
.ov-card.c-ok      .ov-val{color:var(--success)}
.ov-card.c-warn    .ov-val{color:var(--warn)}
.ov-card.c-error   .ov-val{color:var(--accent3)}

/* ── Charts ──────────────────────────────────────────────────── */
.charts-row{
  display:grid;grid-template-columns:repeat(3,1fr);gap:16px;
}
@media(max-width:900px){.charts-row{grid-template-columns:1fr}}

.chart-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:10px;padding:18px;
  box-shadow:var(--glow);
}
.chart-head{
  display:flex;align-items:baseline;justify-content:space-between;
  margin-bottom:14px;
}
.chart-title{font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:var(--muted)}
.chart-live-val{
  font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
}
.chart-live-val.cpu{color:var(--accent)}
.chart-live-val.mem{color:var(--accent2)}
.chart-live-val.pods{color:var(--success)}
canvas{max-height:130px;width:100%!important}

/* ── Table cards ─────────────────────────────────────────────── */
.tcard{
  background:var(--surface);border:1px solid var(--border);
  border-radius:10px;overflow:hidden;box-shadow:var(--glow);
}
.tcard-head{
  padding:13px 18px;
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(0,0,0,0.2);
}
.tcard-title{font-family:'Syne',sans-serif;font-weight:700;font-size:13px}
.badge{
  background:rgba(0,229,255,0.1);color:var(--accent);
  border:1px solid rgba(0,229,255,0.15);
  border-radius:20px;padding:2px 10px;font-size:10px;font-weight:600;
}
.tscroll{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead th{
  padding:9px 14px;
  text-align:left;
  font-size:9px;letter-spacing:0.15em;text-transform:uppercase;
  color:var(--muted);
  background:rgba(0,0,0,0.25);
  border-bottom:1px solid var(--border);
  white-space:nowrap;
  font-weight:600;
}
tbody tr{border-bottom:1px solid rgba(24,36,54,0.7);transition:background .12s}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:rgba(0,229,255,0.03)}
td{padding:9px 14px;white-space:nowrap;vertical-align:middle}

/* Pills */
.pill{
  display:inline-block;padding:2px 9px;border-radius:20px;
  font-size:9px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
}
.pill-green {background:rgba(0,230,118,.1); color:var(--success)}
.pill-red   {background:rgba(255,77,125,.1);color:var(--accent3)}
.pill-yellow{background:rgba(255,170,0,.1); color:var(--warn)}
.pill-blue  {background:rgba(0,229,255,.08);color:var(--accent)}
.pill-purple{background:rgba(124,92,252,.1);color:var(--accent2)}
.pill-gray  {background:rgba(100,120,140,.1);color:var(--muted)}

/* Progress bars */
.bar-row{display:flex;align-items:center;gap:8px;min-width:120px}
.bar-track{flex:1;height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;transition:width .5s ease}
.bar-fill.cpu{background:linear-gradient(90deg,var(--accent),var(--accent2))}
.bar-fill.mem{background:linear-gradient(90deg,var(--accent2),var(--accent3))}
.bar-fill.danger{background:var(--accent3)!important}
.bar-fill.warn  {background:var(--warn)!important}
.bar-pct{font-size:11px;min-width:38px;text-align:right}

/* ── HPA cards ───────────────────────────────────────────────── */
.hpa-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px}

.hpa-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:20px;
  position:relative;overflow:hidden;
  box-shadow:var(--glow);
  transition:border-color .2s;
}
.hpa-card:hover{border-color:rgba(124,92,252,0.4)}
.hpa-card::after{
  content:'HPA';
  position:absolute;right:16px;top:16px;
  font-size:9px;letter-spacing:0.15em;
  color:rgba(124,92,252,0.3);font-weight:700;
}

.hpa-name{font-family:'Syne',sans-serif;font-weight:700;font-size:15px;margin-bottom:3px}
.hpa-meta{font-size:11px;color:var(--muted);margin-bottom:16px;display:flex;align-items:center;gap:8px}

.replica-row{
  display:grid;grid-template-columns:repeat(4,1fr);
  border:1px solid var(--border);border-radius:8px;overflow:hidden;
  margin-bottom:16px;
}
.rep-cell{
  padding:10px 8px;text-align:center;
  border-right:1px solid var(--border);
}
.rep-cell:last-child{border-right:none}
.rep-num{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;line-height:1;margin-bottom:4px}
.rep-label{font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted)}

.cpu-row{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:7px}
.cpu-row strong{color:var(--text)}

/* ── Deployments ─────────────────────────────────────────────── */
.dep-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.dep-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:8px;padding:14px 16px;
  transition:border-color .2s;
}
.dep-card:hover{border-color:rgba(0,229,255,0.2)}
.dep-name{
  font-weight:600;font-size:12px;margin-bottom:2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.dep-ns{font-size:10px;color:var(--muted);margin-bottom:8px}
.dep-rep{font-size:11px}

/* ── Toast ───────────────────────────────────────────────────── */
#toast-container{position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{
  background:var(--surface2);border:1px solid var(--accent);
  border-radius:8px;padding:11px 16px;
  font-size:12px;color:var(--accent);
  box-shadow:0 0 24px rgba(0,229,255,0.15);
  animation:toastIn .25s ease;
  max-width:360px;
}
@keyframes toastIn{from{transform:translateY(12px);opacity:0}to{transform:translateY(0);opacity:1}}

/* Scrollbar */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">K8</div>
    Control Plane Monitor
  </div>
  <div class="header-right">
    <span id="mode-badge" class="mode-badge mode-mock">⬤ Mock</span>
    <div class="live-indicator"><div class="live-dot"></div>Live</div>
    <span id="refresh-time">Starting…</span>
  </div>
</header>

<main>

  <!-- Actions -->
  <div>
    <div class="sec"><span>⚡</span>Actions</div>
    <div class="actions">
      <button class="btn btn-hpa"  onclick="doAction('hpa')">▲ Increase Pod Load (HPA)</button>
      <button class="btn btn-node" onclick="doAction('node')">▲ Increase Node Stress</button>
      <button class="btn btn-stop" onclick="doAction('stop')">■ Stop All Stress</button>
      <button class="btn btn-ref"  onclick="refreshAll()">↻ Refresh Now</button>
    </div>
  </div>

  <!-- Cluster Overview -->
  <div>
    <div class="sec"><span>📊</span>Cluster Overview</div>
    <div class="ov-grid">
      <div class="ov-card c-default"><div class="ov-label">Total Nodes</div>  <div class="ov-val" id="ov-nodes">—</div></div>
      <div class="ov-card c-ok">    <div class="ov-label">Ready Nodes</div>  <div class="ov-val" id="ov-ready">—</div></div>
      <div class="ov-card c-default"><div class="ov-label">Total Pods</div>   <div class="ov-val" id="ov-pods">—</div></div>
      <div class="ov-card c-ok">    <div class="ov-label">Running Pods</div> <div class="ov-val" id="ov-running">—</div></div>
      <div class="ov-card c-error">  <div class="ov-label">CrashLoop</div>   <div class="ov-val" id="ov-crash">—</div></div>
      <div class="ov-card c-default"><div class="ov-label">Deployments</div>  <div class="ov-val" id="ov-deps">—</div></div>
      <div class="ov-card c-default"><div class="ov-label">Services</div>     <div class="ov-val" id="ov-svc">—</div></div>
      <div class="ov-card c-warn">   <div class="ov-label">HPA Replicas</div><div class="ov-val" id="ov-hpa">—</div></div>
    </div>
  </div>

  <!-- Time-series -->
  <div>
    <div class="sec"><span>📈</span>Live Time-Series</div>
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-head">
          <div class="chart-title">Cluster CPU %</div>
          <div class="chart-live-val cpu" id="val-cpu">—%</div>
        </div>
        <canvas id="chart-cpu"></canvas>
      </div>
      <div class="chart-card">
        <div class="chart-head">
          <div class="chart-title">Cluster Memory %</div>
          <div class="chart-live-val mem" id="val-mem">—%</div>
        </div>
        <canvas id="chart-mem"></canvas>
      </div>
      <div class="chart-card">
        <div class="chart-head">
          <div class="chart-title">Total Pod Count</div>
          <div class="chart-live-val pods" id="val-pods">—</div>
        </div>
        <canvas id="chart-pods"></canvas>
      </div>
    </div>
  </div>

  <!-- Nodes -->
  <div>
    <div class="sec"><span>🖥</span>Nodes</div>
    <div class="tcard">
      <div class="tcard-head">
        <span class="tcard-title">Node Inventory</span>
        <span class="badge" id="node-badge">0 nodes</span>
      </div>
      <div class="tscroll">
        <table>
          <thead><tr>
            <th>Node</th><th>Role</th><th>CPU %</th><th>Memory %</th>
            <th>Alloc CPU</th><th>Alloc Mem</th><th>Pods</th><th>Status</th><th>Age</th>
          </tr></thead>
          <tbody id="nodes-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Pods -->
  <div>
    <div class="sec"><span>📦</span>Pods</div>
    <div class="tcard">
      <div class="tcard-head">
        <span class="tcard-title">Pod Inventory</span>
        <span class="badge" id="pod-badge">0 pods</span>
      </div>
      <div class="tscroll">
        <table>
          <thead><tr>
            <th>Pod</th><th>Namespace</th><th>CPU (m)</th><th>Mem (Mi)</th>
            <th>Restarts</th><th>Node</th><th>Status</th><th>Age</th>
          </tr></thead>
          <tbody id="pods-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- HPA -->
  <div>
    <div class="sec"><span>⚖</span>Horizontal Pod Autoscalers</div>
    <div class="hpa-grid" id="hpa-grid">
      <div class="hpa-card" style="color:var(--muted)">No HPAs found.</div>
    </div>
  </div>

  <!-- Deployments -->
  <div>
    <div class="sec"><span>🚀</span>Deployments</div>
    <div class="dep-grid" id="dep-grid"></div>
  </div>

</main>

<div id="toast-container"></div>

<script>
// ── Charts ────────────────────────────────────────────────────────────────────
function makeChart(id, color) {
  const ctx = document.getElementById(id);
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        backgroundColor: color.replace('rgb(','rgba(').replace(')',',0.07)'),
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      }]
    },
    options: {
      animation: { duration: 300 },
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: ctx => ` ${ctx.parsed.y}` }
      }},
      scales: {
        x: { display: false },
        y: {
          min: 0,
          grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
          ticks: { color: '#3d5570', font: { size: 10, family: 'JetBrains Mono' }, maxTicksLimit: 5 },
          border: { display: false }
        }
      },
      maintainAspectRatio: true,
      interaction: { intersect: false, mode: 'index' },
    }
  });
}

const cpuChart  = makeChart('chart-cpu',  'rgb(0,229,255)');
const memChart  = makeChart('chart-mem',  'rgb(124,92,252)');
const podChart  = makeChart('chart-pods', 'rgb(0,230,118)');

function updateChart(chart, labels, values) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = values;
  chart.update('none');
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const get = url => fetch(url).then(r => r.json());
const last = arr => arr && arr.length ? arr[arr.length - 1] : '—';

function pill(status) {
  const map = {
    Ready:'pill-green', NotReady:'pill-red',
    Running:'pill-green', Pending:'pill-yellow', Failed:'pill-red',
    Succeeded:'pill-blue', Unknown:'pill-gray',
    master:'pill-purple', worker:'pill-blue',
    production:'pill-purple', default:'pill-blue',
    'kube-system':'pill-gray', monitoring:'pill-green',
  };
  const c = map[status] || 'pill-blue';
  return `<span class="pill ${c}">${status}</span>`;
}

function bar(pct, cls) {
  const danger = pct > 80 ? ' danger' : pct > 60 ? ' warn' : '';
  const color = pct > 80 ? 'var(--accent3)' : pct > 60 ? 'var(--warn)' : 'var(--text)';
  return `<div class="bar-row">
    <div class="bar-track">
      <div class="bar-fill ${cls}${danger}" style="width:${Math.min(pct,100)}%"></div>
    </div>
    <span class="bar-pct" style="color:${color}">${pct}%</span>
  </div>`;
}

// ── Overview ──────────────────────────────────────────────────────────────────
async function loadOverview() {
  const d = await get('/api/cluster-overview');
  $('ov-nodes').textContent   = d.total_nodes;
  $('ov-ready').textContent   = d.ready_nodes;
  $('ov-pods').textContent    = d.total_pods;
  $('ov-running').textContent = d.running_pods;
  $('ov-crash').textContent   = d.crashloop_pods;
  $('ov-deps').textContent    = d.total_deployments;
  $('ov-svc').textContent     = d.total_services;
  $('ov-hpa').textContent     = d.hpa_replicas;

  const badge = $('mode-badge');
  if (d.mode === 'live') {
    badge.textContent = '⬤ Live K8s';
    badge.className = 'mode-badge mode-live';
  } else {
    badge.textContent = '⬤ Mock Data';
    badge.className = 'mode-badge mode-mock';
  }
}

// ── Time-series ───────────────────────────────────────────────────────────────
async function loadTimeseries() {
  const d = await get('/api/timeseries');
  updateChart(cpuChart,  d.timestamps, d.cluster_cpu);
  updateChart(memChart,  d.timestamps, d.cluster_mem);
  updateChart(podChart,  d.timestamps, d.pod_count);
  $('val-cpu').textContent  = `${last(d.cluster_cpu)}%`;
  $('val-mem').textContent  = `${last(d.cluster_mem)}%`;
  $('val-pods').textContent = last(d.pod_count);
}

// ── Nodes ─────────────────────────────────────────────────────────────────────
async function loadNodes() {
  const nodes = await get('/api/nodes');
  $('node-badge').textContent = `${nodes.length} node${nodes.length !== 1 ? 's' : ''}`;
  $('nodes-body').innerHTML = nodes.map(n => `
    <tr>
      <td style="font-weight:600;color:var(--text)">${n.name}</td>
      <td>${pill(n.role)}</td>
      <td>${bar(n.cpu_pct, 'cpu')}</td>
      <td>${bar(n.mem_pct, 'mem')}</td>
      <td style="color:var(--muted)">${n.alloc_cpu}</td>
      <td style="color:var(--muted)">${n.alloc_mem}</td>
      <td style="color:var(--accent);font-weight:600">${n.pods}</td>
      <td>${pill(n.status)}</td>
      <td style="color:var(--muted)">${n.age}</td>
    </tr>`).join('');
}

// ── Pods ──────────────────────────────────────────────────────────────────────
async function loadPods() {
  const pods = await get('/api/pods');
  $('pod-badge').textContent = `${pods.length} pod${pods.length !== 1 ? 's' : ''}`;
  $('pods-body').innerHTML = pods.map(p => {
    const rc = p.restarts;
    const rcColor = rc > 5 ? 'var(--accent3)' : rc > 0 ? 'var(--warn)' : 'var(--muted)';
    return `<tr>
      <td style="font-weight:600;color:var(--text);max-width:220px;overflow:hidden;text-overflow:ellipsis" title="${p.name}">${p.name}</td>
      <td>${pill(p.namespace)}</td>
      <td style="color:var(--accent)">${p.cpu_mc}m</td>
      <td style="color:var(--accent2)">${p.mem_mi} Mi</td>
      <td style="color:${rcColor};font-weight:${rc > 0 ? 700 : 400}">${rc}</td>
      <td style="color:var(--muted);font-size:11px">${p.node}</td>
      <td>${pill(p.status)}</td>
      <td style="color:var(--muted)">${p.age}</td>
    </tr>`;
  }).join('');
}

// ── HPA ───────────────────────────────────────────────────────────────────────
async function loadHPA() {
  const hpas = await get('/api/hpa');
  if (!Array.isArray(hpas) || hpas.length === 0) return;
  $('hpa-grid').innerHTML = hpas.map(h => {
    const ct = h.cpu_target_pct;
    const cc = h.cpu_current_pct;
    const fill = (ct && cc) ? Math.min(cc / ct * 100, 100) : 0;
    const barColor = fill > 90 ? 'var(--accent3)' : fill > 65 ? 'var(--warn)' : 'var(--success)';
    const scaling = (h.desired_replicas > h.current_replicas) ? '▲ Scaling Up' :
                    (h.desired_replicas < h.current_replicas) ? '▼ Scaling Down' : '● Stable';
    const scalingColor = h.desired_replicas !== h.current_replicas ? 'var(--warn)' : 'var(--success)';
    return `<div class="hpa-card">
      <div class="hpa-name">${h.name}</div>
      <div class="hpa-meta">
        → ${h.target}
        <span class="pill pill-blue">${h.namespace}</span>
        <span style="color:${scalingColor};font-size:10px;font-weight:700">${scaling}</span>
      </div>
      <div class="replica-row">
        <div class="rep-cell">
          <div class="rep-num" style="color:var(--muted)">${h.min_replicas}</div>
          <div class="rep-label">Min</div>
        </div>
        <div class="rep-cell">
          <div class="rep-num" style="color:var(--accent)">${h.current_replicas}</div>
          <div class="rep-label">Current</div>
        </div>
        <div class="rep-cell">
          <div class="rep-num" style="color:var(--warn)">${h.desired_replicas}</div>
          <div class="rep-label">Desired</div>
        </div>
        <div class="rep-cell">
          <div class="rep-num" style="color:var(--muted)">${h.max_replicas}</div>
          <div class="rep-label">Max</div>
        </div>
      </div>
      <div class="cpu-row">
        <span>CPU Target: <strong>${ct != null ? ct + '%' : '—'}</strong></span>
        <span>Current: <strong style="color:${barColor}">${cc != null ? cc + '%' : '—'}</strong></span>
      </div>
      <div class="bar-track" style="height:7px">
        <div class="bar-fill" style="width:${fill}%;background:${barColor};height:100%;border-radius:3px;transition:width .5s"></div>
      </div>
    </div>`;
  }).join('');
}

// ── Deployments ───────────────────────────────────────────────────────────────
async function loadDeployments() {
  const deps = await get('/api/deployments');
  $('dep-grid').innerHTML = deps.map(d => {
    const ok = d.ready >= d.desired;
    return `<div class="dep-card">
      <div class="dep-name" title="${d.name}">${d.name}</div>
      <div class="dep-ns">${d.namespace}</div>
      <div class="dep-rep">
        <span style="color:${ok?'var(--success)':'var(--warn)'}; font-weight:700">${d.ready}</span>
        <span style="color:var(--muted)"> / ${d.desired} ready</span>
      </div>
    </div>`;
  }).join('');
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function doAction(type) {
  const urls = { hpa:'/api/stress-hpa', node:'/api/stress-node', stop:'/api/stop-stress' };
  try {
    const r = await fetch(urls[type], { method: 'POST' });
    const d = await r.json();
    toast(d.status || d.error || 'Done');
  } catch(e) {
    toast('Error: ' + e.message);
  }
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = '✓  ' + msg;
  $('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Main refresh ──────────────────────────────────────────────────────────────
async function refreshAll() {
  await Promise.allSettled([
    loadOverview(),
    loadTimeseries(),
    loadNodes(),
    loadPods(),
    loadHPA(),
    loadDeployments(),
  ]);
  $('refresh-time').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

refreshAll();
setInterval(refreshAll, 5000);
</script>
</body>
</html>
