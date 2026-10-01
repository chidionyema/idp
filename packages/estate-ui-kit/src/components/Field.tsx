import * as React from 'react';
import * as LabelPrimitive from '@radix-ui/react-label';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import { cn } from '../lib/cn';

export const Label = React.forwardRef<HTMLLabelElement, React.ComponentProps<typeof LabelPrimitive.Root>>(
  ({ className, ...p }, ref) => <LabelPrimitive.Root ref={ref} className={cn('text-sm font-medium text-text', className)} {...p} />,
);
Label.displayName = 'Label';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...p }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full min-h-(--size-tap-min) rounded-md border border-border-strong bg-surface-2 px-3 text-md text-text placeholder:text-text-muted',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent aria-invalid:border-state-red-ink',
        className,
      )}
      {...p}
    />
  ),
);
Input.displayName = 'Input';

/** Label + control + hint/error in one block, ids wired. */
export function Field({ id, label, hint, error, children }: { id: string; label: string; hint?: string; error?: string; children: React.ReactElement }) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      {React.cloneElement(children, { id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined } as Record<string, unknown>)}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-state-red-ink">{error}</p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-text-2">{hint}</p>
      ) : null}
    </div>
  );
}

/**
 * The consent box the audit found broken (F1: a 210×46 empty box, label detached, 3:1). Here the
 * control is a fixed 20px Radix box, the whole row is the tap target, and the label is sm text-2.
 */
export function Checkbox({ id, label, className, ...p }: React.ComponentProps<typeof CheckboxPrimitive.Root> & { id: string; label: React.ReactNode }) {
  return (
    <label htmlFor={id} className={cn('flex items-start gap-3 min-h-(--size-tap-min) py-2 cursor-pointer text-sm text-text-2', className)}>
      <CheckboxPrimitive.Root
        id={id}
        className="mt-1 size-5 shrink-0 rounded-sm border border-border-strong bg-surface-2 data-[state=checked]:bg-text data-[state=checked]:border-text data-[state=checked]:text-canvas focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        {...p}
      >
        <CheckboxPrimitive.Indicator className="flex items-center justify-center">
          <svg viewBox="0 0 20 20" className="size-4" aria-hidden><path d="M5 10.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </CheckboxPrimitive.Indicator>
      </CheckboxPrimitive.Root>
      <span>{label}</span>
    </label>
  );
}
