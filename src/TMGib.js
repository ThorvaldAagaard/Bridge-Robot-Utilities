// (?-s)Response\K.*$

const { spawn } = require('child_process');
const net = require('net');
const util = require('util');
const fs = require('fs');
const minimist = require('minimist');
const processFinder = require('./processFinder');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// This is the protocol definition but Bridge Moniteur expects only \n and will fail when GIB is dummy
let messageTerminator = "\r\n"
let GIBCommand = "";
let receivedDataFromTM = '';
let receivedDataFromGib = '';
let isProcessingLine = false;
let commandHistory = [];
let bidding = [];
let plays = [];
let declarer = null;
let contract = null;
let playstarted = false;
let trumpSuit = "N";
let initialWaitTime = 200;
let weDeclare = false;
let weMustLead = false;
let weAreDummy = false;
let trickWinner = "";
let trick = 0;
let teamsSent = false;
let biddingOver = false;
const client = new net.Socket();

const directions = ["North", "East", "South", "West"];

// Create an object to hold the gibProcess reference
const processHolder = {
    gibBackgroundProcess: null,
    GibHandler: null
};

let seating;
let match;
const cardValues = '23456789TJQKA';
const suitOrder = 'SHDC';

function printTrick() {
    if (trickWinner) {
        console.log(`[${timeString()}] Winner of trick ${trick}: ${trickWinner}`);
        trickWinner = "";
    }
}

function determineTrickWinner(plays, trumpSuit = 'N') {
    const cardValues = '23456789TJQKA';

    const trick = plays.map(play => play.split(' '));

    // Filter plays with the trump suit
    const trumpPlays = trick.filter(play => {
        return play[2][1] === trumpSuit;
    });

    if (trumpPlays.length > 0) {
        // Sort the plays based on card values
        trumpPlays.sort((a, b) => cardValues.indexOf(b[2][0]) - cardValues.indexOf(a[2][0]));
        return `${trumpPlays[0][0]}`;
    }

    // Filter plays with the same suit as the first play
    const ledSuit = trick[0][2][1];
    const ledSuitPlays = trick.filter(play => play[2][1] === ledSuit);

    if (ledSuitPlays.length > 0) {
        // Sort the plays based on card values
        ledSuitPlays.sort((a, b) => cardValues.indexOf(b[2][0]) - cardValues.indexOf(a[2][0]));
        return `${ledSuitPlays[0][0]}`;
    }

    // No plays with the trump suit or led suit, return the first play
    return `${trick[0][0]}`;
}

const findPartner = (direction) => {
    const index = directions.indexOf(direction);
    if (index !== -1) {
        const rhoIndex = (index + 2) % 4; // Calculate the index of Partner
        return directions[rhoIndex];
    }
    return null; // Direction not found
};

const findRHO = (direction) => {
    const index = directions.indexOf(direction);
    if (index !== -1) {
        const rhoIndex = (index + 3) % 4; // Calculate the index of RHO
        return directions[rhoIndex];
    }
    return null; // Direction not found
};

// Create an object to store the parameters and their values
const parameters = {
    name: "GIB",
    ip: "127.0.0.1",
    port: 2000,
    timing: 0,
    bidding: false,
    delay: 100,
    gibdir: "./GIB",
    verbose: false,
    simdecl: 50,
    simdef: 50,
    oppquality: 0.5,
    auctcont: 0.55,
    speed: 500,
    gibson: 10,
};

const timeString = () => {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

function biddingOverAndWeMustLead(command) {
    if (command.toLowerCase().indexOf("passes") < 0) {
        return false;
    }
    if (weMustLead) {
        let lastTwoPasses = bidding.slice(-2);
        return lastTwoPasses.every(item => item.toLowerCase().includes("passes"));
    } else {
        return false;
    }
}

const waitForResponse = async (command, initialWait, maxWaitTime) => {

    await new Promise((resolve) => {
        setTimeout(resolve, initialWait);
    });

    let responsePromiseResolved = false;

    return new Promise((resolve, reject) => {
        const checkResponseInterval = 500; // Interval to check for response (1 second)
        const maxIterations = Math.floor(maxWaitTime / checkResponseInterval);
        let iterations = 0;

        const checkResponse = async () => {
            if (responsePromiseResolved) {
                return; // Response already received
            }
            if (receivedDataFromGib) {
                responsePromiseResolved = true; // Set the flag
                const data = receivedDataFromGib;
                receivedDataFromGib = "";
                resolve(data);
            } else if (iterations >= maxIterations) {
                for (let bid of bidding) {
                    console.log(bid)
                }
                await saveCommandHistory(true);
                console.log('Timeout waiting ' + maxWaitTime + ' seconds for response to ' + command);
                console.error('Press Enter to exit...');

                rl.question('', () => {
                });
                process.exit();
                //resolve("")
            } else {
                iterations++;
                setTimeout(checkResponse, checkResponseInterval);
            }
        };

        setTimeout(checkResponse, checkResponseInterval);

        const responsePromise = new Promise((resolve) => {
            if (receivedDataFromGib) {
                resolve(receivedDataFromGib);
            }
        });

        Promise.race([responsePromise])
            .then((data) => {
                // This should only be reached if responsePromise resolves first
                responsePromiseResolved = true; // Set the flag
                if (data === receivedDataFromGib) {
                    receivedDataFromGib = "";
                } else {
                    const count = Math.abs(receivedDataFromGib.length - data.length);
                    receivedDataFromGib = receivedDataFromGib.slice(-count);
                }
                resolve(data);
            })
            .catch((error) => {
                // Handle the rejection here, e.g., log the error
                console.log(`[${timeString()}] ${error.message}`);
                resolve(""); // Resolve with a default value
            });
    });
};

function isContract(bid) {
    const suits = ['C', 'D', 'H', 'S', 'N'];
    return suits.includes(bid.slice(-1));
}

function getContract() {
    let contract = null;
    let doubled = false;
    let redoubled = false;
    let lastBidIndex = null;

    for (let i = bidding.length - 1; i >= 0; i--) {
        const bid = bidding[i];
        if (isContract(bid)) {
            contract = bid.substr(-2);
            lastBidIndex = i;
            break;
        }
        if (bid.endsWith("doubles")) {
            doubled = true;
        }
        if (bid.endsWith("redoubles")) {
            redoubled = true;
        }
    }

    if (contract === null) {
        declarer = "";
        return "Passed out";
    }

    for (let i = 0; i <= lastBidIndex; i++) {
        const bid = bidding[i];
        if (!isContract(bid)) {
            continue;
        }
        if ((i + lastBidIndex) % 2 !== 0) {
            continue;
        }
        if (bid.substr(-2)[1] !== contract[1]) {
            continue;
        }
        declarer = bid.split(' ')[0]
        break;
    }

    const xx = (!doubled) ? '' : (redoubled) ? 'XX' : 'X';

    return contract + xx + declarer.charAt(0);
}

const passOrBidRegex = /(North|East|South|West) (doubles|redoubles|Passes|passes|bids .+?(?=\n|$))/;

const playRegex = /(North|East|South|West) (plays) [2-9TJQKA][SHDC]$/i;

function recordBidding(line) {
    if (!biddingOver && passOrBidRegex.test(line)) {
        bidding.push(line.replace('NT', 'N').split(' ').slice(0, 3).join(' '));
        if (bidding.length > 3) {
            let lastThreePasses = bidding.slice(-3);
            biddingOver = lastThreePasses.every(item => item.toLowerCase().includes("passes"));
            if (biddingOver) {
                contract = getContract();
                trumpSuit = contract.charAt(1);

                if (declarer == parameters.seat) {
                    weDeclare = true;
                }
                if (declarer == findRHO(parameters.seat)) {
                    weMustLead = true
                }
                if (declarer == findPartner(parameters.seat)) {
                    weAreDummy = true
                }
                console.log(`[${timeString()}] *** Playing ${contract}${weDeclare ? ` We Declare` : ""}${weMustLead ? ` We Must Lead` : ""}${weAreDummy ? ` We Are Dummy` : ""}  ${trumpSuit == "N" ? "No Trump" : `Trump ${trumpSuit}`} ***`);
            };
        }
    } else {
        //console.log("Not matched ",line)
    }
}

// Seems like WBridge is using lower letters
function capitalizeLastTwo(inputString) {
    if (inputString.length >= 2) {
        const lastTwo = inputString.slice(-2); // Get the last two characters
        const capitalizedLastTwo = lastTwo.toUpperCase(); // Capitalize them

        // Replace the original last two characters with the capitalized ones
        const modifiedString = inputString.slice(0, -2) + capitalizedLastTwo;
        return modifiedString;
    }
    return inputString; // Return the original string if it's too short
}

function recordPlay(line) {
    if (biddingOver && playRegex.test(line)) {
        plays.push(capitalizeLastTwo(line));
        if (plays.length % 4 == 0) {
            trickWinner = determineTrickWinner(plays.slice(-4), trumpSuit);
            trick = plays.length / 4
            if (parameters.verbose)
                console.log(`Winner of trick ${trick}: ${trickWinner}`);

        }
    }
}

function recordCommand(command, receivedDataFromGib) {
    commandHistory.push({
        command: command,
        response: receivedDataFromGib.replace(/\n/g, "[NEWLINE]").replace(/\r/g, "[CR]")
    });
}

async function saveCommandHistory(error) {
    // Write command history to a file based on the board number
    if (parameters.verbose || error) {
        if (commandHistory.length > 4) {
            const regex = /^(.*?)\s+seated/;
            let match = commandHistory[1].command.match(regex);
            let player = "";
            if (match) {
                player = match[1];
            }
            const boardNumberRegex = /Board number (\d+)\. Dealer (\w+)\./;
            match = commandHistory[4].command.match(boardNumberRegex);
            let boardNumber = 0;
            let dealer = "None";
            if (match) {
                boardNumber = match[1]; // The captured board number
                dealer = match[2];
            }

            let filename = `Command history ${player} - ${boardNumber} - ${dealer}.txt`;

            // Replace invalid characters with underscores
            filename = filename.replace(/[^a-zA-Z0-9 _.-]/g, "_");

            const historyContent = commandHistory.map(entry => {
                return `Command: ${entry.command} Response: ${entry.response}`;
            }).join('\n');

            // Directory where the file should be saved
            const directory = './Logs';

            // Create the directory if it doesn't exist
            if (!fs.existsSync(directory)) {
                fs.mkdirSync(directory);
            }

            await fs.writeFileSync(directory + "/" + filename, historyContent);

            console.log(`[${timeString()}] Command history written to ${filename}`);
        }

        console.log(bidding);
    }
    commandHistory = [];
    bidding = [];
    plays = [];
    declarer = null;
    contract = null;
    weDeclare = false;
    weMustLead = false;
    weAreDummy = false;
    biddingOver = false;
}


async function startGibProcess(command, args, gibdir) {

    teamsSent = false;
    console.log(`[${timeString()}] Loading: "${path.join(gibdir, command)}"`);
    // Spawn the command-line program
    processHolder.gibBackgroundProcess = spawn(command, args, {
        stdio: ['pipe', 'pipe', 'pipe'], // Create pipes for stdin, stdout, and stderr
        cwd: gibdir
    });

    processHolder.gibBackgroundProcess.on('error', (error) => {
        console.error(`[${timeString()}] Bridge.exe not found in ${gibdir}`);
        console.error('Press Enter to exit...');

        rl.question('', () => {
        });
        process.exit();

    });

    // Capture the output from stdout
    processHolder.gibBackgroundProcess.stdout.on('data', (data) => {
        receivedDataFromGib += data.toString().replace('\r\r', '\r');
    });

    // Capture the output from stderr
    processHolder.gibBackgroundProcess.stderr.on('data', (data) => {
        console.error('Error:', data.toString());
    });

    // Handle process exit
    processHolder.gibBackgroundProcess.on('close', async (code) => {
        //console.log(receivedDataFromTM)
        // When the last card is played GIB closed down, so we try to record the last command
        if (receivedDataFromGib) {
            recordCommand(command, receivedDataFromGib)
        }
        console.log(`[${timeString()}] Gib closed`);

    });


    // Handle process exit
    processHolder.gibBackgroundProcess.on('exit', async (code) => {
        printTrick();
        console.log(`[${timeString()}] GIB exited ${code}`);
    });

    const sendCommand = async (command, noResp, ignoreResp) => {

        if (processHolder.gibBackgroundProcess.killed) {
            console.log(`[${timeString()}] Process has been terminated. Cannot send command.`);
            return null; // Return null or some indication that the command was not sent
        }
        if (command.startsWith("Timing")) {
            // This is printed when comming from TM
            // console.log(`[${timeString()}] ${command}`);
            return null;
        }
        if (command.startsWith("Feasability")) {
            // This is printed when comming from TM
            // console.log(`[${timeString()}] ${command}`);
            return null;
        }
        if (command.startsWith("Client")) {
            // This is printed when comming from TM
            // console.log(`[${timeString()}] ${command}`);
            return null;
        }
        if (command.startsWith("Book")) {
            // This is printed when comming from TM
            // console.log(`[${timeString()}] ${command}`);
            return null;
        }
        if (command.startsWith("CC")) {
            // This is printed when comming from TM
            // console.log(`[${timeString()}] ${command}`);
            return null;
        }

        if (command.endsWith("seated")) {
            // Save for restarting GIB
            seating = command;
            if (!command.includes("(")) {
                // We are now using Bridge Moniteur
                messageTerminator = "\n"
            }
        }

        if (command.startsWith("Board")) {
            //console.log("Starts with board")
            // In the protocol this should be responded with "[Hand] ready for deal" 
            // But this is not implemented in GIB
            // STarting a new board
            bidding = [];
            plays = [];
            playstarted = false;
            declarer = null;
            contract = null;
            weDeclare = false;
            weMustLead = false;
            weAreDummy = false;
            biddingOver = false;

            noResp = true;
        }

        if (biddingOverAndWeMustLead(command)) {
            if (parameters.verbose)
                console.log(`Bidding over and we must lead. Command was ${command}`)
            noResp = true;
        }

        if (!weAreDummy) {
            if (weDeclare) {
                if (command.indexOf("plays") > -1) {
                    if (plays.length % 4 == 0) {
                        // if we are to lead at next trick we should not expect a response from GIB                    
                        console.log(`[${timeString()}] We are on lead as declarer`)
                        noResp = true;
                    }
                }
            } else {
                if (command.indexOf("plays") > -1) {
                    if (plays.length % 4 == 0) {
                        // If we won the trick we do not get a response from GIB, that is just waiting for message from TM
                        if (trickWinner == parameters.seat) {
                            console.log(`[${timeString()}] We are on lead`)
                            noResp = true;
                        }
                    }
                }
            }
        }

        if (parameters.verbose)
            console.log(`[${timeString()}] Sending to gib: ${command}${ignoreResp ? ' Ignoring response' : ''} ${noResp ? '(no response expected)' : ''}`);
        else
            console.log(`[${timeString()}] Sending to gib: ${command}`);

        if (receivedDataFromGib && parameters.verbose) {
            console.log("Unprocessed  Data from GIB: ", receivedDataFromGib)
        }

        processHolder.gibBackgroundProcess.stdin.write(command + "\n");

        if (command.startsWith("Board")) {
            // In the protocol this should be responded with "[Hand] ready for deal" 
            // But this is not implemented in GIB
            recordCommand(command, `${parameters.seat} ready for cards`);
            playstarted = true;
            return `${parameters.seat} ready for cards`
        }

        if (command.endsWith("End of session")) {
            await saveCommandHistory();
            processHolder.gibBackgroundProcess.kill();
            console.error('Press Enter to exit...');

            rl.question('', () => {
            });
            process.exit();
        }
        if (noResp) {
            recordCommand(command, "N/A");
            return ""
        }
        return new Promise(async (resolve) => {

            const maxWaitTime = weDeclare ? 600000 : weMustLead ? 600000 : 300000;

            // After command.startsWith("Dummy's cards") we should return 3 lines
            // and GIB has some delay between the lines. 
            // Blue Chip is writing i lowercase
            if (command.toLowerCase().startsWith("dummy's cards")) {
                let response = await waitForResponse(command, initialWaitTime, maxWaitTime);

                if (weDeclare) {
                    let occurrences = (response.match(/\n/g) || []).length;
                    while (occurrences < 3) {
                        if (parameters.verbose) {
                            console.log("Waiting for last part of declarer response");
                        }
                        response += await waitForResponse(command, initialWaitTime, maxWaitTime);
                        occurrences = (response.match(/\n/g) || []).length;
                    }
                }

                console.log(`[${timeString()}] Gib responded: ${response.replace(/\r\n|\n/g, '\n' + ' '.repeat(30))}`);
                recordCommand(command, response);
                resolve(response);
            }
            else {
                initialWaitTime = 200;
                const response = await waitForResponse(command, initialWaitTime, maxWaitTime);
                if (ignoreResp) {
                    resolve(null);
                    recordCommand(command, response + "(Ignored)");
                    console.log(`[${timeString()}] Gib responded: ${response.replace(/\r\n|\n/g, ' ignored\n' + ' '.repeat(30))}`);
                } else {
                    recordCommand(command, response);
                    console.log(`[${timeString()}] Gib responded: ${response.replace(/\r\n|\n/g, '\n' + ' '.repeat(30))}`);
                    resolve(response);
                }
            };

        });
    };

    return {
        sendCommand: sendCommand,
        close: () => {
            processHolder.gibBackgroundProcess.stdin.end(); // Close the stdin stream to allow process termination
        }
    };
}

function waitDelay(delay) {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve();
        }, delay);
    });
}

// Dummy to lead is sent without crlf - seems also to be the same for declarer to lead

async function processLines() {

    while (!isProcessingLine && (receivedDataFromTM.includes('\r\n') || receivedDataFromTM.includes('\n') || receivedDataFromTM.endsWith('.') || receivedDataFromTM == "Dummy to lead" || receivedDataFromTM == `${parameters.seat} to lead`) || receivedDataFromTM == "Start of Board") {
        isProcessingLine = true;
        let line = receivedDataFromTM;
        let indexOfNewline = receivedDataFromTM.indexOf('\r\n');
        if (indexOfNewline < 0) {
            indexOfNewline = receivedDataFromTM.indexOf('\n');
            if (indexOfNewline > 0) {
                line = receivedDataFromTM.substring(0, indexOfNewline).trim();
                receivedDataFromTM = receivedDataFromTM.slice(indexOfNewline + 1).trim();
            } else {
                receivedDataFromTM = "";

            }
        } else {
            line = receivedDataFromTM.substring(0, indexOfNewline).trim();
            // Remove the processed line from receivedData
            receivedDataFromTM = receivedDataFromTM.slice(indexOfNewline + 2).trim();
        }

        console.log(`[${timeString()}] Received from Table Manager: ${line}`);
        if (playstarted && line.toLowerCase() === "start of board") {
            await saveCommandHistory(false);
            console.log(`[${timeString()}] TM is starting a new board`);
            // This should work but isn't, so we have to kill the process to restart
            await processHolder.GibHandler.sendCommand(`-x`, true, false);
            const processes = await processFinder.getProcessesByName("bridge.exe");
            for (let p of processes) {
                if (p.CommandLine == 'bridge.exe ' + parameters.seat + "X") {
                    processFinder.killProcessById(p.ProcessId)
                    console.log(`[${timeString()}] GIB terminated because of new deal received`);
                }
            }
            processHolder.GibHandler = null;
        }
        if (processHolder.GibHandler == null && line != "End of session") {
            console.log(`[${timeString()}] Restarting the process...`);
            processHolder.GibHandler = await startGibProcess('bridge.exe', [parameters.seat + parameters.port], parameters.gibdir);
            await waitDelay(1000);
            receivedDataFromGib = "";
            console.log(`[${timeString()}] Started GIB. ${receivedDataFromGib.split('\n')[0]}`)
            await processHolder.GibHandler.sendCommand(GIBCommand, true, false);
            await waitDelay(parameters.delay);
            // Send seating and match details using the new gibProcess instance
            await processHolder.GibHandler.sendCommand(seating, false, true);
            await processHolder.GibHandler.sendCommand(match, false, true);
        }

        if (processHolder.GibHandler != null) {
            // Send the received data from the Table Manager to GIB


            // TM did send the same Start twice, 
            if (line == "Start of BoardStart of Board") {
                console.log("Start received twice");
                line = "Start of Board"
            }

            // There is an issue, when restarting a match as TM will send the Teams infor twice
            if (line.startsWith("Teams") && teamsSent) {
                // We allready told GIB it is teams, so just responding TM
                line = `${parameters.seat} ready to start`;
                console.log(`[${timeString()}] Sending to Table Manager: ${line}`);
                client.write(line + messageTerminator);
                // Give TM time to process before sending next message
                await waitDelay(parameters.delay);

            } else {
                if (line.startsWith("Teams")) {
                    // Save the match name for restart of the gibProcess
                    match = line;
                    teamsSent = true;
                }

                recordBidding(line);
                recordPlay(line);
                let output = await processHolder.GibHandler.sendCommand(line, false, false);
                printTrick();
                await waitDelay(parameters.delay);

                // Send the output back to the Table Manager
                // In a previous version of the protocol, players confirmed receipt of dummy's hand by sending to the 
                // Table Manager "[Player] received dummy".  That requirement has now been removed from the protocol. 
                // So perhaps that should be filtered
                if (output != null) {
                    const lines = output.split('\r\n');
                    for (const line of lines) {
                        //console.log("line:"+line)
                        if (line != "") {
                            if (line.startsWith("Hand over")) {
                                await saveCommandHistory(false)
                                if (parameters.verbose)
                                    console.log("Unprocessed Data From TM: ", receivedDataFromTM);
                            } else {
                                console.log(`[${timeString()}] Sending to Table Manager: ${line}`);
                                recordBidding(line);
                                recordPlay(line);
                                printTrick();
                                client.write(line + messageTerminator);
                                // Give TM time to process before sending next message
                                await waitDelay(parameters.delay);
                            }
                        }

                    }
                }
            }


            if (receivedDataFromGib) {
                if (parameters.verbose) {
                    console.log("Unprocessed Data from GIB: " + receivedDataFromGib);
                }
                const lines = receivedDataFromGib.split('\r\n');
                receivedDataFromGib = "";
                for (const line of lines) {
                    //console.log("line:"+line)
                    if (line != "") {
                        if (line.startsWith("Hand over")) {
                            await saveCommandHistory(false)
                            console.log(receivedDataFromTM)
                        } else {
                            console.log(`[${timeString()}] Sending to Table Manager(2): ${line}`);
                            recordBidding(line);
                            recordPlay(line);
                            printTrick();
                            client.write(line + messageTerminator);
                            // Give TM time to process before sending next message
                            await waitDelay(parameters.delay);
                        }
                    }
                }
            }
            isProcessingLine = false;

            // Terminate the recursion when there's no more data to process
            if (!(receivedDataFromTM.includes('\r\n') || receivedDataFromTM.includes('\n') || receivedDataFromTM.endsWith('.') || receivedDataFromTM == "Dummy to lead" || receivedDataFromTM == `${parameters.seat} to lead` || receivedDataFromTM == "Start of Board")) {
                return;
            }
        }
        // Process the next line, if available
        await processLines();
    }
}

function connectToTM() {

    client.connect(parameters.port, parameters.ip, () => {
        console.log(`[${timeString()}] Connected to Table Manager`);
        console.log(`[${timeString()}] Sending to Table Manager: Connecting "${parameters.name}" as ${parameters.seat} using protocol version 18`);

        seating = util.format("%s %s seated",
            parameters.seat,
            parameters.name);
        // Create the formatted message
        const message = util.format(
            'Connecting "%s" as %s using protocol version 18\r\n',
            parameters.name,
            parameters.seat
        );
        client.write(message);
    });

    client.on('data', async (data) => {
        receivedDataFromTM += data.toString();

        if (!isProcessingLine) {
            await processLines();
        }
    });

    // Close the client socket when done
    client.on('close', async () => {
        console.log(`[${timeString()}] Connection closed by client`);
        await saveCommandHistory(false);
        processHolder.gibBackgroundProcess.kill();
        console.error('Press Enter to exit...');

        rl.question('', () => {
        });
        process.exit();
    });

    client.on('error', async (e) => {
        console.log(`[${timeString()}] Error from Table Manager: ${e.message}`);
        await saveCommandHistory(false);
        if (processHolder.GibHandler) {
            processHolder.GibHandler.close();
        }
        processHolder.gibBackgroundProcess.kill();
        console.error('Press Enter to exit...');

        rl.question('', () => {
        });
        process.exit();
    });
}


function newFunction() {
    let GIBCommandPart1 = `-${parameters.seat.charAt(0)}Ikr`;
    let GIBCommandPart2 = '1 2023';
    if (parameters.bidding) {
        GIBCommandPart1 += 'F';
    }
    if (parameters.timing > 0) {
        GIBCommandPart1 += 'T';
        GIBCommandPart2 += ' ' + parameters.timing;
    }
    if (parameters.oppquality != 0.5) {
        GIBCommandPart1 += 'o';
        GIBCommandPart2 += ' ' + parameters.oppquality;
    }
    if (parameters.speed != 500) {
        GIBCommandPart1 += 'e';
        GIBCommandPart2 += ' ' + parameters.speed;
    }
    if (parameters.gibson != 10) {
        GIBCommandPart1 += 'B';
        GIBCommandPart2 += ' ' + parameters.gibson;
    }
    if (parameters.simdecl != 50 || parameters.simdef != 50) {
        GIBCommandPart1 += 'm';
        GIBCommandPart2 += ' ' + parameters.simdecl + ' ' + parameters.simdef;
    }
    GIBCommand = GIBCommandPart1 + ' ' + GIBCommandPart2;
}

function displayUsage() {
    console.log(`Usage: node TMGib.exe [options]
Options:
  --seat, -s       Where to sit (North, East, South, West) [Mandatory]
  --name, -n       Name in Table Manager - default GIB
  --ip, -i         IP for Table Manager - default 127.0.0.1
  --port, -p       Port for Table Manager - default 2000
  --timing, -t     time (secs) for one GIB to play one board, on average - Default 60
  --bidding, -b    Tell GIB to use sys.ns sys.ew as input - default False
  --delay, -d      Delay between commands, default 100 ms
  --gibdir, -g     Directory where to find GIB executables - default ./GIB
  --simdecl, -m    number of deals to analyze to pick a play as declarer - default 50
  --simdef, -e     number of deals to analyze to pick a play as defender - default 50
  --speed, -z      how agressive GIB should be on system resources - default 500
  --gibson, -G     Tricks left when GIBSON kicks in - default 10
  --oppquality, -o opponents' bidding quality - 0 = weak; 1 = omniscient  - default 0.5
  --verbose, -v    Display commands issued to GIB and other interesting logging - default False`
  );
}

async function main() {

    console.log(`[${timeString()}] Table manager interface for GIB Version 1.0.15 starting.`)

    const argv = minimist(process.argv.slice(2), {
        string: ['seat', 'name', 'ip', 'port', 'timing', 'bidding', 'delay', 'gibdir', 'verbose', 'oppquality', 'simdecl', 'simdef', 'speed', 'gibson'],
        default: parameters, // Set the default values object directly
        alias: {
            s: 'seat',
            n: 'name',
            i: 'ip',
            p: 'port',
            t: 'timing',
            b: 'bidding',
            d: 'delay',
            g: 'gibdir',
            v: 'verbose',
            o: 'oppquality',
            m: 'simdecl',
            e: 'simdef',
            G: 'gibson',
            z: 'speed'
        },
        demandOption: ['seat'], // Specify the mandatory parameters
        unknown: (param) => {
            if (param === '--help') {
                displayUsage();
                process.exit(0);
            } else {
                console.log(`Unknown parameter: ${param}`);
                return false; // Stop processing
            }
        }
    });

    // Check if "--help" or no arguments are provided
    if (!argv.seat) {
        displayUsage();
        process.exit(1);
    }

    // Set parameters based on parsed arguments
    parameters.seat = argv.seat;
    if (parameters.seat.toUpperCase() != "NORTH" && parameters.seat.toUpperCase() != "EAST" && parameters.seat.toUpperCase() != "SOUTH" && parameters.seat.toUpperCase() != "WEST") {
        console.log(`[${timeString()}] Invalid seat: ${parameters.seat}`);
        displayUsage();
        process.exit(1);
    }
    parameters.name = argv.name;
    parameters.ip = argv.ip;
    parameters.port = argv.port;
    parameters.timing = argv.timing;
    parameters.bidding = argv.bidding;
    parameters.delay = argv.delay;
    parameters.verbose = argv.verbose;
    parameters.gibdir = argv.gibdir;
    if (parameters.verbose) {
        console.log(`[${timeString()}] Extended logging active`)
    }
    parameters.simdecl = argv.simdecl;
    parameters.simdef = argv.simdef;
    parameters.oppquality = argv.oppquality;
    parameters.speed = argv.speed;
    parameters.gibson = argv.gibson

    processHolder.GibHandler = await startGibProcess('bridge.exe', [parameters.seat + parameters.port], parameters.gibdir);
    await waitDelay(1000);
    console.log(`[${timeString()}] Started GIB. ${receivedDataFromGib.split('\n')[0]}`)
    receivedDataFromGib = "";
    newFunction();

    await processHolder.GibHandler.sendCommand(GIBCommand, true, false);
    await waitDelay(parameters.delay);

    console.log(`[${timeString()}] Connecting to Table Manager at ${parameters.ip}:${parameters.port} (as ${parameters.name} sitting ${parameters.seat})`);
    connectToTM();
};


main()

