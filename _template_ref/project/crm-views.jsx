/* TasAR CRM — view components (Bandeja, Propiedades, Pipeline, Clientes, Mercado, Reportes, Comparables, Config) */
const { useState: useStateV, useMemo: useMemoV } = React;
const { HeatmapLogoMark, Icon, I, heatColor, Sparkline, ZoneHeatmap, buildZoneGrid, ITEMS } = window;

/* ============================================================
   1. Bandeja (Inbox)
   ============================================================ */
const INBOX = [
  { id:1, who:'Mariana Sosa',     role:'Banco Río Plata', tone:'',     subj:'Aprobación TR-2451',     prev:'Hola Bárbara, ¿podemos cerrar la tasación de Santa Fe 2350 hoy? El comité se reúne a las 16hs.', when:'hace 8 min', unread:true,  selected:true, av:'green' },
  { id:2, who:'Sistema · Modelo', role:'auto',            tone:'warn', subj:'Alerta · cap rate fuera de rango', prev:'TR-2448 (Quintana 480) muestra cap rate 6.2%, 1.8σ sobre la media de Recoleta. Revisar comparables.', when:'hace 1 h',   unread:true,  av:'warn' },
  { id:3, who:'Daniel Rojas',     role:'TasAR',           tone:'',     subj:'Mencionó en TR-2449',     prev:'@Bárbara, hoy entró un comparable nuevo en Cabello que sube +6% el USD/m². ¿Recalculamos?', when:'hace 2 h',   unread:true,  av:'' },
  { id:4, who:'Fondo Atlas',      role:'cliente',         tone:'',     subj:'Pidió 3 tasaciones',     prev:'Solicitud de tasación para Honduras 5240, Cabildo 2780 y Defensa 870 — modalidad express.', when:'hace 4 h',   unread:false, av:'green' },
  { id:5, who:'Sistema',          role:'auto',            tone:'loss', subj:'TR-2444 vencida sin respuesta', prev:'La solicitud de L. Martinez lleva 48hs sin abrirse. Reasignar?', when:'ayer · 18:02', unread:false, av:'loss' },
  { id:6, who:'Bárbara López',    role:'self',            tone:'',     subj:'Recordatorio · revisar TR-2450',prev:'Te lo agendaste vos misma desde el detalle de TR-2450 para hoy 09:00.', when:'ayer · 09:00', unread:false, av:'' },
  { id:7, who:'REMAX Cono Sur',   role:'cliente',         tone:'',     subj:'Pago confirmado · Mayo', prev:'Recibimos USD 1.200 correspondiente al plan Empresa de mayo. Próxima fecha de cobro: 12 jun.', when:'lun', unread:false, av:'green' },
  { id:8, who:'Daniel Rojas',     role:'TasAR',           tone:'',     subj:'Pull request en metodología', prev:'Subí la v3.3 del modelo hedónico. Cambios: ajuste por orientación y peso de cocheras. Review?', when:'12 may', unread:false, av:'' },
];

function ViewBandeja(){
  const [sel, setSel] = useStateV(1);
  const item = INBOX.find(i => i.id === sel) || INBOX[0];
  return (
    <div className="inbox-shell">
      <div className="inbox-list">
        <div className="page-head" style={{borderBottom:'none', padding:'18px 18px 4px'}}>
          <div>
            <h1 style={{fontSize:22}}>Bandeja</h1>
            <div className="lede" style={{fontSize:12}}>3 sin leer · 5 totales hoy</div>
          </div>
        </div>
        <div className="tabs" style={{paddingInline:14}}>
          <div className="tab on">Sin leer <span className="cnt">3</span></div>
          <div className="tab">Asignadas a mí <span className="cnt">5</span></div>
          <div className="tab">Todo <span className="cnt">128</span></div>
        </div>
        <div style={{overflowY:'auto'}}>
          {INBOX.map(it => (
            <div key={it.id}
                 className={`inbox-item ${it.unread?'unread':''} ${it.id===sel?'selected':''}`}
                 onClick={()=>setSel(it.id)}>
              <div className={`av ${it.av}`}/>
              <div style={{minWidth:0}}>
                <div className="who">{it.who} <span style={{color:'var(--ink-3)', fontWeight:500, fontSize:11.5}}>· {it.role}</span></div>
                <div style={{fontSize:13.2, color:'var(--ink)', fontWeight: it.unread?600:500, marginTop:1}}>{it.subj}</div>
                <div className="prev">{it.prev}</div>
              </div>
              <div className="when">{it.when}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="inbox-detail">
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', gap:24, marginBottom:14}}>
          <div>
            <div className="eyebrow" style={{marginBottom:8}}>De {item.who} · {item.role}</div>
            <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.025em', margin:'0 0 8px'}}>{item.subj}</h1>
            <div style={{fontSize:12, color:'var(--ink-3)', fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>{item.when}</div>
          </div>
          <div style={{display:'flex', gap:8}}>
            <button className="pill-btn ghost"><Icon d={I.share} size={14}/> Reenviar</button>
            <button className="pill-btn accent">Responder →</button>
          </div>
        </div>

        <div className="card" style={{marginTop:20}}>
          <p style={{fontSize:15, lineHeight:1.6, color:'var(--ink)', margin:0}}>{item.prev}</p>
          <p style={{fontSize:15, lineHeight:1.6, color:'var(--ink-2)', marginTop:14}}>
            Te paso adjunto el contrato preliminar para que veas las condiciones. Como hablamos, el cliente final requiere que la tasación quede registrada también en el sistema del BCRA.
          </p>
          <p style={{fontSize:15, lineHeight:1.6, color:'var(--ink-2)', marginTop:14}}>
            Si necesitás algo más de mi lado avisame.<br/><br/>
            Saludos,<br/>Mariana
          </p>
        </div>

        <div className="card">
          <div className="card-head">
            <div><h3 style={{margin:0}}>Tasación referida</h3><div className="sub">Vinculada a este mensaje</div></div>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:16, padding:'4px 0'}}>
            <div style={{width:44, height:44, borderRadius:8, background:'var(--paper-3)', display:'flex', alignItems:'center', justifyContent:'center'}}>
              <Icon d={I.home} size={20}/>
            </div>
            <div style={{flex:1}}>
              <div style={{fontWeight:600, fontSize:14}}>Av. Santa Fe 2350, 8°B</div>
              <div style={{fontSize:12, color:'var(--ink-3)'}}>TR-2451 · Recoleta · 82 m² · USD 248.300</div>
            </div>
            <button className="pill-btn ghost" style={{height:32, fontSize:12}}>Abrir →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   2. Propiedades (table)
   ============================================================ */
const PROPS = [
  { addr:'Av. Santa Fe 2350, 8°B',  zone:'Recoleta',  type:'Dpto', sup:'82',  amb:3, owner:'Banco R\u00edo Plata',     val:'248.300', cap:'4,8%', last:'14 may 26', status:'A la venta' },
  { addr:'Thames 1882, PB',         zone:'Palermo',   type:'Dpto', sup:'64',  amb:2, owner:'Argencapital',         val:'219.840', cap:'5,1%', last:'12 may 26', status:'Alquilada'   },
  { addr:'Cabello 3470, 11°A',      zone:'Palermo',   type:'Dpto', sup:'112', amb:4, owner:'Fondo Atlas',           val:'384.720', cap:'4,5%', last:'10 may 26', status:'A la venta' },
  { addr:'Quintana 480, 5°',        zone:'Recoleta',  type:'Dpto', sup:'186', amb:5, owner:'M. Aldao',              val:'591.480', cap:'3,9%', last:'08 may 26', status:'Vendida'     },
  { addr:'Cabildo 2780, 14°D',      zone:'Belgrano',  type:'Dpto', sup:'74',  amb:3, owner:'Token Homes',           val:'213.860', cap:'5,4%', last:'06 may 26', status:'A la venta' },
  { addr:'Defensa 870',             zone:'San Telmo', type:'PH',   sup:'138', amb:4, owner:'F. Pereyra',            val:'226.320', cap:'6,1%', last:'04 may 26', status:'Alquilada'   },
  { addr:'Av. Pueyrredón 1645, 3°C',zone:'Recoleta',  type:'Dpto', sup:'95',  amb:3, owner:'REMAX Cono Sur',        val:'302.100', cap:'4,8%', last:'02 may 26', status:'A la venta' },
  { addr:'Honduras 5240, 2°',       zone:'Palermo',   type:'Dpto', sup:'48',  amb:1, owner:'L. Martinez',           val:'164.880', cap:'5,8%', last:'01 may 26', status:'A la venta' },
  { addr:'Yatay 460, 7°A',          zone:'Almagro',   type:'Dpto', sup:'68',  amb:2, owner:'M. Sosa',               val:'127.840', cap:'5,4%', last:'29 abr 26', status:'Alquilada'   },
  { addr:'Echeverría 1180, 6°B',    zone:'Belgrano',  type:'Dpto', sup:'92',  amb:3, owner:'Grupo Horizonte',       val:'265.880', cap:'4,9%', last:'27 abr 26', status:'A la venta' },
  { addr:'Olleros 2340, 4°A',       zone:'Colegiales',type:'Dpto', sup:'76',  amb:3, owner:'F. Cordero',            val:'184.680', cap:'5,2%', last:'25 abr 26', status:'Vendida'     },
  { addr:'Av. del Libertador 3290', zone:'N\u00fa\u00f1ez',  type:'Dpto', sup:'124', amb:4, owner:'L. Iribarne',           val:'342.240', cap:'4,4%', last:'23 abr 26', status:'A la venta' },
];

function ViewPropiedades(){
  return (
    <div className="view-pane" style={{display:'flex', flexDirection:'column'}}>
      <div className="page-head">
        <div>
          <h1>Propiedades</h1>
          <div className="lede">2.412 propiedades en seguimiento · 38 nuevas esta semana</div>
        </div>
        <div className="actions">
          <button className="pill-btn ghost"><Icon d={I.download} size={14}/> Exportar</button>
          <button className="pill-btn"><Icon d={I.plus} size={14}/> Agregar propiedad</button>
        </div>
      </div>

      <div className="toolbar">
        <div className="left">
          <div className="chip on">Zona: CABA <span className="x"><Icon d={I.caret} size={11}/></span></div>
          <div className="chip">Tipo: todos</div>
          <div className="chip">Estado: todos</div>
          <div className="chip">Sup: cualquiera</div>
          <div className="chip"><Icon d={I.filter} size={12}/> Más filtros</div>
        </div>
        <div className="right">
          <div className="seg">
            <div className="opt on">Tabla</div>
            <div className="opt">Mapa</div>
            <div className="opt">Cards</div>
          </div>
          <div className="search" style={{flex:'0 0 240px', height:32}}>
            <Icon d={I.search} size={14}/>
            <span>Buscar dirección…</span>
          </div>
        </div>
      </div>

      <div style={{overflow:'auto', flex:1, background:'var(--paper)'}}>
        <table className="props-table">
          <thead>
            <tr>
              <th>Dirección</th>
              <th>Zona</th>
              <th>Tipo</th>
              <th className="right">Sup.</th>
              <th>Amb.</th>
              <th>Owner</th>
              <th className="right">Valor estimado</th>
              <th className="right">Cap rate</th>
              <th>Última tasación</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {PROPS.map((p,i)=>(
              <tr key={i}>
                <td className="addr">{p.addr}</td>
                <td>{p.zone}</td>
                <td>{p.type}</td>
                <td className="right">{p.sup} m²</td>
                <td>{p.amb}</td>
                <td>{p.owner}</td>
                <td className="right" style={{color:'var(--ink)', fontWeight:600}}>USD {p.val}</td>
                <td className="right">{p.cap}</td>
                <td>{p.last}</td>
                <td><span className="pill-cell">{p.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================
   3. Pipeline (kanban)
   ============================================================ */
const PIPE = {
  solicitado:  [
    { id:'TR-2454', addr:'Av. Cabildo 1290', zone:'Belgrano',  amb:'3 amb · 78 m²', price:'USD 224.000', days:'1d' },
    { id:'TR-2453', addr:'Honduras 5240, 2°',zone:'Palermo',   amb:'1 amb · 48 m²', price:'USD 164.880', days:'1d' },
    { id:'TR-2450', addr:'Thames 1882, PB',  zone:'Palermo',   amb:'2 amb · 64 m²', price:'USD 219.840', days:'2d' },
  ],
  'en-analisis': [
    { id:'TR-2451', addr:'Av. Santa Fe 2350',zone:'Recoleta',  amb:'3 amb · 82 m²', price:'USD 248.300', days:'3d' },
    { id:'TR-2446', addr:'Defensa 870',       zone:'San Telmo', amb:'PH 4 amb',      price:'USD 226.320', days:'4d' },
    { id:'TR-2452', addr:'Charcas 4480, 3°', zone:'Palermo',   amb:'2 amb · 58 m²', price:'USD 168.200', days:'2d' },
    { id:'TR-2455', addr:'Av. Las Heras 2680',zone:'Recoleta',  amb:'4 amb · 124 m²',price:'USD 388.240', days:'1d' },
  ],
  comparables: [
    { id:'TR-2456', addr:'Vidal 2240, 5°A',  zone:'Belgrano',  amb:'3 amb · 86 m²', price:'USD 249.400', days:'2d' },
    { id:'TR-2444', addr:'Honduras 5240',     zone:'Palermo',   amb:'1 amb · 48 m²', price:'USD 164.880', days:'5d' },
  ],
  revision: [
    { id:'TR-2448', addr:'Quintana 480, 5°', zone:'Recoleta',  amb:'5 amb · 186 m²',price:'USD 591.480', days:'6d' },
    { id:'TR-2457', addr:'Bonpland 1140, 8°',zone:'Palermo',   amb:'3 amb · 92 m²', price:'USD 308.000', days:'3d' },
  ],
  entregado: [
    { id:'TR-2449', addr:'Cabello 3470, 11°A',zone:'Palermo',   amb:'4 amb · 112 m²',price:'USD 384.720', days:'8d' },
    { id:'TR-2447', addr:'Cabildo 2780, 14°D',zone:'Belgrano',  amb:'3 amb · 74 m²', price:'USD 213.860', days:'9d' },
    { id:'TR-2445', addr:'Av. Pueyrred\u00f3n 1645',zone:'Recoleta',  amb:'3 amb · 95 m²', price:'USD 302.100', days:'10d' },
    { id:'TR-2443', addr:'Yatay 460, 7°A',   zone:'Almagro',   amb:'2 amb · 68 m²', price:'USD 127.840', days:'12d' },
  ],
};
const PIPE_COLS = [
  { id:'solicitado',  name:'Solicitado',   sub:'48 hs SLA' },
  { id:'en-analisis', name:'En análisis',  sub:'modelo activo' },
  { id:'comparables', name:'Comparables',  sub:'humano valida' },
  { id:'revision',    name:'En revisión',  sub:'cliente revisa' },
  { id:'entregado',   name:'Entregado',    sub:'cerrado este mes' },
];

function ViewPipeline(){
  return (
    <div className="view-pane" style={{display:'flex', flexDirection:'column', overflow:'hidden'}}>
      <div className="page-head">
        <div>
          <h1>Pipeline</h1>
          <div className="lede">Mayo 2026 · 22 tasaciones en curso · SLA promedio 4,2 días</div>
        </div>
        <div className="actions">
          <div className="seg">
            <div className="opt on">Mes</div>
            <div className="opt">Trimestre</div>
            <div className="opt">YTD</div>
          </div>
          <button className="pill-btn"><Icon d={I.plus} size={14}/> Nueva tasación</button>
        </div>
      </div>
      <div className="kanban">
        {PIPE_COLS.map(col => (
          <div key={col.id} className={`col-k ${col.id}`}>
            <div className="col-head">
              <div className="ct">
                <span className="d"/>
                <span className="name">{col.name}</span>
                <span className="cnt">{PIPE[col.id].length}</span>
              </div>
              <Icon d={I.more} size={14}/>
            </div>
            <div style={{fontSize:11, color:'var(--ink-3)', paddingInline:8, marginBottom:4}}>{col.sub}</div>
            {PIPE[col.id].map(c => (
              <div key={c.id} className="k-card">
                <div style={{display:'flex', justifyContent:'space-between'}}>
                  <span style={{fontSize:10.5, color:'var(--ink-3)', fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>{c.id}</span>
                  <span style={{fontSize:10.5, color:'var(--ink-3)'}}>{c.zone}</span>
                </div>
                <div className="k-addr">{c.addr}</div>
                <div className="k-meta">{c.amb}</div>
                <div className="k-foot">
                  <span className="k-price">{c.price}</span>
                  <div style={{display:'flex', alignItems:'center', gap:6}}>
                    <span className="k-days">{c.days}</span>
                    <div className="k-av"/>
                  </div>
                </div>
              </div>
            ))}
            <div className="add-card"><Icon d={I.plus} size={12}/> Agregar</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   4. Clientes
   ============================================================ */
const CLIENTS = [
  { id:1, name:'Banco Río Plata',  type:'Banco',          tasaciones:24, mrr:'USD 1.200', mark:'RP', up:true },
  { id:2, name:'Fondo Atlas',      type:'Fondo de inv.',  tasaciones:18, mrr:'USD 1.800', mark:'FA', up:true },
  { id:3, name:'REMAX Cono Sur',   type:'Inmobiliaria',   tasaciones:42, mrr:'USD 1.200', mark:'RX', up:true },
  { id:4, name:'Argencapital',     type:'Desarrollador',  tasaciones:9,  mrr:'USD 480',   mark:'AC', up:false },
  { id:5, name:'Token Homes',      type:'Proptech',       tasaciones:12, mrr:'USD 1.800', mark:'TH', up:true },
  { id:6, name:'Grupo Horizonte',  type:'Inmobiliaria',   tasaciones:7,  mrr:'USD 480',   mark:'GH', up:true },
  { id:7, name:'M. Aldao',         type:'Particular',     tasaciones:2,  mrr:'USD 0',     mark:'MA', up:false },
  { id:8, name:'L. Iribarne',      type:'Particular',     tasaciones:1,  mrr:'USD 0',     mark:'LI', up:false },
  { id:9, name:'F. Pereyra',       type:'Particular',     tasaciones:1,  mrr:'USD 0',     mark:'FP', up:false },
  { id:10,name:'L. Martinez',      type:'Particular',     tasaciones:3,  mrr:'USD 0',     mark:'LM', up:false },
];

function ViewClientes(){
  const [sel, setSel] = useStateV(1);
  const c = CLIENTS.find(x => x.id === sel) || CLIENTS[0];
  return (
    <div className="clients-shell">
      <div className="client-list">
        <div className="page-head" style={{padding:'18px 18px 12px'}}>
          <div>
            <h1 style={{fontSize:22}}>Clientes</h1>
            <div className="lede" style={{fontSize:12}}>318 totales · 14 activos este mes</div>
          </div>
        </div>
        <div className="toolbar" style={{padding:'8px 16px'}}>
          <div className="left">
            <div className="chip on">Activos <span className="x"><Icon d={I.caret} size={11}/></span></div>
            <div className="chip">Plan</div>
            <div className="chip">Tipo</div>
          </div>
        </div>
        <div style={{overflowY:'auto'}}>
          {CLIENTS.map(cl => (
            <div key={cl.id} className={`client-row ${cl.id===sel?'on':''}`} onClick={()=>setSel(cl.id)}>
              <div className="logo">{cl.mark}</div>
              <div style={{minWidth:0}}>
                <div className="name">{cl.name}</div>
                <div className="meta">{cl.type} · {cl.tasaciones} tasaciones</div>
              </div>
              <div className="val">
                <div className="v">{cl.mrr}</div>
                <div className="k">MRR</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="client-detail">
        <div style={{display:'flex', alignItems:'center', gap:18, marginBottom: 24}}>
          <div style={{width:64, height:64, borderRadius:14, background:'var(--ink)', color:'var(--paper)', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:22, letterSpacing:'0.04em'}}>{c.mark}</div>
          <div style={{flex:1}}>
            <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:32, letterSpacing:'-0.035em', margin:'0 0 4px'}}>{c.name}</h1>
            <div style={{color:'var(--ink-3)', fontSize:13.5}}>{c.type} · Cliente desde marzo 2024 · Plan Empresa</div>
          </div>
          <div style={{display:'flex', gap:8}}>
            <button className="pill-btn ghost">Editar</button>
            <button className="pill-btn accent">Nueva tasación →</button>
          </div>
        </div>

        <div className="stat-row" style={{marginTop:0}}>
          <div className="stat">
            <div className="k">Tasaciones totales</div>
            <div className="v num">{c.tasaciones}</div>
            <div className="d up">+4 este mes</div>
          </div>
          <div className="stat">
            <div className="k">Valor agregado tasado</div>
            <div className="v num">USD 8,2M</div>
            <div className="d">42 propiedades</div>
          </div>
          <div className="stat">
            <div className="k">MRR</div>
            <div className="v num">{c.mrr}</div>
            <div className="d">Plan Empresa</div>
          </div>
          <div className="stat">
            <div className="k">NPS último</div>
            <div className="v num">9 / 10</div>
            <div className="d">hace 28 días</div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div><h3>Contactos</h3><div className="sub">3 personas en {c.name}</div></div>
            <button className="pill-btn ghost" style={{height:30, fontSize:12}}>Agregar</button>
          </div>
          <table className="cmp">
            <thead>
              <tr><th>Nombre</th><th>Rol</th><th>Email</th><th>Teléfono</th><th>Última actividad</th></tr>
            </thead>
            <tbody>
              <tr><td className="addr">Mariana Sosa</td><td>Head of Risk</td><td>m.sosa@rioplata.com</td><td>+54 11 5555 0142</td><td>hace 8 min</td></tr>
              <tr><td className="addr">Diego Yáñez</td><td>Analista</td><td>d.yanez@rioplata.com</td><td>+54 11 5555 0143</td><td>ayer</td></tr>
              <tr><td className="addr">Romina Vidal</td><td>Compras</td><td>r.vidal@rioplata.com</td><td>+54 11 5555 0144</td><td>hace 3 días</td></tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-head">
            <div><h3>Actividad reciente</h3><div className="sub">Últimas 30 interacciones</div></div>
          </div>
          <div className="timeline">
            <div className="tl-item">
              <div className="tl-dot accent"/><div className="tl-line"/>
              <div>
                <div className="tl-text"><strong>Tasación TR-2451 enviada</strong> — Av. Santa Fe 2350 · USD 248.300</div>
                <div className="tl-time">hace 12 min</div>
              </div>
            </div>
            <div className="tl-item">
              <div className="tl-dot"/><div className="tl-line"/>
              <div>
                <div className="tl-text"><strong>Solicitó tasación</strong> — vía API · payload v3.2</div>
                <div className="tl-time">hace 2 h</div>
              </div>
            </div>
            <div className="tl-item">
              <div className="tl-dot"/><div className="tl-line"/>
              <div>
                <div className="tl-text"><strong>Renovó plan Empresa</strong> — USD 1.200/mes · 12 meses</div>
                <div className="tl-time">12 may</div>
              </div>
            </div>
            <div className="tl-item">
              <div className="tl-dot"/>
              <div>
                <div className="tl-text"><strong>Descargó reporte #046</strong> — Abril 2026</div>
                <div className="tl-time">8 may</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   5. Mercado dashboard
   ============================================================ */
function buildBigCity(cols=30, rows=16, hot=[16, 8]){
  const out = [];
  for (let j=0; j<rows; j++){
    const row = [];
    for (let i=0; i<cols; i++){
      const dx = (i - hot[0]) / cols;
      const dy = (j - hot[1]) / rows;
      const d = Math.sqrt(dx*dx*1.5 + dy*dy*0.9);
      const n = Math.sin(i*1.7 + j*2.3) * 0.05 + Math.cos(i*0.9 - j*1.1) * 0.06;
      let v = 1 - d*1.85 + n;
      if (v < 0) v = 0;
      if (v > 1) v = 1;
      row.push(v);
    }
    out.push(row);
  }
  for (let j=0; j<rows; j++){ out[j][0] = Math.min(out[j][0], 0.05); }
  return out;
}

function BigCityHeatmap(){
  const grid = useMemoV(() => buildBigCity(30, 16, [17, 8]), []);
  const cell = 22, gap = 3;
  return (
    <div style={{
      display:'grid',
      gridTemplateColumns: `repeat(${grid[0].length}, ${cell}px)`,
      gridTemplateRows:    `repeat(${grid.length}, ${cell}px)`,
      gap,
    }}>
      {grid.flat().map((v,i)=>(
        <div key={i} style={{
          width:cell, height:cell, borderRadius:5,
          background: v < 0.05 ? 'transparent' : heatColor(v, 'var(--accent)'),
        }}/>
      ))}
    </div>
  );
}

const ZONES = [
  { name:'Palermo',     px:'3.420', ch:'+2,1%', up:true },
  { name:'Recoleta',    px:'3.180', ch:'+1,4%', up:true },
  { name:'Belgrano',    px:'2.890', ch:'+0,9%', up:true },
  { name:'Núñez',       px:'2.760', ch:'+1,1%', up:true },
  { name:'Colegiales',  px:'2.430', ch:'+0,7%', up:true },
  { name:'Caballito',   px:'2.140', ch:'+0,2%', up:true },
  { name:'Villa Crespo',px:'2.020', ch:'+0,6%', up:true },
  { name:'Saavedra',    px:'2.020', ch:'+0,3%', up:true },
  { name:'Almagro',     px:'1.880', ch:'-0,3%', up:false },
  { name:'San Telmo',   px:'1.640', ch:'-0,4%', up:false },
  { name:'Boedo',       px:'1.520', ch:'-0,1%', up:false },
  { name:'Flores',      px:'1.480', ch:'-0,2%', up:false },
];

function ViewMercado(){
  const series = [2.41,2.43,2.42,2.46,2.49,2.48,2.52,2.55,2.58,2.62,2.66,2.71,2.75,2.78,2.80,2.83,2.85];
  return (
    <div className="mercado">
      <div className="page-head" style={{border:0, padding:'0 0 8px', background:'transparent'}}>
        <div>
          <h1>Mercado · CABA</h1>
          <div className="lede">Mayo 2026 · datos actualizados hace 24 horas · 18.420 avisos activos</div>
        </div>
        <div className="actions">
          <div className="seg">
            <div className="opt">7d</div>
            <div className="opt">30d</div>
            <div className="opt on">90d</div>
            <div className="opt">12m</div>
            <div className="opt">5a</div>
          </div>
          <button className="pill-btn ghost"><Icon d={I.download} size={14}/> Exportar</button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid-12">
        <div className="kpi" style={{gridColumn:'span 3'}}>
          <div className="k">Índice TasAR · CABA</div>
          <div className="v">2.847</div>
          <div className="d up">+1,2% mensual · +14,2% YoY</div>
        </div>
        <div className="kpi" style={{gridColumn:'span 3'}}>
          <div className="k">Oferta activa</div>
          <div className="v">62.480</div>
          <div className="d down">−3,4% vs Abr</div>
        </div>
        <div className="kpi" style={{gridColumn:'span 3'}}>
          <div className="k">Tiempo medio de venta</div>
          <div className="v">94 días</div>
          <div className="d up">−8 días vs Q1</div>
        </div>
        <div className="kpi" style={{gridColumn:'span 3'}}>
          <div className="k">Permisos nuevos</div>
          <div className="v">1.213</div>
          <div className="d up">+12% interanual</div>
        </div>
      </div>

      {/* Heatmap + zones panel */}
      <div className="grid-12">
        <div className="panel" style={{gridColumn:'span 8'}}>
          <div className="panel-head">
            <div>
              <h3>Mapa de calor · USD/m²</h3>
              <div className="sub">Capital Federal · valor mediano por celda de 200m</div>
            </div>
            <div className="legend">
              <span>menor</span>
              <div className="scale">
                <span style={{background: heatColor(0.1, 'var(--accent)')}}/>
                <span style={{background: heatColor(0.3, 'var(--accent)')}}/>
                <span style={{background: heatColor(0.5, 'var(--accent)')}}/>
                <span style={{background: heatColor(0.7, 'var(--accent)')}}/>
                <span style={{background: heatColor(1.0, 'var(--accent)')}}/>
              </div>
              <span>mayor</span>
            </div>
          </div>
          <div style={{display:'flex', justifyContent:'center', padding:'12px 0'}}>
            <BigCityHeatmap/>
          </div>
        </div>
        <div className="panel" style={{gridColumn:'span 4', display:'flex', flexDirection:'column'}}>
          <div className="panel-head">
            <div><h3>Ranking por zona</h3><div className="sub">USD/m² · top 12</div></div>
            <span style={{fontSize:11, color:'var(--ink-3)', fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>mensual</span>
          </div>
          <div className="zone-list">
            {ZONES.map((z,i)=>(
              <div key={z.name} className="zone-row">
                <div className="rk">#{String(i+1).padStart(2,'0')}</div>
                <div className="nm">{z.name}</div>
                <div className="px">{z.px}</div>
                <div className={`ch ${z.up?'up':'dn'}`}>{z.ch}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid-12">
        <div className="panel" style={{gridColumn:'span 8'}}>
          <div className="panel-head">
            <div><h3>Índice TasAR · evolución</h3><div className="sub">17 meses · enero 2025 — mayo 2026</div></div>
            <span className="mono" style={{color:'var(--gain)', fontWeight:600, fontSize:12}}>+14,2% YoY</span>
          </div>
          <Sparkline data={series}/>
          <div style={{display:'flex', justifyContent:'space-between', marginTop:8, fontSize:11, color:'var(--ink-3)'}}>
            <span className="mono">Ene 25</span>
            <span className="mono">May 26</span>
          </div>
        </div>
        <div className="panel" style={{gridColumn:'span 4'}}>
          <div className="panel-head"><div><h3>Top movers · 30d</h3><div className="sub">Mayor variación mensual</div></div></div>
          <div className="zone-list">
            <div className="zone-row"><div className="rk">▲</div><div className="nm">Núñez</div><div className="px">2.760</div><div className="ch up">+4,2%</div></div>
            <div className="zone-row"><div className="rk">▲</div><div className="nm">Palermo</div><div className="px">3.420</div><div className="ch up">+3,8%</div></div>
            <div className="zone-row"><div className="rk">▲</div><div className="nm">Caballito</div><div className="px">2.140</div><div className="ch up">+2,4%</div></div>
            <div className="zone-row"><div className="rk">▼</div><div className="nm">Flores</div><div className="px">1.480</div><div className="ch dn">-2,8%</div></div>
            <div className="zone-row"><div className="rk">▼</div><div className="nm">Mataderos</div><div className="px">1.220</div><div className="ch dn">-3,1%</div></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   6. Reportes
   ============================================================ */
const REPORTS = [
  { ed:'#047', title:'Mayo 2026',     date:'01 jun 2026 · 38 pp', kpis:[['+14,2%','YoY'],['2.847','USD/m²']], featured:true },
  { ed:'#046', title:'Abril 2026',    date:'02 may 2026 · 36 pp', kpis:[['+12,8%','YoY'],['2.812','USD/m²']] },
  { ed:'#045', title:'Marzo 2026',    date:'01 abr 2026 · 34 pp', kpis:[['+11,4%','YoY'],['2.764','USD/m²']] },
  { ed:'#044', title:'Febrero 2026',  date:'03 mar 2026 · 32 pp', kpis:[['+9,8%','YoY'], ['2.701','USD/m²']] },
  { ed:'#043', title:'Enero 2026',    date:'01 feb 2026 · 38 pp', kpis:[['+8,2%','YoY'], ['2.642','USD/m²']] },
  { ed:'#042', title:'Diciembre 2025',date:'02 ene 2026 · 30 pp', kpis:[['+6,1%','YoY'], ['2.580','USD/m²']] },
];

function ViewReportes(){
  return (
    <div className="view-pane" style={{display:'flex', flexDirection:'column'}}>
      <div className="page-head">
        <div>
          <h1>Reportes</h1>
          <div className="lede">Análisis mensual del mercado · publicamos el primer día hábil del mes</div>
        </div>
        <div className="actions">
          <button className="pill-btn ghost"><Icon d={I.filter} size={14}/> Filtrar</button>
          <button className="pill-btn"><Icon d={I.plus} size={14}/> Reporte custom</button>
        </div>
      </div>
      <div className="reports-grid">
        {REPORTS.map(r => (
          <div key={r.ed} className="report-card">
            <div className="report-cover">
              <div className="num">{r.ed} · MENSUAL</div>
              <div>
                <div className="title">{r.title}</div>
                <div style={{marginTop:14, opacity:0.5}}>
                  <HeatmapLogoMark cell={8} gap={2} accent="var(--accent)"/>
                </div>
              </div>
              {r.featured && (
                <div style={{position:'absolute', top:14, right:14, background:'var(--accent)', color:'var(--ink)', fontSize:10, fontWeight:700, padding:'4px 8px', borderRadius:4, letterSpacing:'0.08em'}}>NUEVO</div>
              )}
            </div>
            <div className="report-body">
              <div className="date">{r.date}</div>
              <div className="stats">
                {r.kpis.map(([v,k],i)=>(
                  <div className="s" key={i}>
                    <div className="v">{v}</div>
                    <div className="k">{k}</div>
                  </div>
                ))}
              </div>
              <div style={{display:'flex', gap:8, marginTop: 14}}>
                <button className="pill-btn accent" style={{height:32, fontSize:12, flex:1}}>Abrir PDF</button>
                <button className="pill-btn ghost" style={{height:32, width:36, padding:0, justifyContent:'center'}}><Icon d={I.share} size={14}/></button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   7. Comparables (map view)
   ============================================================ */
function ComparablesMap(){
  // Use the city heatmap as background, plus dotted pins
  const grid = useMemoV(() => buildBigCity(36, 22, [20, 10]), []);
  const cell = 18, gap = 2;
  return (
    <div style={{position:'relative', padding: 24, width:'100%', height:'100%', display:'flex', alignItems:'center', justifyContent:'center'}}>
      <div style={{position:'relative'}}>
        <div style={{
          display:'grid',
          gridTemplateColumns: `repeat(${grid[0].length}, ${cell}px)`,
          gridTemplateRows:    `repeat(${grid.length}, ${cell}px)`,
          gap,
        }}>
          {grid.flat().map((v,i)=>(
            <div key={i} style={{
              width:cell, height:cell, borderRadius:3,
              background: v < 0.05 ? 'transparent' : heatColor(v, 'var(--accent)'),
              opacity: 0.5,
            }}/>
          ))}
        </div>
        {/* Property pins */}
        {[
          { x: 22, y: 9, hi:true,  label:'248.3k', subj:true },
          { x: 18, y: 7 }, { x: 24, y: 11 }, { x: 26, y: 8 },
          { x: 16, y: 12 }, { x: 20, y: 14 }, { x: 28, y: 13 },
          { x: 14, y: 9 }, { x: 19, y: 11 }, { x: 23, y: 6 },
          { x: 21, y: 13 }, { x: 25, y: 14 }, { x: 17, y: 10 },
        ].map((p, i) => {
          const px = p.x * (cell+gap);
          const py = p.y * (cell+gap);
          return (
            <div key={i} style={{
              position:'absolute', left: px - 6, top: py - 6,
              width: p.subj ? 22 : 14, height: p.subj ? 22 : 14, borderRadius: 99,
              background: p.subj ? 'var(--ink)' : 'var(--paper)',
              border: p.subj ? '3px solid var(--paper)' : '2px solid var(--ink)',
              boxShadow: p.subj ? '0 4px 12px rgba(0,0,0,0.25)' : '0 1px 3px rgba(0,0,0,0.15)',
            }}/>
          );
        })}
        {/* Subject label */}
        <div style={{
          position: 'absolute', left: 22*(cell+gap) + 18, top: 9*(cell+gap) - 10,
          background:'var(--ink)', color:'var(--paper)', padding:'5px 10px', borderRadius:6,
          fontSize:11.5, fontWeight:600, whiteSpace:'nowrap',
        }}>Esta propiedad · USD 248k</div>
      </div>
    </div>
  );
}

function ViewComparables(){
  return (
    <div className="view-pane" style={{display:'flex', flexDirection:'column', overflow:'hidden'}}>
      <div className="page-head">
        <div>
          <h1>Comparables</h1>
          <div className="lede">Buscador de comparables · base de datos en vivo · 18.420 unidades activas en CABA</div>
        </div>
        <div className="actions">
          <button className="pill-btn ghost"><Icon d={I.download} size={14}/> Exportar CSV</button>
        </div>
      </div>
      <div className="toolbar">
        <div className="left">
          <div className="chip on">Recoleta <span className="x"><Icon d={I.caret} size={11}/></span></div>
          <div className="chip">Radio: 800m</div>
          <div className="chip">Dpto · 70-95 m²</div>
          <div className="chip">3 amb</div>
          <div className="chip">Estado: bueno+</div>
          <div className="chip">Últimos 90d</div>
        </div>
        <div className="right">
          <span style={{fontSize:12, color:'var(--ink-3)', fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>34 resultados · USD/m² 2.640 – 3.520</span>
        </div>
      </div>
      <div className="comparables-shell" style={{flex:1, minHeight:0}}>
        <div className="map-pane"><ComparablesMap/></div>
        <div className="map-rail">
          <div className="header">
            <div style={{fontWeight:600, fontSize:14, marginBottom:6}}>Resultados</div>
            <div style={{fontSize:11.5, color:'var(--ink-3)'}}>Ordenado por match con TR-2451</div>
          </div>
          <div className="results">
            {window.COMPARABLES.concat([
              { addr:'Av. Pueyrredón 1645, 3°C', priceUsd:'USD 302.100', upm:'3.180', sup:'95 m²', amb:'3 amb', dist:'620 m', match:78 },
              { addr:'Av. Las Heras 2105, 9°B',  priceUsd:'USD 268.000', upm:'3.241', sup:'82 m²', amb:'3 amb', dist:'380 m', match:88 },
              { addr:'Juncal 1822, 11°D',         priceUsd:'USD 244.000', upm:'2.927', sup:'83 m²', amb:'3 amb', dist:'240 m', match:91 },
            ]).map((c,i)=>(
              <div key={i} className="res-item">
                <div style={{display:'flex', justifyContent:'space-between'}}>
                  <span className="addr">{c.addr}</span>
                  <span className="mono" style={{fontSize:11, fontWeight:600, color:'var(--accent-dk)'}}>{c.match}%</span>
                </div>
                <div className="px">{c.priceUsd} <span style={{color:'var(--ink-3)'}}>· {c.upm} USD/m²</span></div>
                <div style={{fontSize:11.5, color:'var(--ink-3)'}}>{c.sup} · {c.amb} · {c.dist} de TR-2451</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   8. Configuración
   ============================================================ */
function ViewConfig(){
  const [tab, setTab] = useStateV('account');
  const [notif, setNotif] = useStateV({ inbox:true, model:true, weekly:false, sms:false });
  const tabs = [
    { id:'account',   label:'Cuenta',          group:'general' },
    { id:'team',      label:'Equipo',          group:'general' },
    { id:'billing',   label:'Facturación',     group:'general' },
    { id:'api',       label:'API y webhooks',  group:'integraciones' },
    { id:'notif',     label:'Notificaciones',  group:'integraciones' },
    { id:'method',    label:'Metodología',     group:'datos' },
  ];
  return (
    <div className="config-shell">
      <div className="config-side">
        <h6>General</h6>
        {tabs.filter(t=>t.group==='general').map(t=>(
          <div key={t.id} className={`config-tab ${tab===t.id?'on':''}`} onClick={()=>setTab(t.id)}>{t.label}</div>
        ))}
        <h6>Integraciones</h6>
        {tabs.filter(t=>t.group==='integraciones').map(t=>(
          <div key={t.id} className={`config-tab ${tab===t.id?'on':''}`} onClick={()=>setTab(t.id)}>{t.label}</div>
        ))}
        <h6>Datos</h6>
        {tabs.filter(t=>t.group==='datos').map(t=>(
          <div key={t.id} className={`config-tab ${tab===t.id?'on':''}`} onClick={()=>setTab(t.id)}>{t.label}</div>
        ))}
      </div>

      <div className="config-main">
        {tab === 'account' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>Cuenta</h1>
          <div className="config-card">
            <h3>Perfil</h3>
            <p className="sub">Datos de tu cuenta personal en TasAR.</p>
            <div className="config-field">
              <div className="ck">Nombre completo</div>
              <div className="cv"><div className="fake-input">Bárbara López</div></div>
            </div>
            <div className="config-field">
              <div className="ck">Email</div>
              <div className="cv"><div className="fake-input">b.lopez@rioplata.com</div></div>
            </div>
            <div className="config-field">
              <div className="ck">Matrícula</div>
              <div className="cv"><div className="fake-input">MN 4821 · Tasadora habilitada</div></div>
            </div>
            <div className="config-field">
              <div className="ck">Zona horaria</div>
              <div className="cv"><div className="fake-input">America/Argentina/Buenos_Aires (GMT−3)</div></div>
            </div>
          </div>
          <div className="config-card">
            <h3>Seguridad</h3>
            <p className="sub">Sesión y autenticación.</p>
            <div className="config-field">
              <div className="ck">2FA</div>
              <div className="cv" style={{display:'flex', alignItems:'center', gap:12}}><div className="switch on"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>Activada · app autenticadora</span></div>
            </div>
            <div className="config-field">
              <div className="ck">Sesiones activas</div>
              <div className="cv" style={{fontSize:13, color:'var(--ink-2)'}}>3 dispositivos · <a style={{color:'var(--accent-dk)'}}>cerrar otras sesiones</a></div>
            </div>
          </div>
        </>}

        {tab === 'team' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>Equipo</h1>
          <div className="config-card">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
              <div>
                <h3 style={{margin:0}}>12 miembros</h3>
                <p className="sub" style={{margin:0}}>Plan Empresa · hasta 25 usuarios</p>
              </div>
              <button className="pill-btn accent">Invitar usuarios</button>
            </div>
            <table className="cmp">
              <thead><tr><th>Nombre</th><th>Rol</th><th>Email</th><th>Último acceso</th><th></th></tr></thead>
              <tbody>
                <tr><td className="addr">Bárbara López</td><td>Admin · Tasadora</td><td>b.lopez@…</td><td>hace 2 min</td><td><Icon d={I.more} size={14}/></td></tr>
                <tr><td className="addr">Daniel Rojas</td><td>Editor</td><td>d.rojas@…</td><td>hace 1 h</td><td><Icon d={I.more} size={14}/></td></tr>
                <tr><td className="addr">Sofia Mendez</td><td>Tasadora</td><td>s.mendez@…</td><td>ayer</td><td><Icon d={I.more} size={14}/></td></tr>
                <tr><td className="addr">Mariana Sosa</td><td>Cliente · Banco RP</td><td>m.sosa@…</td><td>hace 8 min</td><td><Icon d={I.more} size={14}/></td></tr>
                <tr><td className="addr">Diego Yáñez</td><td>Cliente · Banco RP</td><td>d.yanez@…</td><td>ayer</td><td><Icon d={I.more} size={14}/></td></tr>
              </tbody>
            </table>
          </div>
        </>}

        {tab === 'billing' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>Facturación</h1>
          <div className="config-card">
            <h3>Plan actual</h3>
            <p className="sub">Renueva el 12 de junio · USD 1.200/mes</p>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'18px 0 8px'}}>
              <div>
                <div style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:24, letterSpacing:'-0.02em'}}>Plan Empresa</div>
                <div style={{fontSize:13, color:'var(--ink-3)', marginTop:4}}>Hasta 25 usuarios · tasaciones ilimitadas · API · soporte 24/7</div>
              </div>
              <button className="pill-btn ghost">Cambiar plan</button>
            </div>
          </div>
          <div className="config-card">
            <h3>Próxima factura</h3>
            <p className="sub">12 jun 2026 · USD 1.200,00</p>
            <div className="config-field"><div className="ck">Método de pago</div><div className="cv"><div className="fake-input">Visa termina en 4812 · vence 09/27</div></div></div>
            <div className="config-field"><div className="ck">CUIT</div><div className="cv"><div className="fake-input">30-12345678-9 · Banco Río Plata S.A.</div></div></div>
          </div>
        </>}

        {tab === 'api' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>API y webhooks</h1>
          <div className="config-card">
            <h3>Claves de API</h3>
            <p className="sub">Usá estas claves para integrar TasAR a tu sistema. Documentación → tasar.com.ar/docs</p>
            <div className="config-field"><div className="ck">Producción</div><div className="cv"><div className="fake-input" style={{fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>tsr_live_xxxxxxxxxx7f3a · creada 12 mar 26</div></div></div>
            <div className="config-field"><div className="ck">Sandbox</div><div className="cv"><div className="fake-input" style={{fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>tsr_test_xxxxxxxxxx9e1b · creada 12 mar 26</div></div></div>
            <div style={{display:'flex', gap:8, marginTop:12}}>
              <button className="pill-btn ghost" style={{height:32, fontSize:12}}>Rotar clave</button>
              <button className="pill-btn ghost" style={{height:32, fontSize:12}}>Generar nueva</button>
            </div>
          </div>
          <div className="config-card">
            <h3>Webhooks</h3>
            <p className="sub">Recibí eventos en tu endpoint.</p>
            <div className="config-field"><div className="ck">URL</div><div className="cv"><div className="fake-input" style={{fontFamily:'JetBrains Mono,ui-monospace,monospace'}}>https://api.rioplata.com/webhooks/tasar</div></div></div>
            <div className="config-field"><div className="ck">Eventos</div><div className="cv" style={{fontSize:13, color:'var(--ink-2)'}}>valuation.created, valuation.updated, valuation.delivered</div></div>
            <div className="config-field"><div className="ck">Estado</div><div className="cv" style={{display:'flex', alignItems:'center', gap:10}}><span style={{width:8, height:8, borderRadius:99, background:'var(--accent)'}}/><span style={{fontSize:13}}>Activo · última entrega hace 12 min</span></div></div>
          </div>
        </>}

        {tab === 'notif' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>Notificaciones</h1>
          <div className="config-card">
            <h3>Cuándo avisarte</h3>
            <p className="sub">Estas preferencias aplican a tu cuenta personal.</p>
            {[
              { k:'inbox',  label:'Mensajes en bandeja',         sub:'Cuando un cliente o tu equipo te escribe' },
              { k:'model',  label:'Alertas del modelo',          sub:'Cap rate, USD/m² o stock fuera de rango' },
              { k:'weekly', label:'Resumen semanal',             sub:'Lunes 09:00 · KPIs de tu cartera' },
              { k:'sms',    label:'SMS para urgencias',          sub:'Solo solicitudes marcadas como urgentes' },
            ].map(item => (
              <div className="config-field" key={item.k}>
                <div className="ck">
                  <div>{item.label}</div>
                  <div style={{fontSize:11.5, color:'var(--ink-3)', fontWeight:400, marginTop:2}}>{item.sub}</div>
                </div>
                <div className="cv">
                  <div className={`switch ${notif[item.k]?'on':''}`} onClick={()=>setNotif({...notif, [item.k]:!notif[item.k]})}/>
                </div>
              </div>
            ))}
          </div>
        </>}

        {tab === 'method' && <>
          <h1 style={{fontFamily:'Sora,sans-serif', fontWeight:700, fontSize:28, letterSpacing:'-0.03em', margin:'0 0 20px'}}>Metodología</h1>
          <div className="config-card">
            <h3>Modelo activo</h3>
            <p className="sub">El modelo se actualiza una vez por trimestre. Podés bloquearte en una versión específica.</p>
            <div className="config-field"><div className="ck">Versión actual</div><div className="cv"><div className="fake-input">TasAR Hedónico v3.2 · liberado 12 abr 2026</div></div></div>
            <div className="config-field"><div className="ck">Bloquear versión</div><div className="cv" style={{display:'flex', gap:10, alignItems:'center'}}><div className="switch"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>Recomendamos no bloquear salvo auditorías</span></div></div>
          </div>
          <div className="config-card">
            <h3>Fuentes de datos</h3>
            <p className="sub">Activá las fuentes que querés que el modelo considere.</p>
            <div className="config-field"><div className="ck">Avisos públicos</div><div className="cv" style={{display:'flex', alignItems:'center', gap:10}}><div className="switch on"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>4 portales · 1,8M/mes</span></div></div>
            <div className="config-field"><div className="ck">Escrituras RPI</div><div className="cv" style={{display:'flex', alignItems:'center', gap:10}}><div className="switch on"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>CABA + GBA · feed oficial</span></div></div>
            <div className="config-field"><div className="ck">Permisos municipales</div><div className="cv" style={{display:'flex', alignItems:'center', gap:10}}><div className="switch on"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>14 partidos</span></div></div>
            <div className="config-field"><div className="ck">Datos privados (Río Plata)</div><div className="cv" style={{display:'flex', alignItems:'center', gap:10}}><div className="switch"/> <span style={{fontSize:13, color:'var(--ink-3)'}}>Subí tu historial de tasaciones para refinar el modelo</span></div></div>
          </div>
        </>}
      </div>
    </div>
  );
}

/* ============================================================
   8.5 Estudio (long-scroll editorial reading view)
   ============================================================ */
function BarChart({ data, accent='var(--accent)', height=180 }){
  const max = Math.max(...data.map(d=>d.v));
  const w = 600, pad = 8;
  const colW = (w - 2*pad) / data.length;
  const barW = colW * 0.62;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} style={{display:'block'}}>
      {[0.25, 0.5, 0.75].map(g=>(
        <line key={g} x1={pad} x2={w-pad} y1={pad + g*(height-30-pad)} y2={pad + g*(height-30-pad)}
              stroke="var(--line)" strokeWidth="1" strokeDasharray="3 4"/>
      ))}
      {data.map((d,i) => {
        const h = (d.v / max) * (height - 38 - pad);
        const x = pad + i*colW + (colW - barW)/2;
        const y = height - 30 - h;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={h} rx="3" fill={d.color || accent}/>
            <text x={x + barW/2} y={height - 10} textAnchor="middle"
                  fontSize="10" fontFamily="Inter" fontWeight="500" fill="var(--ink-3)">{d.k}</text>
          </g>
        );
      })}
    </svg>
  );
}

function ViewEstudio(){
  const indexSeries = [2.41,2.43,2.42,2.46,2.49,2.48,2.52,2.55,2.58,2.62,2.66,2.71,2.75,2.78,2.80,2.83,2.85];
  const zoneBars = [
    { k:'Palermo',  v:3420 },
    { k:'Recoleta', v:3180 },
    { k:'Belgrano', v:2890 },
    { k:'Núñez',    v:2760 },
    { k:'Coleg.',   v:2430 },
    { k:'Caballito',v:2140 },
    { k:'V.Crespo', v:2020 },
    { k:'Almagro',  v:1880 },
    { k:'S.Telmo',  v:1640 },
    { k:'Boedo',    v:1520 },
    { k:'Flores',   v:1480 },
  ];
  const permitBars = [
    { k:'May 25', v:1080 }, { k:'Jun', v:1124 }, { k:'Jul', v:1015 }, { k:'Ago', v:980  },
    { k:'Sep',    v:1056 }, { k:'Oct', v:1102 }, { k:'Nov', v:1138 }, { k:'Dic', v:1086 },
    { k:'Ene 26', v:1145 }, { k:'Feb', v:1174 }, { k:'Mar', v:1192 }, { k:'Abr', v:1208 },
    { k:'May',    v:1213, color:'var(--accent)' },
  ];
  const capRates = [
    { zone:'Palermo',    dpto:'4,2%', ph:'4,9%', casa:'4,7%', heat:[0.85, 1.00, 0.95] },
    { zone:'Recoleta',   dpto:'4,8%', ph:'5,2%', casa:'5,1%', heat:[1.00, 0.75, 0.80] },
    { zone:'Belgrano',   dpto:'5,4%', ph:'5,8%', casa:'5,6%', heat:[0.60, 0.40, 0.50] },
    { zone:'Núñez',      dpto:'5,1%', ph:'5,5%', casa:'5,3%', heat:[0.80, 0.55, 0.65] },
    { zone:'Caballito',  dpto:'5,8%', ph:'6,1%', casa:'5,9%', heat:[0.35, 0.20, 0.25] },
    { zone:'San Telmo',  dpto:'6,4%', ph:'6,8%', casa:'6,2%', heat:[0.10, 0.05, 0.15] },
  ];

  return (
    <div className="estudio-shell">
      <div className="estudio-toolbar">
        <div className="left">
          <button className="pill-btn ghost" style={{height:32, fontSize:12}}><Icon d={I.caret} size={12} style={{transform:'rotate(90deg)'}}/> Volver a Reportes</button>
          <div style={{display:'flex', alignItems:'center', gap:10}}>
            <span className="progress">Pág. 7 / 38</span>
            <div className="progress-bar"><div/></div>
          </div>
        </div>
        <div style={{display:'flex', gap:8}}>
          <button className="pill-btn ghost" style={{height:32, fontSize:12}}><Icon d={I.share} size={13}/> Compartir</button>
          <button className="pill-btn ghost" style={{height:32, fontSize:12}}><Icon d={I.download} size={13}/> Descargar PDF</button>
          <button className="pill-btn accent" style={{height:32, fontSize:12}}>Suscribirse</button>
        </div>
      </div>

      <div className="estudio-doc">

        {/* Cover */}
        <div className="estudio-cover">
          <div className="meta">Edición #047 · Mayo 2026 · CABA + GBA</div>
          <h1>El interanual cierra en <span className="accent">+14,2%</span> y el m² supera USD 2.800 por primera vez desde 2019.</h1>
          <p className="stand">
            La recuperación del mercado inmobiliario porteño se afianza en mayo. El stock activo cae por tercer mes consecutivo, los permisos de obra suben 12% interanual y Palermo, Recoleta y Núñez lideran la suba de precios.
          </p>
          <div className="estudio-byline">
            <div className="av"/>
            <div>
              <strong>Equipo TasAR</strong><br/>
              <span>Publicado 1 jun 2026 · 38 páginas · lectura 18 min</span>
            </div>
          </div>
        </div>

        {/* TL;DR */}
        <div className="estudio-tldr">
          <div className="tldr-card">
            <div className="n">01</div>
            <div className="h">El índice toca USD 2.847/m²</div>
            <div className="b">Primer mes por encima de los USD 2.800 desde octubre 2019. La aceleración se sostiene desde noviembre.</div>
          </div>
          <div className="tldr-card">
            <div className="n">02</div>
            <div className="h">Stock activo cae -3,4%</div>
            <div className="b">62.480 unidades en venta en CABA, el menor nivel desde febrero 2023. Tres meses consecutivos en baja.</div>
          </div>
          <div className="tldr-card">
            <div className="n">03</div>
            <div className="h">Permisos +12% interanual</div>
            <div className="b">1.213 permisos aprobados este mes. La obra nueva muestra el mejor mayo en 7 años.</div>
          </div>
        </div>

        {/* Section 1 - index */}
        <div className="estudio-section">
          <div className="sec-num">01 · ÍNDICE</div>
          <h2>El índice supera USD 2.800/m² por primera vez desde 2019.</h2>
          <p>
            El <strong>Índice TasAR CABA</strong> cerró mayo en <strong>USD 2.847/m²</strong>, un +1,2% mensual y +14,2% interanual. Es el mejor mayo desde 2019 y el séptimo mes consecutivo de suba.
          </p>
          <p>
            La dinámica responde a tres factores que vamos a desarmar en este informe: <strong>caída del stock activo</strong>, <strong>recuperación del crédito hipotecario</strong> y un cambio de mix — las ventas se están concentrando en barrios de mayor valor por metro.
          </p>
          <div className="estudio-figure">
            <Sparkline data={indexSeries}/>
            <div style={{display:'flex', justifyContent:'space-between', marginTop:8, fontSize:11, color:'var(--ink-3)'}}>
              <span className="mono">Ene 25 · 2.410</span>
              <span className="mono" style={{color:'var(--ink)', fontWeight:600}}>May 26 · 2.847</span>
            </div>
            <figcaption>Fig. 1 — Índice TasAR CABA, USD/m² mediano ponderado. Fuente: TasAR Index v3.2.</figcaption>
          </div>
          <p>
            La pendiente promedio de los últimos 6 meses (+1,4% mensual) es la más pronunciada desde el ciclo 2017-2018. Si se sostiene, el índice cruzaría los USD 3.000/m² antes de fin de año.
          </p>
        </div>

        {/* Pull quote */}
        <div className="pull-quote">
          “El m² porteño sumó USD 437 en 17 meses. Es la recuperación más firme desde el ciclo de 2017.”
        </div>

        {/* Section 2 - zones */}
        <div className="estudio-section">
          <div className="sec-num">02 · ZONAS</div>
          <h2>Recuperación liderada por Palermo, Recoleta y Núñez.</h2>
          <p>
            La suba no es homogénea. <strong>Palermo</strong> (+3,8% mensual), <strong>Núñez</strong> (+4,2%) y <strong>Caballito</strong> (+2,4%) concentran la mayor expansión. En el otro extremo, zonas del sur — Flores, Mataderos, Boedo — siguen en terreno levemente negativo.
          </p>
          <div className="estudio-figure">
            <BarChart data={zoneBars} height={220}/>
            <figcaption>Fig. 2 — USD/m² mediano por barrio. Top 11 zonas de mayor volumen.</figcaption>
          </div>
          <p>
            La brecha entre el barrio más caro (Palermo) y el más barato del ranking (Flores) es hoy de 2,3x. En 2021 era de 1,9x. La <strong>premiumización</strong> del mercado se acentúa.
          </p>
        </div>

        {/* Section 3 - stock */}
        <div className="estudio-section">
          <div className="sec-num">03 · OFERTA</div>
          <h2>El stock activo cae por tercer mes consecutivo.</h2>
          <p>
            Hay <strong>62.480 unidades en venta en CABA</strong>, -3,4% versus abril y -8,9% interanual. Es el menor nivel desde febrero 2023. El tiempo medio de venta para departamentos de 2 a 3 ambientes bajó de 102 a 94 días.
          </p>
          <p>
            En paralelo, el <strong>ratio de cierre</strong> — cuántos avisos terminan en venta versus los que se dan de baja por desistimiento — subió a 41%, su máximo en 4 años. El mercado está más líquido.
          </p>
        </div>

        {/* Section 4 - permits */}
        <div className="estudio-section">
          <div className="sec-num">04 · OBRA NUEVA</div>
          <h2>Los permisos de obra crecen 12% interanual.</h2>
          <p>
            Se aprobaron <strong>1.213 permisos</strong> de obra nueva en mayo, el mejor mayo desde 2018. Belgrano y Caballito concentran un tercio de los nuevos m² declarados.
          </p>
          <div className="estudio-figure">
            <BarChart data={permitBars} height={200}/>
            <figcaption>Fig. 3 — Permisos de obra nueva aprobados, mensual. Fuente: GCBA · Dirección de Obras Particulares.</figcaption>
          </div>
        </div>

        {/* Section 5 - cap rates */}
        <div className="estudio-section">
          <div className="sec-num">05 · RENTABILIDAD</div>
          <h2>Cap rate por barrio y tipología.</h2>
          <p>
            El cap rate (alquiler anual / valor) sigue siendo el reflejo invertido del precio: las zonas premium rinden menos, las zonas del sur más. La media porteña es <strong>5,3% anual</strong> para departamentos.
          </p>
          <div className="estudio-figure">
            <table className="estudio-table">
              <thead>
                <tr>
                  <th>Zona</th><th className="right">Dpto.</th><th className="right">PH</th><th className="right">Casa</th><th>Calor relativo</th>
                </tr>
              </thead>
              <tbody>
                {capRates.map((r,i)=>(
                  <tr key={i}>
                    <td className="first">{r.zone}</td>
                    <td className="right">{r.dpto}</td>
                    <td className="right">{r.ph}</td>
                    <td className="right">{r.casa}</td>
                    <td>
                      <div style={{display:'flex', gap:3}}>
                        {r.heat.map((v,j)=>(
                          <span key={j} className="heat-cell" style={{background: heatColor(v, 'var(--accent)')}}/>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <figcaption>Fig. 4 — Cap rate anual estimado por barrio y tipología. Mayo 2026.</figcaption>
          </div>
        </div>

        {/* Section 6 - conclusion */}
        <div className="estudio-section">
          <div className="sec-num">06 · LO QUE VIENE</div>
          <h2>Qué esperamos para el segundo semestre.</h2>
          <p>
            Tres señales sugieren que la suba se va a sostener: el stock seguirá cayendo si los permisos no se traducen en oferta real (el lag típico es 18-24 meses), el crédito hipotecario muestra crecimiento sostenido por sexto mes, y el spread entre alquiler y depósito a plazo se cerró — hace más atractivo comprar para alquilar.
          </p>
          <p>
            <strong>Nuestra proyección base</strong> para diciembre es de USD 3.020/m² (+6% en el semestre). Un escenario optimista llevaría el índice a USD 3.140; uno conservador, a USD 2.930.
          </p>
          <p>
            Vamos a estar monitoreando especialmente el comportamiento de Belgrano y Caballito, donde la concentración de obra nueva podría generar correcciones puntuales si la absorción se demora.
          </p>
        </div>

        {/* Footer */}
        <div className="estudio-foot">
          <div>
            <h4>Metodología</h4>
            <p>El Índice TasAR utiliza un modelo hedónico v3.2 sobre 2,4M de avisos activos, escrituras del RPI y permisos municipales. Cada precio se ajusta por sup. cubierta, antigüedad, estado, orientación y amenities.</p>
          </div>
          <div>
            <h4>Sobre TasAR</h4>
            <p>Estudios de mercado inmobiliario · 142 zonas cubiertas · actualización cada 24h. Suscribite para recibir las próximas ediciones el primer día hábil de cada mes.</p>
          </div>
        </div>

      </div>
    </div>
  );
}

/* ============================================================
   Export all views to window for crm-app.jsx router
   ============================================================ */
Object.assign(window, {
  ViewBandeja,
  ViewPropiedades,
  ViewPipeline,
  ViewClientes,
  ViewMercado,
  ViewEstudio,
  ViewReportes,
  ViewComparables,
  ViewConfig,
});
