// Connect to the socket.io server
const socket = io();

// DOM Elements
const connectionStatus = document.getElementById('connection-status');
const statusDot = document.querySelector('.pulse-dot');
const dangerBanner = document.getElementById('danger-banner');

// Gauges
const tempValue = document.getElementById('temp-value');
const tempMaxVal = document.getElementById('temp-max-val');
const tempProgress = document.getElementById('temp-gauge-progress');

const cpuValue = document.getElementById('cpu-value');
const cpuCoresCount = document.getElementById('cpu-cores-count');
const cpuProgress = document.getElementById('cpu-gauge-progress');

const ramValue = document.getElementById('ram-value');
const ramDetails = document.getElementById('ram-details');
const ramProgress = document.getElementById('ram-gauge-progress');

// System Info
const sysOs = document.getElementById('sys-os');
const sysCpu = document.getElementById('sys-cpu');
const sysHost = document.getElementById('sys-host');
const batteryRow = document.getElementById('battery-row');
const sysBattery = document.getElementById('sys-battery');
const extraPowerInfo = document.getElementById('extra-power-info');

// Dynamic Containers
const dynamicGaugesContainer = document.getElementById('dynamic-gauges-container');
const storageList = document.getElementById('storage-list');
const allSensorsList = document.getElementById('all-sensors-list');
const netDownVal = document.getElementById('net-down');
const netUpVal = document.getElementById('net-up');

// Settings
const thresholdSlider = document.getElementById('temp-threshold');
const thresholdVal = document.getElementById('threshold-val');
const notifyToggle = document.getElementById('notify-toggle');
const soundToggle = document.getElementById('sound-toggle');

// State Variables
let totalRamBytes = 0;
let maxTempSeen = 0;
let tempThreshold = parseInt(localStorage.getItem('tempThreshold')) || 75;
let notifyEnabled = localStorage.getItem('notifyEnabled') === 'true';
let soundEnabled = localStorage.getItem('soundEnabled') !== 'false'; // default true

// Web Audio API Elements
let audioCtx = null;
let lastBeepTime = 0;

// Initialize Settings Inputs
if (thresholdSlider) {
    thresholdSlider.value = tempThreshold;
    thresholdVal.textContent = `${tempThreshold}°C`;
    thresholdSlider.addEventListener('input', (e) => {
        tempThreshold = parseInt(e.target.value);
        thresholdVal.textContent = `${tempThreshold}°C`;
        localStorage.setItem('tempThreshold', tempThreshold);
        initAudioContext();
    });
}

if (notifyToggle) {
    notifyToggle.checked = notifyEnabled;
    notifyToggle.addEventListener('change', async (e) => {
        notifyEnabled = e.target.checked;
        localStorage.setItem('notifyEnabled', notifyEnabled);
        
        if (notifyEnabled && Notification.permission !== 'granted') {
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                alert("Veuillez autoriser les notifications dans votre navigateur.");
                notifyToggle.checked = false;
                notifyEnabled = false;
            }
        }
    });
}

if (soundToggle) {
    soundToggle.checked = soundEnabled;
    soundToggle.addEventListener('change', (e) => {
        soundEnabled = e.target.checked;
        localStorage.setItem('soundEnabled', soundEnabled);
        initAudioContext();
    });
}

// Enable Audio on any click to prevent browser autoplay block
document.body.addEventListener('click', () => {
  initAudioContext();
}, { once: true });

function initAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function playAlertChime() {
  if (!soundEnabled) return;
  const now = Date.now();
  if (now - lastBeepTime < 3500) return;
  lastBeepTime = now;

  try {
    initAudioContext();
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(800, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(300, audioCtx.currentTime + 0.4);
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.4);
  } catch (error) {
    console.error('Audio chime failed:', error);
  }
}

function sendDesktopNotification(currentTemp) {
  if (!notifyEnabled) return;
  if (Notification.permission === 'granted') {
    new Notification("🔥 Alerte Température CPU", {
      body: `La température du CPU a atteint ${currentTemp}°C !`,
      tag: 'thermal-alert'
    });
  }
}

// Initialize Chart.js
const ctx = document.getElementById('tempChart').getContext('2d');
const chartGradient = ctx.createLinearGradient(0, 0, 0, 250);
chartGradient.addColorStop(0, 'rgba(229, 46, 113, 0.4)');
chartGradient.addColorStop(1, 'rgba(229, 46, 113, 0.0)');

const tempChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: Array(40).fill(''),
    datasets: [{
      label: 'Température CPU (°C)',
      data: Array(40).fill(null),
      borderColor: '#ff3366',
      borderWidth: 3,
      pointRadius: 0,
      pointHoverRadius: 6,
      pointBackgroundColor: '#ff3366',
      backgroundColor: chartGradient,
      fill: true,
      tension: 0.3
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true },
      tooltip: { enabled: true }
    },
    scales: {
      x: { grid: { display: false } },
      y: { min: 25, max: 95 }
    }
  }
});

// Socket Event Handlers
socket.on('connect', () => {
  connectionStatus.textContent = "Connecté";
  statusDot.className = "pulse-dot active";
});

socket.on('disconnect', () => {
  connectionStatus.textContent = "Déconnecté. Reconnexion...";
  statusDot.className = "pulse-dot";
});

socket.on('system-static', (data) => {
  sysOs.textContent = `${data.os.distro} ${data.os.release}`;
  sysCpu.textContent = `${data.cpu.manufacturer} ${data.cpu.brand}`;
  sysHost.textContent = data.os.hostname;
  cpuCoresCount.textContent = `${data.cpu.cores} cœurs`;
});

socket.on('system-dynamic', (data) => {
  // Update CPU Load
  const cpuLoadVal = Math.round(data.cpuLoad.currentLoad);
  cpuValue.textContent = cpuLoadVal;
  updateCircularProgress(cpuProgress, cpuLoadVal, getLoadColor(cpuLoadVal));

  // Update RAM usage
  const ramPercentVal = Math.round(data.ram.percentage);
  ramValue.textContent = ramPercentVal;
  const ramUsedGB = (data.ram.used / (1024 * 1024 * 1024)).toFixed(1);
  const ramTotalGB = (data.ram.total / (1024 * 1024 * 1024)).toFixed(1);
  ramDetails.textContent = `${ramUsedGB} / ${ramTotalGB} GB`;
  updateCircularProgress(ramProgress, ramPercentVal, getLoadColor(ramPercentVal));

  // Update CPU Temperature
  const currentTemp = Math.round(data.temperature.main);
  if (currentTemp > 0) {
    tempValue.textContent = currentTemp;
    if (currentTemp > maxTempSeen) {
      maxTempSeen = currentTemp;
      tempMaxVal.textContent = `Max: ${maxTempSeen}°C`;
    }
    updateCircularProgress(tempProgress, (currentTemp / 100) * 100, getTempColor(currentTemp));
    addChartData(currentTemp);
    if (currentTemp >= tempThreshold) {
      dangerBanner.classList.remove('hidden');
      playAlertChime();
      sendDesktopNotification(currentTemp);
    } else {
      dangerBanner.classList.add('hidden');
    }
  }

  renderDynamicGauges(data);
  renderStorage(data.storage);
  netDownVal.textContent = formatSpeed(data.network.rx_sec);
  netUpVal.textContent = formatSpeed(data.network.tx_sec);
  renderThermalSensors(data.temperature);

  if (data.battery && data.battery.hasBattery) {
    batteryRow.style.display = 'flex';
    sysBattery.textContent = `${data.battery.percent}% ${data.battery.isCharging ? '(Charge)' : ''}`;
  } else {
    batteryRow.style.display = 'none';
  }
});

function renderDynamicGauges(data) {
  dynamicGaugesContainer.innerHTML = '';
  if (data.gpus && data.gpus.length > 0) {
    data.gpus.forEach(gpu => {
      const gpuItem = document.createElement('div');
      gpuItem.className = 'dynamic-item';
      const usage = gpu.utilization !== null ? gpu.utilization : 0;
      gpuItem.innerHTML = `
        <div class="item-header"><span>🎮 ${gpu.name}</span><span>${gpu.temp || '--'}°C | ${usage}%</span></div>
        <div class="item-bar-bg"><div class="item-bar-fill" style="width: ${usage}%; background: ${getLoadColor(usage)}"></div></div>
      `;
      dynamicGaugesContainer.appendChild(gpuItem);
    });
  } else {
    dynamicGaugesContainer.innerHTML = '<p class="empty-msg">Aucun GPU additionnel.</p>';
  }
}

function renderStorage(storageData) {
  storageList.innerHTML = '';
  if (storageData) {
    storageData.slice(0, 4).forEach(disk => {
      const diskItem = document.createElement('div');
      diskItem.className = 'storage-item';
      diskItem.innerHTML = `
        <div class="storage-info"><span>💽 ${disk.mount}</span><span>${disk.use.toFixed(1)}%</span></div>
        <div class="item-bar-bg"><div class="item-bar-fill" style="width: ${disk.use}%; background: ${getLoadColor(disk.use)}"></div></div>
      `;
      storageList.appendChild(diskItem);
    });
  }
}

function renderThermalSensors(tempData) {
  allSensorsList.innerHTML = '';
  if (tempData.cores) {
    tempData.cores.forEach((temp, i) => addSensorBox(`Core ${i}`, temp));
  }
  if (tempData.chips) {
    tempData.chips.forEach((temp, i) => addSensorBox(`Chip ${i}`, temp));
  }
}

function addSensorBox(label, value) {
  const box = document.createElement('div');
  box.className = 'sensor-box';
  box.innerHTML = `<span class="sensor-label">${label}</span><span class="sensor-value" style="color: ${getTempColor(value)}">${Math.round(value)}°C</span>`;
  allSensorsList.appendChild(box);
}

function updateCircularProgress(element, value, color) {
  const degrees = (value / 100) * 360;
  element.style.setProperty('--progress-color', color);
  element.style.background = `conic-gradient(${color} ${degrees}deg, rgba(255, 255, 255, 0.04) ${degrees}deg)`;
}

function getLoadColor(value) {
  if (value < 50) return '#00f0ff';
  if (value < 80) return '#ffaa00';
  return '#ff3366';
}

function getTempColor(value) {
  if (value < 55) return '#00ff88';
  if (value < 75) return '#ffaa00';
  return '#ff3366';
}

function addChartData(value) {
  const timeString = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  tempChart.data.labels.push(timeString);
  tempChart.data.datasets[0].data.push(value);
  if (tempChart.data.labels.length > 40) {
    tempChart.data.labels.shift();
    tempChart.data.datasets[0].data.shift();
  }
  tempChart.update('none');
}

function formatSpeed(bytesPerSec) {
  const kbs = bytesPerSec / 1024;
  return kbs < 1024 ? `${kbs.toFixed(1)} KB/s` : `${(kbs / 1024).toFixed(1)} MB/s`;
}
