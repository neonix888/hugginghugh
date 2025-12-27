/**
 * HuggingHugh Chart Utilities
 *
 * Initializes Chart.js charts for model history visualization.
 */

// Color palette matching CSS variables
const COLORS = {
    primary: '#2563eb',
    primaryLight: 'rgba(37, 99, 235, 0.1)',
    success: '#10b981',
    successLight: 'rgba(16, 185, 129, 0.1)',
    warning: '#f59e0b',
    warningLight: 'rgba(245, 158, 11, 0.1)',
    danger: '#ef4444',
    dangerLight: 'rgba(239, 68, 68, 0.1)',
    medium: '#f97316',
    mediumLight: 'rgba(249, 115, 22, 0.1)',
    text: '#374151',
    textMuted: '#6b7280',
    border: '#e5e7eb',
    background: '#f9fafb',
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
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            titleColor: COLORS.text,
            bodyColor: COLORS.text,
            borderColor: COLORS.border,
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            titleFont: {
                weight: 'bold',
            },
        },
    },
    scales: {
        x: {
            grid: {
                display: false,
            },
            ticks: {
                color: COLORS.textMuted,
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
    gradient.addColorStop(0, COLORS.primaryLight);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

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
                pointHoverBorderColor: '#fff',
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
    gradient.addColorStop(0, COLORS.successLight);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

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
                pointHoverBorderColor: '#fff',
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
