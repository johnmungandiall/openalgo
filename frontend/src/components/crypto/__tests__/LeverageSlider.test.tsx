import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LeverageSlider } from '../LeverageSlider';

describe('LeverageSlider', () => {
  it('renders leverage slider with correct value', () => {
    render(<LeverageSlider value={10} onChange={vi.fn()} />);
    expect(screen.getByText('10x')).toBeInTheDocument();
  });

  it('displays correct risk level for different leverage values', () => {
    const { rerender } = render(<LeverageSlider value={3} onChange={vi.fn()} />);
    expect(screen.getByText('Low Risk')).toBeInTheDocument();

    rerender(<LeverageSlider value={8} onChange={vi.fn()} />);
    expect(screen.getByText('Medium Risk')).toBeInTheDocument();

    rerender(<LeverageSlider value={12} onChange={vi.fn()} />);
    expect(screen.getByText('High Risk')).toBeInTheDocument();

    rerender(<LeverageSlider value={20} onChange={vi.fn()} />);
    expect(screen.getByText('Very High Risk')).toBeInTheDocument();
  });

  it('calculates liquidation price for LONG position', () => {
    render(
      <LeverageSlider
        value={10}
        onChange={vi.fn()}
        entryPrice={50000}
        quantity={0.5}
        side="LONG"
      />
    );
    expect(screen.getByText(/Liquidation Price:/)).toBeInTheDocument();
  });

  it('calculates required margin correctly', () => {
    render(
      <LeverageSlider
        value={10}
        onChange={vi.fn()}
        entryPrice={50000}
        quantity={0.5}
        side="LONG"
      />
    );
    expect(screen.getByText(/Required Margin:/)).toBeInTheDocument();
    expect(screen.getByText(/\$2500\.00/)).toBeInTheDocument();
  });

  it('shows warning for high leverage', () => {
    render(<LeverageSlider value={15} onChange={vi.fn()} />);
    expect(screen.getByText(/High leverage increases liquidation risk/)).toBeInTheDocument();
  });

  it('does not show warning for low leverage', () => {
    render(<LeverageSlider value={5} onChange={vi.fn()} />);
    expect(screen.queryByText(/High leverage increases liquidation risk/)).not.toBeInTheDocument();
  });
});
