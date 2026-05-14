import { ReactNode } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

interface MobilePageHeaderProps {
  title: string;
  description?: string;
  subtitle?: string;
  onBack?: () => void;
  actions?: ReactNode;
}

/** Stub mínimo — el header completo es opcional dado que usamos el Layout global */
export function MobilePageHeader({ title, description, actions }: MobilePageHeaderProps) {
  const { theme } = useTheme();
  return (
    <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${theme.border}` }}>
      <div>
        <h2 className="font-semibold" style={{ color: theme.text }}>{title}</h2>
        {description && <p className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export default MobilePageHeader;
