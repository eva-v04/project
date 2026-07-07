import logger from "../misc/logger";
import {mapGetSet, locationToStringWithFileAndEnd, Location, SimpleLocation} from "../misc/util";
import {
   // AbbreviatedPathPattern,
    AccessPathPattern,
    CallResultAccessPathPattern,
    ComponentAccessPathPattern,
    ImportAccessPathPattern,
    PropertyAccessPathPattern
} from "./patterns";
import {isCallExpression, isNewExpression, isOptionalCallExpression, Node} from "@babel/types";
import {AccessPathPatternCanonicalizer} from "./patternparser";
import {AccessPath} from "../analysis/accesspaths";
import {FragmentState} from "../analysis/fragmentstate";


//import { globalNativeEdgesStore } from "./nativestore";


export type PatternType = "import" | "read" | "write" | "call" | "component";

export type AccessPathPatternToNodes = Record<PatternType, Map<AccessPathPattern, Set<Node>>>;
export type NodeToAccessPathPatterns = Record<PatternType, Map<Node, Set<AccessPathPattern>>>;
export type AccessPathString = string;
export type AccessPathPatternToLocations = Record<PatternType, Record<AccessPathString, Array<SimpleLocation & {filename: string}>>>;


//DEBUG
import {FunctionInfo, ModuleInfo} from "../analysis/infos";
//import { GlobalState } from "../analysis/globalstate";
// Map που συνδέει το ID του Node με μια λίστα από callers
//const nodeToCallers = new Map<number, Array<{name: string, loc: string}>>();


/**
 * Finds the usage of the API of external modules.
 */
export function getAPIUsage(f: FragmentState): [AccessPathPatternToNodes, NodeToAccessPathPatterns] {
    logger.info("Collecting API usage");
    const reached: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res1: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res2: NodeToAccessPathPatterns = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const c = new AccessPathPatternCanonicalizer;
    const worklist = new Map<AccessPathPattern, Set<AccessPath>>();

    function add(t: PatternType, p: AccessPathPattern, ap: AccessPath, n: Node) {
        //
        
       /* function sub(p: AccessPathPattern): AccessPathPattern | undefined {
            return p instanceof PropertyAccessPathPattern ? p.base :
                    p instanceof CallResultAccessPathPattern ? p.fun :
                        p instanceof ComponentAccessPathPattern ? p.component :
                            undefined;
        }

        function copyWithSub(as: AccessPathPattern, sub: AccessPathPattern): AccessPathPattern {
            if (as instanceof PropertyAccessPathPattern)
                return new PropertyAccessPathPattern(sub, as.props);
            else if (as instanceof CallResultAccessPathPattern)
                return new CallResultAccessPathPattern(sub);
            else if (as instanceof ComponentAccessPathPattern)
                return new ComponentAccessPathPattern(sub);
            else
                return as;
        }*/
        
        // abbreviate long patterns shortening του Jelly



        // ------
        let finalPathStr = p.toString();

        // Αν το path έρχεται ελλιπές από το Jelly (δηλαδή έχει μόνο το binding και τη μέθοδο)
        if ((finalPathStr.includes("binding") || finalPathStr.includes("bindings")) && 
            !finalPathStr.toLowerCase().includes("statement") && 
            !finalPathStr.toLowerCase().includes("database")) {
            
            // Εξετάζουμε τον AST Node για να βρούμε το όνομα της μεταβλητής (π.χ. stmt.finalize)
            if (n && (n.type === "CallExpression" || n.type === "OptionalCallExpression" || n.type === "MemberExpression")) {
                const callee = (n as any).callee || (n as any).object;
                
                if (callee && callee.type === "MemberExpression") {
                    const objName = callee.object?.name?.toLowerCase() || "";
                    const propName = callee.property?.name || "";

                    // Αν η μεταβλητή παραπέμπει σε Statement (π.χ. stmt, statement)
                    if (objName.includes("stmt") || objName.includes("statement")) {
                        const rootImport = new ImportAccessPathPattern("sqlite3-binding");
                        // Αναδομούμε το αντικείμενο p ΕΞΑΡΧΗΣ με τη σωστή δομή: Import -> Statement -> Μέθοδος
                        p = new PropertyAccessPathPattern(rootImport, ["Statement", propName || "finalize"]);
                    }
                    // Αν η μεταβλητή παραπέμπει σε Database (π.χ. db, database)
                    else if (objName.includes("db") || objName.includes("database")) {
                        const rootImport = new ImportAccessPathPattern("sqlite3-binding");
                        p = new PropertyAccessPathPattern(rootImport, ["Database", propName || "finalize"]);
                    }
                }
            }
        }
        // ------


        console.log('PATTERN BEFORE SHORTENING:', p.toString());
        console.log('ACCESS PATH:', ap.toString());

        // --- CUSTOM SHORTENING ΣΤΗΝ add (ΚΛΑΣΗ...ΜΕΘΟΔΟΣ) ---
        let currentPattern: AccessPathPattern = p;
        let depth = 0;
        let lastProp: string[] | undefined = undefined;
        let baseClassName: string | undefined = undefined;
        let rootImportPattern: AccessPathPattern | undefined = undefined;

        while (currentPattern) {
            console.log(`CURRENTPATTERN: currentPattern: ${currentPattern}, depth: ${depth}`);
            if (currentPattern instanceof PropertyAccessPathPattern) { //;
                if (depth === 0) {
                    lastProp = currentPattern.props;
                    //console.log(`LASTPROP: Found lastProp at depth 0: ${lastProp}`);
                }
                if (depth === 1 && currentPattern.props && currentPattern.props.length > 0) {
                    baseClassName = currentPattern.props[0];
                    //console.log(`BASECLASS: Found baseClassName at depth 1: ${baseClassName}`);
                }
                depth++;
                currentPattern = currentPattern.base;
                //console.log(`DEPTH: ${depth}, currentPattern: ${currentPattern}`);
            } else if (currentPattern instanceof CallResultAccessPathPattern) {
                depth++;
                currentPattern = currentPattern.fun;
            } else if (currentPattern instanceof ComponentAccessPathPattern) {
                depth++;
                currentPattern = currentPattern.component;
            } else if (currentPattern instanceof ImportAccessPathPattern) {
                rootImportPattern = currentPattern; 
                break;
            } else {
                break;
            }
        }

        if (depth >= 4 && rootImportPattern && lastProp) {
            if (baseClassName && baseClassName !== "prototype" && baseClassName !== "constructor") {
                // rootImportPatter = πχ sqlite3
                // Κρατάμε εσωτερικά το rootImportPattern για να μην κρασάρει ο αναλυτής,
                // αλλά στο flatProps βάζουμε ΜΟΝΟ την Κλάση (π.χ. Statement) και το Τέλος (π.χ. finalize)
                const flatProps = [baseClassName, ...lastProp];
                p = new PropertyAccessPathPattern(rootImportPattern, flatProps);
            } else {
                p = new PropertyAccessPathPattern(rootImportPattern, lastProp);
            }
        }
        // --- ΤΕΛΟΣ SHORTENING ---
        
        //

        // Καθαρισμός του pattern μέσω του canonicalizer (χωρίς abbreviations)
        p = c.canonicalize(p);
        
        const aps = mapGetSet(reached[t], p);
        if (!aps.has(n)) {
            if (logger.isDebugEnabled())
                logger.debug(`Found ${t} ${p} at ${locationToStringWithFileAndEnd(n.loc)}`);
            aps.add(n);

            function isReadAtCall(): boolean {
                if (t === "read") {
                    const m = f.callResultAccessPaths.get(ap);
                    if (m)
                        for (const f of m.keys())
                            if ((isCallExpression(f) || isOptionalCallExpression(f) || isNewExpression(f)) && f.callee === n)
                                return true;
                }
                return false;
            }

            if (isReadAtCall()) { 
                if (logger.isDebugEnabled())
                    logger.debug(`Read-call ${ap} at ${locationToStringWithFileAndEnd(n.loc)}`);
            } else {
                mapGetSet(res1[t], p).add(n);
                mapGetSet(res2[t], n).add(p);
            }
            mapGetSet(worklist, p).add(ap);
        }
    } // κλείνει σωστά η add

    // find imports
    for (const [ap, m] of f.moduleAccessPaths)
        for (const n of m.keys())
            add("import", c.canonicalize(new ImportAccessPathPattern(ap.moduleInfo.getOfficialName())), ap, n);

    // iteratively find property reads, writes, calls and components
    for (const [p, aps] of worklist)
        for (const ap of aps) {
            aps.delete(ap);
            if (aps.size === 0)
                worklist.delete(p);
            
            // property reads
            const m1 = f.propertyReadAccessPaths.get(ap);
            if (m1)
                for (const [prop, np] of m1)
                    for (const [n2, {bp}] of np)
                        add("read", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);
            
            // property writes
            const m2 = f.propertyWriteAccessPaths.get(ap);
            if (m2)
                for (const [prop, np] of m2)
                    for (const [n2, {bp}] of np)
                        add("write", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);

            // calls
            const m3 = f.callResultAccessPaths.get(ap);
            if (m3)
                for (const [n2, {bp}] of m3)
                    add("call", c.canonicalize(new CallResultAccessPathPattern(p)), bp, n2);

            // components
            const m4 = f.componentAccessPaths.get(ap);
            if (m4)
                for (const [n2, {bp}] of m4)
                    add("component", c.canonicalize(new ComponentAccessPathPattern(p)), bp, n2);
        }

    return [res1, res2];
}

export function reportAPIUsage(r1: AccessPathPatternToNodes, r2: NodeToAccessPathPatterns) { // TODO: split into two functions?
    logger.info("API usage, access path patterns -> nodes:");
    let numAccessPathPatterns = 0, numAccessPathPatternsAtNodes = 0;
    for (const [t, m] of Object.entries(r1)) {
        for (const [p, ns] of m) {
            logger.info(`${t} ${p}:`);
            for (const n of ns)
                logger.info(`  ${locationToStringWithFileAndEnd(n.loc)}`);
            numAccessPathPatternsAtNodes += ns.size;
        }
        numAccessPathPatterns += m.size;
    }
    logger.info(`Access path patterns: ${numAccessPathPatterns}, access path patterns at nodes: ${numAccessPathPatternsAtNodes}`);
}


//DEBUG
// Βοηθητική συνάρτηση για να καθαρίζει τους callers βάσει ΜΟΝΟ του Loc
function deduplicateCallers(callers: any[]): any[] {
    const seenLocs = new Set();
    return callers.filter(c => {
        const key = c.loc; 
        if (seenLocs.has(key)) return false;
        seenLocs.add(key);
        return true;
    });
}

// DEBUG
// Ορισμός ενός σταθερού counter για τις C συναρτήσεις
let cFunctionIdCounter = 9000; 

export function convertAPIUsageToJSON(r: AccessPathPatternToNodes, _?: any, f?: any): any {
    const res: any = {import: {}, read: {}, write: {}, call: {}, component: {}};

    //πίνακας που αποθηκεύει όλα τα matches για matches.json
    const allMatches: Array<{jelly_pattern: string, gasket_jsname: string, cfunc: string, confidence: number}> = [];

    
    const seenGlobalNodes = new Set<string>();

    for (const type of Object.getOwnPropertyNames(r) as Array<PatternType>) {
    const t: Record<string, any> = {};
    for (const [p, nodes] of r[type]) {
        const a: Array<any> = [];

        for (const n of nodes) {
            if (n.loc) {
                const loc = n.loc as Location;
                const locKey = locationToStringWithFileAndEnd(n.loc);
                const filename = loc.module?.getPath() || "";
                
                const dedupeKey = `${filename}:${loc.start.line}:${loc.start.column}:${type}`;

                let resolvedBaseStr = p.toString();
                
                // Καθαρίζουμε τα < >
                let cleanPath = resolvedBaseStr.replace(/[<>]/g, "");

                // Αν το module-part περιέχει slashes (λόγω του filename), απομονώνουμε το base name
                if (cleanPath.includes("/")) {
                    let pathParts = cleanPath.split(".");
                    if (pathParts[0].includes("/")) {
                    const slashParts = pathParts[0].split("/");
                    pathParts[0] = slashParts[slashParts.length - 1];
                }
                cleanPath = pathParts.join(".");
            }

            //  ΑΦΑΙΡΕΣΗ ΤΟΥ NATIVE/IMPORT ROOT (π.χ. sqlite3-binding, bindings)
            let pathTokens = cleanPath.split(".").map(s => s.trim()).filter(s => s.length > 0);
            if (pathTokens.length >= 2 && (pathTokens[0].includes("binding") || pathTokens[0] === "bindings" || pathTokens[0] === "sqlite3")) {
                pathTokens.shift(); // Αφαιρεί το πρώτο στοιχείο, αφήνοντας την κλάση/μέθοδο ως ρίζα
                }
            cleanPath = pathTokens.join(".");
            
            cleanPath = cleanPath
                .replace(/\.apply/g, "")
                .replace(/\.call/g, "")
                .replace(/\(\)/g, "")
                .replace(/\{([^}]+)\}/g, "$1") // Μετατρέπει το {map,apply} σε map,apply
                .replace(/\.{2,}/g, ".");

            // Αν περιέχει κόμμα από το destructing, κρατάμε μόνο την ουσιαστική μέθοδο
            if (cleanPath.includes(",")) {
                cleanPath = cleanPath.split(",")[0].trim();
            }

                // Το patternName που θα πάει στο Gasket Matching για να κάνει matching με bridges
                let patternName = `${type} ${cleanPath}`; 

                console.log('!DEBUG2 PATTERNANAME:', patternName);
                const callersList = f ? (f.nodeToCallers.get(locKey as any) || []) : [];
                const deduplicatedCallers = deduplicateCallers(callersList);

                const calleeName = `${loc.start.line}:${loc.start.column}:${loc.end.line}:${loc.end.column}`;
                const calleeLoc = `${filename}:${calleeName}`;
                

                    //Καταγραφή στο JSON output chunk
                    if (deduplicatedCallers.length === 0) {
                        const hasEdge = a.some(e => e.callee.loc === calleeLoc && e.caller === null);
                        if (!hasEdge) {
                            a.push({ callee: { name: calleeName, loc: calleeLoc }, caller: null });
                        }
                    } else {
                        for (const c of deduplicatedCallers) {
                            const hasEdge = a.some(e => e.callee.loc === calleeLoc && e.caller?.loc === c.loc);
                            if (!hasEdge) {
                                a.push({
                                    callee: { name: calleeName, loc: calleeLoc },
                                    caller: { name: c.name, loc: c.loc }
                                });
                            }
                        }
                    }

                    //  Ενημέρωση του Call Graph και Matching
                    if (!seenGlobalNodes.has(dedupeKey)) {
                        seenGlobalNodes.add(dedupeKey);

                        const targetModule = loc.module;
                        if (targetModule) {
                            console.log(patternName);

                            // Δυναμική φόρτωση του gasket json ΜΕΣΩ ENVIRONMENT VARIABLES
                            let gasketBridges: any[] = [];
                            try {
                                const fs = require("fs");
                                const path = require("path");
                                
                                // Διαβάζουμε τις μεταβλητές από το περιβάλλον (Environment)
                                const targetPackageFromCLI = process.env.PNAME; // π.χ. sharp
                                const targetVersionFromCLI = process.env.PVER;  // π.χ. 0.35.0
                                
                                // Καθαρό όνομα του τρέχοντος πακέτου που αναλύει η add αυτή τη στιγμή
                                const currentPackage = targetModule.getOfficialName().split('/')[0];
                                
                                if (!targetPackageFromCLI || !targetVersionFromCLI || currentPackage.toLowerCase() !== targetPackageFromCLI.toLowerCase()) {
                                    gasketBridges = [];
                                } else {
                                    const staticDir = "/home/eva/Ptuxiakh/web/static/";
                                    
                                    // Σχηματίζουμε το ακριβές όνομα του φακέλου
                                    const exactFolderName = `gasket_analysis_${targetPackageFromCLI.toLowerCase()}_${targetVersionFromCLI}`;
                                    const jsonPath = path.join(staticDir, exactFolderName, `bridges_${targetPackageFromCLI.toLowerCase()}.json`);
                                    
                                    if (fs.existsSync(jsonPath)) {
                                        const raw = fs.readFileSync(jsonPath, "utf-8");
                                        const parsed = JSON.parse(raw);
                                        gasketBridges = parsed.bridges || [];
                                    } else {
                                        // Fallback σε latest
                                        const latestFolderName = `gasket_analysis_${targetPackageFromCLI.toLowerCase()}_latest`;
                                        const fallbackPath = path.join(staticDir, latestFolderName, `bridges_${targetPackageFromCLI.toLowerCase()}.json`);
                                        if (fs.existsSync(fallbackPath)) {
                                            const raw = fs.readFileSync(fallbackPath, "utf-8");
                                            const parsed = JSON.parse(raw);
                                            gasketBridges = parsed.bridges || [];
                                        } else {
                                            logger.warn(`[GASKET CLI] Could not find bridges file at: ${jsonPath}`);
                                        }
                                    }
                                }
                            } catch (e: any) {
                                logger.warn(`[GASKET CLI] Failed to load bridges using Env Vars: ${e.message}`);
                            }

                            // Δίνουμε το p.toString() (ολόκληρο) για να κουμπώνουν οι ακμές στα full paths των αποτελεσμάτων
                            const nativeCalleeInfo = f.a.registerNativeFunctionInfo(targetModule, n, p.toString());
                            
                            if (deduplicatedCallers.length === 0) {
                                f.registerRealNativeCallEdge(n, targetModule, nativeCalleeInfo);
                            } else {
                                for (let i = 0; i < deduplicatedCallers.length; i++) {
                                    let jsCallerInfo: FunctionInfo | ModuleInfo = targetModule;
                                    for (const fun of f.a.functionInfos.values()) {
                                        if (fun.loc && fun.moduleInfo === targetModule && !fun.isNative) {
                                            if (n.loc.start.line >= fun.loc.start.line && n.loc.end.line <= fun.loc.end.line) {
                                                jsCallerInfo = fun;
                                                break;
                                            }
                                        }
                                    }
                                    f.registerRealNativeCallEdge(n, jsCallerInfo, nativeCalleeInfo);
                                }
                            }

                            // C-BRIDGE MATCHING ΛΟΓΙΚΗ
                            console.log(`[DEBUG GASKET] Checking ${patternName} against ${gasketBridges.length} bridges`);
                            // Περνάμε και το allMatches ως 3ο όρισμα
                            const matchedCfunc = findGasketCfuncMatch(patternName, gasketBridges, allMatches);
                            if (matchedCfunc) {
                                (nativeCalleeInfo as any).cfunc = matchedCfunc;
                                (nativeCalleeInfo as any).hasCBridge = true;

                                const cFuncName = `[C Function] ${matchedCfunc}`;
                                
                                // Αναζήτηση αν υπάρχει ήδη η C συνάρτηση καταγεγραμμένη καθολικά
                                const artificialStrKey = `CFunctionNode:${matchedCfunc}`;
                                let cFuncInfo = f.a.functionInfos.get(artificialStrKey);

                                if (!cFuncInfo) {
                                    cFuncInfo = new FunctionInfo(cFuncName, n.loc!, targetModule, false, true);
                                    
                                    // Ανάθεση σταθερού, μοναδικού ID που δεν επηρεάζεται από το μέγεθος των maps
                                    (cFuncInfo as any).id = String(cFunctionIdCounter++);
                                    
                                    targetModule.functions.add(cFuncInfo);
                                    f.a.functionInfos.set(artificialStrKey, cFuncInfo);
                                    
                                    if (f.functions) f.functions.add(cFuncInfo);
                                }

                                // Διασφάλιση σύνδεσης της Native JS με τη C Function
                                f.registerRealNativeCallEdge(n, nativeCalleeInfo, cFuncInfo);

                                // Εξαναγκασμός του exporter να συμπεριλάβει την ακμή
                                const callEdges = mapGetSet(f.callToFunction, n);
                                callEdges.add(cFuncInfo);
                            }
                        }
                    }
                }
            }
            t[p.toString()] = a; //βάζει αρχικό access path στα αποτελέσαμτα
            //t[patternName] = a; //κομμένο access path
        }
        res[type] = t;
    }
    //για matches.json
    try {
        const fs = require("fs");
        const path = require("path");
        const targetPackage = (process.env.PNAME || "unknown").toLowerCase();
        
        // Το αρχείο θα αποθηκεύεται στον φάκελο jelly
        const outputPath = path.join(__dirname, `../../${targetPackage}_matches.json`);
        
        fs.writeFileSync(outputPath, JSON.stringify(allMatches, null, 2), "utf-8");
        console.log(`\n SUCCESS: All native matches exported to ${outputPath}\n`);
    } catch (err: any) {
        console.error(`[ERROR EXPORTING MATCHES] ${err.message}`);
    }
    return res;
}

function levenshteinDistance(s1: string, s2: string): number {
    const m = s1.length, n = s2.length;
    const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (s1[i - 1] === s2[j - 1]) dp[i][j] = dp[i - 1][j - 1];
            else dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + 1);
        }
    }
    return dp[m][n];
}

function extractStructuralTokens(fqnString: string): string[] {
    //  Αφαιρούμε τα προθέματα τύπων (call, write, read, κλπ) από την αρχή του string
    let s = fqnString.replace(/^(call|write|read|import|component)\s+/, "");

    //Αντικαθιστούμε τις 3 τελείες με απλή τελεία πριν το split
    s = s.replace(/\.\.\./g, ".");
    s = s.replace(/…/g, ".");

    s = s.replace(/^<[^>]+>(\(\))?/, "");

    if (s.includes("/")) {
        const parts = s.split("/");
         s = parts[parts.length - 1];
    }

    s = s.replace(/\(\)/g, "")
         .replace(/\.prototype/g, "")
         .replace(/\.GET/g, "") 
         .replace(/\.SET/g, "");

    let tokens = s.split(".").map(t => t.trim().toLowerCase()).filter(t => t.length > 0);

    const garbageTokens = new Set(["apply", "node_sqlite3"]);
    tokens = tokens.filter(t => !garbageTokens.has(t));

    return tokens;
}

//προσθέτω το allMatches ως 3ο όρισμα για το matches.json
function findGasketCfuncMatch(jellyPattern: string, gasketBridges: any[], allMatches: any[]): string | undefined {
    const cleanJellyPattern = jellyPattern.replace(/^native:/, "");
    const jTokens = extractStructuralTokens(cleanJellyPattern);
    if (jTokens.length === 0) return undefined;

    let bestMatch: any = null;
    let highestSimilarity = 0;
    const threshold = 0.95; //!confidence

    // Ελέγχουμε αν το Jelly έχασε το base object (π.χ. ["get", "get"] -> μοναδικό token "get")
    const uniqueJellyTokens = Array.from(new Set(jTokens));
    const isDegeneratePattern = uniqueJellyTokens.length === 1;
    const degenerateMethod = uniqueJellyTokens[0]; // π.χ. "get", "run", "all"

    for (const bridge of gasketBridges) {
        if (!bridge.jsname) continue;
        
        const gTokens = extractStructuralTokens(bridge.jsname);
        if (gTokens.length === 0) continue;

        //ΓΙΑ  ΧΑΜΕΝΑ PATTERNS
        if (isDegeneratePattern) {
            const lastGasketToken = gTokens[gTokens.length - 1];
            if (lastGasketToken === degenerateMethod) {
                
                    bestMatch = bridge;
                    highestSimilarity = 1.0;
                    break; 
              
            }
            continue; // Πάμε στην επόμενη γέφυρα αν δεν ταιριάζει
        }

        // Κλασικός έλεγχος Levenshtein για  patterns
        const jCleanStr = jTokens.join("");
        const gCleanStr = gTokens.join("");

        const maxLen = Math.max(jCleanStr.length, gCleanStr.length);
        if (maxLen === 0) continue;
        const distance = levenshteinDistance(jCleanStr, gCleanStr);
        const similarity = 1 - distance / maxLen;

        if (similarity === 1.0) {
            highestSimilarity = 1.0;
            bestMatch = bridge;
            break; 
        }

        if (similarity > threshold && similarity > highestSimilarity) {
            highestSimilarity = similarity;
            bestMatch = bridge;
        }
    }

    if (bestMatch) {
        console.log(` [MATCH DETECTED]`);
        
        // Προσθήκη στο allMatches για το matches.json
        allMatches.push({
            "jelly_pattern": jellyPattern,
            "gasket_jsname": bestMatch["jsname"],
            "cfunc": bestMatch["cfunc"],
            "confidence": Number(highestSimilarity.toFixed(2))
        });

        console.log(JSON.stringify({
            "jelly_pattern": jellyPattern,
            "gasket_jsname": bestMatch["jsname"],
            "cfunc": bestMatch["cfunc"],
            "confidence": Number(highestSimilarity.toFixed(2))
        }, null, 2));
        console.log("--------------------------------------------------");

        return bestMatch.cfunc; 
    }

    return undefined;
}