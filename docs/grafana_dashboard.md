# Troostwatch Grafana Dashboard

This document describes a reference Grafana dashboard for monitoring Troostwatch
when metrics are exported to Prometheus.

## Setup Requirements

1. **Prometheus**: Scraping the `/metrics` endpoint from the FastAPI app
2. **Grafana**: Connected to Prometheus as a data source

## Dashboard JSON

Import the following JSON into Grafana (Dashboards → Import → Paste JSON):

```json
{
  "annotations": {
    "list": []
  },
  "title": "Troostwatch Overview",
  "uid": "troostwatch-main",
  "version": 1,
  "timezone": "browser",
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "title": "API Requests per Second",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
      "targets": [
        {
          "expr": "rate(api_requests_total[5m])",
          "legendFormat": "{{endpoint}} {{method}} {{status}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        }
      }
    },
    {
      "id": 2,
      "title": "API Error Rate (%)",
      "type": "stat",
      "gridPos": { "x": 12, "y": 0, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "sum(rate(api_requests_total{status=~\"4..|5..\"}[5m])) / sum(rate(api_requests_total[5m])) * 100"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "value": 0, "color": "green" },
              { "value": 1, "color": "yellow" },
              { "value": 5, "color": "red" }
            ]
          }
        }
      }
    },
    {
      "id": 3,
      "title": "API Latency (p95)",
      "type": "stat",
      "gridPos": { "x": 18, "y": 0, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "value": 0, "color": "green" },
              { "value": 0.5, "color": "yellow" },
              { "value": 1, "color": "red" }
            ]
          }
        }
      }
    },
    {
      "id": 4,
      "title": "API Latency Distribution",
      "type": "timeseries",
      "gridPos": { "x": 12, "y": 4, "w": 12, "h": 4 },
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(api_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(api_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    },
    {
      "id": 5,
      "title": "Sync Runs",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 8, "w": 12, "h": 8 },
      "targets": [
        {
          "expr": "increase(sync_runs_total{status=\"success\"}[1h])",
          "legendFormat": "Success ({{auction_code}})"
        },
        {
          "expr": "increase(sync_runs_total{status=\"failed\"}[1h])",
          "legendFormat": "Failed ({{auction_code}})"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {
            "drawStyle": "bars"
          }
        }
      }
    },
    {
      "id": 6,
      "title": "Sync Success Rate",
      "type": "gauge",
      "gridPos": { "x": 12, "y": 8, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "sum(sync_runs_total{status=\"success\"}) / sum(sync_runs_total) * 100"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "min": 0,
          "max": 100,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "value": 0, "color": "red" },
              { "value": 90, "color": "yellow" },
              { "value": 98, "color": "green" }
            ]
          }
        }
      }
    },
    {
      "id": 7,
      "title": "Avg Sync Duration",
      "type": "stat",
      "gridPos": { "x": 18, "y": 8, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "rate(sync_run_duration_seconds_sum[5m]) / rate(sync_run_duration_seconds_count[5m])"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    },
    {
      "id": 8,
      "title": "Lots Synced per Hour",
      "type": "timeseries",
      "gridPos": { "x": 12, "y": 12, "w": 12, "h": 4 },
      "targets": [
        {
          "expr": "increase(sync_lots_processed_total[1h])",
          "legendFormat": "{{auction_code}}"
        }
      ]
    },
    {
      "id": 9,
      "title": "Bids per Hour",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 16, "w": 12, "h": 8 },
      "targets": [
        {
          "expr": "increase(bids_total{outcome=\"success\"}[1h])",
          "legendFormat": "Successful"
        },
        {
          "expr": "increase(bids_total{outcome=\"failed\"}[1h])",
          "legendFormat": "Failed"
        },
        {
          "expr": "increase(bids_total{outcome=\"rejected\"}[1h])",
          "legendFormat": "Rejected"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": {
            "drawStyle": "bars",
            "stacking": { "mode": "normal" }
          }
        }
      }
    },
    {
      "id": 10,
      "title": "Bid Success Rate",
      "type": "gauge",
      "gridPos": { "x": 12, "y": 16, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "sum(bids_total{outcome=\"success\"}) / sum(bids_total) * 100"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "min": 0,
          "max": 100,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "value": 0, "color": "red" },
              { "value": 80, "color": "yellow" },
              { "value": 95, "color": "green" }
            ]
          }
        }
      }
    },
    {
      "id": 11,
      "title": "Total Bids Today",
      "type": "stat",
      "gridPos": { "x": 18, "y": 16, "w": 6, "h": 4 },
      "targets": [
        {
          "expr": "sum(increase(bids_total[24h]))"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 12,
      "title": "Bids by Auction",
      "type": "piechart",
      "gridPos": { "x": 12, "y": 20, "w": 12, "h": 4 },
      "targets": [
        {
          "expr": "sum by (auction_code) (bids_total)",
          "legendFormat": "{{auction_code}}"
        }
      ]
    }
  ],
  "schemaVersion": 38
}
```

## Panel Descriptions

### Row 1: API Health

| Panel | Type | Description |
|-------|------|-------------|
| API Requests per Second | Time series | Request rate by endpoint, method, and status |
| API Error Rate | Stat | Percentage of 4xx/5xx responses |
| API Latency (p95) | Stat | 95th percentile response time |
| API Latency Distribution | Time series | p50, p95, p99 latency over time |

### Row 2: Sync Operations

| Panel | Type | Description |
|-------|------|-------------|
| Sync Runs | Bar chart | Success/failure count per auction |
| Sync Success Rate | Gauge | Overall sync reliability |
| Avg Sync Duration | Stat | Mean time per sync run |
| Lots Synced per Hour | Time series | Processing volume |

### Row 3: Bidding Activity

| Panel | Type | Description |
|-------|------|-------------|
| Bids per Hour | Stacked bar | Bid outcomes over time |
| Bid Success Rate | Gauge | Percentage of successful bids |
| Total Bids Today | Stat | 24h bid volume |
| Bids by Auction | Pie chart | Distribution across auctions |

## Recommended Alerts

Configure these alerts in Grafana or Prometheus Alertmanager:

```yaml
groups:
  - name: troostwatch
    rules:
      - alert: HighAPIErrorRate
        expr: |
          sum(rate(api_requests_total{status=~"5.."}[5m]))
          / sum(rate(api_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API error rate above 5%"

      - alert: SyncFailures
        expr: |
          increase(sync_runs_total{status="failed"}[1h]) > 3
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Multiple sync failures in the last hour"

      - alert: HighAPILatency
        expr: |
          histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API p95 latency above 2 seconds"

      - alert: NoSyncActivity
        expr: |
          increase(sync_runs_total[2h]) == 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "No sync runs in the last 2 hours"
```

## Prometheus Scrape Config

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'troostwatch'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']  # FastAPI app address
    metrics_path: '/metrics'
```

## Notes

- The dashboard uses 5-minute rate windows for smooth graphs
- Thresholds are suggestions; adjust based on your SLOs
- For high-cardinality labels (many auctions), consider aggregating
