// Color palette for users - vibrant colors for glass design
const COLORS = [
    '#00d4ff', '#a855f7', '#ec4899', '#10b981', '#f97316',
    '#06b6d4', '#8b5cf6', '#f43f5e', '#22c55e', '#eab308',
    '#0ea5e9', '#d946ef', '#fb7185', '#34d399', '#fbbf24'
];

// Chart instances
let positionChart = null;
let pnlChart = null;

// Animation state
let animationState = {
    running: false,
    startTime: null,
    endTime: null,
    duration: 10000,
    animationFrame: null,
    data: {},
    timeline: [],
    currentTimelineIndex: 0
};

// Initialize charts with improved styling
function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                enabled: true,
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(10, 10, 26, 0.9)',
                titleColor: 'rgba(255, 255, 255, 0.95)',
                bodyColor: 'rgba(255, 255, 255, 0.8)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
                displayColors: true,
                boxPadding: 6,
                titleFont: { weight: '600', size: 13 },
                bodyFont: { size: 12 },
                callbacks: {
                    title: function(context) {
                        if (context[0]) {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                            });
                        }
                        return '';
                    },
                    label: function(context) {
                        const value = context.parsed.y;
                        const formatted = Math.abs(value) >= 1000 
                            ? value.toLocaleString('en-US', { maximumFractionDigits: 2 })
                            : value.toFixed(4);
                        return ` ${context.dataset.label}: ${formatted}`;
                    }
                }
            }
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    displayFormats: {
                        hour: 'MMM d, HH:mm',
                        day: 'MMM d',
                        minute: 'HH:mm',
                        second: 'HH:mm:ss'
                    }
                },
                grid: { 
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: { 
                    color: 'rgba(255, 255, 255, 0.5)',
                    font: { size: 11 },
                    maxRotation: 0
                }
            },
            y: {
                grid: { 
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: { 
                    color: 'rgba(255, 255, 255, 0.5)',
                    font: { size: 11 },
                    callback: function(value) {
                        if (Math.abs(value) >= 1000000) {
                            return (value / 1000000).toFixed(1) + 'M';
                        } else if (Math.abs(value) >= 1000) {
                            return (value / 1000).toFixed(1) + 'K';
                        }
                        return value.toFixed(2);
                    }
                }
            }
        },
        interaction: {
            mode: 'index',
            axis: 'x',
            intersect: false
        },
        hover: {
            mode: 'index',
            intersect: false
        }
    };

    const positionCtx = document.getElementById('positionChart').getContext('2d');
    positionChart = new Chart(positionCtx, {
        type: 'line',
        data: { datasets: [] },
        options: { ...chartOptions }
    });

    const pnlCtx = document.getElementById('pnlChart').getContext('2d');
    pnlChart = new Chart(pnlCtx, {
        type: 'line',
        data: { datasets: [] },
        options: { ...chartOptions }
    });
}

// Parse datetime-local input to milliseconds
function parseDateTime(value) {
    if (!value) return null;
    return new Date(value).getTime();
}

// Format timestamp for display
function formatTime(ms) {
    const date = new Date(ms);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// Shorten address for display
function shortenAddress(addr) {
    return addr.slice(0, 6) + '...' + addr.slice(-4);
}

// Fetch position history for a user
async function fetchPositionHistory(user, coin, fromMs, toMs) {
    const params = new URLSearchParams({
        user,
        coin,
        fromMs: fromMs.toString(),
        toMs: toMs.toString()
    });
    
    const response = await fetch(`/v1/positions/history?${params}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch data for ${shortenAddress(user)}`);
    }
    return response.json();
}

// Update status display
function setStatus(text, state = 'idle') {
    document.getElementById('statusText').textContent = text;
    const dot = document.getElementById('statusDot');
    dot.classList.remove('running', 'error');
    if (state === 'running') dot.classList.add('running');
    if (state === 'error') dot.classList.add('error');
}

// Update progress bar
function setProgress(percent) {
    document.getElementById('progressFill').style.width = `${percent}%`;
}

// Update current time display
function setCurrentTime(ms) {
    if (ms) {
        document.getElementById('currentTime').textContent = formatTime(ms);
    } else {
        document.getElementById('currentTime').textContent = '--';
    }
}

// Build legend
function buildLegend(containerId, data) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    Object.entries(data).forEach(([address, info]) => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = `
            <div class="legend-color" style="background: ${info.color}"></div>
            <span>${shortenAddress(address)}</span>
        `;
        container.appendChild(item);
    });
}

// Merge all position events into a unified timeline
function buildUnifiedTimeline(data, startMs, endMs) {
    const allTimestamps = new Set();
    allTimestamps.add(startMs);
    
    Object.values(data).forEach(info => {
        info.positions.forEach(pos => {
            if (pos.timeMs >= startMs && pos.timeMs <= endMs) {
                allTimestamps.add(pos.timeMs);
            }
        });
    });
    
    allTimestamps.add(endMs);
    
    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b);
    const timeline = [];
    
    sortedTimestamps.forEach(ts => {
        const event = { timeMs: ts, values: {} };
        
        Object.entries(data).forEach(([address, info]) => {
            let lastPos = null;
            for (const pos of info.positions) {
                if (pos.timeMs <= ts) {
                    lastPos = pos;
                } else {
                    break;
                }
            }
            
            event.values[address] = {
                netSize: lastPos ? lastPos.netSize : 0,
                realizedPnl: lastPos ? lastPos.realizedPnl : 0
            };
        });
        
        timeline.push(event);
    });
    
    return timeline;
}

// Start visualization
async function startVisualization() {
    const startTimeInput = document.getElementById('startTime').value;
    const endTimeInput = document.getElementById('endTime').value;
    const token = document.getElementById('token').value.trim().toUpperCase();
    const duration = parseFloat(document.getElementById('duration').value) * 1000;
    const addressesText = document.getElementById('addresses').value.trim();

    if (!startTimeInput || !endTimeInput) {
        alert('Please enter start and end times');
        return;
    }
    if (!token) {
        alert('Please enter a token symbol');
        return;
    }
    if (!addressesText) {
        alert('Please enter at least one user address');
        return;
    }

    const startMs = parseDateTime(startTimeInput);
    const endMs = parseDateTime(endTimeInput);
    const addresses = addressesText.split('\n').map(a => a.trim()).filter(a => a);

    if (addresses.length === 0) {
        alert('Please enter at least one valid address');
        return;
    }

    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;

    setStatus('Fetching data...', 'running');
    setProgress(0);

    try {
        const data = {};
        for (let i = 0; i < addresses.length; i++) {
            const addr = addresses[i];
            setStatus(`Fetching ${shortenAddress(addr)}...`, 'running');
            
            const positions = await fetchPositionHistory(addr, token, startMs, endMs);
            data[addr] = {
                positions: positions,
                color: COLORS[i % COLORS.length]
            };
        }

        const timeline = buildUnifiedTimeline(data, startMs, endMs);
        
        if (timeline.length < 2) {
            throw new Error('No position data found in the specified time range');
        }

        animationState = {
            running: true,
            startTime: startMs,
            endTime: endMs,
            duration: duration,
            data: data,
            timeline: timeline,
            currentTimelineIndex: 0
        };

        buildLegend('positionLegend', data);
        buildLegend('pnlLegend', data);
        initializeChartDatasets(data);

        setStatus('Running...', 'running');
        const animationStartTime = performance.now();
        animate(animationStartTime);

    } catch (error) {
        console.error(error);
        setStatus(`Error: ${error.message}`, 'error');
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
    }
}

// Initialize chart datasets with step line for candle-like effect
function initializeChartDatasets(data) {
    positionChart.data.datasets = Object.entries(data).map(([address, info]) => ({
        label: shortenAddress(address),
        data: [],
        borderColor: info.color,
        backgroundColor: info.color + '15',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: info.color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        stepped: 'before',  // Step line for candle-like appearance
        fill: true,
        tension: 0
    }));

    pnlChart.data.datasets = Object.entries(data).map(([address, info]) => ({
        label: shortenAddress(address),
        data: [],
        borderColor: info.color,
        backgroundColor: info.color + '15',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: info.color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        stepped: 'before',  // Step line for candle-like appearance
        fill: true,
        tension: 0
    }));

    positionChart.update('none');
    pnlChart.update('none');
}

// Animation loop
function animate(animationStartTime) {
    if (!animationState.running) return;

    const now = performance.now();
    const elapsed = now - animationStartTime;
    const progress = Math.min(elapsed / animationState.duration, 1);

    const timeRange = animationState.endTime - animationState.startTime;
    const currentSimTime = animationState.startTime + (timeRange * progress);

    setProgress(progress * 100);
    setCurrentTime(currentSimTime);

    const timeline = animationState.timeline;
    const addresses = Object.keys(animationState.data);
    
    addresses.forEach((addr, idx) => {
        const posData = [];
        const pnlData = [];
        
        for (const event of timeline) {
            if (event.timeMs > currentSimTime) break;
            
            const values = event.values[addr];
            posData.push({ x: event.timeMs, y: values.netSize });
            pnlData.push({ x: event.timeMs, y: values.realizedPnl });
        }
        
        positionChart.data.datasets[idx].data = posData;
        pnlChart.data.datasets[idx].data = pnlData;
    });

    positionChart.options.scales.x.min = animationState.startTime;
    positionChart.options.scales.x.max = animationState.endTime;
    pnlChart.options.scales.x.min = animationState.startTime;
    pnlChart.options.scales.x.max = animationState.endTime;

    positionChart.update('none');
    pnlChart.update('none');

    if (progress < 1) {
        animationState.animationFrame = requestAnimationFrame(() => animate(animationStartTime));
    } else {
        setStatus('Complete', 'idle');
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        animationState.running = false;
    }
}

// Stop visualization
function stopVisualization() {
    animationState.running = false;
    if (animationState.animationFrame) {
        cancelAnimationFrame(animationState.animationFrame);
    }
    setStatus('Stopped', 'idle');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}

// Set default times: Jan 1, 2025 to Jan 1, 2026
function setDefaultTimes() {
    document.getElementById('startTime').value = '2025-12-22T00:00';
    document.getElementById('endTime').value = '2026-01-18T00:00';
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setDefaultTimes();
});
