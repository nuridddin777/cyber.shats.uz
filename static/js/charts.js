/* ============================================================
   CYBER SHATS — Admin panel grafiklari (Chart.js)
   Ma'lumotlar window.CS_ADMIN_DATA orqali shablon ichida uzatiladi.
   ============================================================ */
(function () {
    if (typeof Chart === 'undefined' || !window.CS_ADMIN_DATA) return;
    var d = window.CS_ADMIN_DATA;

    Chart.defaults.color = '#8a8a92';
    Chart.defaults.font.family = "'JetBrains Mono', monospace";

    var lineCanvas = document.getElementById('activityChart');
    if (lineCanvas) {
        new Chart(lineCanvas, {
            type: 'line',
            data: {
                labels: d.dayLabels,
                datasets: [{
                    label: 'Faol foydalanuvchilar',
                    data: d.activitySeries,
                    borderColor: '#ff3b3b',
                    backgroundColor: 'rgba(255,59,59,0.12)',
                    pointBackgroundColor: '#ff3b3b',
                    tension: 0.35,
                    fill: true,
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,59,59,0.08)' } },
                    y: { grid: { color: 'rgba(255,59,59,0.08)' }, beginAtZero: true }
                }
            }
        });
    }

    var donutCanvas = document.getElementById('sourceDonut');
    if (donutCanvas) {
        new Chart(donutCanvas, {
            type: 'doughnut',
            data: {
                labels: d.sourceLabels,
                datasets: [{
                    data: d.sourceSeries,
                    backgroundColor: ['#ff3b3b', '#b8b8c0', '#ffb238', '#8a2020'],
                    borderColor: '#0b0b0d',
                    borderWidth: 2,
                }]
            },
            options: {
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
                cutout: '68%'
            }
        });
    }
})();
