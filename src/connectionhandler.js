const net = require('net');
const EventEmitter = require('events');

class ConnectionHandler extends EventEmitter {

    constructor(bcPort, tmPort) {
        super();
        this.bcPort = bcPort;
        this.tmPort = tmPort;
        this.delimiter = "\n";
        this.TM = "BM";
        this.tmSocket = null;
    }

    timeString() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
        //return "";
        return `${hours}:${minutes}:${seconds}.${milliseconds}`;
    };

    handleIncommingData(srcSocket, destSocket, sender) {
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

                await this.processLine(line, destSocket, sender);
            }
        });
    }

    async processLine(line, destSocket, sender) {
        let processedLine = line.toString('utf8').trim();

        console.log(`[${this.timeString()}] From ${sender}      : ${processedLine}`);

        if (sender === 'BCPort') {
            //console.log(`[${this.timeString()}] Message to send  : ${processedLine.trim() }`);
        } else {
            const words = processedLine.split(' ');

            if (this.TM == "BM") {

                // This is needed for Blue Chip to know connection is accepted
                if (words.length > 2 && words[words.length - 1] == "seated") {
                    words[1] = '("' + words[1];
                    words[words.length - 2] = words[words.length - 2] + '")';
                    processedLine = words.join(' ');
                }

                if (processedLine.indexOf("to lead") > 0) {
                    // Wait a second. Should be done by BM, but isn't or lost somewhere
                    await this.delay(1000); // Delay of 0.1 seconds
                }
            }
        }

        const processedBuffer = Buffer.from(processedLine, 'utf8');
        await this.forwardDataToDestination(processedBuffer, destSocket);

        if (processedLine.indexOf("of session") > -1) {
            this.stop();
        }
    }

    async forwardDataToDestination(buffer, destSocket) {
        await this.delay(100); // Delay of 0.1 seconds
        console.log(`[${this.timeString()}] Sending to ${destSocket.remotePort == this.tmPort ? "TM" : "BC"}    : ${buffer}`);
        if (destSocket.remotePort == this.tmPort) {
            destSocket.write(buffer + this.delimiter);
        } else {
            destSocket.write(buffer + "\r\n");
        }
    }

    async handleBCConnection(bcConn, bmSocket) {
        const bcAddress = `${bcConn.remoteAddress}:${bcConn.remotePort}`;
        console.log(`[${this.timeString()}] Accepted connection from ${bcAddress}`);

        // Wait for the destination connection to be established
        bmSocket = await this.establishTMSocket();

        // Listen for the 'close' event on the client socket
        bcConn.on('close', () => {
            console.log(`[${this.timeString()}] Client disconnected`);

            // Implement cleanup logic or notification as needed

            // Close the bmSocket if needed
            if (bmSocket) {
                bmSocket.end();
            }

            // Emit the 'completed' event to indicate the handler is done
            this.emit('completed');
        });

        bcConn.on('error', error => {
            console.error(`[${this.timeString()}] Error in bcConn:`, error);
            // You can take appropriate actions here, such as logging the error or closing the socket.
        });

        this.handleIncommingData(bcConn, bmSocket, 'BCPort');
        this.handleIncommingData(bmSocket, bcConn, 'BMPort'); // Forward data to the opposite direction
    }

    async establishTMSocket() {
        return new Promise(resolve => {
            const bmSocket = net.connect(this.tmPort, '127.0.0.1', () => {
                resolve(bmSocket); // Resolve the promise once the connection is established
            });
        });
    }
    async waitForData(socket) {
        return new Promise(resolve => {
            socket.once('data', () => {
                resolve();
            });
        });
    }

    async startMapping(bcPort, bmPort) {
        this.bcServer = net.createServer(bcConn => {
            this.handleBCConnection(bcConn, this.tmSocket);
        });

        this.bcServer.listen(bcPort, () => {
            console.log(`[${this.timeString()}] Listening on port ${bcPort} (BCPort)`);
        });

    }

    delay(ms) {
        //console.log("hesitating")
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    start() {
        this.startMapping(this.bcPort, this.tmPort);
    }

    stop() {
        if (this.tmSocket) {
            this.tmSocket.end();
        }
        this.bcServer.close();
        this.emit('completed');
    }
}

function createConnectionHandler(bcPort, bmPort) {
    return new ConnectionHandler(bcPort, bmPort);
}

module.exports = createConnectionHandler;
