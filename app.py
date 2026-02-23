from flask import Flask, jsonify, render_template
from collections import deque
import threading
import datetime
import random
import time

app = Flask(__name__)

# ─── Try to load real Kubernetes config ────────────────────────────────────────
K8S_AVAILABLE = False
v1 = apps_v1 = custom_api = autoscaling_v2 = autoscaling_v1 = None

try:
    from kubernetes import client, config
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

    v1            = client.CoreV1Api()
    apps_v1       = client.AppsV1Api()
    custom_api    = client.CustomObjectsApi()
    try:
        autoscaling_v2 = client.AutoscalingV2Api()
        HPA_V2 = True
    except AttributeError:
        autoscaling_v1 = client.AutoscalingV1Api()
        HPA_V2 = False

    # Quick connectivity test
    v1.list_node(_request_timeout=3)
    K8S_AVAILABLE = True
    print("✅  Connected to real Kubernetes cluster")
except Exception as e:
    print(f"⚠️  Kubernetes not available ({e}) — using mock data")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _parse_cpu(value):
    if not value:
        return 0.0
    if value.endswith("n"):
        return float(value[:-1]) / 1_000_000
    if value.endswith("u"):
        return float(value[:-1]) / 1_000
    if value.endswith("m"):
        return float(value[:-1])
    return float(value) * 1000

def _parse_memory(value):
    if not value:
        return 0.0
    units = {"Ki": 1/1024, "Mi": 1, "Gi": 1024, "Ti": 1024*1024}
    for suffix, factor in units.items():
        if str(value).endswith(suffix):
            return float(value[:-len(suffix)]) * factor
    return float(value) / (1024 * 1024)

def _node_metrics_raw():
    try:
        return custom_api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes"
        ).get("items", [])
    except Exception:
        return []

def _pod_metrics_raw():
    try:
        return custom_api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="pods"
        ).get("items", [])
    except Exception:
        return []


# ─── Rolling Time-Series Buffer ────────────────────────────────────────────────
MAX_SAMPLES = 60
timeseries = {
    "timestamps":  deque(maxlen=MAX_SAMPLES),
    "cluster_cpu": deque(maxlen=MAX_SAMPLES),
    "cluster_mem": deque(maxlen=MAX_SAMPLES),
    "pod_count":   deque(maxlen=MAX_SAMPLES),
}

# Seed mock timeseries with some history so charts aren't empty on load
_base_cpu = 35.0
_base_mem = 52.0
_base_pods = 18
for i in range(30):
    _t = (datetime.datetime.utcnow() - datetime.timedelta(seconds=(30-i)*5))
    timeseries["timestamps"].append(_t.strftime("%H:%M:%S"))
    timeseries["cluster_cpu"].append(round(_base_cpu + random.uniform(-5, 5), 1))
    timeseries["cluster_mem"].append(round(_base_mem + random.uniform(-3, 3), 1))
    timeseries["pod_count"].append(_base_pods + random.randint(-2, 2))


def _collect_timeseries():
    while True:
        try:
            if K8S_AVAILABLE:
                node_items  = _node_metrics_raw()
                nodes_list  = v1.list_node()
                pod_items   = _pod_metrics_raw()
                total_cpu   = sum(_parse_cpu(n["usage"]["cpu"]) for n in node_items)
                total_mem   = sum(_parse_memory(n["usage"]["memory"]) for n in node_items)
                alloc_cpu   = sum(_parse_cpu(n.status.allocatable.get("cpu","0")) for n in nodes_list.items) or 1
                alloc_mem   = sum(_parse_memory(n.status.allocatable.get("memory","0")) for n in nodes_list.items) or 1
                cpu_pct     = round(total_cpu / alloc_cpu * 100, 1)
                mem_pct     = round(total_mem / alloc_mem * 100, 1)
                pod_cnt     = len(pod_items)
            else:
                # Smooth mock random walk
                prev_cpu = timeseries["cluster_cpu"][-1] if timeseries["cluster_cpu"] else 35.0
                prev_mem = timeseries["cluster_mem"][-1] if timeseries["cluster_mem"] else 52.0
                prev_pod = timeseries["pod_count"][-1]   if timeseries["pod_count"]   else 18
                cpu_pct  = round(max(5, min(95, prev_cpu + random.uniform(-3, 3))), 1)
                mem_pct  = round(max(10, min(90, prev_mem + random.uniform(-2, 2))), 1)
                pod_cnt  = max(10, min(40, prev_pod + random.randint(-1, 1)))

            timeseries["timestamps"].append(datetime.datetime.utcnow().strftime("%H:%M:%S"))
            timeseries["cluster_cpu"].append(cpu_pct)
            timeseries["cluster_mem"].append(mem_pct)
            timeseries["pod_count"].append(pod_cnt)
        except Exception:
            pass
        time.sleep(5)

threading.Thread(target=_collect_timeseries, daemon=True).start()


# ─── Mock Data Generators ──────────────────────────────────────────────────────
def mock_cluster_overview():
    return {
        "total_nodes":       3,
        "ready_nodes":       3,
        "total_pods":        18,
        "running_pods":      16,
        "crashloop_pods":    1,
        "total_deployments": 6,
        "total_services":    8,
        "hpa_replicas":      4,
        "mode":              "mock"
    }

def mock_nodes():
    names = ["node-master-01", "node-worker-01", "node-worker-02"]
    roles = ["master", "worker", "worker"]
    return [
        {
            "name":      names[i],
            "role":      roles[i],
            "cpu_pct":   round(random.uniform(20, 75), 1),
            "mem_pct":   round(random.uniform(30, 80), 1),
            "alloc_cpu": "4000m",
            "alloc_mem": "8192Mi",
            "pods":      random.randint(4, 10),
            "status":    "Ready",
            "age":       f"{random.randint(1,30)}d",
        }
        for i in range(3)
    ]

def mock_pods():
    namespaces = ["default", "kube-system", "monitoring", "production"]
    statuses   = ["Running","Running","Running","Running","Pending","Failed"]
    pod_names  = [
        "frontend-7d9f8b-xkp2q", "backend-api-5c6d7-mnb3r", "redis-master-0",
        "postgres-0", "nginx-ingress-controller-abc12", "coredns-74ff55c5b-lkj8m",
        "metrics-server-6f754f88b-pqrs1", "kube-proxy-node1", "prometheus-0",
        "grafana-6d96c9f4-zt7vx", "load-generator", "worker-queue-84f9b-rtyu4",
        "auth-service-3b5f6-nmop2", "mail-service-9c2d1-vwxy5",
        "scheduler-7a8b9-efgh6", "cache-warmer-1c2d3-ijkl7",
        "log-aggregator-4e5f6-mnop8", "health-checker-7g8h9-qrst9"
    ]
    result = []
    for i, name in enumerate(pod_names):
        restarts = random.choices([0, 0, 0, 1, 3, 8], weights=[50,20,10,10,7,3])[0]
        result.append({
            "name":      name,
            "namespace": namespaces[i % len(namespaces)],
            "cpu_mc":    round(random.uniform(1, 250), 1),
            "mem_mi":    round(random.uniform(10, 512), 1),
            "restarts":  restarts,
            "node":      f"node-worker-0{(i%2)+1}",
            "status":    statuses[i % len(statuses)],
            "age":       f"{random.randint(1,48)}h",
        })
    return result

def mock_hpa():
    return [
        {
            "name":             "frontend-hpa",
            "namespace":        "production",
            "target":           "frontend",
            "min_replicas":     1,
            "max_replicas":     10,
            "current_replicas": 3,
            "desired_replicas": 4,
            "cpu_target_pct":   50,
            "cpu_current_pct":  67,
        },
        {
            "name":             "backend-hpa",
            "namespace":        "production",
            "target":           "backend-api",
            "min_replicas":     2,
            "max_replicas":     8,
            "current_replicas": 2,
            "desired_replicas": 2,
            "cpu_target_pct":   60,
            "cpu_current_pct":  28,
        },
    ]

def mock_deployments():
    items = [
        ("frontend",      "production", 3, 3),
        ("backend-api",   "production", 2, 2),
        ("auth-service",  "production", 2, 1),
        ("redis",         "default",    1, 1),
        ("prometheus",    "monitoring", 1, 1),
        ("grafana",       "monitoring", 1, 1),
    ]
    return [{"name":n,"namespace":ns,"desired":d,"ready":r,"available":r} for n,ns,d,r in items]


# ─── API Routes ────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/cluster-overview")
def cluster_overview():
    if not K8S_AVAILABLE:
        return jsonify(mock_cluster_overview())
    try:
        pods        = v1.list_pod_for_all_namespaces().items
        nodes       = v1.list_node().items
        deployments = apps_v1.list_deployment_for_all_namespaces().items
        services    = v1.list_service_for_all_namespaces().items
        running     = sum(1 for p in pods if p.status.phase == "Running")
        crashloop   = sum(
            1 for p in pods
            if p.status.container_statuses and
            any(cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff"
                for cs in p.status.container_statuses)
        )
        ready_nodes = sum(
            1 for n in nodes
            if any(c.type == "Ready" and c.status == "True" for c in (n.status.conditions or []))
        )
        hpa_replicas = 0
        try:
            if HPA_V2:
                hpas = autoscaling_v2.list_horizontal_pod_autoscaler_for_all_namespaces().items
            else:
                hpas = autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces().items
            hpa_replicas = sum(h.status.current_replicas or 0 for h in hpas)
        except Exception:
            pass
        return jsonify({
            "total_nodes": len(nodes), "ready_nodes": ready_nodes,
            "total_pods": len(pods),   "running_pods": running,
            "crashloop_pods": crashloop, "total_deployments": len(deployments),
            "total_services": len(services), "hpa_replicas": hpa_replicas,
            "mode": "live"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nodes")
def nodes_route():
    if not K8S_AVAILABLE:
        return jsonify(mock_nodes())
    try:
        nodes        = v1.list_node().items
        node_metrics = {n["metadata"]["name"]: n for n in _node_metrics_raw()}
        pods_all     = v1.list_pod_for_all_namespaces().items
        data = []
        for node in nodes:
            name = node.metadata.name
            role = "master" if any(
                k in (node.metadata.labels or {})
                for k in ["node-role.kubernetes.io/master","node-role.kubernetes.io/control-plane"]
            ) else "worker"
            alloc_cpu = _parse_cpu(node.status.allocatable.get("cpu","0"))
            alloc_mem = _parse_memory(node.status.allocatable.get("memory","0"))
            used_cpu = used_mem = 0.0
            if name in node_metrics:
                used_cpu = _parse_cpu(node_metrics[name]["usage"]["cpu"])
                used_mem = _parse_memory(node_metrics[name]["usage"]["memory"])
            cpu_pct = round(used_cpu / alloc_cpu * 100, 1) if alloc_cpu else 0
            mem_pct = round(used_mem / alloc_mem * 100, 1) if alloc_mem else 0
            pods_on_node = sum(1 for p in pods_all if p.spec.node_name == name)
            ready = any(c.type=="Ready" and c.status=="True" for c in (node.status.conditions or []))
            age_s = (datetime.datetime.utcnow().replace(tzinfo=None) -
                     node.metadata.creation_timestamp.replace(tzinfo=None)).total_seconds()
            age = f"{int(age_s//86400)}d" if age_s > 86400 else f"{int(age_s//3600)}h"
            data.append({
                "name": name, "role": role,
                "cpu_pct": cpu_pct, "mem_pct": mem_pct,
                "alloc_cpu": f"{int(alloc_cpu)}m", "alloc_mem": f"{int(alloc_mem)}Mi",
                "pods": pods_on_node, "status": "Ready" if ready else "NotReady", "age": age
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pods")
def pods_route():
    if not K8S_AVAILABLE:
        return jsonify(mock_pods())
    try:
        pods        = v1.list_pod_for_all_namespaces().items
        pod_metrics = {
            f"{p['metadata']['namespace']}/{p['metadata']['name']}": p
            for p in _pod_metrics_raw()
        }
        data = []
        for pod in pods:
            key = f"{pod.metadata.namespace}/{pod.metadata.name}"
            cpu_mc = mem_mi = 0.0
            if key in pod_metrics:
                for c in pod_metrics[key].get("containers", []):
                    cpu_mc += _parse_cpu(c["usage"]["cpu"])
                    mem_mi += _parse_memory(c["usage"]["memory"])
            restarts = 0
            if pod.status.container_statuses:
                restarts = sum(cs.restart_count for cs in pod.status.container_statuses)
            age_s = (datetime.datetime.utcnow().replace(tzinfo=None) -
                     pod.metadata.creation_timestamp.replace(tzinfo=None)).total_seconds()
            age = f"{int(age_s//3600)}h" if age_s > 3600 else f"{int(age_s//60)}m"
            data.append({
                "name": pod.metadata.name, "namespace": pod.metadata.namespace,
                "cpu_mc": round(cpu_mc,1), "mem_mi": round(mem_mi,1),
                "restarts": restarts, "node": pod.spec.node_name or "—",
                "status": pod.status.phase or "Unknown", "age": age
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/hpa")
def hpa_route():
    if not K8S_AVAILABLE:
        return jsonify(mock_hpa())
    try:
        data = []
        if HPA_V2:
            hpas = autoscaling_v2.list_horizontal_pod_autoscaler_for_all_namespaces().items
            for h in hpas:
                cpu_target = cpu_current = None
                for m in (h.spec.metrics or []):
                    if m.type=="Resource" and m.resource.name=="cpu":
                        if m.resource.target.type=="Utilization":
                            cpu_target = m.resource.target.average_utilization
                for cm in (h.status.current_metrics or []):
                    if cm.type=="Resource" and cm.resource.name=="cpu":
                        cpu_current = cm.resource.current.average_utilization
                data.append({
                    "name": h.metadata.name, "namespace": h.metadata.namespace,
                    "target": h.spec.scale_target_ref.name,
                    "min_replicas": h.spec.min_replicas, "max_replicas": h.spec.max_replicas,
                    "current_replicas": h.status.current_replicas,
                    "desired_replicas": h.status.desired_replicas,
                    "cpu_target_pct": cpu_target, "cpu_current_pct": cpu_current,
                })
        else:
            hpas = autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces().items
            for h in hpas:
                data.append({
                    "name": h.metadata.name, "namespace": h.metadata.namespace,
                    "target": h.spec.scale_target_ref.name,
                    "min_replicas": h.spec.min_replicas, "max_replicas": h.spec.max_replicas,
                    "current_replicas": h.status.current_replicas,
                    "desired_replicas": h.status.desired_replicas,
                    "cpu_target_pct": h.spec.target_cpu_utilization_percentage,
                    "cpu_current_pct": h.status.current_cpu_utilization_percentage,
                })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/deployments")
def deployments_route():
    if not K8S_AVAILABLE:
        return jsonify(mock_deployments())
    try:
        deps = apps_v1.list_deployment_for_all_namespaces().items
        return jsonify([{
            "name": d.metadata.name, "namespace": d.metadata.namespace,
            "desired": d.spec.replicas, "ready": d.status.ready_replicas or 0,
            "available": d.status.available_replicas or 0,
        } for d in deps])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/timeseries")
def timeseries_route():
    return jsonify({
        "timestamps":  list(timeseries["timestamps"]),
        "cluster_cpu": list(timeseries["cluster_cpu"]),
        "cluster_mem": list(timeseries["cluster_mem"]),
        "pod_count":   list(timeseries["pod_count"]),
    })


@app.route("/api/stress-hpa", methods=["POST"])
def stress_hpa():
    if not K8S_AVAILABLE:
        return jsonify({"status": "Mock: HPA load generator started — CPU will spike in charts"})
    import subprocess
    subprocess.Popen(
        "kubectl run load-generator --image=busybox --restart=Never "
        "-- /bin/sh -c 'while true; do for i in $(seq 1 200); do wget -q -O- http://hpa-service & done; wait; done'",
        shell=True
    )
    return jsonify({"status": "HPA load generator pod started"})


@app.route("/api/stress-node", methods=["POST"])
def stress_node():
    if not K8S_AVAILABLE:
        return jsonify({"status": "Mock: Node stress started — memory pressure simulated"})
    import subprocess
    subprocess.Popen(
        "kubectl run node-stressor --image=progrium/stress --restart=Never -- --cpu 4 --timeout 300",
        shell=True
    )
    return jsonify({"status": "Node stress pod started"})


@app.route("/api/stop-stress", methods=["POST"])
def stop_stress():
    if not K8S_AVAILABLE:
        return jsonify({"status": "Mock: All stress pods deleted"})
    import subprocess
    subprocess.Popen(
        "kubectl delete pod load-generator node-stressor --ignore-not-found", shell=True
    )
    return jsonify({"status": "Stress pods deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
