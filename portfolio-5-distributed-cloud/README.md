# Portfolio 5: Distributed and Cloud Database Exercise

Describe or demonstrate a distributed or cloud database approach for the [university portal](../CASE_STUDY.md).

This activity uses PostgreSQL logical replication in a local Docker Compose network, plus a shard-key simulation and a cloud deployment design. The primary accepts writes; the application routes reporting reads to the subscriber. No hosted cloud account is required.

## Working files

- [Publisher and subscriber architecture](architecture.md)
- [Docker Compose setup](compose.yaml)
- [Publication and subscription SQL](primary-publication.sql), [subscriber setup](subscriber-subscription.sql)
- [Write to the publisher](write-primary.sql), [read from the subscriber](verify-replica.sql), [check publisher status](status-primary.sql), and [check subscriber status](status-replica.sql)
- [Pause replication](pause-replication.sql) and [resume replication](resume-replication.sql)
- [Shard-key simulation](shard-key-simulation.sql) and its [output](shard-key-simulation-output.txt)
- [Run results](run-results.md)

## Evidence

- Logical-replication architecture and local Compose configuration
- Initial copy, streaming status, and publisher/subscriber outputs
- A paused-replication stale-read demonstration and catch-up after resuming
- Discussion of consistency, read routing, availability, failover, and sequence limitations
- Shard-key analysis with a hash-partition simulation: transcript queries touch 1 of 4 shards, capacity checks touch all 4. Recommendation to shard by `section_id`.
- Mapping of the local setup to a managed cloud deployment: synchronous HA standby vs asynchronous read replicas, backups/PITR, and secrets

Captured output is linked from [run-results.md](run-results.md).

Start with `docker compose up -d`, then run the subscription setup as described in [run-results.md](run-results.md). This is a local teaching demo; the fixed credentials in the Compose and SQL setup files are for disposable containers only.
