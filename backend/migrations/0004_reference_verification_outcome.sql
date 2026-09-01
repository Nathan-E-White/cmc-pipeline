-- This declared runner audits a reference case; it does not solve a physical case.
UPDATE runs AS r
SET outcome = 'indeterminate', updated_at = now()
FROM run_attempts AS a
WHERE a.run_id = r.run_id
  AND a.runner_key = 'reference-solver'
  AND r.lifecycle = 'terminal'
  AND r.outcome = 'solved';

UPDATE run_summary_projections AS s
SET outcome = 'indeterminate', updated_at = now()
FROM run_attempts AS a
WHERE a.run_id = s.run_id
  AND a.runner_key = 'reference-solver'
  AND s.outcome = 'solved';
