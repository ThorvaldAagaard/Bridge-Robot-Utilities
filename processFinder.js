const { promisify } = require('util');
const exec = promisify(require('child_process').exec);

// Function to convert WMI date-time to JavaScript Date object
    function wmiDateToDate(wmiDate) {
        if (typeof wmiDate !== 'string') {
            return "Not a string";
        }

        const wmiDateRegex = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d{6})/;
        const matches = wmiDate.match(wmiDateRegex);

        if (!matches) {
            return null;
        }

        const year = parseInt(matches[1]);
        const month = parseInt(matches[2]) - 1;
        const day = parseInt(matches[3]);
        const hours = parseInt(matches[4]);
        const minutes = parseInt(matches[5]);
        const seconds = parseInt(matches[6]);
        const milliseconds = parseInt(matches[7]);

        return new Date(year, month, day, hours, minutes, seconds, milliseconds);
    }


module.exports = {
    getProcessesByName: async function (name) {
        const { stdout } = await exec(`powershell.exe -command "Get-WmiObject Win32_Process | Select-Object ProcessId, Name, CommandLine, CreationDate | Where-Object { $_.Name -eq '${name}' } | ConvertTo-Json"`);

        if (!stdout.trim()) {
            return []; // Return an empty array if no processes are found
        }
        
        const processes = JSON.parse(stdout);

        const processesArray = Array.isArray(processes) ? processes : [processes]; // Ensure it's an array

        for (const process of processesArray) {
            process.CreationDateNew = wmiDateToDate(process.CreationDate);
        }

        // Sort processes by CreationDate in ascending order
        processesArray.sort((a, b) => a.CreationDateNew.getTime() - b.CreationDateNew.getTime());

        return processesArray;
    },

    killProcessById: async function (processId) {
        const { stdout } = await exec(`taskkill /F /PID ${processId}`);
        return stdout;
    },

    wmiDateToDate: wmiDateToDate
};
