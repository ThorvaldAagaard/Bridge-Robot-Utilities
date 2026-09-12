// TMWbridge5 -- lets WBridge5 be started and seated automatically by a table manager.
//
// WBridge5 launched as `Wbridge5.exe Autoconnect <port>` connects on its own, but always
// announces itself as
//
//     Connecting "WBridge5" as ANYPL using protocol version 18
//
// ANYPL means "any player": WBridge5 does not choose a seat, it asks the table manager to
// assign one. There is no way to tell it which seat to take -- a third command line argument
// is ignored and the Table/seat keys in WBRIDGE5.INI have no effect on this.
//
// Bridge Moniteur handles that (bm17.r, Get-Client: it tests for "Any" in the seat and hands
// out the first vacant one). TMJob does not: its ProcessConnect takes exactly five characters
// after " as " and matches them against north/east/south/west, so it answers
//
//     Illegal hand 'anypl' specified
//
// and WBridge5 never gets seated. This program sits between the two and rewrites that one
// token. One listening port per seat, so the port WBridge5 is pointed at decides where it
// sits. Everything after the handshake is passed through byte for byte in both directions --
// WBridge5 accepts the table manager's own wording, including TMJob's
// `North ("WBridge5") seated`, so nothing else needs touching.
//
//     Wbridge5.exe Autoconnect 2010  ->  :2010 (here) -> table manager :2000  as North
//
// With --exe it also starts the WBridge5 instances itself, one per seat, and stops them again
// on exit -- then a match needs no manual step at all. They may all run from the same folder;
// --dir is only for giving the seats different WBRIDGE5.INI settings, such as a different
// bidding system for each pair.

const net = require('net');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const minimist = require('minimist');

const VERSION = '1.0.19';
const SEATS = ['North', 'East', 'South', 'West'];

const timeString = () => {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

const log = (message) => console.log(`[${timeString()}] ${message}`);

const parameters = {
    ip: '127.0.0.1',
    port: 2000,
    firstport: 2010,
    seats: 'North,East,South,West',
    name: '',
    exe: '',
    dir: '',
    verbose: false,
};

function usage() {
    console.log(`
TMWbridge5, Version ${VERSION}

Seats WBridge5 at a table manager that cannot handle its "ANYPL" connect message.

  --port, -p        Table manager port - default ${parameters.port}
  --ip, -i          Table manager IP - default ${parameters.ip}
  --firstport, -f   First port to listen on - default ${parameters.firstport}
  --seats, -s       Seats to serve, in port order - default ${parameters.seats}
  --name, -n        Team name to announce. One name, or NS/EW comma separated
                    (e.g. -n "WB5-NS,WB5-EW"). Default: leave WBridge5's own name
  --exe, -e         Path to Wbridge5.exe. When given, an instance is started per seat
  --dir, -d         Base folder for the started instances; each seat runs in <dir>\\<Seat>
  --verbose, -v     Log all traffic, both directions - default false
  --help, -h        This text

Point each WBridge5 at the port for the seat it should take:

  Wbridge5.exe Autoconnect ${parameters.firstport}      North
  Wbridge5.exe Autoconnect ${parameters.firstport + 1}      East
  Wbridge5.exe Autoconnect ${parameters.firstport + 2}      South
  Wbridge5.exe Autoconnect ${parameters.firstport + 3}      West

--dir is optional: WBridge5 only writes WBRIDGE5.INI back when a setting is changed,
so instances can share a folder. Use it when the seats need different settings --
WBRIDGE5.INI is where the bidding system is configured, so separate folders are what
let N/S and E/W play different systems.
`);
}

// ---------------------------------------------------------------- command line

const aliases = {
    p: 'port', i: 'ip', f: 'firstport', s: 'seats',
    n: 'name', e: 'exe', d: 'dir', v: 'verbose', h: 'help',
};

const argv = minimist(process.argv.slice(2), {
    string: ['ip', 'seats', 'name', 'exe', 'dir'],
    boolean: ['verbose', 'help'],
    alias: aliases,
});

if (argv.help) { usage(); process.exit(0); }

// minimist puts both spellings of an alias into argv, so the short forms are legal keys too.
const known = new Set([...Object.keys(parameters), ...Object.keys(aliases), 'help', '_']);
for (const key of Object.keys(argv)) {
    if (!known.has(key)) {
        console.error(`Unknown parameter '${key}'. Use --help for the list.`);
        process.exit(2);
    }
}
if (argv._.length > 0) {
    console.error(`Unexpected argument '${argv._[0]}'. Use --help for the list.`);
    process.exit(2);
}
for (const key of Object.keys(parameters)) {
    if (argv[key] !== undefined) parameters[key] = argv[key];
}

const seats = String(parameters.seats).split(',').map(s => s.trim()).filter(s => s.length > 0)
    .map(s => {
        const seat = SEATS.find(x => x.toLowerCase() === s.toLowerCase());
        if (!seat) { console.error(`Bad seat '${s}' -- expected ${SEATS.join(', ')}`); process.exit(2); }
        return seat;
    });
if (seats.length === 0) { console.error('No seats to serve.'); process.exit(2); }

const port = parseInt(parameters.port, 10);
const firstPort = parseInt(parameters.firstport, 10);
if (!Number.isInteger(port) || !Number.isInteger(firstPort)) {
    console.error('--port and --firstport must be numbers.');
    process.exit(2);
}

// One name, or two: the first for North/South, the second for East/West. A table manager may
// refuse two pairs that announce the same team name, and every WBridge5 announces "WBridge5",
// which is what blocks a WBridge5 against WBridge5 match.
const names = String(parameters.name).split(',').map(s => s.trim());
const teamFor = (seat) => {
    if (!parameters.name) return '';
    const nsew = (seat === 'North' || seat === 'South') ? 0 : 1;
    return names.length > 1 ? names[nsew] : names[0];
};

if (parameters.exe && !fs.existsSync(parameters.exe)) {
    console.error(`Wbridge5 executable not found: ${parameters.exe}`);
    process.exit(2);
}

// ---------------------------------------------------------------- the rewrite

// Applied to the handshake line only. "ANYPL" cannot legally appear anywhere else in the
// protocol, but scoping the rewrite to the first line keeps the play traffic untouched by
// construction rather than by luck.
function rewriteHandshake(line, seat, team) {
    let rewritten = line.replace(/ as ANYPL /i, ` as ${seat} `);
    if (team) rewritten = rewritten.replace(/Connecting\s+"[^"]*"/i, `Connecting "${team}"`);
    return rewritten;
}

// ---------------------------------------------------------------- the proxy

const servers = [];
const started = [];

function serve(listenPort, seat) {
    const team = teamFor(seat);

    const server = net.createServer(wb5 => {
        log(`${seat}: WBridge5 connected on port ${listenPort}`);
        const tm = net.connect(port, parameters.ip, () =>
            log(`${seat}: connected to table manager ${parameters.ip}:${port}`));

        let seated = false;
        let buffer = '';

        wb5.on('data', chunk => {
            if (seated) {
                if (parameters.verbose) process.stdout.write(`[${timeString()}] ${seat} WB5 > ${chunk}`);
                tm.write(chunk);
                return;
            }
            buffer += chunk.toString('ascii');
            const newlineIndex = buffer.indexOf('\n');
            if (newlineIndex === -1) return;               // handshake line not complete yet

            const terminator = buffer[newlineIndex - 1] === '\r' ? '\r\n' : '\n';
            const line = buffer.slice(0, newlineIndex).replace(/\r$/, '');
            const rest = buffer.slice(newlineIndex + 1);
            buffer = '';
            seated = true;

            const sent = rewriteHandshake(line, seat, team);
            log(`${seat}: WBridge5 sent '${line}'`);
            if (sent !== line) log(`${seat}: rewritten as  '${sent}'`);
            else log(`${seat}: no rewrite needed -- WBridge5 named its own seat`);

            tm.write(sent + terminator);
            if (rest.length > 0) tm.write(Buffer.from(rest, 'ascii'));
        });

        // Nothing to fix on the way back: WBridge5 accepts the table manager's own wording.
        tm.on('data', chunk => {
            if (parameters.verbose) process.stdout.write(`[${timeString()}] ${seat} TM  > ${chunk}`);
            wb5.write(chunk);
        });

        const closed = (who) => () => {
            log(`${seat}: ${who} closed the connection`);
            wb5.destroy();
            tm.destroy();
        };
        wb5.on('close', closed('WBridge5'));
        tm.on('close', closed('table manager'));
        wb5.on('error', error => console.error(`[${timeString()}] ${seat}: WBridge5 error: ${error.message}`));
        tm.on('error', error => console.error(`[${timeString()}] ${seat}: table manager error: ${error.message}`));
    });

    server.on('error', error => {
        console.error(`[${timeString()}] Cannot listen on port ${listenPort}: ${error.message}`);
        process.exit(1);
    });
    server.listen(listenPort, () =>
        log(`Listening on ${listenPort} for ${seat}${team ? ` (as "${team}")` : ''}`));

    servers.push(server);
}

// ---------------------------------------------------------------- starting WBridge5

function startWbridge5(listenPort, seat) {
    const folder = parameters.dir
        ? path.join(parameters.dir, seat)
        : path.dirname(parameters.exe);

    if (!fs.existsSync(folder)) {
        console.error(`[${timeString()}] ${seat}: folder does not exist: ${folder}`);
        process.exit(1);
    }

    const exe = parameters.dir
        ? (fs.existsSync(path.join(folder, path.basename(parameters.exe)))
            ? path.join(folder, path.basename(parameters.exe))
            : parameters.exe)
        : parameters.exe;

    const child = spawn(exe, ['Autoconnect', String(listenPort)], {
        cwd: folder,
        detached: false,
        stdio: 'ignore',
    });
    child.on('error', error =>
        console.error(`[${timeString()}] ${seat}: could not start WBridge5: ${error.message}`));
    started.push(child);
    log(`${seat}: started ${path.basename(exe)} Autoconnect ${listenPort} in ${folder}`);
}

// ---------------------------------------------------------------- go

log(`Table manager seat proxy for WBridge5 Version ${VERSION} starting.`);
log(`Table manager at ${parameters.ip}:${port}`);

seats.forEach((seat, index) => serve(firstPort + index, seat));

if (parameters.exe) {
    // Sharing one folder is fine -- WBridge5 only writes WBRIDGE5.INI back when a setting is
    // changed. --dir is for giving the seats different settings, not for keeping them apart.
    // A moment for the listeners to be up before anything tries to connect to them.
    setTimeout(() => seats.forEach((seat, index) => startWbridge5(firstPort + index, seat)), 500);
}

function stop() {
    log('Stopping.');
    for (const child of started) {
        try { child.kill(); } catch (error) { /* already gone */ }
    }
    for (const server of servers) server.close();
    process.exit(0);
}

process.on('SIGINT', stop);
process.on('SIGTERM', stop);
