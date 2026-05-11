const fs = require('fs');

const jsonFile = process.argv[2];
const outputFile = process.argv[3];
const templateFile = process.argv[4];

if (!jsonFile || !outputFile || !templateFile) {
    console.error("Usage: node generate_final_html.js <json> <output> <template_path>");
    process.exit(1);
}

try {
    const rawData = fs.readFileSync(jsonFile, 'utf-8');
    const template = fs.readFileSync(templateFile, 'utf-8');
    const analysisData = JSON.parse(rawData);

    // ΜΕΤΑΤΡΟΠΗ: Φτιάχνουμε τη δομή που περιμένει το visualizer.ts
    const visualizerFormat = {
        graphs: [{
            title: "Merged Call Graph (JS + Native)",
            kind: "callgraph",
            elements: [] // Θα το γεμίσει το script μέσα στο HTML
        }],
        // Περνάμε τα ωμά δεδομένα σε ένα δικό μας πεδίο για να τα επεξεργαστεί το HTML
        rawJellyData: analysisData 
    };

    const safeJsonData = JSON.stringify(visualizerFormat);
    const finalHtml = template.replace("$DATA", () => safeJsonData);

    fs.writeFileSync(outputFile, finalHtml);
    console.log("Generated successfully with Visualizer Format!");
} catch (err) {
    console.error("Error:", err.message);
}