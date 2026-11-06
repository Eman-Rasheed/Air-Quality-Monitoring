import { useEffect, useRef, useState } from 'react';
import { Activity, Wind, RefreshCw, Database, MapPin, Download, Menu } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, AreaChart, Area, Legend } from 'recharts';

const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

// [api key, label, colour, css id]
const P = [
  ['pm2_5', 'PM2.5', '#E0707A', 'pm25'],
  ['pm10', 'PM10', '#E8A04A', 'pm10'],
  ['carbon_monoxide', 'CO', '#8C79C9', 'co'],
  ['nitrogen_dioxide', 'NO₂', '#4A90C8', 'no2'],
  ['sulphur_dioxide', 'SO₂', '#A3BC45', 'so2'],
  ['ozone', 'O₃', '#36B0A0', 'o3']
];
const COLOR = Object.fromEntries(P.map(([k, , c]) => [k, c]));
const hexAlpha = a => Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16).padStart(2, '0');
const CITY_COLORS = ['#766B91', '#5FA88A', '#4A90C8', '#C5A77B', '#CF777B', '#8C79C9'];
const NAV = [['overview', '◈', 'Overview', '#8C79C9'], ['cities', '▥', 'City comparison', '#4A90C8'], ['trends', '⌁', 'Hourly trends', '#E0707A'], ['correlation', '◎', 'Correlations', '#36B0A0'], ['records', '▤', 'Records', '#E8A04A']];
const PAGE_IDS = NAV.map(n => n[0]);
// Open-Meteo sends UTC times without a "Z". Show everything in Pakistan time (UTC+5).
// If your backend already stores local time, set this to false.
const DATA_IS_UTC = true;
const toDate = ts => { const t = String(ts).replace(' ', 'T'); return new Date(DATA_IS_UTC && !/(Z|[+-]\d\d:?\d\d)$/.test(t) ? t + 'Z' : t); };
const fmtTime = ts => toDate(ts).toLocaleString('en-GB', { timeZone: 'Asia/Karachi', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true });
const pktHour = ts => Number(toDate(ts).toLocaleString('en-GB', { timeZone: 'Asia/Karachi', hour: '2-digit', hourCycle: 'h23' })) % 24;
const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

async function get(path, opts) {
  let r = await fetch(API + path, opts);
  if (!r.ok) {
    let e = await r.json().catch(() => ({}));
    throw Error(e.detail || r.statusText);
  }
  return r.json();
}

// Counts from 0 up to the real value (final value is always exact)
function useCount(target, ms = 1100) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (reduced()) { setV(target); return; }
    let raf, t0;
    const step = t => {
      t0 ??= t;
      const p = Math.min((t - t0) / ms, 1);
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return v;
}

function Stat({ icon, label, value, suffix = '', pad = 0, loading, i }) {
  const n = useCount(value || 0);
  return (
    <article className="reveal" style={{ '--d': 120 + i * 90 + 'ms' }}>
      <span className="float">{icon}</span>
      <small>{label}</small>
      {loading ? <div className="skeleton sk-num" /> : <strong>{String(n).padStart(pad, '0')}{suffix}</strong>}
    </article>
  );
}


const Seg = ({ value, onChange, opts }) => (
  <div className="seg">{opts.map(([v, l]) => <button key={v} className={value === v ? 'on' : ''} onClick={() => onChange(v)}>{l}</button>)}</div>
);
const Chips = ({ on, toggle }) => (
  <div className="chips">{P.map(([k, n, c]) => (
    <button key={k} className={'chip' + (on(k) ? ' on' : '')} style={{ '--p': c }} onClick={() => toggle(k)}>{n}</button>
  ))}</div>
);
const Ctl = ({ label, children }) => <div className="ctl"><span className="cl">{label}</span>{children}</div>;
const PageHead = ({ title, sub, children }) => (
  <div className="pagehead reveal">
    <div><h2>{title}</h2><p className="sub">{sub}</p></div>
    {children}
  </div>
);
function Tile({ k, n, v, i }) {
  const c = useCount(Math.round(v));
  return (
    <article data-pollutant={k} className="reveal" style={{ '--d': i * 80 + 'ms' }}>
      <small>{n}</small><strong>{c} <span className="unit">avg</span></strong>
    </article>
  );
}
function CorrBar({ a, b, v, i, label }) {
  return (
    <div className="cbar reveal" style={{ '--d': i * 60 + 'ms' }}>
      <span className="cl2"><i style={{ background: a[2] }} />{label || a[1] + ' × ' + b[1]}<i style={{ background: b[2] }} /></span>
      <div className="track"><em className={v < 0 ? 'neg' : ''} style={{ '--w': Math.abs(v) * 100 + '%', background: `linear-gradient(90deg, ${a[2]}, ${b[2]})` }} /></div>
      <b>{v.toFixed(2)}</b>
    </div>
  );
}

const PARTICLES = Array.from({ length: 16 }, (_, i) => ({
  x: (i * 37) % 100, s: 6 + ((i * 13) % 14), t: 12 + ((i * 7) % 12), d: -((i * 5) % 14), c: P[i % 6][2]
}));

// every word animates in on its own
const Words = ({ text, start = 0, step = 130, hl = [] }) =>
  text.split(' ').map((w, i) => (
    <span key={i} className={'wd' + (hl.includes(w) ? ' hl' : '')} style={{ animationDelay: start + i * step + 'ms' }}>{w}</span>
  ));

// Self-contained styles, so the welcome page always looks right
const WELCOME_CSS = `
.welcome{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;overflow:hidden;
  background:radial-gradient(700px 420px at 15% 10%,rgba(54,176,160,.18),transparent 60%),
             radial-gradient(700px 420px at 85% 15%,rgba(140,121,201,.20),transparent 60%),
             radial-gradient(700px 480px at 50% 100%,rgba(224,112,122,.12),transparent 60%),#F6F4FA;
  transition:opacity .6s ease,transform .6s ease,filter .6s ease}
.welcome.leaving{opacity:0;transform:scale(1.05);filter:blur(6px);pointer-events:none}
.welcome .pt{position:absolute;bottom:-20px;border-radius:50%;opacity:0;animation:wfloat linear infinite}
@keyframes wfloat{0%{transform:translate3d(0,0,0);opacity:0}15%{opacity:.4}100%{transform:translate3d(60px,-110vh,0);opacity:0}}
.welcome .inner{position:relative;width:100%;max-width:820px;padding:24px;display:flex;flex-direction:column;align-items:center;text-align:center}
.welcome .logo-tile{width:84px;height:84px;display:grid;place-items:center;border-radius:26px;color:#fff;margin-bottom:22px;
  background:linear-gradient(135deg,#8C79C9,#36B0A0);box-shadow:0 16px 44px rgba(140,121,201,.45);
  animation:wlogo 1.1s cubic-bezier(.2,.8,.3,1.3) both,wbob 4s ease-in-out 1.2s infinite}
@keyframes wlogo{from{opacity:0;transform:scale(.3) rotate(-120deg)}to{opacity:1;transform:none}}
@keyframes wbob{50%{transform:translateY(-6px)}}
.welcome .eyebrow{font:700 12px 'DM Sans',sans-serif;letter-spacing:4px;color:#5FA88A;margin-bottom:14px;display:flex;flex-wrap:wrap;justify-content:center;gap:0 12px}
.welcome .title{font:800 clamp(34px,6.4vw,66px)/1.12 Manrope,sans-serif;color:#4E465C;margin:0 0 16px;display:flex;flex-wrap:wrap;justify-content:center;gap:0 .28em}
.welcome .sub2{font:500 clamp(14px,2vw,17px) 'DM Sans',sans-serif;color:#8A8296;margin:0 0 26px;display:flex;flex-wrap:wrap;justify-content:center;gap:0 .32em}
.welcome .wd{display:inline-block;opacity:0;animation:wword .85s cubic-bezier(.2,.7,.2,1) forwards}
@keyframes wword{from{opacity:0;transform:translateY(34px) scale(.92);filter:blur(10px)}to{opacity:1;transform:none;filter:blur(0)}}
.welcome .hl{background:linear-gradient(100deg,#8C79C9,#4A90C8 45%,#36B0A0);-webkit-background-clip:text;background-clip:text;color:transparent;
  background-size:200% 100%;animation:wword .85s cubic-bezier(.2,.7,.2,1) forwards,wshine 5s linear 1.5s infinite}
@keyframes wshine{to{background-position:-200% 0}}
.welcome .dots{display:flex;gap:10px;justify-content:center;margin-bottom:30px}
.welcome .dots i{width:11px;height:11px;border-radius:50%;opacity:0;animation:wpopdot .5s cubic-bezier(.2,.8,.3,1.4) forwards,wbob 2.6s ease-in-out infinite}
@keyframes wpopdot{from{opacity:0;transform:scale(0)}to{opacity:1;transform:none}}
.welcome .cta{position:relative;overflow:hidden;display:inline-flex;align-items:center;justify-content:center;gap:10px;margin:0 auto;
  padding:16px 38px;font:700 15px 'DM Sans',sans-serif;letter-spacing:.3px;color:#fff;border:0;border-radius:999px;cursor:pointer;
  background:linear-gradient(135deg,#8C79C9 0%,#6F8FD0 50%,#36B0A0 100%);background-size:160% 100%;
  box-shadow:0 10px 28px rgba(140,121,201,.45);opacity:0;
  animation:wcta .8s cubic-bezier(.2,.7,.2,1) 1.9s forwards,wring 2.8s ease-out 2.8s infinite;
  transition:transform .25s ease,background-position .5s ease,box-shadow .25s ease}
@keyframes wcta{from{opacity:0;transform:translateY(24px) scale(.9)}to{opacity:1;transform:none}}
@keyframes wring{0%{box-shadow:0 10px 28px rgba(140,121,201,.45),0 0 0 0 rgba(54,176,160,.45)}100%{box-shadow:0 10px 28px rgba(140,121,201,.45),0 0 0 22px rgba(54,176,160,0)}}
.welcome .cta::after{content:"";position:absolute;top:0;left:-70%;width:50%;height:100%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.55),transparent);transform:skewX(-20deg);transition:left .7s ease}
.welcome .cta:hover{transform:translateY(-4px) scale(1.05);background-position:100% 0;box-shadow:0 16px 38px rgba(54,176,160,.5)}
.welcome .cta:hover::after{left:130%}
.welcome .cta:active{transform:translateY(-1px) scale(.97)}
.welcome .cta .arrow{display:inline-block;transition:transform .3s ease}
.welcome .cta:hover .arrow{transform:translateX(6px)}
.welcome .cta:focus-visible{outline:3px solid #36B0A0;outline-offset:4px}
@media (prefers-reduced-motion:reduce){.welcome *{animation-duration:.01ms!important;animation-delay:0ms!important}}
`;

function Welcome({ leaving, onEnter }) {
  return (
    <div className={'welcome' + (leaving ? ' leaving' : '')}>
      <style>{WELCOME_CSS}</style>
      {PARTICLES.map((p, i) => (
        <span key={i} className="pt" style={{ left: p.x + '%', width: p.s, height: p.s, background: p.c, animationDuration: p.t + 's', animationDelay: p.d + 's' }} />
      ))}
      <div className="inner">
        <div className="logo-tile"><Wind size={38} /></div>
        <div className="eyebrow"><Words text="AIRSCOPE PAKISTAN" start={300} step={150} /></div>
        <h1 className="title"><Words text="Breathe data. Understand Pakistan’s air." start={550} step={170} hl={['Breathe', 'air.']} /></h1>
        <p className="sub2"><Words text="Hourly pollutant intelligence across five cities." start={1350} step={90} /></p>
        <div className="dots">{P.map((p, i) => <i key={p[0]} style={{ background: p[2], animationDelay: 1700 + i * 80 + 'ms, ' + i * 200 + 'ms' }} />)}</div>
        <button className="cta" onClick={onEnter}>Explore Dashboard <span className="arrow">→</span></button>
      </div>
    </div>
  );
}

export default function App() {
  const initPage = PAGE_IDS.includes(window.location.hash.slice(1)) ? window.location.hash.slice(1) : null;
  const [stage, setStage] = useState(initPage ? 'app' : 'welcome'); // welcome | leaving | app
  const [data, setData] = useState(null),
        [rows, setRows] = useState([]),
        [city, setCity] = useState('All cities'),
        [pollutant, setPollutant] = useState('pm2_5'),
        [status, setStatus] = useState('Loading'),
        [busy, setBusy] = useState(false),
        [error, setError] = useState(''),
        [toast, setToast] = useState(null),
        [page, setPage] = useState(initPage || 'overview'),
        [leaving, setLeaving] = useState(false),
        [menu, setMenu] = useState(false),
        [cityView, setCityView] = useState('grouped'),
        [scale, setScale] = useState('cap'),
        [shown, setShown] = useState(P.map(p => p[0])),
        [trendType, setTrendType] = useState('area'),
        [trendScope, setTrendScope] = useState('avg'),
        [curve, setCurve] = useState('monotone'),
        [corrView, setCorrView] = useState('heat'),
        [focus, setFocus] = useState('pm2_5'),
        [recSort, setRecSort] = useState('new'),
        [recRows, setRecRows] = useState(15),
        [cols, setCols] = useState(P.map(p => p[0]));

  const notify = (type, msg) => { setToast({ type, msg }); setTimeout(() => setToast(null), 3500); };

  async function load() {
    try {
      let [s, r, t] = await Promise.all([
        get('/api/summary'),
        get('/api/records?limit=500' + (city === 'All cities' ? '' : '&city=' + encodeURIComponent(city))),
        get('/api/etl/status')
      ]);
      setData(s); setRows(r); setStatus(t.status || 'Ready'); setError('');
    } catch (e) {
      setError(e.message); setStatus('API offline');
    }
  }

  useEffect(() => {
    load();
    let interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [city]);

  function go(id) {
    setMenu(false);
    if (id === page) return;
    setLeaving(true);
    setTimeout(() => { setPage(id); setLeaving(false); history.replaceState(null, '', '#' + id); window.scrollTo(0, 0); }, reduced() ? 0 : 220);
  }
  function enter() {
    history.replaceState(null, '', '#overview');
    setStage('leaving');
    setTimeout(() => setStage('app'), reduced() ? 0 : 650);
  }
  const toggleIn = (list, set) => k => set(l => (l.includes(k) ? (l.length > 1 ? l.filter(x => x !== k) : l) : P.map(p => p[0]).filter(x => x === k || l.includes(x))));

  async function refresh() {
    setBusy(true);
    try {
      await get('/api/etl/run', { method: 'POST' });
      setStatus('Running');
      let timer = setInterval(async () => {
        try {
          let s = await get('/api/etl/status');
          setStatus(s.status);
          if (s.status !== 'started') {
            clearInterval(timer);
            await load();
            setBusy(false);
            notify('ok', 'Data refreshed successfully');
          }
        } catch (e) {
          clearInterval(timer); setError(e.message); setBusy(false); notify('err', e.message);
        }
      }, 2500);
    } catch (e) {
      setError(e.message); setBusy(false); notify('err', e.message);
    }
  }

  function csv() {
    let keys = ['city', 'timestamp', ...P.map(x => x[0])];
    let body = [keys.join(','), ...rows.map(r => keys.map(k => JSON.stringify(r[k] ?? '')).join(','))].join('\n');
    let a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([body], { type: 'text/csv' }));
    a.download = 'air-quality-records.csv';
    a.click();
    notify('ok', 'CSV exported');
  }

  let cities = (data?.city_summaries || []).filter(x => city === 'All cities' || x.city === city);
  let bars = cities.map(x => ({ city: x.city, ...Object.fromEntries(P.map(p => [p[0], x.pollutants[p[0]]?.mean])) }));
  const hourFromRows = () => {
    const g = {};
    rows.forEach(r => {
      const h = pktHour(r.timestamp);
      g[h] ??= { hour: h };
      P.forEach(([k]) => { if (Number.isFinite(r[k])) { (g[h][k] ??= { s: 0, c: 0 }); g[h][k].s += r[k]; g[h][k].c++; } });
    });
    return Object.values(g).map(o => ({ hour: o.hour, ...Object.fromEntries(P.map(([k]) => [k, o[k] ? o[k].s / o[k].c : null])) })).sort((a, b) => a.hour - b.hour);
  };
  const hourlyRaw = city === 'All cities'
    ? (data?.hourly || []).map(x => ({ ...x, hour: (x.hour + (DATA_IS_UTC ? 5 : 0)) % 24 })).sort((a, b) => a.hour - b.hour)
    : hourFromRows();
  let hourly = hourlyRaw.map(x => ({ ...x, time: String(x.hour).padStart(2, '0') + ':00' }));
  const scopeText = city === 'All cities' ? 'Average of all ' + (cities.length || 5) + ' cities' : city;
  const cur = P.find(x => x[0] === pollutant);
  const pColor = cur[2];
  const loading = !data && !error;
  const avg = k => { const v = cities.map(x => x.pollutants[k]?.mean).filter(Number.isFinite); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0; };
  const anim = { isAnimationActive: !reduced(), animationDuration: 900, animationEasing: 'ease-out' };

  if (stage !== 'app') return <Welcome leaving={stage === 'leaving'} onEnter={enter} />;

  const citySel = (
    <select value={city} onChange={e => setCity(e.target.value)}>
      <option>All cities</option>
      {(data?.cities || []).map(c => <option key={c}>{c}</option>)}
    </select>
  );

  // ---- City comparison chart ----
  const vis = P.filter(p => shown.includes(p[0]));
  const stacked = cityView === 'stacked', horiz = cityView === 'horizontal';
  const vAx = stacked || scale === 'auto' ? {} : scale === 'log'
    ? { scale: 'log', domain: [1, 'auto'], allowDataOverflow: true }
    : { domain: [0, 1000], ticks: [0, 250, 500, 750, 1000], allowDataOverflow: true };
  const grid = <CartesianGrid strokeDasharray="3 3" opacity={0.1} />;
  const cityChart = cityView === 'lines' ? (
    <LineChart key="lines" data={bars}>
      {grid}<XAxis dataKey="city" /><YAxis {...vAx} /><Tooltip animationDuration={150} /><Legend />
      {vis.map(([k, n, c], i) => <Line key={k} type="monotone" dataKey={k} name={n} stroke={c} strokeWidth={3} dot={{ r: 4, fill: '#fff', stroke: c, strokeWidth: 2 }} {...anim} animationBegin={i * 80} />)}
    </LineChart>
  ) : (
    <BarChart key={cityView} data={bars} layout={horiz ? 'vertical' : 'horizontal'}>
      {grid}
      {horiz ? <XAxis type="number" {...vAx} /> : <XAxis dataKey="city" />}
      {horiz ? <YAxis type="category" dataKey="city" width={90} /> : <YAxis {...vAx} />}
      <Tooltip animationDuration={150} /><Legend />
      {vis.map(([k, n, c], i) => (
        <Bar key={k} dataKey={k} name={n} fill={c} stackId={stacked ? 's' : undefined}
          radius={stacked ? 0 : horiz ? [0, 4, 4, 0] : [4, 4, 0, 0]} {...anim} animationBegin={stacked ? 0 : i * 90} />
      ))}
    </BarChart>
  );

  // ---- Hourly trend chart ----
  const ax = [
    <CartesianGrid key="g" strokeDasharray="3 3" opacity={0.1} />,
    <XAxis key="x" dataKey="time" interval="preserveStartEnd" minTickGap={26} />,
    <YAxis key="y" />,
    <Tooltip key="t" animationDuration={150} cursor={{ stroke: pColor, strokeDasharray: '4 4', fill: pColor + '22' }} itemStyle={{ color: pColor }} />
  ];
  const tAnim = { ...anim, animationDuration: 1300, animationEasing: 'ease-in-out' };
  // one line per city (needs the records of all cities)
  const compare = city === 'All cities' && trendScope === 'cities';
  const cityNames = data?.cities || [];
  const cityLines = () => {
    const g = {};
    rows.forEach(r => {
      if (!Number.isFinite(r[pollutant])) return;
      const h = pktHour(r.timestamp);
      g[h] ??= { hour: h, time: String(h).padStart(2, '0') + ':00' };
      const o = (g[h][r.city] ??= { s: 0, c: 0 });
      o.s += r[pollutant]; o.c++;
    });
    return Object.values(g).map(o => {
      const x = { hour: o.hour, time: o.time };
      cityNames.forEach(n => { if (o[n]) x[n] = o[n].s / o[n].c; });
      return x;
    }).sort((a, b) => a.hour - b.hour);
  };
  const trendChart = compare ? (
    <LineChart key={'c' + pollutant} data={cityLines()}>{ax}<Legend />
      {cityNames.map((n, i) => (
        <Line key={n} type="monotone" dataKey={n} name={n} stroke={CITY_COLORS[i % CITY_COLORS.length]} strokeWidth={3} dot={false} connectNulls
          activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} {...tAnim} animationBegin={i * 120} />
      ))}
    </LineChart>
  ) : trendType === 'line' ? (
    <LineChart key={'l' + pollutant + curve} data={hourly}>{ax}
      <Line type={curve} dataKey={pollutant} name={cur[1]} stroke={pColor} strokeWidth={3} dot={false} activeDot={{ r: 6, fill: pColor, stroke: '#fff', strokeWidth: 3 }} {...tAnim} />
    </LineChart>
  ) : trendType === 'bar' ? (
    <BarChart key={'b' + pollutant} data={hourly}>{ax}
      <Bar dataKey={pollutant} name={cur[1]} fill={pColor} radius={[4, 4, 0, 0]} {...anim} />
    </BarChart>
  ) : (
    <AreaChart key={'a' + pollutant + curve} data={hourly}>
      <defs>
        <linearGradient id={'fill-' + pollutant} x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={pColor} stopOpacity={0.65} /><stop offset="95%" stopColor={pColor} stopOpacity={0} />
        </linearGradient>
      </defs>{ax}
      <Area type={curve} dataKey={pollutant} name={cur[1]} stroke={pColor} strokeWidth={3} fillOpacity={1} fill={'url(#fill-' + pollutant + ')'}
        activeDot={{ r: 6, fill: pColor, stroke: '#fff', strokeWidth: 3 }} {...tAnim} />
    </AreaChart>
  );
  const vals = hourly.map(h => ({ t: h.time, v: h[pollutant] })).filter(h => Number.isFinite(h.v));
  const peak = vals.reduce((m, h) => (!m || h.v > m.v ? h : m), null);
  const low = vals.reduce((m, h) => (!m || h.v < m.v ? h : m), null);
  const mean = vals.length ? vals.reduce((a, h) => a + h.v, 0) / vals.length : null;

  // ---- Correlation ----
  const corr = (r, c) => data?.correlations?.[r]?.[c] ?? 0;
  const pairs = [];
  P.forEach((a, i) => P.forEach((b, j) => { if (j > i) pairs.push({ a, b, v: corr(a[0], b[0]) }); }));
  pairs.sort((x, y) => Math.abs(y.v) - Math.abs(x.v));
  const fp = P.find(p => p[0] === focus);

  // ---- Records ----
  let shownRows = [...rows];
  if (recSort === 'pm') shownRows.sort((a, b) => (b.pm2_5 ?? 0) - (a.pm2_5 ?? 0));
  if (recSort === 'co') shownRows.sort((a, b) => (b.carbon_monoxide ?? 0) - (a.carbon_monoxide ?? 0));
  shownRows = shownRows.slice(0, recRows);
  const vcols = P.filter(p => cols.includes(p[0]));
  const pc = NAV.find(n => n[0] === page)[3];

  return (
    <div className="layout app-in">
      <div className="ambient" aria-hidden="true"><i /><i /><i /></div>
      <button className="menu-btn" onClick={() => setMenu(m => !m)} aria-label="Menu"><Menu size={18} /></button>
      <div className={'scrim' + (menu ? ' show' : '')} onClick={() => setMenu(false)} />
      <aside className={menu ? 'open' : ''}>
        <div className="logo"><Wind /> <b>AirScope</b></div>
        <p>PAKISTAN AIR QUALITY</p>
        {NAV.map(([id, ico, name]) => (
          <a key={id} href={'#' + id} className={page === id ? 'active' : ''} onClick={e => { e.preventDefault(); go(id); }}>
            <span className="ico">{ico}</span> {name}
          </a>
        ))}
        <div className="asidefoot">Open-Meteo API<br />ETL + EDA project</div>
      </aside>
      <main>
        <header className="reveal">
          <div>
            <small>AIR QUALITY INTELLIGENCE</small>
            <h1>Pakistan Air Monitor</h1>
            <p>Hourly pollutant analysis across five cities</p>
          </div>
          <div className="actions">
            <button onClick={csv}><Download size={15} /> Export CSV</button>
            <button className={'primary' + (busy ? ' spinning' : '')} onClick={refresh} disabled={busy}>
              <RefreshCw size={15} /> {busy ? 'Refreshing...' : 'Refresh data'}
            </button>
          </div>
        </header>

        {error && <div className="error">{error} — ensure the Python backend is running.</div>}

        <div key={page} className={'page' + (leaving ? ' out' : '')} style={{ '--pg': pc }}>

          {page === 'overview' && (
            <section>
              <PageHead title="National overview" sub="Live pipeline numbers and the average level of every pollutant">{citySel}</PageHead>
              <div className="stats">
                <Stat i={0} loading={loading} icon={<Database />} label="DATABASE RECORDS" value={data?.record_count || 0} />
                <Stat i={1} loading={loading} icon={<MapPin />} label="CITIES WITH DATA" value={data?.city_summaries?.filter(x => x.record_count).length || 0} suffix=" / 5" />
                <Stat i={2} loading={loading} icon={<Activity />} label="POLLUTANTS TRACKED" value={6} pad={2} />
                <article className="reveal" style={{ '--d': '390ms' }}>
                  <span className="float"><Wind /></span><small>PIPELINE STATUS</small>
                  <strong className="status"><i className={'live' + (busy ? ' on' : '')} />{status}</strong>
                </article>
              </div>
              {!loading && !data?.record_count && <div className="empty">No data yet. Start the ETL refresh to collect hourly observations.</div>}
              <h2 className="sub-h reveal" style={{ '--d': '500ms' }}>Average level by pollutant</h2>
              <div className="pollutant-summary">
                {P.map(([k, n], i) => <Tile key={k + city} k={P[i][3]} n={n} v={avg(k)} i={i + 6} />)}
              </div>
            </section>
          )}

          {page === 'cities' && (
            <section>
              <PageHead title="City comparison" sub="Mean concentrations · API-provided units" />
              <div className="controls reveal" style={{ '--d': '80ms' }}>
                <Ctl label="View"><Seg value={cityView} onChange={setCityView} opts={[['grouped', 'Grouped'], ['stacked', 'Stacked'], ['horizontal', 'Horizontal'], ['lines', 'Lines']]} /></Ctl>
                <Ctl label="Scale"><Seg value={scale} onChange={setScale} opts={[['cap', 'Cap 1000'], ['auto', 'Auto'], ['log', 'Log']]} /></Ctl>
                <Ctl label="Pollutants"><Chips on={k => shown.includes(k)} toggle={toggleIn(shown, setShown)} /></Ctl>
              </div>
              <div className="chart tall reveal" style={{ '--d': '160ms' }}>
                {loading ? <div className="skeleton sk-chart" /> : !bars.length ? <div className="empty">No city data yet. Press Refresh data.</div> : <>
                    <div className="chead">
                      <h3>Mean concentration of each pollutant in every city</h3>
                      <span className="unit-badge">{city === 'All cities' ? 'All cities' : city} · µg/m³</span>
                    </div>
                    <div className="rc"><ResponsiveContainer width="100%" height="100%" minHeight={280}>{cityChart}</ResponsiveContainer></div>
                  </>}
              </div>
              {scale === 'cap' && !stacked && <p className="sub">Scale capped at 1000: taller bars are cut off, hover for the exact value.</p>}
            </section>
          )}

          {page === 'trends' && (
            <section>
              <PageHead title="Hourly pollution trends" sub={cur[1] + ' by hour of day · ' + scopeText + ' · ' + hourly.length + ' hour' + (hourly.length === 1 ? '' : 's') + ' of data'}>{citySel}</PageHead>
              <div className="controls reveal" style={{ '--d': '80ms' }}>
                <Ctl label="Pollutant">
                  <div className="chips">{P.map(([k, n, c]) => <button key={k} className={'chip' + (pollutant === k ? ' on' : '')} style={{ '--p': c }} onClick={() => setPollutant(k)}>{n}</button>)}</div>
                </Ctl>
                <Ctl label="Data"><Seg value={city === 'All cities' ? trendScope : 'avg'} onChange={setTrendScope} opts={[['avg', 'Average of all cities'], ['cities', 'Compare cities']]} /></Ctl>
                {!compare && <Ctl label="Chart"><Seg value={trendType} onChange={setTrendType} opts={[['area', 'Area'], ['line', 'Line'], ['bar', 'Bars']]} /></Ctl>}
                {!compare && trendType !== 'bar' && <Ctl label="Curve"><Seg value={curve} onChange={setCurve} opts={[['monotone', 'Smooth'], ['step', 'Stepped']]} /></Ctl>}
              </div>
              <div className="insights">
                {[[compare ? 'Peak hour (all-city avg)' : 'Peak hour', peak && `${peak.t} · ${peak.v.toFixed(1)}`], ['Lowest hour', low && `${low.t} · ${low.v.toFixed(1)}`], ['Daily average', mean != null && mean.toFixed(1)]].map(([l, v], i) => (
                  <div key={l} className="ins reveal" data-pollutant={cur[3]} style={{ '--d': 120 + i * 80 + 'ms' }}><small>{l}</small><strong>{v || '—'}</strong></div>
                ))}
              </div>
              <div className="chart tall glow reveal" data-pollutant={cur[3]} style={{ '--d': '260ms' }}>
                {loading ? <div className="skeleton sk-chart" /> : !hourly.length ? <div className="empty">No hourly data yet. Press Refresh data.</div> : <>
                    <div className="chead">
                      <h3><span className="dot" style={{ background: pColor }} />{compare ? cur[1] + ' · one line for every city' : cur[1] + ' · average level for each hour of the day'}</h3>
                      <span className="unit-badge">{compare ? 'All cities compared' : scopeText} · µg/m³</span>
                    </div>
                    <div className="rc"><ResponsiveContainer width="100%" height="100%" minHeight={280}>{trendChart}</ResponsiveContainer></div>
                  </>}
              </div>
              {!loading && hourly.length > 0 && hourly.length < 12 && (
                <p className="warn">Only {hourly.length} hour{hourly.length === 1 ? '' : 's'} of readings are stored ({data?.record_count || 0} records in total), so the trend looks short. A full day needs 24 hours of data per city.</p>
              )}
            </section>
          )}

          {page === 'correlation' && (
            <section>
              <PageHead title="Pollutant correlations" sub="Pearson correlation · darker = stronger, dashed = negative" />
              <div className="controls reveal" style={{ '--d': '80ms' }}>
                <Ctl label="View"><Seg value={corrView} onChange={setCorrView} opts={[['heat', 'Heatmap'], ['rank', 'Strongest pairs'], ['focus', 'Focus']]} /></Ctl>
                {corrView === 'focus' && (
                  <Ctl label="Pollutant"><div className="chips">{P.map(([k, n, c]) => <button key={k} className={'chip' + (focus === k ? ' on' : '')} style={{ '--p': c }} onClick={() => setFocus(k)}>{n}</button>)}</div></Ctl>
                )}
              </div>
              {corrView === 'heat' && (
                <div className="matrix">
                  {P.map(([r, rn, rc], ri) => (
                    <div className="matrixrow" key={r}>
                      <b style={{ '--p': rc }}>{rn}</b>
                      {P.map(([c, cn, cc], ci) => {
                        let v = corr(r, c), abs = Math.abs(v), diag = r === c;
                        let style = diag ? { background: rc }
                          : { background: `linear-gradient(135deg, ${rc}${hexAlpha(0.18 + 0.82 * abs)}, ${cc}${hexAlpha(0.18 + 0.82 * abs)})`, color: abs > 0.7 ? '#fff' : undefined };
                        return <span key={c} className={'pop ' + (diag ? 'diag' : v < 0 ? 'neg' : '')} title={rn + ' × ' + cn + ': ' + v} style={{ ...style, animationDelay: (ri * 6 + ci) * 18 + 'ms' }}>{v.toFixed(2)}</span>;
                      })}
                    </div>
                  ))}
                </div>
              )}
              {corrView === 'rank' && <div className="cbars">{pairs.slice(0, 10).map((p, i) => <CorrBar key={p.a[0] + p.b[0]} {...p} i={i} />)}</div>}
              {corrView === 'focus' && (
                <div className="cbars">{P.filter(p => p[0] !== focus).map(p => ({ a: fp, b: p, v: corr(focus, p[0]) })).sort((x, y) => Math.abs(y.v) - Math.abs(x.v))
                  .map((p, i) => <CorrBar key={focus + p.b[0]} {...p} i={i} />)}</div>
              )}
              <p className="sub">Correlation does not prove causation.</p>
            </section>
          )}

          {page === 'records' && (
            <section>
              <PageHead title="Latest observations" sub={'Times in Pakistan time (PKT) · latest reading: ' + (rows[0] ? fmtTime(rows[0].timestamp) + ' PKT' : 'none yet')}>{citySel}</PageHead>
              <div className="controls reveal" style={{ '--d': '80ms' }}>
                <Ctl label="Sort"><Seg value={recSort} onChange={setRecSort} opts={[['new', 'Newest'], ['pm', 'Highest PM2.5'], ['co', 'Highest CO']]} /></Ctl>
                <Ctl label="Rows"><Seg value={recRows} onChange={setRecRows} opts={[[10, '10'], [15, '15'], [30, '30'], [50, '50']]} /></Ctl>
                <Ctl label="Columns"><Chips on={k => cols.includes(k)} toggle={toggleIn(cols, setCols)} /></Ctl>
              </div>
              <div className="tablewrap reveal" style={{ '--d': '160ms' }}>
                <table>
                  <thead><tr><th>City</th><th>Timestamp</th>{vcols.map(([k, n, c]) => <th key={k} style={{ boxShadow: `inset 0 -3px 0 ${c}` }}>{n}</th>)}</tr></thead>
                  <tbody>
                    {loading ? Array.from({ length: 5 }, (_, i) => <tr key={i}><td colSpan={8}><div className="skeleton sk-row" /></td></tr>)
                      : shownRows.map((r, i) => (
                        <tr key={recSort + i} className="rowin" style={{ animationDelay: i * 25 + 'ms' }}>
                          <td>{r.city}</td><td>{fmtTime(r.timestamp)} PKT</td>
                          {vcols.map(([k]) => <td key={k}>{r[k] ?? '—'}</td>)}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>

        <footer>AirScope Pakistan · Data source: Open-Meteo Air Quality API</footer>
      </main>

      {toast && <div className={'toast ' + toast.type} role="status">{toast.type === 'ok' ? '✓ ' : '! '}{toast.msg}</div>}
    </div>
  );
}
