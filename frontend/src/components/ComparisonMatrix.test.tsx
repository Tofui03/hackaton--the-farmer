import { render, screen } from '@testing-library/react';
import { ComparisonMatrix } from './ComparisonMatrix';
import { makeAuditRecord, makeReviewRecord } from '../test/recordFactory';
import { FIELD_NAMES } from '../utils';

it('UI-DIFF-001 renders all seven mandatory fields in four-column matrix', () => {
  render(<ComparisonMatrix record={makeAuditRecord()} onEvidence={() => undefined} />);
  for (const field of FIELD_NAMES) expect(screen.getByTestId(`comparison-row-${field}`)).toBeInTheDocument();
  expect(screen.getAllByTestId(/^comparison-row-/)).toHaveLength(7);
  expect(screen.getByText('Shipping Instruction (SI)')).toBeInTheDocument();
  expect(screen.getByText('Draft Bill of Lading (BL)')).toBeInTheDocument();
  expect(screen.getByText('Outcome / Result')).toBeInTheDocument();
});

it('UI-DIFF-002 keeps unresolved rows visible', () => {
  render(<ComparisonMatrix record={makeReviewRecord()} onEvidence={() => undefined} />);
  const row = screen.getByTestId('comparison-row-gross_weight_kg');
  expect(row).toHaveTextContent('UNRESOLVED');
  expect(row).toHaveTextContent('[Not Found in Document]');
});
