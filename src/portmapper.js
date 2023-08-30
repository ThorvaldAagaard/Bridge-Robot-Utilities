const net = require('net');

let bcServer = null;
let bmSocket = null;
const bcPort = 2001; // BCPort
const bmPort = 2000; // BMPort
const delimiter = "\n";
const TM = "BM";

// const bcPort = 2001; // BCPort
// const bmPort = 2010; // BMPort
// const delimiter = "\r\n";
// const TM = "BC";

const timeString = () => {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    //return "";
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

function forwardData(srcSocket, destSocket, sender) {
    let buffer = Buffer.alloc(0);
    srcSocket.on('data', async data => {
        buffer = Buffer.concat([buffer, data]);

        while (true) {
            const newlineIndex = buffer.indexOf('\n');

            if (newlineIndex === -1) {
                break; // Incomplete line
            }

            const line = buffer.slice(0, newlineIndex + 1);
            buffer = buffer.slice(newlineIndex + 1);

            await processLine(line, destSocket, sender);
        }
    });
}

async function processLine(line, destSocket, sender) {
    let processedLine = line.toString('utf8').trim();

    // if (processedLine.indexOf("Heartbeat") > -1) {
    //     return;
    // }

    // if (processedLine.indexOf("Timing") > -1) {
    //     await delay(1000); // Let jack send ready first
    //     return;
    // }

    console.log(`[${timeString()}] From ${sender}      : ${processedLine}`);

    if (sender === 'BCPort') {
        // Jack
        //processedLine = processedLine.replace("version 20", "version 18");
        //console.log(`[${timeString()}] Message to send  : ${processedLine.trim() }`);
    } else {
        const words = processedLine.split(' ');

        if (TM == "BM") {

            processedLine = processedLine.replace("Dummy", "dummy").replace("of Board", "of board").replace("E/W", " E/W")
            if (processedLine.indexOf("cards") > 0) {
                processedLine = processedLine.replace(/\. /g, '.')
            }
            if (words.length > 2 && words[words.length - 1] == "seated") {
                words[1] = '("' + words[1];
                words[words.length - 2] = words[words.length - 2] + '")';
                processedLine = words.join(' ');
            }

            if (words[words.length - 2] == "plays") {
                words[words.length - 1] = words[words.length - 1].toUpperCase();
                processedLine = words.join(' ');
            }
            processedLine = processedLine.trim().replace("Passes", "passes");
            
        }

        if (processedLine.indexOf("to lead") > 0) {
            // Wait a second. Should be done by BM, but isn't or lost somewhere
            await delay(1000); // Delay of 0.1 seconds
        }
        //console.log(`[${timeString()}] Message to send  : ${processedLine.trim()}`);
    }

    const processedBuffer = Buffer.from(processedLine, 'utf8');
    await forwardToDestination(processedBuffer, destSocket);

    if (processedLine.indexOf("of session") > -1) {
        bmSocket.end();
        bcServer.close(() => {
            process.exit();
        });
    }
}

async function forwardToDestination(buffer, destSocket) {
    await delay(100); // Delay of 0.1 seconds
    console.log(`[${timeString()}] Sending to ${destSocket.remotePort == bmPort ? "TM" : "BC"}    : ${buffer}`);
    if (destSocket.remotePort == bmPort) {
        destSocket.write(buffer + delimiter);
    } else {
        destSocket.write(buffer + "\r\n");
    }
}

function handleConnection(bcConn, bmSocket) {
    const bcAddress = `${bcConn.remoteAddress}:${bcConn.remotePort}`;
    console.log(`[${timeString()}] Accepted connection from ${bcAddress}`);

    const bmAddress = `${bmSocket.remoteAddress}:${bmSocket.remotePort}`;
    console.log(`[${timeString()}] Connected to destination ${bmAddress}`);

    forwardData(bcConn, bmSocket, 'BCPort');
    forwardData(bmSocket, bcConn, 'BMPort');
}

function startMapping(bcPort, bmPort) {
    bmSocket = net.connect(bmPort, '127.0.0.1');

    bcServer = net.createServer(bcConn => {
        handleConnection(bcConn, bmSocket);
    });

    bcServer.listen(bcPort, () => {
        console.log(`[${timeString()}] Listening on port ${bcPort} (BCPort) will map to ${bmPort} (BMPort)`);
    });

    process.on('SIGINT', () => {
        console.log(`[${timeString()}] Terminating...`);
        bmSocket.end();
        bcServer.close(() => {
            process.exit();
        });
    });
}

function delay(ms) {
    //console.log("hesitating")
    return new Promise(resolve => setTimeout(resolve, ms));
}

startMapping(bcPort, bmPort);
