import { clsx, type ClassValue } from 'clsx';
/** Join class names. The kit has no runtime class merging; variants are exclusive by design. */
export const cn = (...inputs: ClassValue[]) => clsx(inputs);
