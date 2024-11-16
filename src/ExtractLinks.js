const fs = require('fs');
const { exec } = require('child_process');
const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');
const readline = require('readline');

// Constant for the Bridge Composer application path
const BRIDGE_COMPOSER_PATH = '"C:\\Program Files\\Bridge Club Software\\BridgeComposer\\BridgeComposer.exe"';
const SCRIPT_PATH = 'D:\\Bridge\\software\\Bridge Composer'; // Adjust this base directory as needed

function timeString() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    //return "";
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

function dateString() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are 0-based
    const day = String(now.getDate()).padStart(2, '0');

    // Construct the date string in YYYYMMDD format
    return `${year}${month}${day}`;
}

function sanitizeFilename(title) {
    // Replace any character that is not a word character (alphanumeric & underscore) or space with an underscore
    return title.replace(/[<>:"\/\\|?*\x00-\x1F]/g, '_').trim().replace(/\s+/g, '_');
}
// Function to extract links
async function extractLinks(url) {
    var content = ""
    try {
        // Fetch the webpage
        const { data } = await axios.get(url);
        
        // Load the HTML into cheerio
        const $ = cheerio.load(data);

        // Extract the title from the <td> element
        const titleElement = $('td.bbo_tlv').first(); // Use .first() to get the first match
        var name1 
        var name2
        if (titleElement.length) {
            pageTitle = titleElement.text().trim(); // Extract and trim the title

            // Extract the usernames from the <th> elements with the class 'username'
            const usernames = [];
            $('th.username').each((index, element) => {
                usernames.push($(element).text().trim());
            });
            // Log the names to the console
            console.log(usernames);
            if (usernames.length == 2) {
                name1 = usernames[0]; // first name
                name2 = usernames[1]; // second name
                pageTitle = dateString() + "_" + name1 + "_" + name2
            } else {
                // Use a regular expression to capture the two names, ignoring the "Friend Challenge: " part
                const regex = /(\w+)\s*\/\s*(\w+)/;
                const match = pageTitle.match(regex);

                if (match) {
                    name1 = match[1]; // first name
                    name2 = match[2]; // second name
                    console.log("First name:", name1);
                    console.log("Second name:", name2);
                    pageTitle = dateString() + "_" + name1 + "_" + name2
                } else {
                    console.log("No match found.");
                }
            }
            console.log('Page Title:', pageTitle); // Log the page title
            console.log(pageTitle)
            pageTitle = sanitizeFilename(pageTitle) + ".pbn"
        } else {
            console.log('Title not found.');
            pageTitle = "test.pbn"
        }

        content = "vg|Robot Challenge,,MP,1,32,"+name1+",0,"+name2+",0|\n"
        var i = 0
        // Find all anchor tags and extract links
        $('a').each((_, element) => {
            const link = $(element).attr('href');
            
            if (link && link.includes('handviewer.html?')) {
                // Extract the part after 'lin='
                const linPart = link.split('lin=')[1];
            
                if (linPart) {
                    // Unescape the URL part after 'lin='
                    const unescapedLinPart = decodeURIComponent(linPart);
                    var tagRoom = (i % 2 === 0) ? 'O' : 'C';                
                    // Log or use the unescaped part as needed
                    //console.log("qx|"+tagRoom+(Math.floor(i / 2)+1)+"|"+unescapedLinPart);
                    content += "qx|"+tagRoom+(Math.floor(i / 2)+1)+"|"+unescapedLinPart + "\n"
                }
                i += 1
            }
        });
    } catch (error) {
        console.error('Error fetching or parsing the webpage:', error);
    }
    return {content, pageTitle}
}

function askForUrl() {
    return new Promise((resolve) => {
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        rl.question('Please enter the URL: ', (url) => {
            rl.close();
            resolve(url); // Resolve the promise with the user-provided URL
        });
    });
}

async function main() {
    // Check if a URL is passed as a command-line argument
    console.log(process.argv)
    var webpageUrl = process.argv[2]; // Get the URL from the command line
    if (!webpageUrl) {
        if (!webpageUrl) {
            webpageUrl = await askForUrl(); // Await the user input
            console.log(`You entered: ${webpageUrl}`);
        }
    }    
    
    const currentDirectory = process.cwd();

    console.log("Requesting", webpageUrl)
    // Run ExtractLinks logic and save to test.pbn
    const extractedContent = await extractLinks(webpageUrl);
    const outputFilePath = path.join(currentDirectory, extractedContent.pageTitle);

    fs.writeFile(outputFilePath, extractedContent.content, (err) => {
        if (err) {
            console.error('Error writing to file:', err);
        } else {
            console.log(`Output written to ${outputFilePath}`);
        }
    });

    // After saving the file, run the wscript command
    const formatMatchScriptPath = path.join(SCRIPT_PATH, 'FormatMatch.js');

    const wscriptCommand = `wscript "${formatMatchScriptPath}" "${outputFilePath}" -nq`;

    exec(wscriptCommand, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing wscript: ${error.message}`);
            return;
        }
        if (stderr) {
            console.error(`${stderr}`);
        }
        console.log(`${stdout}`);
        // After running wscript, update the output file content
        updateFileContent(outputFilePath)
            .then(() => {
                // Construct and execute the Bridge Composer command
                const bridgeComposerCommand = `${BRIDGE_COMPOSER_PATH} "${outputFilePath}"`;
                
                // Execute the command in detached mode
                const child = exec(bridgeComposerCommand, { detached: true });
                child.unref(); // Prevent waiting for the process to finish

                // exec(bridgeComposerCommand, (error, stdout, stderr) => {
                //     if (error) {
                //         console.error(`Error executing Bridge Composer: ${error.message}`);
                //         return;
                //     }
                //     if (stderr) {
                //         console.error(`stderr: ${stderr}`);
                //     }
                //     console.log(`Bridge Composer stdout: ${stdout}`);
                // });
            })
            .catch(err => console.error('Error updating file content:', err));
    });

    // %PipColors #0000ff,#ff0000,#ffc000,#008000

}

// Function to update the content of the file as needed
async function updateFileContent(filePath) {
    // Read the existing content
    let content = await fs.promises.readFile(filePath, 'utf8');

    const newContent = content
    .split('\n')
    .map(line => {
        // Replace the line starting with %PipColors
        if (line.startsWith('%PipColors')) {
            return '%PipColors #0000ff,#ff0000,#ffc000,#008000'; // Replace with the new line
        }
        // Skip the line if it matches '[Event ""]'
        if (line.startsWith('[Event ""]')) {
            return null; // Return null to indicate this line should be removed
        }
        if (line.startsWith('[Event "')) {
            line = line.replace('[Event "', '[Event "##');
            return line
        }
        return line; // Return the original line if no match
    })
    .filter(line => line !== null) // Filter out any null entries to delete them
    .join('\n'); // Rejoin the lines to form the updated content

    console.log(`Content updated: ${filePath}`);
    // Write the updated content back to the file
    await fs.promises.writeFile(filePath, newContent);
    console.log(`File updated: ${filePath}`);
}

console.log(`[${timeString()}] Extract challenge match from BBO as PBN. version 1.0.12 starting.`)

main();