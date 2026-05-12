const fs = require('fs');

const analysisFile = process.argv[2];
const apiFile = process.argv[3] || 'api_results.json';
const outputFile = 'merged_results.json';

try {
    const analysisData = JSON.parse(fs.readFileSync(analysisFile, 'utf8'));
    const apiData = JSON.parse(fs.readFileSync(apiFile, 'utf8'));

    // Βρίσκουμε τον επόμενο διαθέσιμο δείκτη για συναρτήσεις
    let nextFunIndex = Object.keys(analysisData.functions).length;

    for (const type in apiData) {
        for (const pattern in apiData[type]) {
            apiData[type][pattern].forEach(occurrence => {
                // Για κάθε εμφάνιση (occurrence), φτιάχνουμε ένα ΜΟΝΑΔΙΚΟ όνομα
                // Προσθέτουμε τη γραμμή (line) για να ξεχωρίζουν στον γράφο
                //προσθετω  ${nextFunIndex})`;
                const apiName = `NATIVE:${pattern} [Line: ${occurrence.start.line}] (ID: ${nextFunIndex})`;
            
                // Δημιουργούμε ΠΑΝΤΑ νέο index, δεν ψάχνουμε αν υπάρχει ήδη
                const apiIndex = nextFunIndex.toString();
                analysisData.functions[apiIndex] = apiName;
                nextFunIndex++;

                // Σύνδεση των callers με αυτό το συγκεκριμένο, μοναδικό node
                occurrence.callers.forEach(caller => {
                    const callerIdx = parseInt(caller.name);
                    if (!isNaN(callerIdx)) {
                        analysisData.fun2fun.push([callerIdx, parseInt(apiIndex)]);
                    }
                });
            });
        }
    }

    fs.writeFileSync(outputFile, JSON.stringify(analysisData, null, 2));
    console.log(`Merged ${analysisFile} and ${apiFile} into ${outputFile}`);

} catch (err) {
    console.error("Error:", err.message);
}

