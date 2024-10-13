const fs = require('fs');
const { exec } = require('child_process');
const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');

// Constant for the Bridge Composer application path
const BRIDGE_COMPOSER_PATH = '"C:\\Program Files\\Bridge Club Software\\BridgeComposer\\BridgeComposer.exe"';
const SCRIPT_PATH = 'D:\\Bridge\\software\\Bridge Composer'; // Adjust this base directory as needed


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
        if (titleElement.length) {
            pageTitle = titleElement.text().trim(); // Extract and trim the title
            console.log('Page Title:', pageTitle); // Log the page title
            pageTitle = sanitizeFilename(pageTitle) + ".pbn"
        } else {
            console.log('Title not found.');
            pageTitle = "test.pbn"
        }

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

async function main() {
    // Check if a URL is passed as a command-line argument
    const webpageUrl = process.argv[2]; // Get the URL from the command line
    if (!webpageUrl) {
        console.error('Please provide a URL as a command-line argument.');
        process.exit(1); // Exit the program with an error code
    }    const currentDirectory = process.cwd();

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

    // Replace the line starting with %PipColors
    const newContent = content.split('\n').map(line => {
        // Check if the line starts with %PipColors
        if (line.startsWith('%PipColors')) {
            return '// %PipColors #0000ff,#ff0000,#ffc000,#008000'; // Replace with the new line
        }
        return line; // Return the original line if no match
    }).join('\n'); // Rejoin the lines to form the updated content

    console.log(`Content updated: ${filePath}`);
    // Write the updated content back to the file
    await fs.promises.writeFile(filePath, newContent);
    console.log(`File updated: ${filePath}`);
}

main();