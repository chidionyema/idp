// SidebarItem still wants a Material-shaped icon component. Remix is the official
// Backstage icon set (IconElement prefers it; Material icons are deprecated).
// Pin the package below 4.9.0 — 4.9.0 changed licence.
// https://backstage.io/api/stable/types/_backstage_frontend-plugin-api.index.IconElement.html
import type { ComponentType } from 'react';
import type { IconComponent } from '@backstage/core-plugin-api';

type Remix = ComponentType<{
  size?: number | string;
  color?: string;
  className?: string;
}>;

// Material's three icon sizes in pixels; anything else (inherit, default) reads as medium.
const SIZE_PX: Record<string, number> = { small: 20, medium: 24, large: 32 };

export function remix(Icon: Remix): IconComponent {
  const Wrapped: IconComponent = ({ fontSize }) => {
    const size = SIZE_PX[fontSize ?? 'medium'] ?? 24;
    return <Icon size={size} color="currentColor" />;
  };
  Wrapped.displayName = `Remix(${Icon.displayName ?? Icon.name})`;
  return Wrapped;
}
