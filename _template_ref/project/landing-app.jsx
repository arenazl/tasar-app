/* TasAR Landing — main app */
const { useState, useMemo, useEffect } = React;
const { TweaksPanel, useTweaks, TweakSection, TweakToggle, TweakColor, TweakRadio } = window;

/* ============================================================
   Heatmap mark — reuse our logo's grid system, smaller
   ============================================================ */
const GRID_MID_LANDING = [
  [0.15, 0.25, 0.45, 0.55, 0.30, 0.15],
  [0.25, 0.55, 0.90, 1.00, 0.60, 0.25],
  [0.20, 0.45, 0.80, 0.85, 0.45, 0.20],
  [0.12, 0.22, 0.35, 0.40, 0.22, 0.12],
];
function heatColor(v, accent){
  if (v < 0.2)  return `${accent}1f`;     // 12% alpha
  if (v < 0.4)  return `${accent}52`;     // 32%
  if (v < 0.6)  return `${accent}8c`;     // 55%
  if (v < 0.85) return accent;
  return accent;
}
function alphaScale(accent, a){ return `${accent}${Math.round(a*255).toString(16).padStart(2,'0')}`; }

function HeatmapLogoMark({ cell = 6, gap = 1.5, accent }){
  const grid = GRID_MID_LANDING;
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
   CityHeatmap — bigger, stylized hero with labels
   Vaguely BA-shaped: a wider grid with hottest cells off-center
   to feel like a real "central business district" map.
   ============================================================ */
function buildCityGrid(cols=22, rows=14, hot=[10, 6]){
  // Distance-based intensity from hot point, with some noise
  const seed = (i,j) => {
    const dx = (i - hot[0]) / cols;
    const dy = (j - hot[1]) / rows;
    const d = Math.sqrt(dx*dx*1.4 + dy*dy*0.9);
    // pseudo noise
    const n = Math.sin(i*1.7 + j*2.3) * 0.05 + Math.cos(i*0.9 - j*1.1) * 0.06;
    let v = 1 - d*1.9 + n;
    if (v < 0) v = 0;
    if (v > 1) v = 1;
    return v;
  };
  const out = [];
  for (let j=0; j<rows; j++){
    const row = [];
    for (let i=0; i<cols; i++) row.push(seed(i, j));
    out.push(row);
  }
  // carve out some "river/edge" coolness on the left edge to feel less circular
  for (let j=0; j<rows; j++){
    out[j][0] = Math.min(out[j][0], 0.05);
    out[j][1] = Math.min(out[j][1], 0.08);
  }
  return out;
}

function CityHeatmap({ accent }){
  const grid = useMemo(() => buildCityGrid(22, 14, [11, 7]), []);
  const cols = grid[0].length, rows = grid.length;
  const cell = 22, gap = 3;
  const w = cols*cell + (cols-1)*gap;
  const h = rows*cell + (rows-1)*gap;

  // Labels for selected hot zones. `side` decides which way the callout floats.
  const labels = [
    { i: 12, j: 6,  name: 'Palermo',   px: 'USD 3.420 /m²', d: '+2.1%', side:'left'  },
    { i: 9,  j: 5,  name: 'Recoleta',  px: 'USD 3.180 /m²', d: '+1.4%', side:'right' },
    { i: 14, j: 9,  name: 'Belgrano',  px: 'USD 2.890 /m²', d: '+0.9%', side:'right' },
    { i: 6,  j: 10, name: 'San Telmo', px: 'USD 1.640 /m²', d: '−0.4%', side:'right' },
  ];

  return (
    <div style={{position:'relative', width: w, height: h, marginInline:'auto'}}>
      <div style={{
        display:'grid',
        gridTemplateColumns:`repeat(${cols}, ${cell}px)`,
        gridTemplateRows:`repeat(${rows}, ${cell}px)`,
        gap,
      }}>
        {grid.flat().map((v,k)=>{
          const isHot = v >= 0.85;
          return (
            <div key={k} style={{
              width:cell, height:cell, borderRadius: 5,
              background: v < 0.05
                ? 'transparent'
                : heatColor(v, accent),
              animation: isHot ? `cell-pulse 2.6s ease-in-out infinite` : undefined,
              animationDelay: `${(k%5)*0.18}s`,
            }}/>
          );
        })}
      </div>
      {/* Labels */}
      {labels.map(l => {
        const x = l.i * (cell+gap) + cell/2;
        const y = l.j * (cell+gap) + cell/2;
        const isDown = l.d.startsWith('−');
        const onRight = l.side === 'right'; // callout extends to the right of anchor
        const calloutW = 120;
        const offset = 18;
        return (
          <div key={l.name} style={{
            position:'absolute',
            left: onRight ? x + offset : x - offset - calloutW,
            top: y - 22,
            width: calloutW,
            background:'var(--paper)', border:'1px solid var(--line-2)', borderRadius: 8,
            padding:'7px 10px',
            fontFamily:"'Inter',sans-serif", fontSize: 11,
            boxShadow:'0 4px 16px rgba(13,20,18,0.08)',
            display:'flex', flexDirection:'column', gap:2,
          }}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:6}}>
              <span style={{fontWeight:600, color:'var(--ink)'}}>{l.name}</span>
              <span className="mono" style={{
                fontSize:10, fontWeight:600,
                color: isDown ? 'var(--loss)' : 'var(--gain)',
              }}>{l.d}</span>
            </div>
            <div className="mono" style={{fontSize:10.5, color:'var(--ink-3)'}}>{l.px}</div>
            {/* connector dot */}
            <div style={{
              position:'absolute',
              left: onRight ? -7 : 'auto',
              right: onRight ? 'auto' : -7,
              top:'50%', transform:'translateY(-50%)',
              width:6, height:6, borderRadius:99, background:'var(--ink)',
            }}/>
          </div>
        );
      })}
      <style>{`
        @keyframes cell-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.6; transform: scale(0.96); }
        }
      `}</style>
    </div>
  );
}

/* ============================================================
   Ticker — scrolling zone prices
   ============================================================ */
const TICKER_DATA = [
  ['Palermo',     '3.420', '+2.1%'],
  ['Recoleta',    '3.180', '+1.4%'],
  ['Belgrano',    '2.890', '+0.9%'],
  ['Caballito',   '2.140', '+0.2%'],
  ['Núñez',       '2.760', '+1.1%'],
  ['Villa Crespo','2.020', '+0.6%'],
  ['Almagro',     '1.880', '−0.3%'],
  ['San Telmo',   '1.640', '−0.4%'],
  ['Boedo',       '1.520', '−0.1%'],
  ['Flores',      '1.480', '−0.2%'],
  ['Colegiales',  '2.430', '+0.7%'],
  ['Saavedra',    '2.020', '+0.3%'],
];
function Ticker(){
  const items = [...TICKER_DATA, ...TICKER_DATA]; // duplicate for seamless loop
  return (
    <div className="ticker">
      <div className="ticker-tag">EN VIVO · CABA · USD/m²</div>
      <div className="ticker-track">
        {items.map(([z,p,c], i) => {
          const down = c.startsWith('−');
          return (
            <div className="ticker-item" key={i}>
              <span className="zone">{z}</span>
              <span className="px">{p}</span>
              <span className={`chg ${down ? 'down' : 'up'}`}>{c}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ============================================================
   Top Nav
   ============================================================ */
function TopNav({ accent }){
  return (
    <nav className="top gutter">
      <a href="#" style={{display:'flex', alignItems:'center', gap:12, textDecoration:'none', color:'var(--ink)'}}>
        <HeatmapLogoMark cell={7} gap={1.6} accent={accent}/>
        <span style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:24, letterSpacing:'-0.035em'}}>TasAR</span>
      </a>
      <div className="links">
        <a href="#mercado">Mercado</a>
        <a href="#productos">Productos</a>
        <a href="#reporte">Reportes</a>
        <a href="#tasador">Tasador</a>
        <a href="#empresas">Empresas</a>
      </div>
      <div style={{display:'flex', gap: 10, alignItems:'center'}}>
        <button className="pill ghost">Ingresar</button>
        <button className="pill accent">Pedir demo →</button>
      </div>
    </nav>
  );
}

/* ============================================================
   Hero
   ============================================================ */
function Hero({ accent }){
  return (
    <section className="hero gutter">
      <div>
        <div className="eyebrow">Mayo 2026 · Reporte #047</div>
        <h1 className="display-tight">
          El mercado<br/>
          inmobiliario,<br/>
          <span className="accent">en datos.</span>
        </h1>
        <p className="lede">
          TasAR procesa millones de avisos, escrituras y permisos al mes para darte
          el precio real de cada zona, edificio y tipología. Sin opiniones. Sin "estimaciones".
          Sin un broker en el medio.
        </p>
        <div className="hero-ctas">
          <button className="pill accent">Ver el último reporte →</button>
          <button className="pill ghost">Probar el tasador</button>
        </div>
        <div className="hero-meta">
          <div className="cell">
            <div className="label">Avisos analizados</div>
            <div className="num val">2,4M</div>
          </div>
          <div className="cell">
            <div className="label">Zonas cubiertas</div>
            <div className="num val">142</div>
          </div>
          <div className="cell">
            <div className="label">Actualización</div>
            <div className="num val">24h</div>
          </div>
        </div>
      </div>

      {/* Heatmap card */}
      <div className="heatcard">
        <div className="head">
          <div>
            <div className="title">Valor promedio USD/m² · Capital Federal</div>
            <div className="sub">14 de mayo, 2026 · n=18.420 avisos activos</div>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:6, fontSize:11, color:'var(--ink-3)'}}>
            <span className="live-dot"/> en vivo
          </div>
        </div>
        <div style={{padding:'12px 0'}}>
          <CityHeatmap accent={accent}/>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div className="legend">
            <span>menor</span>
            <div className="scale">
              <span style={{background: alphaScale(accent,0.12)}}/>
              <span style={{background: alphaScale(accent,0.32)}}/>
              <span style={{background: alphaScale(accent,0.55)}}/>
              <span style={{background: accent}}/>
            </div>
            <span>mayor</span>
          </div>
          <div className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>
            Fuente · TasAR Index v3.2
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   Metrics row
   ============================================================ */
function MetricsRow(){
  const data = [
    { k:'Índice TasAR · CABA', v:'2.847', d:'USD/m² promedio ponderado', chg:'+1.2% mensual' },
    { k:'Tiempo medio de venta', v:'94', d:'días en CABA · 2BR', chg:'−8 días vs Q1' },
    { k:'Oferta activa', v:'62.480', d:'unidades en venta', chg:'−3.4% vs Abr' },
    { k:'Permisos nuevos', v:'1.213', d:'aprobados este mes', chg:'+12% interanual' },
  ];
  return (
    <section id="mercado" className="metrics">
      {data.map((m,i)=>(
        <div className="m" key={i}>
          <div className="k">{m.k}</div>
          <div className="v num">{m.v}</div>
          <div className="d">{m.d}</div>
          <div className="mono" style={{fontSize:11, color: m.chg.startsWith('−') ? 'var(--loss)' : 'var(--gain)', fontWeight:600}}>{m.chg}</div>
        </div>
      ))}
    </section>
  );
}

/* ============================================================
   Products
   ============================================================ */
function Products(){
  const items = [
    {
      tag:'Reportes',
      title:'Informes mensuales',
      desc:'Análisis profundo del mercado por zona, tipología y segmento. PDF + datos en CSV. Publicamos el 5 de cada mes.',
      price:'USD 240',
      unit:'/mes',
    },
    {
      tag:'API',
      title:'TasAR Data API',
      desc:'Conectá tu CRM, modelo o sitio. Series de precios, índices, y geoanalítica con SLA del 99.9%.',
      price:'USD 1.200',
      unit:'/mes desde',
    },
    {
      tag:'Servicio',
      title:'Tasaciones a medida',
      desc:'Para bancos, fondos y judicial. Tasador matriculado + nuestro modelo. Entrega en 48hs hábiles.',
      price:'A medida',
      unit:'',
    },
  ];
  return (
    <section id="productos" className="section gutter">
      <div className="section-head">
        <h2 className="display">Tres formas de usar TasAR</h2>
        <div className="right">
          Cada producto comparte el mismo motor: el TasAR Index, alimentado por escrituras del RPI, avisos activos y permisos municipales.
        </div>
      </div>
      <div className="products">
        {items.map((p,i)=>(
          <div className="prod" key={i}>
            <div className="tag">{p.tag}</div>
            <h3>{p.title}</h3>
            <p>{p.desc}</p>
            <div className="foot">
              <div className="price">{p.price}<small>{p.unit}</small></div>
              <div className="arrow">→</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   Sparkline chart
   ============================================================ */
function Sparkline({ data, accent }){
  const w = 480, h = 180, pad = 12;
  const max = Math.max(...data), min = Math.min(...data);
  const x = (i) => pad + (i / (data.length-1)) * (w - 2*pad);
  const y = (v) => pad + (1 - (v-min)/(max-min)) * (h - 2*pad);
  const points = data.map((v,i) => `${x(i)},${y(v)}`).join(' ');
  const areaPath = `M ${x(0)},${h-pad} L ${points.split(' ').join(' L ')} L ${x(data.length-1)},${h-pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} style={{display:'block'}}>
      <defs>
        <linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%"  stopColor={accent} stopOpacity="0.28"/>
          <stop offset="100%" stopColor={accent} stopOpacity="0"/>
        </linearGradient>
      </defs>
      {/* gridlines */}
      {[0.25, 0.5, 0.75].map(g=>(
        <line key={g} x1={pad} x2={w-pad} y1={pad + g*(h-2*pad)} y2={pad + g*(h-2*pad)}
              stroke="var(--line)" strokeWidth="1" strokeDasharray="3 4"/>
      ))}
      <path d={areaPath} fill="url(#spark-fill)"/>
      <polyline points={points} fill="none" stroke={accent} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"/>
      {/* end dot */}
      <circle cx={x(data.length-1)} cy={y(data[data.length-1])} r="5" fill={accent}/>
      <circle cx={x(data.length-1)} cy={y(data[data.length-1])} r="11" fill={accent} opacity="0.18"/>
    </svg>
  );
}

/* ============================================================
   Featured Report preview
   ============================================================ */
function ReportPreview({ accent }){
  const series = [2.41,2.43,2.42,2.46,2.49,2.48,2.52,2.55,2.58,2.62,2.66,2.71,2.75,2.78,2.80,2.83,2.85];
  return (
    <section id="reporte" className="section gutter">
      <div className="section-head">
        <h2 className="display">Reporte de mayo</h2>
        <div className="right">
          Nuestro informe insignia. 38 páginas. Disponible para suscriptores el primer día hábil del mes.
        </div>
      </div>
      <div className="report">
        <div style={{display:'flex', flexDirection:'column'}}>
          <div className="meta">Mayo 2026 · Edición #047 · CABA + GBA</div>
          <h3 className="display">El interanual cierra en +14,2% y el m² supera los USD 2.800 por primera vez desde 2019.</h3>
          <ul>
            <li>Recuperación liderada por Palermo, Recoleta y Núñez.</li>
            <li>Caída sostenida del stock activo (−3.4% mes a mes).</li>
            <li>Permisos de obra nueva crecen 12% interanual.</li>
            <li>Análisis de cap rate por barrio y tipología.</li>
          </ul>
          <div style={{marginTop: 32, display:'flex', gap:10}}>
            <button className="pill accent">Descargar PDF (suscriptores)</button>
            <button className="pill ghost">Ver resumen gratuito</button>
          </div>
        </div>
        <div className="chart-card">
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
            <div>
              <div className="eyebrow">Índice TasAR · CABA</div>
              <div className="num" style={{fontSize: 36, marginTop: 4}}>2.847 <small style={{fontSize:14, color:'var(--ink-3)', fontWeight:500}}>USD/m²</small></div>
            </div>
            <div className="mono up" style={{fontWeight:600}}>+14,2% YoY</div>
          </div>
          <Sparkline data={series} accent={accent}/>
          <div style={{display:'flex', justifyContent:'space-between'}}>
            <div className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>Ene 25</div>
            <div className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>May 26</div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   Tasador interactive (UI only — placeholders)
   ============================================================ */
function Tasador({ accent }){
  const [tipo, setTipo] = useState('Departamento');
  const [estado, setEstado] = useState('Bueno');
  return (
    <section id="tasador" className="section gutter">
      <div className="section-head">
        <h2 className="display">Tasador instantáneo</h2>
        <div className="right">
          Estimación en segundos basada en comparables reales de los últimos 90 días. Gratis hasta 5 consultas por mes.
        </div>
      </div>
      <div className="tasador">
        <div className="tasador-form">
          <div className="eyebrow">Datos del inmueble</div>
          <div className="field">
            <label>Dirección</label>
            <div className="ctl mono">Av. Santa Fe 2350, Recoleta</div>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Sup. cubierta</label>
              <div className="ctl mono">82 m²</div>
            </div>
            <div className="field">
              <label>Ambientes</label>
              <div className="ctl mono">3</div>
            </div>
          </div>
          <div className="field">
            <label>Tipo</label>
            <div className="chips">
              {['Departamento','PH','Casa','Oficina','Local'].map(t=>(
                <div key={t} className={`chip ${tipo===t?'on':''}`} onClick={()=>setTipo(t)}>{t}</div>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Estado</label>
            <div className="chips">
              {['A estrenar','Muy bueno','Bueno','A reciclar'].map(t=>(
                <div key={t} className={`chip ${estado===t?'on':''}`} onClick={()=>setEstado(t)}>{t}</div>
              ))}
            </div>
          </div>
          <button className="pill accent" style={{alignSelf:'flex-start', marginTop:8}}>Calcular valor →</button>
        </div>

        <div className="tasador-result">
          <div className="eyebrow">Estimación TasAR</div>
          <div className="num value">USD 248.300</div>
          <div className="range">Rango probable · USD 232.000 – 264.500 · ±6,5%</div>

          <div style={{marginTop: 12}}>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:12, color:'var(--ink-3)', marginBottom:6}}>
              <span>Confianza del modelo</span>
              <span className="mono" style={{color:'var(--ink)', fontWeight:600}}>87%</span>
            </div>
            <div className="conf"><div className="bar" style={{width:'87%', background:accent}}/></div>
          </div>

          <div className="hairline" style={{marginBlock:8}}/>

          <div style={{display:'flex', flexDirection:'column', gap:10}}>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:13}}>
              <span style={{color:'var(--ink-2)'}}>Valor por m²</span>
              <span className="mono" style={{fontWeight:600}}>USD 3.028 /m²</span>
            </div>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:13}}>
              <span style={{color:'var(--ink-2)'}}>Comparables usados</span>
              <span className="mono" style={{fontWeight:600}}>34 unidades</span>
            </div>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:13}}>
              <span style={{color:'var(--ink-2)'}}>Tiempo medio de venta</span>
              <span className="mono" style={{fontWeight:600}}>78 días</span>
            </div>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:13}}>
              <span style={{color:'var(--ink-2)'}}>Cap rate estimado</span>
              <span className="mono" style={{fontWeight:600}}>4,8% anual</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   How it works
   ============================================================ */
function HowItWorks(){
  const steps = [
    { n:'01', t:'Capturamos todo', d:'Avisos, escrituras del RPI, permisos municipales y datos abiertos. Más de 2,4M de registros mensuales.' },
    { n:'02', t:'Limpiamos y validamos', d:'Detección de duplicados, anomalías y precios fuera de mercado. Un equipo humano revisa los casos límite.' },
    { n:'03', t:'Indexamos y publicamos', d:'Modelos hedónicos por barrio. Resultados auditables — vos podés ver cada comparable que usamos.' },
  ];
  return (
    <section className="section gutter" style={{background:'var(--paper-2)'}}>
      <div className="section-head">
        <h2 className="display">Cómo trabajamos</h2>
        <div className="right">
          Metodología abierta. Si querés auditar cualquier dato del índice, te damos los comparables exactos.
        </div>
      </div>
      <div className="how">
        {steps.map(s=>(
          <div className="step" key={s.n}>
            <div className="n">{s.n}</div>
            <h4>{s.t}</h4>
            <p>{s.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   Clients + Testimonial
   ============================================================ */
function Clients(){
  const names = ['BANCO RÍO PLATA','REMAX CONO SUR','ARGENCAPITAL','FONDO ATLAS','TOKEN HOMES','GRUPO HORIZONTE'];
  return (
    <section id="empresas" className="clients gutter">
      <div className="eyebrow" style={{textAlign:'center', marginBottom:32}}>Usan TasAR para tomar decisiones</div>
      <div className="clients-grid">
        {names.map(n=>(<div className="client-logo" key={n}>{n}</div>))}
      </div>
    </section>
  );
}

function Testimonial(){
  return (
    <section className="section gutter">
      <div className="eyebrow" style={{marginBottom:32}}>Lo que dicen</div>
      <div className="quote">
        "Antes de TasAR estábamos viendo el mercado <span className="accent">con dos meses de atraso.</span> Hoy decidimos las tasas de un crédito hipotecario con datos que tienen 24 horas."
      </div>
      <div className="attrib">
        <div className="avatar"/>
        <div className="who">
          Mariana Sosa
          <small>Head of Risk · Banco Río Plata</small>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   Final CTA
   ============================================================ */
function FinalCTA({ accent }){
  return (
    <section className="section gutter">
      <div className="cta-final" style={{background:'var(--ink)'}}>
        <div>
          <div className="eyebrow" style={{color:'rgba(250,251,250,0.55)', marginBottom: 24}}>
            Empezá hoy
          </div>
          <h2 className="display-tight">
            Tomá decisiones<br/>
            con datos, <span style={{color:accent}}>no con intuición.</span>
          </h2>
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:24}}>
          <p>30 días de prueba para empresas. Acceso a 3 reportes históricos y a la API en modo lectura.</p>
          <div style={{display:'flex', gap:10}}>
            <button className="pill" style={{background:accent, color:'var(--ink)'}}>Pedir demo →</button>
            <button className="pill" style={{background:'transparent', color:'var(--paper)', border:'1px solid rgba(250,251,250,0.25)'}}>Ver planes</button>
          </div>
        </div>
        {/* decorative heatmap stripe bottom-right */}
        <div style={{position:'absolute', right:-40, bottom:-40, opacity:0.25}}>
          <HeatmapLogoMark cell={28} gap={6} accent={accent}/>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   Footer
   ============================================================ */
function Footer({ accent }){
  return (
    <footer className="gutter">
      <div className="foot-cols">
        <div>
          <div style={{display:'flex', alignItems:'center', gap:12, marginBottom: 16}}>
            <HeatmapLogoMark cell={7} gap={1.6} accent={accent}/>
            <span style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:22, letterSpacing:'-0.035em'}}>TasAR</span>
          </div>
          <p style={{color:'var(--ink-3)', fontSize:13.5, lineHeight:1.55, maxWidth: 280, margin:0}}>
            Inteligencia del mercado inmobiliario argentino. Datos auditables, metodología abierta.
          </p>
        </div>
        <div>
          <h5>Producto</h5>
          <ul>
            <li><a href="#">Reportes</a></li>
            <li><a href="#">Tasador</a></li>
            <li><a href="#">API</a></li>
            <li><a href="#">Planes</a></li>
          </ul>
        </div>
        <div>
          <h5>Empresa</h5>
          <ul>
            <li><a href="#">Quiénes somos</a></li>
            <li><a href="#">Metodología</a></li>
            <li><a href="#">Prensa</a></li>
            <li><a href="#">Trabajar</a></li>
          </ul>
        </div>
        <div>
          <h5>Recursos</h5>
          <ul>
            <li><a href="#">Blog</a></li>
            <li><a href="#">Glosario</a></li>
            <li><a href="#">Newsletter</a></li>
            <li><a href="#">Soporte</a></li>
          </ul>
        </div>
        <div>
          <h5>Contacto</h5>
          <ul>
            <li><a href="mailto:hola@tasar.com.ar">hola@tasar.com.ar</a></li>
            <li><a href="#">+54 11 5555 0142</a></li>
            <li><a href="#">Av. Córdoba 1234, CABA</a></li>
          </ul>
        </div>
      </div>
      <div className="foot-bottom">
        <div>© 2026 TasAR · CUIT 30-71234567-8</div>
        <div style={{display:'flex', gap: 18}}>
          <a href="#" style={{color:'var(--ink-3)'}}>Términos</a>
          <a href="#" style={{color:'var(--ink-3)'}}>Privacidad</a>
          <a href="#" style={{color:'var(--ink-3)'}}>Metodología</a>
        </div>
      </div>
    </footer>
  );
}

/* ============================================================
   App with Tweaks
   ============================================================ */
function App(){
  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "theme": "light",
    "accent": "#00B37E"
  }/*EDITMODE-END*/;

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tweaks.theme);
    document.documentElement.style.setProperty('--accent', tweaks.accent);
    // derive accent-dark by darkening (simple shift): just keep base for now
  }, [tweaks.theme, tweaks.accent]);

  return (
    <>
      <div data-screen-label="01 Landing">
        <Ticker/>
        <div className="page">
          <TopNav accent={tweaks.accent}/>
          <Hero accent={tweaks.accent}/>
          <MetricsRow/>
          <Products/>
          <ReportPreview accent={tweaks.accent}/>
          <Tasador accent={tweaks.accent}/>
          <HowItWorks/>
          <Clients/>
          <Testimonial/>
          <FinalCTA accent={tweaks.accent}/>
          <Footer accent={tweaks.accent}/>
        </div>
      </div>

      <TweaksPanel title="Tweaks · TasAR">
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
            options={['#00B37E','#0F6E5A','#C9A24A','#B5563A','#3B82F6','#0D1412']}
            onChange={(v)=>setTweak('accent', v)}
          />
        </TweakSection>
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
