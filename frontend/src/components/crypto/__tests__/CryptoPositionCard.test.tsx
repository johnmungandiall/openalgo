import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CryptoPositionCard } from '../CryptoPositionCard';

describe('CryptoPositionCard', () => {
  const mockPosition = {
    symbol: 'BTCUSDT',
    side: 'LONG' as const,
    quantity: 0.5,
    entryPrice: 50000,
    markPrice: 51000,
    liquidationPrice: 45250,
    unrealizedPnl: 500,
    margin: 2500,
    leverage: 10,
    marginMode: 'ISOLATED',
    roe: 20
  };

  it('renders position card with correct symbol and side', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
  });

  it('displays leverage badge', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('10x')).toBeInTheDocument();
  });

  it('displays position details correctly', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('0.5')).toBeInTheDocument();
    expect(screen.getByText('$50000')).toBeInTheDocument();
    expect(screen.getByText('$51000')).toBeInTheDocument();
    expect(screen.getByText('$2500')).toBeInTheDocument();
  });

  it('displays unrealized PnL with correct color for profit', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('$500.00')).toBeInTheDocument();
    expect(screen.getByText('+20%')).toBeInTheDocument();
  });

  it('displays unrealized PnL with correct color for loss', () => {
    const lossPosition = { ...mockPosition, unrealizedPnl: -300, roe: -12 };
    render(<CryptoPositionCard position={lossPosition} />);
    expect(screen.getByText('$300.00')).toBeInTheDocument();
    expect(screen.getByText('-12%')).toBeInTheDocument();
  });

  it('displays liquidation price and risk level', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('$45250')).toBeInTheDocument();
    expect(screen.getByText(/Risk:/)).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(<CryptoPositionCard position={mockPosition} />);
    expect(screen.getByText('Add Margin')).toBeInTheDocument();
    expect(screen.getByText('Reduce Margin')).toBeInTheDocument();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('calls onAddMargin when Add Margin button is clicked', async () => {
    const onAddMargin = vi.fn();
    render(<CryptoPositionCard position={mockPosition} onAddMargin={onAddMargin} />);

    const button = screen.getByText('Add Margin');
    button.click();
    expect(onAddMargin).toHaveBeenCalled();
  });

  it('calls onClose when Close button is clicked', async () => {
    const onClose = vi.fn();
    render(<CryptoPositionCard position={mockPosition} onClose={onClose} />);

    const button = screen.getByText('Close');
    button.click();
    expect(onClose).toHaveBeenCalled();
  });

  it('shows SHORT badge with correct variant', () => {
    const shortPosition = { ...mockPosition, side: 'SHORT' as const };
    render(<CryptoPositionCard position={shortPosition} />);
    expect(screen.getByText('SHORT')).toBeInTheDocument();
  });
});
