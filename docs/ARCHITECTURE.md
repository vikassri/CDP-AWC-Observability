# Architecture

Hub-and-spoke observability for seven AWC Kubernetes clusters. In-cluster `ccf-monitoring` remains the spoke; this tool is the **control plane + correlation hub** on your workstation or observability VM.

## Data paths

- **Discovery:** `config/clusters.yaml` maps each engine id (`cdf`, `cde`, …) to a kubeconfig. Collectors call `kubectl` against that file and list NiFi / Trino / SparkApplication / FlinkDeployment / Airflow pods. Explore via `GET /clusters/{id}/workloads`, `GET /clusters/workloads/fleet`, or `python scripts/explore-clusters.py`.
- **Metrics:** Hub agents discover workloads, maintain `kubectl port-forward` where needed, write Prometheus `file_sd` under `deploy/data/prometheus/file_sd/`. Hub Prometheus (Docker) federates NiFi and scrapes status exporters for Trino, Spark, Flink, Airflow.
- **Logs:** Hub agents start `collectors/logging/kubectl_logs_to_otel.py` per discovered pod when `*_logs` is enabled in `clusters.yaml`. Logs ship to OTel Collector → OpenSearch index `cpw-logs` (start `otel-collector` + `opensearch` in compose for search).
- **Alerts:** YAML rules in `config/alerts/` synced to Grafana provisioning via `POST /alerts/sync`.
- **Remediations:** Allowlisted K8s actions with preview → approve → execute and Postgres audit.

## AWC console

Fleet rows link to [deployed experiences](https://console.awc.spoc.cloudera-labs.com/deployed-experiences?view=engines) using `config/awc.yaml`.

## Security

Kubeconfigs and JWTs are never committed. Use VPN/bastion to reach private API servers (`10.0.x.x`).
