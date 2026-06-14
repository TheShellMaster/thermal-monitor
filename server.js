import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import si from 'systeminformation';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: '*',
  }
});

const PORT = process.env.PORT || 3000;

// Serve static public folder
app.use(express.static(path.join(__dirname, 'public')));

// Cache static system info (only query once at startup)
let systemStaticInfo = null;

async function getStaticInfo() {
  if (systemStaticInfo) return systemStaticInfo;
  try {
    const [cpu, os, memLayout] = await Promise.all([
      si.cpu(),
      si.osInfo(),
      si.memLayout()
    ]);
    systemStaticInfo = {
      cpu: {
        manufacturer: cpu.manufacturer,
        brand: cpu.brand,
        speed: cpu.speed,
        cores: cpu.cores,
        physicalCores: cpu.physicalCores
      },
      os: {
        platform: os.platform,
        distro: os.distro,
        release: os.release,
        hostname: os.hostname
      },
      ram: {
        total: memLayout.reduce((acc, current) => acc + (current.size || 0), 0)
      }
    };
  } catch (error) {
    console.error('Error fetching static info:', error);
    systemStaticInfo = { cpu: {}, os: {}, ram: {} };
  }
  return systemStaticInfo;
}

// Fallback for Linux temperatures when systeminformation returns empty or invalid values
function readLinuxTemperatures() {
  try {
    const thermalPath = '/sys/class/thermal';
    if (!fs.existsSync(thermalPath)) return null;

    const files = fs.readdirSync(thermalPath);
    let maxTemp = -1;
    let mainTemp = -1;
    const cores = [];

    for (const file of files) {
      if (file.startsWith('thermal_zone')) {
        const tempFile = path.join(thermalPath, file, 'temp');
        const typeFile = path.join(thermalPath, file, 'type');
        
        if (fs.existsSync(tempFile)) {
          const rawTemp = fs.readFileSync(tempFile, 'utf8').trim();
          const tempVal = parseInt(rawTemp, 10) / 1000;
          if (isNaN(tempVal)) continue;

          let typeName = 'unknown';
          if (fs.existsSync(typeFile)) {
            typeName = fs.readFileSync(typeFile, 'utf8').trim().toLowerCase();
          }

          // Look for typical CPU core or Package temperatures first
          if (typeName.includes('cpu') || typeName.includes('x86_pkg') || mainTemp === -1) {
            mainTemp = tempVal;
          }
          cores.push(tempVal);
          if (tempVal > maxTemp) {
            maxTemp = tempVal;
          }
        }
      }
    }

    if (mainTemp !== -1) {
      return {
        main: mainTemp,
        cores: cores,
        max: maxTemp
      };
    }
  } catch (error) {
    console.debug('Linux temp fallback not available or failed:', error.message);
  }
  return null;
}

// Get dynamic statistics
async function getDynamicInfo() {
  try {
    const [mem, currentLoad, graphics, battery] = await Promise.all([
      si.mem(),
      si.currentLoad(),
      si.graphics(),
      si.battery()
    ]);

    // Retrieve CPU temperatures (try SI library first, then Linux sysfs fallback)
    let temp = await si.cpuTemperature();
    if (!temp || temp.main === -1 || temp.main === null) {
      const fallbackTemp = readLinuxTemperatures();
      if (fallbackTemp) {
        temp = fallbackTemp;
      }
    }

    // Format GPU controllers
    const gpus = (graphics.controllers || []).map(gpu => ({
      name: gpu.model || gpu.name || 'Generic GPU',
      vendor: gpu.vendor || 'Unknown',
      temp: gpu.temperatureGpu || null,
      utilization: gpu.utilizationGpu || null,
      memoryTotal: gpu.memoryTotal || null,
      memoryUsed: gpu.memoryUsed || null
    }));

    return {
      timestamp: Date.now(),
      temperature: {
        main: temp.main || 0,
        cores: temp.cores || [],
        max: temp.max || 0
      },
      cpuLoad: {
        currentLoad: currentLoad.currentLoad || 0,
        cores: (currentLoad.cpus || []).map(c => c.load)
      },
      ram: {
        total: mem.total,
        free: mem.free,
        used: mem.used,
        active: mem.active,
        percentage: (mem.used / mem.total) * 100
      },
      gpus: gpus,
      battery: {
        hasBattery: battery.hasBattery,
        isCharging: battery.isCharging,
        percent: battery.percent,
        type: battery.type
      }
    };
  } catch (error) {
    console.error('Error fetching dynamic info:', error);
    return {
      timestamp: Date.now(),
      temperature: { main: 0, cores: [], max: 0 },
      cpuLoad: { currentLoad: 0, cores: [] },
      ram: { total: 0, free: 0, used: 0, active: 0, percentage: 0 },
      gpus: [],
      battery: { hasBattery: false, isCharging: false, percent: 0, type: '' }
    };
  }
}

// Socket communication
io.on('connection', async (socket) => {
  console.log(`Client connected: ${socket.id}`);

  // Send static info immediately on connection
  const staticData = await getStaticInfo();
  socket.emit('system-static', staticData);

  // Send initial dynamic info
  const initialDynamic = await getDynamicInfo();
  socket.emit('system-dynamic', initialDynamic);
});

// Periodic broadcast (every 1.5 seconds)
setInterval(async () => {
  if (io.engine.clientsCount > 0) {
    const dynamicData = await getDynamicInfo();
    io.emit('system-dynamic', dynamicData);
  }
}, 1500);

httpServer.listen(PORT, '0.0.0.0', () => {
  console.log(`--------------------------------------------------`);
  console.log(`🔥 Thermal Monitor server is running on:`);
  console.log(`   👉 http://localhost:${PORT}`);
  console.log(`--------------------------------------------------`);
});
