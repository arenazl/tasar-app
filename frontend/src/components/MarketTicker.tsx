import { useTheme } from '../contexts/ThemeContext';

interface TickerItem {
  zone: string;
  price: number;
  change: number; // % vs mes anterior
}

const DEFAULT_DATA: TickerItem[] = [
  { zone: 'Palermo', price: 3420, change: 2.1 },
  { zone: 'Recoleta', price: 3180, change: 1.4 },
  { zone: 'Belgrano', price: 2890, change: 0.9 },
  { zone: 'Núñez', price: 2750, change: 1.8 },
  { zone: 'Caballito', price: 2410, change: -0.3 },
  { zone: 'Villa Crespo', price: 2380, change: 1.2 },
  { zone: 'San Telmo', price: 1640, change: -0.4 },
  { zone: 'Almagro', price: 2050, change: 0.7 },
  { zone: 'Colegiales', price: 2680, change: 1.6 },
  { zone: 'Saavedra', price: 2240, change: 0.5 },
  { zone: 'Flores', price: 1820, change: -0.8 },
  { zone: 'Vte. López', price: 3150, change: 2.4 },
  { zone: 'La Plata', price: 1450, change: 0.3 },
  { zone: 'Rosario', price: 1690, change: 1.1 },
  { zone: 'Córdoba', price: 1530, change: 0.6 },
  { zone: 'Mendoza', price: 1380, change: -0.5 },
];

interface Props {
  data?: TickerItem[];
  /** Velocidad en segundos para completar un loop. Mayor = más lento. Defecto 60s. */
  speed?: number;
  /** Compacto = padding y fuente reducidos (uso en top de Login, footer). */
  compact?: boolean;
}

/**
 * Marquesina tipo bolsa de valores — scroll horizontal continuo con precios
 * de zonas inmobiliarias en USD/m² + variación porcentual.
 *
 * El truco: renderizamos la data 2 veces seguidas y animamos translateX
 * desde 0 hasta -50%. Cuando llega al 50% (que es el inicio de la copia)
 * el loop reinicia sin glitch visual.
 */
export default function MarketTicker({ data = DEFAULT_DATA, speed = 60, compact = false }: Props) {
  const { theme } = useTheme();
  const items = [...data, ...data]; // duplicado para loop infinito sin corte visible

  return (
    <div
      className={`relative overflow-hidden ${compact ? 'py-1.5' : 'py-2.5'}`}
      style={{
        background: theme.card,
        borderTop: `1px solid ${theme.border}`,
        borderBottom: `1px solid ${theme.border}`,
      }}
    >
      {/* Fade gradients en los bordes */}
      <div className="absolute left-0 top-0 bottom-0 w-16 z-10 pointer-events-none"
        style={{ background: `linear-gradient(to right, ${theme.card}, transparent)` }} />
      <div className="absolute right-0 top-0 bottom-0 w-16 z-10 pointer-events-none"
        style={{ background: `linear-gradient(to left, ${theme.card}, transparent)` }} />

      {/* Label fijo a la izquierda */}
      <div className="absolute left-0 top-0 bottom-0 flex items-center z-20 pl-3 pr-4"
        style={{ background: theme.card, borderRight: `1px solid ${theme.border}` }}>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: theme.success }} />
          <span className={`${compact ? 'text-[9px]' : 'text-[10px]'} uppercase tracking-[0.2em] font-bold`}
            style={{ color: theme.textSecondary }}>
            USD/m² · en vivo
          </span>
        </div>
      </div>

      {/* Track scrolling */}
      <div
        className="flex items-center gap-8 whitespace-nowrap ml-32"
        style={{
          animation: `tickerScroll ${speed}s linear infinite`,
          willChange: 'transform',
        }}
      >
        {items.map((item, i) => (
          <div key={i} className={`inline-flex items-center gap-2 ${compact ? 'text-xs' : 'text-sm'}`}>
            <span className="font-semibold" style={{ color: theme.text }}>{item.zone}</span>
            <span className="font-mono tabular-nums" style={{ color: theme.textSecondary }}>
              USD {item.price.toLocaleString()}
            </span>
            <span
              className={`font-mono tabular-nums font-semibold ${compact ? 'text-[10px]' : 'text-xs'}`}
              style={{ color: item.change >= 0 ? theme.success : theme.danger }}
            >
              {item.change >= 0 ? '▲' : '▼'} {item.change >= 0 ? '+' : ''}{item.change.toFixed(1)}%
            </span>
            <span className="opacity-30" style={{ color: theme.textSecondary }}>·</span>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes tickerScroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
