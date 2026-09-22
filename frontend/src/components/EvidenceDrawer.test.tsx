import { fireEvent, render, screen } from '@testing-library/react';
import { EvidenceDrawer } from './EvidenceDrawer';

it('UI-DRW-001 renders source evidence and closes on Escape', () => {
  const close = vi.fn();
  render(<EvidenceDrawer open field="shipper" onClose={close} evidence={[{ evidence_id: 'ev1', source_type: 'document', source_id: 'si.txt', kind: 'text_span', quote: 'ACME CORP', location: { page: 1 } }]} />);
  expect(screen.getByText('ACME CORP')).toBeInTheDocument();
  expect(screen.getByText(/page 1/)).toBeInTheDocument();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(close).toHaveBeenCalledTimes(1);
});
