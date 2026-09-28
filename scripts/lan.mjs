// Prints the address to open on a phone connected to the same Wi-Fi.
import { networkInterfaces } from 'node:os';

const ips = Object.entries(networkInterfaces())
  .flatMap(([name, list]) => (list ?? []).map((i) => ({ name, ...i })))
  .filter((i) => i.family === 'IPv4' && !i.internal && !/vEthernet|VirtualBox|VMware|WSL|Docker/i.test(i.name));

if (!ips.length) console.log('No network connection found. Connect this computer to Wi-Fi first.');
for (const i of ips) console.log(`${i.name.padEnd(20)} http://${i.address}:5173`);
