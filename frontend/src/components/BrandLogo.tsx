import { useTheme } from '../contexts/ThemeContext';

type Variant = 'topbar' | 'standard' | 'icon';

interface Props {
  variant?: Variant;
  className?: string;
  /** Forzá colores claros (sobre fondo oscuro) o oscuros (sobre fondo claro). Sin esto usa el tema. */
  force?: 'light' | 'dark';
}

/**
 * Logo oficial TasAR — recreado en SVG fiel al brand book.
 *
 * Anatomía: grilla 6x4 de cuadrados redondeados, con un patrón de "mapa de calor"
 * donde los cuadrados centrales son verde fuerte y los externos verde claro.
 *
 * Variantes:
 *  - icon: solo la grilla (favicon, badges, avatares)
 *  - topbar: grilla + wordmark "TasAR" horizontal (header de la app)
 *  - standard: grilla + wordmark + tagline "Mapa de valor · Por zona"
 */
export default function BrandLogo({ variant = 'topbar', className = '', force }: Props) {
  const { mode, theme } = useTheme();
  const effectiveMode = force || mode;
  const isDark = effectiveMode === 'dark';

  // Colores del logo siempre verdes (es la identidad TasAR), pero adaptados al fondo
  const wordmarkColor = isDark ? '#ffffff' : '#0f172a';
  const taglineColor = isDark ? '#94a3b8' : '#64748b';

  // Paleta del heatmap del logo — verde TasAR
  const heatColors = {
    lightest: isDark ? '#1f3a2e' : '#bbf7d0',
    light:    isDark ? '#34d399' : '#86efac',
    mid:      '#22c55e',
    strong:   '#10b981',
    darkest:  isDark ? '#065f46' : '#065f46',
  };

  // Patrón del logo: matriz 6 cols x 4 rows, intensidades 0-4
  // (replica visual del logo del brand book — concentración de "calor" al centro)
  const pattern = [
    [0, 1, 1, 1, 1, 0],
    [1, 1, 3, 3, 1, 1],
    [1, 2, 4, 4, 2, 1],
    [0, 1, 2, 2, 1, 0],
  ];
  const intensityColor = [
    heatColors.lightest,
    heatColors.light,
    heatColors.mid,
    heatColors.strong,
    heatColors.darkest,
  ];

  // viewBox cuadrado 60×60 con la grilla 6×4 centrada (offset Y=10 para centrar)
  const Icon = (
    <svg viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg" className="h-full w-auto flex-shrink-0">
      {pattern.map((row, y) =>
        row.map((intensity, x) => (
          <rect
            key={`${x}-${y}`}
            x={x * 10 + 1}
            y={y * 10 + 11}
            width={8}
            height={8}
            rx={1.8}
            fill={intensityColor[intensity]}
          />
        ))
      )}
    </svg>
  );

  if (variant === 'icon') {
    return <div className={`inline-block ${className}`}>{Icon}</div>;
  }

  if (variant === 'standard') {
    return (
      <div className={`inline-flex flex-col items-center gap-2 ${className}`}>
        <div className="h-16">{Icon}</div>
        <div className="text-3xl font-black tracking-tight" style={{ color: wordmarkColor }}>
          TasAR
        </div>
        <div className="text-[10px] tracking-[0.2em] uppercase font-medium" style={{ color: taglineColor }}>
          Mapa de valor · Por zona
        </div>
      </div>
    );
  }

  // topbar (default)
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      <div className="h-full">{Icon}</div>
      <div className="font-black text-xl tracking-tight leading-none" style={{ color: wordmarkColor }}>
        TasAR
      </div>
    </div>
  );
}
