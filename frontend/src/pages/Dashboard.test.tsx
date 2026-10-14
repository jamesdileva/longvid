import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Dashboard from './Dashboard';
import * as api from '../services/api';

const HEALTH_FIXTURE = { status: 'ok', version: '0.1.0', database: 'ok' };

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Dashboard', () => {
  it('shows the backend as online when the health check succeeds', async () => {
    vi.spyOn(api, 'fetchHealth').mockResolvedValue(HEALTH_FIXTURE);

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('backend-status')).toHaveTextContent('Online');
    });
    expect(screen.getByTestId('backend-version')).toHaveTextContent('0.1.0');
  });

  it('shows the backend as offline when the health check fails', async () => {
    vi.spyOn(api, 'fetchHealth').mockRejectedValue(new Error('unreachable'));

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('backend-status')).toHaveTextContent('Offline');
    });
  });
});
