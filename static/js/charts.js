/**
 * HuggingHugh Chart Utilities
 *
 * Initializes Chart.js charts for model history visualization.
 */

// Color palette matching CSS variables
const COLORS = {
    primary: '#00ff41',
    primaryLight: 'rgba(0, 255, 65, 0.15)',
    success: '#00ff41',
    successLight: 'rgba(0, 255, 65, 0.15)',
    warning: '#ffb000',
    warningLight: 'rgba(255, 176, 0, 0.15)',
    danger: '#ff3333',
    dangerLight: 'rgba(255, 51, 51, 0.15)',
    medium: '#ff8800',
    mediumLight: 'rgba(255, 136, 0, 0.15)',
    text: '#88cc88',
    textMuted: '#4a6a4a',
    border: '#1a3a1a',
    background: '#111111',
};

// Common chart options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        intersect: false,
        mode: 'index',
    },
    plugins: {
        legend: {
            display: false,
        },
        tooltip: {
            backgroundColor: 'rgba(10, 10, 10, 0.95)',
            titleColor: '#00ff41',
            bodyColor: '#88cc88',
            borderColor: '#1a3a1a',
            borderWidth: 1,
            cornerRadius: 0,
            padding: 12,
            titleFont: { family: "'JetBrains Mono', monospace", weight: 'bold' },
            bodyFont: { family: "'JetBrains Mono', monospace" },
        },
    },
    scales: {
        x: {
            grid: {
                display: false,
            },
            ticks: {
                color: COLORS.textMuted,
                font: { family: "'JetBrains Mono', monospace", size: 10 },
                maxRotation: 0,
                autoSkip: true,
                maxTicksLimit: 7,
            },
        },
        y: {
            grid: {
                color: COLORS.border,
                drawBorder: false,
            },
            ticks: {
                color: COLORS.textMuted,
                font: { family: "'JetBrains Mono', monospace", size: 10 },
            },
        },
    },
};

/**
 * Initialize trust score trend chart
 */
function initScoreChart(canvasId, historyData, timeRange = 30) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !historyData || historyData.length === 0) return null;

    // Filter data by time range
    const filteredData = filterByTimeRange(historyData, timeRange);

    const labels = filteredData.map(d => formatDate(d.scan_date));
    const scores = filteredData.map(d => d.trust_score);

    // Calculate gradient color based on score trend
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(0, 255, 65, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 255, 65, 0)');

    return new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Trust Score',
                data: scores,
                borderColor: COLORS.primary,
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: COLORS.primary,
                pointHoverBorderColor: '#0a0a0a',
                pointHoverBorderWidth: 2,
            }],
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    min: 0,
                    max: 100,
                    ticks: {
                        ...commonOptions.scales.y.ticks,
                        stepSize: 20,
                        callback: value => value + '%',
                    },
                },
            },
            plugins: {
                ...commonOptions.plugins,
                tooltip: {
                    ...commonOptions.plugins.tooltip,
                    callbacks: {
                        label: context => `Score: ${context.parsed.y}%`,
                    },
                },
            },
        },
    });
}

/**
 * Initialize vulnerability trend chart
 */
function initVulnChart(canvasId, historyData, timeRange = 30) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !historyData || historyData.length === 0) return null;

    const filteredData = filterByTimeRange(historyData, timeRange);

    const labels = filteredData.map(d => formatDate(d.scan_date));
    const critical = filteredData.map(d => d.vuln_critical || 0);
    const high = filteredData.map(d => d.vuln_high || 0);
    const total = filteredData.map(d => d.vuln_count || 0);
    const other = total.map((t, i) => Math.max(0, t - critical[i] - high[i]));

    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Critical',
                    data: critical,
                    backgroundColor: COLORS.danger,
                    borderRadius: 2,
                },
                {
                    label: 'High',
                    data: high,
                    backgroundColor: COLORS.warning,
                    borderRadius: 2,
                },
                {
                    label: 'Other',
                    data: other,
                    backgroundColor: COLORS.medium,
                    borderRadius: 2,
                },
            ],
        },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16,
                        color: COLORS.text,
                    },
                },
            },
            scales: {
                ...commonOptions.scales,
                x: {
                    ...commonOptions.scales.x,
                    stacked: true,
                },
                y: {
                    ...commonOptions.scales.y,
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        ...commonOptions.scales.y.ticks,
                        stepSize: 1,
                    },
                },
            },
        },
    });
}

/**
 * Initialize rank history chart
 */
function initRankChart(canvasId, historyData, timeRange = 30) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !historyData || historyData.length === 0) return null;

    const filteredData = filterByTimeRange(historyData, timeRange);

    const labels = filteredData.map(d => formatDate(d.scan_date));
    const ranks = filteredData.map(d => d.rank);

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(0, 255, 65, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 255, 65, 0)');

    return new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Rank',
                data: ranks,
                borderColor: COLORS.success,
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: COLORS.success,
                pointHoverBorderColor: '#0a0a0a',
                pointHoverBorderWidth: 2,
            }],
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    reverse: true, // Lower rank is better
                    beginAtZero: false,
                    ticks: {
                        ...commonOptions.scales.y.ticks,
                        callback: value => '#' + value,
                    },
                },
            },
            plugins: {
                ...commonOptions.plugins,
                tooltip: {
                    ...commonOptions.plugins.tooltip,
                    callbacks: {
                        label: context => `Rank: #${context.parsed.y}`,
                    },
                },
            },
        },
    });
}

/**
 * Filter history data by time range
 */
function filterByTimeRange(data, days) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);

    return data.filter(d => new Date(d.scan_date) >= cutoff);
}

/**
 * Format date for chart labels
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const month = date.toLocaleDateString('en-US', { month: 'short' });
    const day = date.getDate();
    return `${month} ${day}`;
}

/**
 * Update charts when time range changes
 */
function updateTimeRange(timeRange, historyData) {
    // Destroy existing charts
    Chart.getChart('scoreChart')?.destroy();
    Chart.getChart('vulnChart')?.destroy();
    Chart.getChart('rankChart')?.destroy();

    // Reinitialize with new time range
    initScoreChart('scoreChart', historyData.score_history, timeRange);
    initVulnChart('vulnChart', historyData.score_history, timeRange);

    if (historyData.rank_history && historyData.rank_history.length > 0) {
        initRankChart('rankChart', historyData.rank_history, timeRange);
    }

    // Update active button
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.range) === timeRange);
    });
}

// Export functions for use in templates
window.HuggingHughCharts = {
    initScoreChart,
    initVulnChart,
    initRankChart,
    updateTimeRange,
};
