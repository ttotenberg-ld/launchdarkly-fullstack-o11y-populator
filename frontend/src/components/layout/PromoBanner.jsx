import { useEffect, useState } from 'react';
import { useFlags } from 'launchdarkly-react-client-sdk';

/**
 * Site-wide promo banner driven by the `promo-banner` LD flag.
 *
 * Variants:
 *   - none             → banner hidden (control)
 *   - free-shipping-50 → free shipping over $50 messaging
 *   - percent-off      → 20% off first order messaging
 *   - urgency          → flash sale with live countdown
 *
 * Demo-grade: the urgency countdown is cosmetic and resets on mount.
 */
export default function PromoBanner() {
  const flags = useFlags();
  const variant = flags['promo-banner'] || 'none';
  const [secondsLeft, setSecondsLeft] = useState(2 * 60 * 60); // 2 hours

  useEffect(() => {
    if (variant !== 'urgency') return;
    const tick = setInterval(() => {
      setSecondsLeft((s) => (s > 0 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(tick);
  }, [variant]);

  if (variant === 'none') return null;

  const config = {
    'free-shipping-50': {
      bg: 'linear-gradient(90deg, #0a66c2, #1d4ed8)',
      text: 'Free shipping on orders over $50. No code needed.',
      emoji: '',
    },
    'percent-off': {
      bg: 'linear-gradient(90deg, #059669, #10b981)',
      text: '20% off your first order. Automatic at checkout.',
      emoji: '',
    },
    'urgency': {
      bg: 'linear-gradient(90deg, #dc2626, #f97316)',
      text: `Flash sale — ends in ${formatCountdown(secondsLeft)}`,
      emoji: '',
    },
  }[variant];

  if (!config) return null;

  return (
    <div
      data-testid="promo-banner"
      data-variant={variant}
      style={{
        background: config.bg,
        color: '#ffffff',
        textAlign: 'center',
        padding: '10px 16px',
        fontSize: '14px',
        fontWeight: 600,
        letterSpacing: '0.2px',
      }}
    >
      {config.text}
    </div>
  );
}

function formatCountdown(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
