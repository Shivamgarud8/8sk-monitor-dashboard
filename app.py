from flask import Flask, jsonify, render_template
import os
import psutil
from kubernetes import client, config

app = Flask(__name__)

# Load Kubernetes config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

v1 = client.CoreV1Api()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- NODES ----------------
@app.route("/nodes")
def nodes():
    nodes = v1.list_node()
    data = []

    for node in nodes.items:
        data.append({
            "name": node.metadata.name,
            "cpu_capacity": node.status.capacity.get("cpu"),
            "memory_capacity": node.status.capacity.get("memory")
        })

    return jsonify(data)

# ---------------- PODS ----------------
@app.route("/pods")
def pods():
    pods = v1.list_pod_for_all_namespaces()
    data = []

    for pod in pods.items:
        data.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name
        })

    return jsonify(data)

# ---------------- SERVICES ----------------
@app.route("/services")
def services():
    services = v1.list_service_for_all_namespaces()
    data = []

    for svc in services.items:
        data.append({
            "name": svc.metadata.name,
            "type": svc.spec.type,
            "cluster_ip": svc.spec.cluster_ip
        })

    return jsonify(data)

# ---------------- CPU + MEMORY ----------------
@app.route("/cpu")
def cpu():
    return jsonify({
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent
    })

# ---------------- HPA STRESS ----------------
@app.route("/stress-pod", methods=["POST"])
def stress_pod():
    os.system("""
kubectl run load-generator \
--image=busybox \
--restart=Never \
-- /bin/sh -c '
while true; do
  for i in $(seq 1 200); do
    wget -q -O- http://hpa-service &
  done
  wait
done'
""")
    return jsonify({"status": "HPA load started"})

# ---------------- NODE STRESS ----------------
@app.route("/stress-node", methods=["POST"])
def stress_node():
    os.system("stress --cpu 4 --timeout 300 &")
    return jsonify({"status": "Node stress started"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
