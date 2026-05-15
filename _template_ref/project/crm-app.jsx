/* TasAR CRM — main app */
const { useState, useEffect, useMemo } = React;
const { TweaksPanel, useTweaks, TweakSection, TweakRadio, TweakColor } = window;

/* ============================================================
   Heatmap mark (logo)
   ============================================================ */
const LOGO_GRID = [
  [0.15, 0.25, 0.45, 0.55, 0.30, 0.15],
  [0.25, 0.55, 0.90, 1.00, 0.60, 0.25],
  [0.20, 0.45, 0.80, 0.85, 0.45, 0.20],
  [0.12, 0.22, 0.35, 0.40, 0.22, 0.12],
];
function heatColor(v, accent, hex){
  // Use rgba so we don't depend on accent having particular hex format
  const a = v < 0.2 ? 0.12 : v < 0.4 ? 0.32 : v < 0.6 ? 0.55 : v < 0.85 ? 0.85 : 1.0;
  return `color-mix(in srgb, ${accent} ${a*100}%, transparent)`;
}
function HeatmapLogoMark({ cell = 6, gap = 1.5, accent = 'var(--accent)' }){
  const grid = LOGO_GRID;
  const cols = grid[0].length, rows = grid.length;
  return (
    <div style={{
      display:'grid',
      gridTemplateColumns:`repeat(${cols}, ${cell}px)`,
      gridTemplateRows:`repeat(${rows}, ${cell}px)`,
      gap,
    }}>
      {grid.flat().map((v,i)=>(
        <div key={i} style={{
          width:cell, height:cell, borderRadius: Math.max(1, cell*0.18),
          background: heatColor(v, accent),
        }}/>
      ))}
    </div>
  );
}

/* ============================================================
   Tiny icons (inline svg, currentColor)
   ============================================================ */
const Icon = ({ d, size=18 }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d={d}/>
  </svg>
);
const I = {
  inbox:     "M22 12h-6l-2 3h-4l-2-3H2 M5.45 5.11l-3.13 6.27a2 2 0 0 0-.21.9V19a2 2 0 0 0 2 2h15.8a2 2 0 0 0 2-2v-6.73a2 2 0 0 0-.21-.9l-3.13-6.27A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
  home:      "M3 9.5L12 2l9 7.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V9.5z",
  doc:       "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h5",
  pipe:      "M9 3H4v5 M20 16v5h-5 M20 8a4 4 0 0 0-4-4h-1 M4 16a4 4 0 0 0 4 4h1",
  users:     "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75 M9 7a4 4 0 1 0 0 0z",
  chart:     "M3 3v18h18 M7 14l3-3 4 4 5-6",
  map:       "M1 6v15l7-3 8 3 7-3V3l-7 3-8-3-7 3z M8 3v15 M16 6v15",
  bell:      "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.7 21a2 2 0 0 1-3.4 0",
  book:      "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z",
  search:    "M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0 M21 21l-4.3-4.3",
  plus:      "M12 5v14 M5 12h14",
  gear:      "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
  caret:     "M6 9l6 6 6-6",
  star:      "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
  bldg:      "M3 21h18 M5 21V7l8-4v18 M19 21V11l-6-4 M9 9v.01 M9 12v.01 M9 15v.01 M9 18v.01",
  filter:    "M22 3H2l8 9.46V19l4 2v-8.54L22 3z",
  more:      "M12 12m0 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2 M5 12m0 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2 M19 12m0 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2",
  download:  "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3",
  share:     "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8 M16 6l-4-4-4 4 M12 2v13",
  pin:       "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z M12 10m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0",
};

/* ============================================================
   Mock data
   ============================================================ */
const ITEMS = [
  { id:'TR-2451', addr:'Av. Santa Fe 2350, 8°B',     zone:'Recoleta',   sup:'82 m²', amb:'3 amb', val:'USD 248.300', upm:'3.028', status:'en-analisis', statusLabel:'En análisis', client:'Banco Río Plata', priority:true },
  { id:'TR-2450', addr:'Thames 1882, PB',            zone:'Palermo',    sup:'64 m²', amb:'2 amb', val:'USD 219.840', upm:'3.435', status:'solicitado',  statusLabel:'Solicitado',  client:'Argencapital',     priority:false },
  { id:'TR-2449', addr:'Cabello 3470, 11°A',         zone:'Palermo',    sup:'112 m²',amb:'4 amb', val:'USD 384.720', upm:'3.435', status:'entregado',   statusLabel:'Entregado',   client:'Fondo Atlas',      priority:false },
  { id:'TR-2448', addr:'Quintana 480, 5°',           zone:'Recoleta',   sup:'186 m²',amb:'5 amb', val:'USD 591.480', upm:'3.180', status:'revision',    statusLabel:'En revisión', client:'M. Aldao',         priority:true },
  { id:'TR-2447', addr:'Cabildo 2780, 14°D',         zone:'Belgrano',   sup:'74 m²', amb:'3 amb', val:'USD 213.860', upm:'2.890', status:'entregado',   statusLabel:'Entregado',   client:'Token Homes',      priority:false },
  { id:'TR-2446', addr:'Defensa 870',                zone:'San Telmo',  sup:'138 m²',amb:'PH 4 amb', val:'USD 226.320', upm:'1.640', status:'en-analisis', statusLabel:'En análisis', client:'F. Pereyra',       priority:false },
  { id:'TR-2445', addr:'Av. Pueyrredón 1645, 3°C',   zone:'Recoleta',   sup:'95 m²', amb:'3 amb', val:'USD 302.100', upm:'3.180', status:'entregado',   statusLabel:'Entregado',   client:'REMAX Cono Sur',   priority:false },
  { id:'TR-2444', addr:'Honduras 5240, 2°',          zone:'Palermo',    sup:'48 m²', amb:'1 amb', val:'USD 164.880', upm:'3.435', status:'solicitado',  statusLabel:'Solicitado',  client:'L. Martinez',      priority:false },
  { id:'TR-2443', addr:'Yatay 460, 7°A',             zone:'Almagro',    sup:'68 m²', amb:'2 amb', val:'USD 127.840', upm:'1.880', status:'entregado',   statusLabel:'Entregado',   client:'M. Sosa',          priority:false },
];

const COMPARABLES = [
  { addr:'Av. Santa Fe 2412, 9°A',  sup:'78 m²', amb:'3 amb', priceUsd:'USD 238.600', upm:'3.059', dist:'120 m', sold:'Hace 28 días', match:96 },
  { addr:'Av. Callao 1280, 12°B',   sup:'85 m²', amb:'3 amb', priceUsd:'USD 254.900', upm:'2.999', dist:'380 m', sold:'Hace 41 días', match:92 },
  { addr:'Junín 1480, 5°A',         sup:'80 m²', amb:'3 amb', priceUsd:'USD 244.000', upm:'3.050', dist:'440 m', sold:'Hace 12 días', match:89 },
  { addr:'Av. Las Heras 1840, 7°D', sup:'78 m²', amb:'2 amb', priceUsd:'USD 252.840', upm:'3.241', dist:'520 m', sold:'Hace 60 días', match:84 },
  { addr:'Vicente López 1920, 6°B', sup:'88 m²', amb:'3 amb', priceUsd:'USD 251.680', upm:'2.860', dist:'310 m', sold:'Hace 75 días', match:81 },
];

const TIMELINE = [
  { t:'Comparables actualizados',  when:'hace 12 min',  detail:'34 unidades en radio 800m', accent:true },
  { t:'Bárbara López revisó',      when:'hace 2 h',     detail:'Aprobó el modelo hedónico' },
  { t:'Modelo recalculó',          when:'hace 5 h',     detail:'Ajuste por estado a "Bueno"' },
  { t:'Solicitud creada',          when:'ayer · 14:32', detail:'por Banco Río Plata · API v3.2' },
];

const TABS = [
  { id:'all',     label:'Todas',         cnt:142 },
  { id:'mine',    label:'Asignadas a mí',cnt:18  },
  { id:'urgent',  label:'Urgentes',      cnt:4   },
  { id:'review',  label:'En revisión',   cnt:7   },
];

/* ============================================================
   Sidebar
   ============================================================ */
function Sidebar({ view, setView }){
  const navMain = [
    { id:'bandeja',    icon:'inbox', label:'Bandeja',       badge:'12'   },
    { id:'tasaciones', icon:'doc',   label:'Tasaciones',    badge:'142'  },
    { id:'propiedades',icon:'home',  label:'Propiedades',   badge:'2.4k' },
    { id:'pipeline',   icon:'pipe',  label:'Pipeline',      badge:''     },
    { id:'clientes',   icon:'users', label:'Clientes',      badge:'318'  },
    { id:'mercado',     icon:'map',   label:'Mercado',       badge:''     },
    { id:'estudios',    icon:'book',  label:'Estudios',      badge:'#047' },
    { id:'reportes',    icon:'chart', label:'Reportes',      badge:''     },
  ];
  const navData = [
    { id:'comparables', icon:'pin',  label:'Comparables',   badge:'live', accent:true },
    { id:'config',      icon:'gear', label:'Configuración', badge:'' },
  ];
  return (
    <aside className="sidebar">
      <div className="logo-row">
        <HeatmapLogoMark cell={6.5} gap={1.4}/>
        <span className="wm">TasAR</span>
      </div>

      <div className="org-pill">
        <div className="av">RP</div>
        <div className="col">
          <div className="name">Río Plata · Tasaciones</div>
          <div className="plan">Plan Empresa · 12 usuarios</div>
        </div>
        <div className="caret"><Icon d={I.caret} size={14}/></div>
      </div>

      <div className="nav-section">
        <h6>Trabajo</h6>
        {navMain.map(n => (
          <div key={n.id} className={`nav-item ${view===n.id?'active':''}`} onClick={()=>setView(n.id)}>
            <span className="icon"><Icon d={I[n.icon]}/></span>
            <span>{n.label}</span>
            {n.badge && <span className="badge">{n.badge}</span>}
          </div>
        ))}
      </div>

      <div className="nav-section">
        <h6>Datos</h6>
        {navData.map(n => (
          <div key={n.id} className={`nav-item ${view===n.id?'active':''}`} onClick={()=>setView(n.id)}>
            <span className="icon"><Icon d={I[n.icon]}/></span>
            <span>{n.label}</span>
            {n.badge && <span className={`badge ${n.accent?'accent':''}`}>{n.badge}</span>}
          </div>
        ))}
      </div>

      <div className="sidebar-foot">
        <div className="user-row">
          <div className="av"/>
          <div style={{display:'flex', flexDirection:'column'}}>
            <div className="name">Bárbara López</div>
            <div className="role">Tasadora · MN 4821</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

/* ============================================================
   TopBar
   ============================================================ */
function TopBar({ view }){
  const titles = {
    bandeja:    { crumb:['Bandeja'], hideAction:false },
    tasaciones: { crumb:['Tasaciones','TR-2451','Av. Santa Fe 2350, 8°B'], hideAction:false },
    propiedades:{ crumb:['Propiedades'], hideAction:false },
    pipeline:   { crumb:['Pipeline'], hideAction:false },
    clientes:   { crumb:['Clientes'], hideAction:false },
    mercado:    { crumb:['Mercado','CABA · Mayo 2026'], hideAction:true },
    estudios:   { crumb:['Estudios','Edición #047 · Mayo 2026'], hideAction:true },
    reportes:   { crumb:['Reportes'], hideAction:false },
    comparables:{ crumb:['Comparables'], hideAction:true },
    config:     { crumb:['Configuración'], hideAction:true },
  };
  const t = titles[view] || titles.tasaciones;
  return (
    <div className="topbar">
      <div className="crumbs">
        {t.crumb.map((c,i,arr) => (
          <React.Fragment key={i}>
            {i===arr.length-1 && arr.length>1 ? <strong>{c}</strong> : <span>{c}</span>}
            {i < arr.length - 1 && <span className="sep">{i===0 ? '/' : '·'}</span>}
          </React.Fragment>
        ))}
      </div>
      <div className="search">
        <Icon d={I.search} size={15}/>
        <span>Buscar dirección, ID, cliente…</span>
        <span className="kbd">⌘K</span>
      </div>
      <div className="topbar-actions">
        <button className="icon-btn"><Icon d={I.bell} size={16}/><span className="dot"/></button>
        <button className="icon-btn"><Icon d={I.gear} size={16}/></button>
        {!t.hideAction && <button className="pill-btn"><Icon d={I.plus} size={14}/> Nueva tasación</button>}
      </div>
    </div>
  );
}

/* ============================================================
   List pane
   ============================================================ */
function ListPane({ selected, onSelect }){
  const [tab, setTab] = useState('all');
  return (
    <div className="list-pane">
      <div className="list-head">
        <div className="list-title">
          <h2>Tasaciones</h2>
          <span className="count">142 totales · 8 esta semana</span>
        </div>
        <div className="tabs">
          {TABS.map(t => (
            <div key={t.id} className={`tab ${tab===t.id?'on':''}`} onClick={()=>setTab(t.id)}>
              {t.label} <span className="cnt">{t.cnt}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="filter-row">
        <div className="chip on">Estado: cualquiera <span className="x"><Icon d={I.caret} size={11}/></span></div>
        <div className="chip">Zona: CABA <span className="x">×</span></div>
        <div className="chip">Cliente: todos</div>
        <div className="chip"><Icon d={I.filter} size={12}/> Más</div>
      </div>
      <div className="items">
        {ITEMS.map(it => (
          <div key={it.id}
               className={`item ${it.id===selected?'selected':''}`}
               onClick={()=>onSelect(it.id)}>
            <div className="item-row1">
              <span className="item-addr">{it.addr}</span>
              <span className="item-id">{it.id}</span>
            </div>
            <div className="item-row1">
              <div className="item-meta">
                <span>{it.zone}</span>
                <span style={{color:'var(--ink-4)'}}>·</span>
                <span>{it.sup}</span>
                <span style={{color:'var(--ink-4)'}}>·</span>
                <span>{it.amb}</span>
              </div>
              <span className="price">{it.val}</span>
            </div>
            <div className="item-row1">
              <div className={`status ${it.status}`}>
                <span className="d"/>
                {it.statusLabel}
              </div>
              <span style={{fontSize:11, color:'var(--ink-3)'}}>{it.client}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   Mini zone heatmap (for detail pane)
   ============================================================ */
function buildZoneGrid(cols=16, rows=9, hot=[8,5]){
  const out = [];
  for (let j=0; j<rows; j++){
    const row = [];
    for (let i=0; i<cols; i++){
      const dx = (i-hot[0])/cols, dy = (j-hot[1])/rows;
      const d = Math.sqrt(dx*dx*1.4 + dy*dy*0.9);
      const n = Math.sin(i*1.7+j*2.3)*0.04 + Math.cos(i*0.9-j*1.1)*0.05;
      let v = 1 - d*1.8 + n;
      if (v < 0) v = 0;
      if (v > 1) v = 1;
      row.push(v);
    }
    out.push(row);
  }
  return out;
}
function ZoneHeatmap(){
  const grid = useMemo(() => buildZoneGrid(20, 9, [10, 5]), []);
  const cell = 18, gap = 3;
  return (
    <div style={{position:'relative'}}>
      <div style={{
        display:'grid',
        gridTemplateColumns: `repeat(${grid[0].length}, ${cell}px)`,
        gridTemplateRows:    `repeat(${grid.length}, ${cell}px)`,
        gap,
      }}>
        {grid.flat().map((v,i)=>(
          <div key={i} style={{
            width:cell, height:cell, borderRadius:4,
            background: v < 0.05 ? 'transparent' : heatColor(v, 'var(--accent)'),
          }}/>
        ))}
      </div>
      {/* property pin */}
      <div style={{
        position:'absolute',
        left: 10 * (cell+gap) + cell/2 - 7,
        top:  5 * (cell+gap) + cell/2 - 7,
        width: 14, height: 14, borderRadius: 99, background: 'var(--ink)',
        border: '3px solid var(--paper)', boxShadow:'0 2px 6px rgba(0,0,0,0.25)',
      }}/>
      <div style={{
        position:'absolute',
        left: 10 * (cell+gap) + cell/2 + 14,
        top:  5 * (cell+gap) + cell/2 - 16,
        background:'var(--ink)', color:'var(--paper)',
        fontSize: 11, fontWeight: 600, padding:'4px 8px', borderRadius:6,
        whiteSpace:'nowrap',
      }}>Esta propiedad</div>
    </div>
  );
}

/* ============================================================
   Sparkline (value history)
   ============================================================ */
function Sparkline({ data }){
  const w = 600, h = 140, pad = 8;
  const max = Math.max(...data), min = Math.min(...data);
  const x = (i) => pad + (i/(data.length-1)) * (w - 2*pad);
  const y = (v) => pad + (1 - (v-min)/(max-min)) * (h - 2*pad);
  const points = data.map((v,i) => `${x(i)},${y(v)}`).join(' ');
  const area = `M ${x(0)},${h-pad} L ${points.split(' ').join(' L ')} L ${x(data.length-1)},${h-pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} style={{display:'block'}}>
      <defs>
        <linearGradient id="spark-fill-crm" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%"  stopColor="var(--accent)" stopOpacity="0.22"/>
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0"/>
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map(g=>(
        <line key={g} x1={pad} x2={w-pad} y1={pad+g*(h-2*pad)} y2={pad+g*(h-2*pad)}
              stroke="var(--line)" strokeWidth="1" strokeDasharray="3 4"/>
      ))}
      <path d={area} fill="url(#spark-fill-crm)"/>
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"/>
      <circle cx={x(data.length-1)} cy={y(data[data.length-1])} r="4.5" fill="var(--accent)"/>
      <circle cx={x(data.length-1)} cy={y(data[data.length-1])} r="10"  fill="var(--accent)" opacity="0.2"/>
    </svg>
  );
}

/* ============================================================
   Detail pane
   ============================================================ */
function DetailPane({ item }){
  if (!item) return null;
  const series = [2380, 2410, 2425, 2440, 2460, 2480, 2510, 2530, 2560, 2590, 2620, 2680, 2720, 2780, 2820, 2890, 3028];

  return (
    <div className="detail-pane">
      {/* Header */}
      <div className="detail-head">
        <div className="left">
          <div className="row-flex" style={{color:'var(--ink-3)', fontSize:12}}>
            <span className="mono">{item.id}</span>
            <span style={{color:'var(--ink-4)'}}>·</span>
            <div className={`status ${item.status}`}><span className="d"/>{item.statusLabel}</div>
            <span style={{color:'var(--ink-4)'}}>·</span>
            <span className="live"><span className="ld"/>live · 34 comparables</span>
          </div>
          <h1>{item.addr}</h1>
          <div className="sub">
            <Icon d={I.pin} size={14}/> {item.zone}, CABA · {item.sup} · {item.amb} · estado bueno
          </div>
        </div>
        <div className="actions">
          <button className="pill-btn ghost"><Icon d={I.share} size={14}/> Compartir</button>
          <button className="pill-btn ghost"><Icon d={I.download} size={14}/> Exportar PDF</button>
          <button className="pill-btn accent">Enviar a cliente →</button>
        </div>
      </div>

      {/* Stat row */}
      <div className="stat-row">
        <div className="stat">
          <div className="k">Estimación TasAR</div>
          <div className="v num">USD 248.300</div>
          <div className="d">Rango USD 232 – 264k · ±6,5%</div>
        </div>
        <div className="stat">
          <div className="k">USD por m²</div>
          <div className="v num">3.028</div>
          <div className="d up">+4,8% vs zona</div>
        </div>
        <div className="stat">
          <div className="k">Confianza del modelo</div>
          <div className="v num">87%</div>
          <div className="d">Alta · 34 comparables</div>
        </div>
        <div className="stat">
          <div className="k">Cap rate estimado</div>
          <div className="v num">4,8%</div>
          <div className="d">anual · alquiler 1.244 USD</div>
        </div>
      </div>

      {/* Two cards stacked: zone heatmap, then valuation history */}
      <div className="card">
        <div className="card-head">
          <div>
            <h3>Mapa de valor · Recoleta</h3>
            <div className="sub">Radio 800m · 18.420 avisos activos</div>
          </div>
          <span className="live"><span className="ld"/>en vivo</span>
        </div>
        <div style={{display:'flex', justifyContent:'center'}}>
          <ZoneHeatmap/>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', marginTop:14, fontSize:11, color:'var(--ink-3)'}}>
          <div className="mono">Mín USD 2.640 /m²</div>
          <div className="mono" style={{color:'var(--ink)', fontWeight:600}}>Mediana 3.028</div>
          <div className="mono">Máx USD 3.520 /m²</div>
        </div>
      </div>
      <div className="card">
        <div className="card-head">
          <div>
            <h3>Histórico USD/m² · Recoleta</h3>
            <div className="sub">17 meses · enero 2025 — mayo 2026</div>
          </div>
          <span className="mono" style={{color:'var(--gain)', fontWeight:600, fontSize:12}}>+14,2% YoY</span>
        </div>
        <Sparkline data={series}/>
        <div style={{display:'flex', justifyContent:'space-between', marginTop:8, fontSize:11, color:'var(--ink-3)'}}>
          <span className="mono">Ene 25</span>
          <span className="mono">May 26</span>
        </div>
      </div>

      {/* Comparables table */}
      <div className="card">
        <div className="card-head">
          <div>
            <h3>Comparables usados (5 de 34)</h3>
            <div className="sub">Ventas y avisos de los últimos 90 días · radio 800m</div>
          </div>
          <button className="pill-btn ghost" style={{height:30, padding:'0 10px', fontSize:12}}>Ver los 34</button>
        </div>
        <table className="cmp">
          <thead>
            <tr>
              <th>Dirección</th>
              <th>Sup.</th>
              <th>Ambientes</th>
              <th className="right">Precio</th>
              <th className="right">USD/m²</th>
              <th>Distancia</th>
              <th>Cerrado</th>
              <th>Match</th>
            </tr>
          </thead>
          <tbody>
            {COMPARABLES.map((c,i)=>(
              <tr key={i}>
                <td className="addr">{c.addr}</td>
                <td>{c.sup}</td>
                <td>{c.amb}</td>
                <td className="right" style={{color:'var(--ink)', fontWeight:600}}>{c.priceUsd}</td>
                <td className="right">{c.upm}</td>
                <td>{c.dist}</td>
                <td>{c.sold}</td>
                <td>
                  <div className="row-flex" style={{gap:8}}>
                    <span className="match-bar"><div style={{width:`${c.match}%`}}/></span>
                    <span className="mono" style={{fontSize:12, fontWeight:600}}>{c.match}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================
   Right rail
   ============================================================ */
function RightRail(){
  return (
    <div className="rail">
      <div>
        <h4>Cliente</h4>
        <div className="contact-card">
          <div className="av"/>
          <div style={{display:'flex', flexDirection:'column'}}>
            <div className="name">Banco Río Plata</div>
            <div className="meta">Mariana Sosa · Risk · MS@</div>
          </div>
        </div>
      </div>

      <div>
        <h4>Datos del inmueble</h4>
        <div className="kv-list">
          <div className="kv"><span className="k">Tipo</span><span className="v">Departamento</span></div>
          <div className="kv"><span className="k">Sup. cubierta</span><span className="v mono">82 m²</span></div>
          <div className="kv"><span className="k">Sup. descubierta</span><span className="v mono">6 m²</span></div>
          <div className="kv"><span className="k">Ambientes</span><span className="v mono">3</span></div>
          <div className="kv"><span className="k">Antigüedad</span><span className="v">18 años</span></div>
          <div className="kv"><span className="k">Estado</span><span className="v">Bueno</span></div>
          <div className="kv"><span className="k">Orientación</span><span className="v">Frente · NE</span></div>
          <div className="kv"><span className="k">Piso</span><span className="v">8°</span></div>
          <div className="kv"><span className="k">Cochera</span><span className="v">Sí · fija</span></div>
        </div>
      </div>

      <div>
        <h4>Actividad</h4>
        <div className="timeline">
          {TIMELINE.map((t,i)=>(
            <div className="tl-item" key={i}>
              <div className={`tl-dot ${t.accent?'accent':''}`}/>
              <div className="tl-line"/>
              <div>
                <div className="tl-text"><strong>{t.t}</strong> — {t.detail}</div>
                <div className="tl-time">{t.when}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   ViewTasaciones (the original 3-pane layout)
   ============================================================ */
function ViewTasaciones(){
  const [selected, setSelected] = useState('TR-2451');
  const item = ITEMS.find(i => i.id === selected) || ITEMS[0];
  return (
    <div className="workspace">
      <ListPane selected={selected} onSelect={setSelected}/>
      <DetailPane item={item}/>
      <RightRail/>
    </div>
  );
}

/* ============================================================
   App
   ============================================================ */
function App(){
  const [view, setView] = useState('tasaciones');

  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "theme": "light",
    "accent": "#00B37E"
  }/*EDITMODE-END*/;
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tweaks.theme);
    document.documentElement.style.setProperty('--accent', tweaks.accent);
  }, [tweaks.theme, tweaks.accent]);

  // View router. Each view component is on window (registered by crm-views.jsx).
  const Views = {
    bandeja:     window.ViewBandeja,
    tasaciones:  ViewTasaciones,
    propiedades: window.ViewPropiedades,
    pipeline:    window.ViewPipeline,
    clientes:    window.ViewClientes,
    mercado:     window.ViewMercado,
    estudios:    window.ViewEstudio,
    reportes:    window.ViewReportes,
    comparables: window.ViewComparables,
    config:      window.ViewConfig,
  };
  const CurrentView = Views[view] || ViewTasaciones;

  return (
    <>
      <div className="app" data-screen-label={`01 CRM · ${view}`}>
        <Sidebar view={view} setView={setView}/>
        <main className="col">
          <TopBar view={view}/>
          <CurrentView/>
        </main>
      </div>

      <TweaksPanel title="Tweaks · CRM">
        <TweakSection title="Tema">
          <TweakRadio
            label="Modo"
            value={tweaks.theme}
            options={[{label:'Light', value:'light'}, {label:'Dark', value:'dark'}]}
            onChange={(v)=>setTweak('theme', v)}
          />
        </TweakSection>
        <TweakSection title="Color de acento">
          <TweakColor
            label="Accent"
            value={tweaks.accent}
            options={['#00B37E','#0F6E5A','#3B82F6','#C9532A','#D9A93A','#0D1412']}
            onChange={(v)=>setTweak('accent', v)}
          />
        </TweakSection>
      </TweaksPanel>
    </>
  );
}

// Expose shared helpers + data for crm-views.jsx (loaded after this file)
Object.assign(window, { HeatmapLogoMark, Icon, I, ITEMS, COMPARABLES, heatColor, Sparkline, ZoneHeatmap, buildZoneGrid });

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
