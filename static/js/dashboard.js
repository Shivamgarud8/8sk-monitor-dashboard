const ctx = document.getElementById('cpuGauge');

const gauge = new Chart(ctx, {
    type: 'doughnut',
    data: {
        datasets: [{
            data: [0, 100],
            backgroundColor: ['#22c55e', '#1e293b']
        }]
    },
    options: {
        circumference: 180,
        rotation: 270,
        cutout: '70%'
    }
});

function updateCPU() {
    fetch('/cpu')
        .then(res => res.json())
        .then(data => {
            gauge.data.datasets[0].data = [data.cpu, 100 - data.cpu];
            gauge.update();
        });
}

setInterval(updateCPU, 2000);

function stressPod() {
    fetch('/stress-pod', { method: 'POST' });
}

function stressNode() {
    fetch('/stress-node', { method: 'POST' });
}
