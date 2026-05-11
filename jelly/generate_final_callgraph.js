const fs = require('fs');

const jsonFile = process.argv[2];
const outputFile = process.argv[3];
const templateFile = process.argv[4];

if (!jsonFile || !outputFile || !templateFile) {
    console.error("Usage: node generate_final_html.js <json> <output> <template_path>");
    process.exit(1);
}

//Το visualizer.ts περιμένει ένα συγκεκριμένο format για τα nodes και edges, οπότε πρέπει να μετατρέψω το merged_results.json σε αυτό το format.
try {
    const rawData = fs.readFileSync(jsonFile, 'utf-8');
    const template = fs.readFileSync(templateFile, 'utf-8');
    const data = JSON.parse(rawData);

    // Μετατροπή των functions σε Nodes
    const nodes = Object.keys(data.functions).map(id => ({
        data: {
            id: parseInt(id),
            name: data.functions[id],
            kind: data.functions[id].startsWith("NATIVE") ? "function" : "function",
            fullName: data.functions[id]
        }
    }));

    //Μετατροπή των fun2fun σε Edges
    const edges = data.fun2fun.map((edge, index) => ({
        data: {
            id: `e${index}`,
            source: edge[0],
            target: edge[1],
            kind: "call"
        }
    }));

    //Δημιουργία της δομής που περιμένει το Visualizer.ts 
    const visualizerData = {
        graphs: [{
            title: "Native Bridge Analysis (Merged)",
            kind: "callgraph",
            elements: [...nodes, ...edges]
        }]
    };

    const safeJsonData = JSON.stringify(visualizerData);

    // Χρήση substring αντί για replace για αποφυγή προβλημάτων με μεγάλα αρχεία
    const dataMarker = "$DATA";
    const i = template.indexOf(dataMarker);
    if (i === -1) throw new Error("Could not find $DATA marker in template");

    const finalHtml = template.substring(0, i) + safeJsonData + template.substring(i + dataMarker.length);

    fs.writeFileSync(outputFile, finalHtml);
    console.log(`Successfully generated ${outputFile} with ${nodes.length} nodes and ${edges.length} edges.`);

} catch (err) {
    console.error("Error:", err.message);
}