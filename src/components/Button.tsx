import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../lib/cn';

// Every button clears the 44px tap minimum (tokens.size.tap-min); the audit of 2026-09-30 found
// 29 of 49 home controls under it. Arrow labels never wrap away from their arrow (audit F10).
const button = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-sans font-medium ' +
    'min-h-(--size-tap-min) px-4 text-sm transition-colors duration-(--motion-fast) ease-estate ' +
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ' +
    'disabled:opacity-50 disabled:pointer-events-none select-none',
  {
    variants: {
      variant: {
        primary: 'bg-text text-canvas hover:bg-text-2',
        accent: 'bg-accent text-on-accent hover:bg-accent-pressed',
        secondary: 'bg-surface-2 text-text border border-border-strong hover:bg-surface-3',
        ghost: 'bg-transparent text-text hover:bg-surface-3',
        link: 'bg-transparent text-accent underline underline-offset-4 px-1 hover:text-accent-pressed',
      },
      size: {
        md: 'text-sm',
        lg: 'text-md px-6 min-h-(--space-12)',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof button> & { asChild?: boolean };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return <Comp ref={ref} className={cn(button({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = 'Button';
