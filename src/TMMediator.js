const createConnectionHandler = require('./connectionHandler');

function timeString() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    //return "";
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

console.log(`[${timeString()}] Table manager mediator for Blue Chip Bridge version 1.0.8 starting.`)

const bcPort1 = 2001;
const bmPort1 = 2000;
const handler1 = createConnectionHandler(bcPort1, bmPort1);
handler1.start();

const bcPort2 = 2002;
const bmPort2 = 2000; // Use the same bmPort if needed
const handler2 = createConnectionHandler(bcPort2, bmPort2);
handler2.start();

const bcPort3 = 2003;
const bmPort3 = 2000; // Use the same bmPort if needed
const handler3 = createConnectionHandler(bcPort3, bmPort3);
handler3.start();

const bcPort4 = 2004;
const bmPort4 = 2000; // Use the same bmPort if needed
const handler4 = createConnectionHandler(bcPort4, bmPort4);
handler4.start();

let completedHandlers = 0;

// Define a function to handle completion of a handler
function handleHandlerCompletion() {
    completedHandlers++;
    console.log('Handler closed');
    // Check if all handlers are completed
    if (completedHandlers === 4) {
        console.log('All handlers are done. Terminating...');
        process.exit();
    }
}

// Set up completion handlers for each handler
handler1.on('completed', handleHandlerCompletion);
handler2.on('completed', handleHandlerCompletion);
handler3.on('completed', handleHandlerCompletion);
handler4.on('completed', handleHandlerCompletion);

process.on('SIGINT', () => {
    console.log("Terminating...");
    handler1.stop();
    handler2.stop();
    handler3.stop();
    handler4.stop();
    process.exit();
});

