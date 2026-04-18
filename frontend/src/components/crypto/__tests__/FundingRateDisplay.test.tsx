import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { FundingRateDisplay } from '../FundingRateDisplay';

describe('FundingRateDisplay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders funding rate display with symbol', () => {
    const nextFundingTime = Date.now() + 3600000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={0.0001}
        nextFundingTime={nextFundingTime}
      />
    );
    expect(screen.getByText(/Funding Rate - BTCUSDT/)).toBeInTheDocument();
  });

  it('displays positive funding rate correctly', () => {
    const nextFundingTime = Date.now() + 3600000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={0.0001}
        nextFundingTime={nextFundingTime}
      />
    );
    expect(screen.getByText('0.0100%')).toBeInTheDocument();
    expect(screen.getByText('Longs pay Shorts')).toBeInTheDocument();
  });

  it('displays negative funding rate correctly', () => {
    const nextFundingTime = Date.now() + 3600000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={-0.0001}
        nextFundingTime={nextFundingTime}
      />
    );
    expect(screen.getByText('-0.0100%')).toBeInTheDocument();
    expect(screen.getByText('Shorts pay Longs')).toBeInTheDocument();
  });

  it('displays countdown timer', () => {
    const nextFundingTime = Date.now() + 3600000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={0.0001}
        nextFundingTime={nextFundingTime}
      />
    );
    expect(screen.getByText(/1h 0m 0s/)).toBeInTheDocument();
    expect(screen.getByText('Next funding')).toBeInTheDocument();
  });

  it('updates countdown timer every second', () => {
    const nextFundingTime = Date.now() + 3600000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={0.0001}
        nextFundingTime={nextFundingTime}
      />
    );

    expect(screen.getByText(/1h 0m 0s/)).toBeInTheDocument();

    vi.advanceTimersByTime(1000);
    expect(screen.getByText(/0h 59m 59s/)).toBeInTheDocument();
  });

  it('displays "Funding in progress" when time is up', () => {
    const nextFundingTime = Date.now() - 1000;
    render(
      <FundingRateDisplay
        symbol="BTCUSDT"
        fundingRate={0.0001}
        nextFundingTime={nextFundingTime}
      />
    );
    expect(screen.getByText('Funding in progress...')).toBeInTheDocument();
  });
});
