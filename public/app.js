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
const sysRam = document.getElementById('sys-ram');
const sysHost = document.getElementById('sys-host');
const gpuRow = document.getElementById('gpu-row');
const sysGpu = document.getElementById('sys-gpu');
const batteryRow = document.getElementById('battery-row');
const sysBattery = document.getElementById('sys-battery');

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
thresholdSlider.value = tempThreshold;
thresholdVal.textContent = `${tempThreshold}°C`;
notifyToggle.checked = notifyEnabled;
soundToggle.checked = soundEnabled;

// Event Listeners for Settings
thresholdSlider.addEventListener('input', (e) => {
  tempThreshold = parseInt(e.target.value);
  thresholdVal.textContent = `${tempThreshold}°C`;
  localStorage.setItem('tempThreshold', tempThreshold);
  initAudioContext(); // Resume audio context on user interaction
});

notifyToggle.addEventListener('change', async (e) => {
  notifyEnabled = e.target.checked;
  localStorage.setItem('notifyEnabled', notifyEnabled);
  
  if (notifyEnabled && Notification.permission !== 'granted') {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      alert("Veuillez autoriser les notifications dans votre navigateur pour recevoir les alertes.");
      notifyToggle.checked = false;
      notifyEnabled = false;
      localStorage.setItem('notifyEnabled', false);
    }
  }
});

soundToggle.addEventListener('change', (e) => {
  soundEnabled = e.target.checked;
  localStorage.setItem('soundEnabled', soundEnabled);
  initAudioContext();
});

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

// Generate synthesizer alarm sound
function playAlertChime() {
  if (!soundEnabled) return;
  const now = Date.now();
  if (now - lastBeepTime < 3500) return; // Debounce alarm sound
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

// Desktop notification helper
function sendDesktopNotification(currentTemp) {
  if (!notifyEnabled) return;
  if (Notification.permission === 'granted') {
    new Notification("🔥 Alerte Température CPU", {
      body: `La température du CPU a atteint ${currentTemp}°C, dépassant le seuil de ${tempThreshold}°C !`,
      tag: 'thermal-alert',
      requireInteraction: false
    });
  }
}

// Initialize Chart.js
const ctx = document.getElementById('tempChart').getContext('2d');

// Chart styles and gradients
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
      legend: {
        display: true,
        labels: {
          color: '#8a8ab0',
          font: { family: 'Outfit', size: 12 }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(15, 15, 30, 0.95)',
        titleFont: { family: 'Outfit' },
        bodyFont: { family: 'Outfit' },
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#8a8ab0' }
      },
      y: {
        min: 25,
        max: 95,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#8a8ab0',
          callback: function(value) { return value + '°C'; }
        }
      }
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
  // OS Details
  sysOs.textContent = `${data.os.distro} ${data.os.release} (${data.os.platform})`;
  
  // CPU Model
  sysCpu.textContent = `${data.cpu.manufacturer} ${data.cpu.brand} (${data.cpu.cores} cœurs)`;
  
  // Total Memory
  totalRamBytes = data.ram.total || 0;
  if (totalRamBytes > 0) {
    const totalGB = (totalRamBytes / (1024 * 1024 * 1024)).toFixed(1);
    sysRam.textContent = `${totalGB} GB`;
  } else {
    sysRam.textContent = 'Indisponible';
  }

  // Hostname
  sysHost.textContent = data.os.hostname;

  // Set logical CPU cores text
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
    
    // Update Max Temperature Seen
    if (currentTemp > maxTempSeen) {
      maxTempSeen = currentTemp;
      tempMaxVal.textContent = `Max: ${maxTempSeen}°C`;
    }
    
    // Update Circular temperature gauge
    updateCircularProgress(tempProgress, (currentTemp / 100) * 100, getTempColor(currentTemp));

    // Append to Chart.js
    addChartData(currentTemp);

    // Thermal Alert Threshold Verification
    if (currentTemp >= tempThreshold) {
      dangerBanner.classList.remove('hidden');
      playAlertChime();
      sendDesktopNotification(currentTemp);
    } else {
      dangerBanner.classList.add('hidden');
    }
  } else {
    tempValue.textContent = '--';
  }

  // Update GPU Info if any GPU is present
  if (data.gpus && data.gpus.length > 0) {
    gpuRow.style.display = 'flex';
    const primaryGpu = data.gpus[0];
    let gpuText = `${primaryGpu.name}`;
    if (primaryGpu.temp !== null) {
      gpuText += ` (${primaryGpu.temp}°C)`;
    }
    sysGpu.textContent = gpuText;
  } else {
    gpuRow.style.display = 'none';
  }

  // Update Battery Info if present
  if (data.battery && data.battery.hasBattery) {
    batteryRow.style.display = 'flex';
    let batteryText = `${data.battery.percent}%`;
    if (data.battery.isCharging) {
      batteryText += ' (En charge)';
    } else {
      batteryText += ' (Sur batterie)';
    }
    sysBattery.textContent = batteryText;
  } else {
    batteryRow.style.display = 'none';
  }
});

// Helper functions for updating UI gauges
function updateCircularProgress(element, value, color) {
  const degrees = (value / 100) * 360;
  element.style.setProperty('--progress-color', color);
  element.style.background = `conic-gradient(${color} ${degrees}deg, rgba(255, 255, 255, 0.04) ${degrees}deg)`;
}

function getLoadColor(value) {
  if (value < 50) return 'var(--color-cyan)';
  if (value < 80) return 'var(--color-orange)';
  return 'var(--color-red)';
}

function getTempColor(value) {
  if (value < 55) return 'var(--color-green)';
  if (value < 75) return 'var(--color-orange)';
  return 'var(--color-red)';
}

// Chart.js updates
function addChartData(value) {
  const timeString = new Date().toLocaleTimeString('fr-FR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  
  tempChart.data.labels.push(timeString);
  tempChart.data.datasets[0].data.push(value);

  // Keep last 40 entries
  if (tempChart.data.labels.length > 40) {
    tempChart.data.labels.shift();
    tempChart.data.datasets[0].data.shift();
  }

  tempChart.update('none'); // Update without transition animation for better rendering speed
}
