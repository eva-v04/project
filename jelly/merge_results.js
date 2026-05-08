const fs = require('fs');

const analysisFile = process.argv[2] || 'result.json';
const apiFile = 'api_results.json';
const outputFile = 'merged_results.json';

try {
    const analysisData = JSON.parse(fs.readFileSync(analysisFile, 'utf8'));
    const apiData = JSON.parse(fs.readFileSync(apiFile, 'utf8'));

    // Δημιουργούμε ένα Set με όλα τα API calls για να τα προσθέσουμε στο fun2fun
    // !Στο Jelly, το fun2fun είναι μια λίστα από πίνακες: [ [caller, callee], [caller, callee], ... ]
    
    for (const type in apiData) {
        for (const pattern in apiData[type]) {
            apiData[type][pattern].forEach(occurrence => {
                const apiName = `API:${pattern}`; // Το όνομα της native συνάρτησης

                occurrence.callers.forEach(caller => {
                    // Προσθέτουμε τη νέα κλήση στη λίστα fun2fun
                    // caller.name είναι το ID της JS συνάρτησης
                    //analysisData.fun2fun.push([caller.name, apiName]);
                    analysisData.fun2fun.push([caller.loc, apiName]);

                });
            });
        }
    }

    //  Προσθήκη των API ονομάτων στη λίστα των αρχείων ή των functions 
    
    fs.writeFileSync(outputFile, JSON.stringify(analysisData, null, 2));
    
    console.log(`Merged ${analysisFile} and ${apiFile} into ${outputFile}`);
    console.log(`Total calls in fun2fun now: ${analysisData.fun2fun.length}`);

} catch (err) {
    console.error("Error:", err.message);
}