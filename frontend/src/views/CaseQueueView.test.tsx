import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { makeAuditRecord, makeReviewRecord } from '../test/recordFactory';

const listAudits = vi.fn();
const getSubmission = vi.fn();

vi.mock('../api/client', () => ({
  listAudits: (...args: unknown[]) => listAudits(...args),
  getSubmission: (...args: unknown[]) => getSubmission(...args),
  ApiError: class ApiError extends Error {
    status: number;
    payload: unknown;
    constructor(status: number, message: string, payload: unknown) { super(message); this.status = status; this.payload = payload; }
  },
}));

import { CaseQueueView } from './CaseQueueView';

beforeEach(() => {
  listAudits.mockReset();
  getSubmission.mockReset();
});

it('UI-GRID-001 derives queue metrics from live AuditRecord data', async () => {
  const match = makeAuditRecord();
  const review = makeReviewRecord();
  review.email_id = 'email-test-002';
  review.email.email_id = 'email-test-002';
  listAudits.mockResolvedValue([match, review]);
  render(<MemoryRouter><CaseQueueView /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('email-test-001')).toBeInTheDocument());
  expect(screen.getByText('Total').parentElement).toHaveTextContent('2');
  expect(screen.getByText('Needs Review').parentElement).toHaveTextContent('1');
  expect(screen.getByText('Clean Matches').parentElement).toHaveTextContent('1');
  expect(screen.queryByText('520')).not.toBeInTheDocument();
});

it('UI-BADGE-001 outcome badges include text and non-color icon cues', async () => {
  listAudits.mockResolvedValue([makeReviewRecord()]);
  render(<MemoryRouter><CaseQueueView /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('NEEDS REVIEW')).toBeInTheDocument());
  expect(screen.getAllByText('◷').length).toBeGreaterThan(0);
});
