# Normalised vs star schema benchmark

PostgreSQL 18.6; median of 200 runs after 5 warm-up runs; times from EXPLAIN (ANALYZE), in milliseconds.

| Query | Rows | Joins (norm / star) | Tables (norm / star) | Planning ms (norm / star) | Execution ms (norm / star) | Same rows |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 Cumulative time per rider (GC) | 160 | 2 / 1 | 4 / 3 | 0.044 / 0.035 | 1.069 / 0.617 | yes |
| Q2 Best team classification | 23 | 3 / 1 | 4 / 2 | 0.053 / 0.022 | 2.498 / 1.217 | yes |
| Q3 Stage-by-stage performance | 21 | 6 / 2 | 5 / 3 | 0.19 / 0.06 | 1.999 / 1.418 | yes |
| Q4 Speed roll-up by type and nation | 113 | 3 / 2 | 4 / 3 | 0.057 / 0.029 | 1.812 / 1.344 | yes |
