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

// Build timeline with equal interval snapshots
function buildUnifiedTimeline(data, startMs, endMs) {
    // Create snapshots at equal intervals (e.g., every 1% of time range)
    const numSnapshots = 75; // Number of snapshots for smooth animation
    const timeRange = endMs - startMs;
    const interval = timeRange / (numSnapshots - 1);
    
    const timeline = [];
    
    for (let i = 0; i < numSnapshots; i++) {
        const ts = startMs + (interval * i);
        const event = { timeMs: ts, values: {} };
        
        Object.entries(data).forEach(([address, info]) => {
            // Find the most recent position at or before this timestamp
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
    }
    
    // Ensure last snapshot matches closest position to end time
    Object.entries(data).forEach(([address, info]) => {
        let closestPos = null;
        let minDiff = Infinity;
        
        info.positions.forEach(pos => {
            const diff = Math.abs(pos.timeMs - endMs);
            if (diff < minDiff && pos.timeMs <= endMs) {
                minDiff = diff;
                closestPos = pos;
            }
        });
        
        if (closestPos && timeline.length > 0) {
            timeline[timeline.length - 1].values[address] = {
                netSize: closestPos.netSize,
                realizedPnl: closestPos.realizedPnl
            };
        }
    });
    
    return timeline;
}

// Calculate predetermined scales for Y axes
function calculateScales(timeline) {
    let minPosition = Infinity;
    let maxPosition = -Infinity;
    let minPnl = Infinity;
    let maxPnl = -Infinity;
    
    timeline.forEach(event => {
        Object.values(event.values).forEach(values => {
            minPosition = Math.min(minPosition, values.netSize);
            maxPosition = Math.max(maxPosition, values.netSize);
            minPnl = Math.min(minPnl, values.realizedPnl);
            maxPnl = Math.max(maxPnl, values.realizedPnl);
        });
    });
    
    // Add 10% padding
    const positionPadding = Math.abs(maxPosition - minPosition) * 0.1;
    const pnlPadding = Math.abs(maxPnl - minPnl) * 0.1;
    
    return {
        position: {
            min: minPosition - positionPadding,
            max: maxPosition + positionPadding
        },
        pnl: {
            min: minPnl - pnlPadding,
            max: maxPnl + pnlPadding
        }
    };
}

// Clear error for a specific field
function clearError(fieldId) {
    const errorElement = document.getElementById(fieldId + '-error');
    if (errorElement) {
        errorElement.textContent = '';
    }
}

// Show error for a specific field
function showError(fieldId, message) {
    const errorElement = document.getElementById(fieldId + '-error');
    if (errorElement) {
        errorElement.textContent = message;
    }
}

// Clear all errors
function clearAllErrors() {
    ['startTime', 'endTime', 'token', 'duration', 'addresses'].forEach(clearError);
}

// Start visualization
async function startVisualization() {
    clearAllErrors();
    
    const startTimeInput = document.getElementById('startTime').value;
    const endTimeInput = document.getElementById('endTime').value;
    const token = document.getElementById('token').value.trim().toUpperCase();
    const duration = parseFloat(document.getElementById('duration').value) * 1000;
    const addressesText = document.getElementById('addresses').value.trim();

    // Validation
    let hasError = false;
    
    if (!startTimeInput) {
        showError('startTime', 'Start time is required');
        hasError = true;
    }
    if (!endTimeInput) {
        showError('endTime', 'End time is required');
        hasError = true;
    }
    if (!token) {
        showError('token', 'Token symbol is required');
        hasError = true;
    }
    if (!addressesText) {
        showError('addresses', 'At least one address is required');
        hasError = true;
    }
    
    if (hasError) return;

    const startMs = parseDateTime(startTimeInput);
    const endMs = parseDateTime(endTimeInput);
    const addresses = addressesText.split('\n').map(a => a.trim()).filter(a => a);

    if (addresses.length === 0) {
        showError('addresses', 'Please enter at least one valid address');
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
        const scales = calculateScales(timeline);

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
            scales: scales,
            currentTimelineIndex: 0
        };

        buildLegend('positionLegend', data);
        buildLegend('pnlLegend', data);
        initializeChartDatasets(data);

        // Fetch leaderboard data while animation is starting
        fetchLeaderboard();

        setStatus('Running...', 'running');
        const animationStartTime = performance.now();
        animate(animationStartTime);

    } catch (error) {
        console.error(error);
        setStatus(`Error: ${error.message}`, 'error');
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        
        // Show error based on context
        if (error.message.includes('Failed to fetch data')) {
            showError('addresses', 'Failed to fetch data for one or more addresses');
        }
    }
}

// Initialize chart datasets with smooth curves
function initializeChartDatasets(data) {
    positionChart.data.datasets = Object.entries(data).map(([address, info]) => ({
        label: shortenAddress(address),
        data: [],
        borderColor: info.color,
        backgroundColor: info.color + '15',
        borderWidth: 2.5,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: info.color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        fill: true,
        tension: 0.4,  // Smooth cubic curves
        cubicInterpolationMode: 'monotone'
    }));

    pnlChart.data.datasets = Object.entries(data).map(([address, info]) => ({
        label: shortenAddress(address),
        data: [],
        borderColor: info.color,
        backgroundColor: info.color + '15',
        borderWidth: 2.5,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: info.color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        fill: true,
        tension: 0.4,  // Smooth cubic curves
        cubicInterpolationMode: 'monotone'
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
    positionChart.options.scales.y.min = animationState.scales.position.min;
    positionChart.options.scales.y.max = animationState.scales.position.max;
    
    pnlChart.options.scales.x.min = animationState.startTime;
    pnlChart.options.scales.x.max = animationState.endTime;
    pnlChart.options.scales.y.min = animationState.scales.pnl.min;
    pnlChart.options.scales.y.max = animationState.scales.pnl.max;

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

// Leaderboard data
let leaderboardData = [];
let currentSortMetric = 'pnl';

// Fetch leaderboard from API
async function fetchLeaderboard() {
    if (!animationState.data || Object.keys(animationState.data).length === 0) return;
    
    try {
        setStatus('Loading leaderboard...', 'running');
        
        const addresses = Object.keys(animationState.data).join(',');
        const token = document.getElementById('token').value.trim().toUpperCase();
        const startMs = animationState.startTime;
        const endMs = animationState.endTime;
        
        const params = new URLSearchParams({
            users: addresses,
            coin: token,
            fromMs: startMs.toString(),
            toMs: endMs.toString()
        });
        
        const response = await fetch(`/v1/leaderboard/combined?${params}`);
        if (!response.ok) {
            throw new Error('Failed to fetch leaderboard data');
        }
        
        leaderboardData = await response.json();
        displayLeaderboard(currentSortMetric);
        document.getElementById('leaderboardContainer').style.display = 'block';
        setStatus('Complete', 'idle');
        
    } catch (error) {
        console.error('Leaderboard error:', error);
        setStatus('Complete (leaderboard unavailable)', 'idle');
    }
}

// Format number for display
function formatNumber(num, decimals = 2) {
    if (Math.abs(num) >= 1000000) {
        return (num / 1000000).toFixed(decimals) + 'M';
    } else if (Math.abs(num) >= 1000) {
        return (num / 1000).toFixed(decimals) + 'K';
    }
    return num.toFixed(decimals);
}

// Display leaderboard
function displayLeaderboard(sortBy = 'pnl') {
    currentSortMetric = sortBy;
    
    // Sort data
    const sorted = [...leaderboardData].sort((a, b) => {
        const valA = a[sortBy];
        const valB = b[sortBy];
        return valB - valA; // Descending order
    });
    
    // Update UI
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    
    sorted.forEach((entry, index) => {
        const row = document.createElement('tr');
        
        const pnlClass = entry.pnl > 0 ? 'positive' : entry.pnl < 0 ? 'negative' : '';
        const returnClass = entry.returnPct > 0 ? 'positive' : entry.returnPct < 0 ? 'negative' : '';
        
        row.innerHTML = `
            <td class="rank-cell">${index + 1}</td>
            <td class="address-cell">${shortenAddress(entry.user)}</td>
            <td class="text-right ${pnlClass}">${formatNumber(entry.pnl)}</td>
            <td class="text-right">${formatNumber(entry.volume)}</td>
            <td class="text-right ${returnClass}">${entry.returnPct.toFixed(2)}%</td>
            <td class="text-right">${entry.tradeCount}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Update active button
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.sort === sortBy) {
            btn.classList.add('active');
        }
    });
}

// Sort leaderboard
function sortLeaderboard(metric) {
    displayLeaderboard(metric);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setDefaultTimes();
});
